"""reaction_analogy (Route A) — Reaction Analogy Transfer Engine.

RA-M1 scope: RA-0 donor reaction corpus v1 + RA-1 similarity-retrieval pilot.

Iron rules (PLAN.md §5):
  - fail-closed: missing/unparseable data is reported, never invented
  - RED tests first, then implementation green
  - deterministic double-run, byte-identical (sha256)
  - read-only vs demov2/demov3/reaction_v3; work + commit only inside this repo
  - answer isolation: the restricted accepted-products file is never read
"""