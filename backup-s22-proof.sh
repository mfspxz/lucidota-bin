#!/bin/bash
# backup-s22-proof.sh — S22-proof backup, tiers 0+1. No network, no new creds.
# Tier 0: irreplaceable state (ledger, memory, identity, key workspace dirs).
# Tier 1: git bundles (full clone-in-a-file, no remote required).
# Build artifacts (target/, .venv, node_modules, model weights) are excluded:
# they are reproducible and would balloon the backup 10x.
# Off-VM distribution (R2 / git push) needs Zackary's rotated creds — see
# ~/workspace/BACKUP-PROTOCOL.md. Until then, bundles are push-ready.
set -euo pipefail
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST="$HOME/workspace/backups/$STAMP"
mkdir -p "$DEST/git" "$DEST/state"
chmod 700 "$HOME/workspace/backups"

echo "== tier 1: git bundles =="
for r in "$HOME"/workspace/*/; do
  if [ -d "$r/.git" ]; then
    name=$(basename "$r")
    if git -C "$r" bundle create "$DEST/git/$name.bundle" --all >/dev/null 2>&1; then
      echo "  bundled $name"
    else
      echo "  SKIP $name (bundle failed)"
    fi
  fi
done

echo "== tier 0: home state =="
tar -czf "$DEST/state/home-state.tgz" -C "$HOME" \
  MEMORY.md USER.md IDENTITY.md SOUL.md AGENTS.md TOOLS.md ledger memory 2>/dev/null || true

echo "== tier 0: workspace state =="
tar -czf "$DEST/state/workspace-state.tgz" -C "$HOME/workspace" \
  --exclude='*/target' --exclude='*/.venv' --exclude='*/node_modules' \
  --exclude='*/__pycache__' --exclude='*.gguf' --exclude='*.pt' \
  --exclude='*.bin' --exclude='*.safetensors' --exclude='*.onnx' \
  heartbeat keys proof-ledger compute exchange adhkey canon ledger-graph eventd 2>/dev/null || true

echo "== manifest =="
(cd "$DEST" && find . -type f ! -name MANIFEST.sha256 | sort | xargs sha256sum > MANIFEST.sha256)

echo "== rotation (keep 4) =="
ls -dt "$HOME"/workspace/backups/*/ 2>/dev/null | tail -n +5 | xargs -r rm -rf || true

echo "backup $STAMP done: $(du -sh "$DEST" | cut -f1)"
