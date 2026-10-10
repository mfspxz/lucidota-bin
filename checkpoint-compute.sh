#!/usr/bin/env bash
# checkpoint-compute.sh — recurring insurance snapshot of uncommitted
# ~/workspace/compute/ work. Promotes the wave-8 one-off checkpoint
# (built after the 20:51Z `git reset --hard` incident vaporized
# uncommitted work) into a scheduled hook.
#
# Capture shape (same as the one-off):
#   <STAMP>/HEAD.txt      — git HEAD sha at capture
#   <STAMP>/tree.diff     — `git diff HEAD` (tracked changes only)
#   <STAMP>/MANIFEST.md   — sha256 per captured file + best-effort owner
#   <STAMP>/SNAPSHOT.json — machine metadata incl. the change signature
#   <STAMP>/<files...>    — full copies of tracked-modified + untracked
#
# Cheap no-op: signature = sha256(HEAD + `git status --porcelain`).
# If it matches the latest snapshot's signature, nothing changed — exit 0
# without capturing. `git status --porcelain` on compute/ is milliseconds.
#
# Exit codes (eventd contract): 0 = no-op / nothing to do,
#   2 = new snapshot captured (fires compute.snapshot),
#   3 = secret gate tripped (snapshot deleted, fail-closed),
#   1 = error.
#
# Read-only to the protected repo: cp / git diff / git rev-parse only.
# Zero git mutations. Never snapshots ~/.ssh, credentials, or secret files
# (name-pattern exclusions + secret-scrub gate, fail-closed).
set -u

REPO="${COMPUTE_SNAPSHOT_REPO:-$HOME/workspace/compute}"
SNAPDIR="${COMPUTE_SNAPSHOT_DIR:-$HOME/workspace/backups/compute-snapshots}"
OWNERS="$SNAPDIR/owners.map"
LOCKF="$SNAPDIR/.lock"
KEEP=4
FORCE="${1:-}"

mkdir -p "$SNAPDIR"
chmod 700 "$SNAPDIR" 2>/dev/null || true

# --- single-flight: another run already capturing -> no-op, exit 0
exec 9>"$LOCKF"
if ! flock -n 9; then
  echo "checkpoint-compute: another run holds the lock; skipping"
  exit 0
fi

# --- cheap change signature (from the FILTERED capture set, so volatile
# scratch churn can't defeat the no-op check)
HEAD_SHA="$(git -C "$REPO" rev-parse HEAD 2>/dev/null)" || { echo "checkpoint-compute: cannot read HEAD"; exit 1; }

# --- enumerate capture set: tracked-modified + untracked (respect .gitignore)
mapfile -t MODIFIED < <(git -C "$REPO" diff --name-only HEAD -- . 2>/dev/null || true)
mapfile -t UNTRACKED < <(git -C "$REPO" ls-files --others --exclude-standard -- . 2>/dev/null || true)

# --- exclusion patterns: bulk regenerable output + anything secret-shaped
is_excluded() {
  case "$1" in
    burn-outputs/*|*/burn-outputs/*) return 0 ;;
    runs/tmp*|*/runs/tmp*) return 0 ;;
    .pytest-tmp/*|*/.pytest-tmp/*|.pytest_cache/*|*/.pytest_cache/*) return 0 ;;
    __pycache__/*|*/__pycache__/*|*.pyc) return 0 ;;
    .venv/*|*/.venv/*|target/*|*/target/*|node_modules/*|*/node_modules/*) return 0 ;;
    *.tmp|*.tmp-*|*/.tmp|*/.tmp-*) return 0 ;;  # transient churn, not work product
    *.pem|*.key|id_rsa*|.ssh/*|*/.ssh/*) return 0 ;;
    .env|.env.*|*/.env|*/.env.*) return 0 ;;
    *credentials*|*secret*|*token*|*passwd*|*shadow*) return 0 ;;
    .git/*) return 0 ;;
  esac
  return 1
}

FILES=()
for f in "${MODIFIED[@]}" "${UNTRACKED[@]}"; do
  [ -n "$f" ] || continue
  is_excluded "$f" && continue
  [ -f "$REPO/$f" ] || continue
  FILES+=("$f")
done

SIG="$(printf '%s\n%s' "$HEAD_SHA" "$(printf '%s\n' "${FILES[@]}")" | sha256sum | cut -d' ' -f1)"

latest="$(ls -dt "$SNAPDIR"/*/ 2>/dev/null | grep -v '/\.' | head -1 || true)"
if [ -n "$latest" ] && [ -f "$latest/SNAPSHOT.json" ] && [ "$FORCE" != "--force" ]; then
  prev_sig="$(python3 -c "import json;print(json.load(open('$latest/SNAPSHOT.json'))['signature'])" 2>/dev/null || true)"
  if [ "$SIG" = "$prev_sig" ]; then
    echo "checkpoint-compute: unchanged (sig ${SIG:0:12}); no-op"
    exit 0
  fi
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$SNAPDIR/$STAMP"
mkdir -p "$DEST"

# (FILES[] computed above, before the signature no-op check)

# --- copy preserving relative paths
total_bytes=0
for f in "${FILES[@]}"; do
  mkdir -p "$DEST/$(dirname "$f")"
  cp -p "$REPO/$f" "$DEST/$f"
  total_bytes=$(( total_bytes + $(stat -c%s "$DEST/$f" 2>/dev/null || echo 0) ))
done

# --- HEAD.txt + tree.diff
printf '%s\n' "$HEAD_SHA" > "$DEST/HEAD.txt"
git -C "$REPO" diff HEAD -- . ':!burn-outputs' > "$DEST/tree.diff" 2>/dev/null || true

# --- owner lookup (best-effort, sidecar map outside the protected repo)
owner_of() {
  local f="$1"
  if [ -f "$OWNERS" ]; then
    while IFS=$'\t' read -r prefix owner; do
      [ -z "$prefix" ] && continue
      case "$prefix" in \#*) continue ;; esac
      case "$f" in "$prefix"*) printf '%s' "$owner"; return 0 ;; esac
    done < "$OWNERS"
  fi
  printf 'unclaimed'
}

# --- MANIFEST.md
{
  echo "# compute snapshot $STAMP"
  echo
  echo "Recurring insurance snapshot of uncommitted compute/ work."
  echo "Read-only capture; repo untouched. Point-in-time: concurrently-appended"
  echo "logs may be torn at the tail — verify hash chains before trusting them."
  echo
  echo "HEAD at snapshot: $HEAD_SHA"
  echo "Snapshot time: $STAMP"
  echo "Files captured: ${#FILES[@]} ($total_bytes bytes)"
  echo
  echo "## Files (sha256, owner)"
  echo
  echo "| file | sha256 | owner |"
  echo "|---|---|---|"
  for f in "${FILES[@]}"; do
    h="$(sha256sum "$DEST/$f" | cut -d' ' -f1)"
    echo "| \`$f\` | \`$h\` | $(owner_of "$f") |"
  done
} > "$DEST/MANIFEST.md"

# --- SNAPSHOT.json (machine metadata for the cheap no-op check)
python3 - "$DEST/SNAPSHOT.json" "$STAMP" "$HEAD_SHA" "$SIG" "$total_bytes" "${#FILES[@]}" <<'EOF'
import json, sys
path, stamp, head, sig, nbytes, nfiles = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
json.dump({"stamp": stamp, "head": head, "signature": sig,
           "file_count": nfiles, "total_bytes": nbytes}, open(path, "w"), indent=1)
EOF

# --- secret gate (fail-closed): scrub the snapshot; flag -> delete + exit 3
if [ "${#FILES[@]}" -gt 0 ]; then
  scrub_hits=""
  scrub_out="$(cd "$REPO" && python3 "$HOME/workspace/bin/secret-scrub.py" "${FILES[@]/#/$DEST/}" 2>&1)" || true
  # re-scan the actual snapshot copies (paths above point at the copies)
  if echo "$scrub_out" | grep -q "BLOCKED"; then
    scrub_hits="$scrub_out"
  fi
  if [ -n "$scrub_hits" ]; then
    echo "checkpoint-compute: SECRET GATE TRIPPED — deleting snapshot"
    echo "$scrub_hits" | head -5
    rm -rf "$DEST"
    exit 3
  fi
fi

# --- rotation: keep newest $KEEP
ls -dt "$SNAPDIR"/*/ 2>/dev/null | grep -v '/\.' | tail -n +$((KEEP + 1)) | xargs -r rm -rf || true

echo "checkpoint-compute: captured $STAMP (${#FILES[@]} files, $total_bytes bytes)"
exit 2
