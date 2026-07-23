# ESM2 Domain-Adaptive Pre-training Plan (Path B)

Date: 2026-07-02
Status: PROPOSED — planning only, does not block P1 (P1 uses frozen M1 first)
Target repo paths:
  docs/reference_plans/ESM2_DAPT_PLAN_PATHB_20260702.md
  scripts/dapt/dapt_train.py
  scripts/dapt/dapt_export_embeddings.py

## 1. Goal

Build an enzyme-domain-specialized protein language model by continuing MLM
pre-training of ESM2 on our enzyme sequences. The resulting model replaces the
general ESM2-3B M1 feature with a domain-adapted feature that retains ESM2's
general protein knowledge while better representing enzyme-specific patterns.

Output: per-protein pooled embedding (replacement for M1) AND per-residue
embedding (new, residue-level feature). Both exported from the adapted model.

Critical constraint: the training objective is MLM (representation), NOT
classification. This is the direct fix for the M2 failure mode — M2 collapsed
because it was a task-specific classifier branch, not a general representation.

## 2. Base Model Selection

| Option | HF checkpoint | Params | Hidden | Aligns with | GPU cost | Recommend |
|---|---|---|---|---|---|---|
| B-3B | `facebook/esm2_t36_3B_UR50D` | 3B | 2560 | M1 (drop-in) | high | if HPC has 4+ A100/H100 |
| B-650M | `facebook/esm2_t33_650M_UR50D` | 650M | 1280 | EnzymeCAGE native esm_dim | 5x lower | cost-sensitive default |

Decision rule:

```
if HPC has >= 4 x A100-40G (or >= 2 x H100-80G):
    use B-3B  (drop-in replacement for M1, dim 2560)
else:
    use B-650M (dim 1280, EnzymeCAGE baseline already supports 1280)
```

Both use the same ESM2 tokenizer (BPE on amino acids). No custom tokenizer.

## 3. Data Preparation

Source sequences:

```
shard NPZ key `seqs` from gateF3 full export (195,743 enzymes)
+ optional: UniRef50 enzyme sequences (EC-annotated) to boost volume
```

Preprocessing pipeline:

```
1. extract seqs from shard NPZ -> all_enzymes.fasta
2. CD-HIT clustering, identity cutoff 0.9
   cd-hit -i all_enzymes.fasta -o dapt_seqs_090.fasta -c 0.9 -n 5 -d 0
3. length filter: keep 30 <= len <= 1022  (ESM2 max context = 1022 tokens)
4. random shuffle, hold out 5% as eval set (perplexity)
5. tokenize with EsmTokenizer, save as HF datasets (tokenized, on disk)
```

Expected volume after dedup: ~120k-150k sequences (sufficient for DAPT; the
literature shows domain-adaptive MLM is effective at 10^5 scale).

## 4. Training Setup

Framework: HuggingFace `transformers` + `accelerate` (FSDP or DDP).
Model class: `EsmForMaskedLM`.
Data collator: `DataCollatorForLanguageModeling(mlm=True, mlm_probability=0.15)`.

### 4.1 Full fine-tuning (B-3B, recommended if GPU allows)

```
precision : bfloat16
strategy  : FSDP (shard grad + sharded optimizer states)
lr        : 5e-5
warmup    : 10% of total steps
scheduler : cosine
epochs    : 3  (DAPT overfits fast on small data; do not exceed 5)
batch     : max_tokens 8192 per step (grad accumulation as needed)
mask_prob : 0.15
weight_decay : 0.01
max_len   : 1022
```

### 4.2 LoRA fallback (low-resource, single-GPU)

```
library   : peft
r         : 16
alpha     : 32
target    : query, value (ESM2 attention projections)
lr        : 1e-4
epochs    : 3
batch     : max_tokens 4096
precision : bfloat16
```

LoRA trains ~5x fewer optimizer states, single A100-40G feasible. Merge weights
before export.

## 5. Training Script Skeleton

`scripts/dapt/dapt_train.py`:

```python
import argparse
from datasets import load_from_disk
from transformers import (
    EsmForMaskedLM, EsmTokenizerFast,
    Trainer, TrainingArguments,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model   # comment out for full FT

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="facebook/esm2_t36_3B_UR50D")
    ap.add_argument("--data", required=True, help="path to tokenized dataset")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["full", "lora"], default="full")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--max_len", type=int, default=1022)
    args = ap.parse_args()

    tok = EsmTokenizerFast.from_pretrained(args.model)
    model = EsmForMaskedLM.from_pretrained(args.model, dtype="bfloat16")

    if args.mode == "lora":
        cfg = LoraConfig(r=16, lora_alpha=32, target_modules=["query","value"],
                         task_type="MLM")
        model = get_peft_model(model, cfg)

    ds = load_from_disk(args.data)
    collator = DataCollatorForLanguageModeling(tok, mlm=True,
                                               mlm_probability=0.15,
                                               max_length=args.max_len,
                                               padding="max_length")

    targs = TrainingArguments(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=32,
        learning_rate=args.lr,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        bf16=True,
        save_strategy="epoch",
        save_total_limit=3,
        logging_steps=20,
        report_to="none",
        # fsdp="full_shard auto_wrap"   # uncomment for full FT on 3B
    )

    trainer = Trainer(model=model, args=targs, train_dataset=ds["train"],
                      eval_dataset=ds["eval"], data_collator=collator)
    trainer.train()
    trainer.save_model(args.out)
    tok.save_pretrained(args.out)

if __name__ == "__main__":
    main()
```

## 6. Evaluation (Gate Before Adoption)

A model is adopted only if it passes ALL three:

```
G1  MLM perplexity on held-out eval set
    pass: adapted ppl < baseline (original ESM2) ppl on same eval set

G2  Step6 feature diagnostic on adapted embedding (mean pool)
    pass: effective_rank >= 600   (baseline M1 = 691.8)
          pairwise_cosine_mean <= 0.75  (baseline M1 = 0.711)
          (do NOT require strict improvement over M1; require non-degradation)

G3  Downstream proxy: train a 2-layer MLP on round1 train split,
    eval AUC on valid split. Compare adapted vs original-M1.
    pass: adapted AUC >= original-M1 AUC - 0.005 (non-inferiority)
```

If G1 passes but G2/G3 fail: the model learned MLM but not useful enzyme
representation. Try fewer epochs (overfit) or add more data. Do NOT ship.

If all fail: revert to M1-only (P1 proceeds with original M1, no loss).

## 7. Feature Export & Replacement

`scripts/dapt/dapt_export_embeddings.py` (sketch):

```python
# load adapted model + tokenizer
# for each UID in shard order:
#   tokenize seq, forward through EsmForMaskedLM.base_model (encoder only)
#   hidden = last_hidden_state            # (L, 2560) per-residue
#   pooled = mean(hidden, dim=0, mask)    # (2560,) per-protein
# write new shard NPZ with key:
#   embedding_pooled_vec_dapt  (2560,)   -- per-protein
#   embedding_per_residue      (L, 2560) -- per-residue (new, optional)
```

Naming: keep original `embedding_pooled_vec` (M1) intact; write DAPT features
under a new key so M1 and M1-DAPT can be A/B compared in Step6.

Replacement flow:

```
1. export M1-DAPT shards (new key embedding_pooled_vec_dapt)
2. run Step6 diagnostic on the new key (G2)
3. if pass: switch P1 config feature_key -> embedding_pooled_vec_dapt
4. if fail: keep feature_key = embedding_pooled_vec (original M1)
```

## 8. Rollback

DAPT is a pure feature-side experiment. If it fails evaluation, P1 continues
with the original M1-only plan (`P0_M1_ONLY_PLAN_20260702.md`). No downstream
code or split changes. Cost is only the HPC time spent on DAPT.

## 9. Resource & Cost Estimate

| Item | B-3B full FT | B-650M full FT | B-3B LoRA |
|---|---|---|---|
| GPUs | 4-8 x A100-40G | 1-2 x A100-40G | 1 x A100-40G |
| Time / epoch (est. 130k seqs) | ~3-5 h | ~1-1.5 h | ~2-3 h |
| Total (3 epochs) | ~10-15 h | ~3-5 h | ~6-9 h |
| Disk (ckpt) | ~12 GB (bf16) + optimizer | ~2.6 GB | ~12 GB (merged) |

Recommend running B-650M first as a cheap probe: if it passes G1-G3, the 3B
run may be unnecessary. If 650M fails G2/G3, then invest in 3B.

## 10. Risks

- Overfitting: 130k seqs vs 3B params. Mitigate with 3 epochs max + eval
  perplexity each epoch; keep the checkpoint with lowest eval ppl.
- Domain gap too small: our enzymes may already be well-represented in ESM2's
  UniRef50 pre-training, so DAPT gains little. G3 (downstream non-inferiority)
  is the real test; if M1 already passes G2, DAPT may not be worth it.
- Pooling mismatch: original M1 is pooled inside LucaProt's encoder. DAPT
  export uses plain mean-pool. This is fine — we replace the feature, not
  reproduce LucaPCycle's internal pooling.
- Classification objective trap: if anyone suggests "just fine-tune ESM2 on
  our enzyme classification task" — do NOT. That recreates the M2 failure.
  Stay on MLM.

## 11. Open Questions For HPC Side

1. GPU type and count available on the HPC account (decides B-3B vs B-650M).
2. Is CD-HIT installed, or install via conda?
3. Slurm partition name and max walltime for multi-GPU jobs.
```
