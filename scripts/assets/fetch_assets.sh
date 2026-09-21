#!/usr/bin/env bash
# 从仓库外拉回 assets_manifest.json 列出的数据/权重/产物，并校验 sha256。
#   A) rsync:  export ENZYMECAGE_ASSET_REMOTE="user@host:/path/to/assets"
#   B) HF:     export ENZYMECAGE_ASSET_HF_REPO="org/dataset-name"
set -euo pipefail
MANIFEST="${1:-assets_manifest.json}"
DEST="${ENZYMECAGE_ASSET_DEST:-$PWD}"
REMOTE="${ENZYMECAGE_ASSET_REMOTE:-}"
HF_REPO="${ENZYMECAGE_ASSET_HF_REPO:-}"

[ -f "$MANIFEST" ] || { echo "找不到清单 $MANIFEST"; exit 2; }

if [ -n "$HF_REPO" ]; then
  echo ">> 从 Hugging Face 拉取: $HF_REPO → $DEST"
  hf download "$HF_REPO" --repo-type dataset --local-dir "$DEST"
elif [ -n "$REMOTE" ]; then
  echo ">> 从远程 rsync: $REMOTE → $DEST"
  rsync -av --relative "$REMOTE/./" "$DEST/"
else
  echo "未设置 ENZYMECAGE_ASSET_REMOTE 或 ENZYMECAGE_ASSET_HF_REPO —— 见 ARTIFACTS.md" >&2
  exit 2
fi

echo ">> 校验 sha256"
python3 "$(dirname "$0")/verify_assets.py" "$MANIFEST"
