#!/usr/bin/env bash
# sign-receipt.sh — wrap a full-send lane receipt in a lucidota-receipt/1 envelope.
#
# Lane receipts are authenticity-critical (RT-SWEEP-2026-10-08-002): an unsigned
# .done.json is forgeable by any workspace-write-capable process. This script
# seals the receipt with the authority key via the EXISTING envelope code
# (proof-ledger/rs/src/envelope.rs) — no second envelope format.
#
# Usage: sign-receipt.sh <payload.json> <lane> <wave> [out.done.json]
#   payload.json : the inner receipt {lane, wave, status, summary, evidence_paths[], gates_moved[], next_gaps[]}
#   lane/wave    : must match payload.lane / payload.wave (anti-replay binding)
#   out.done.json: destination (default: stdout)
#
# The script adds "ts" (RFC3339 UTC) to the payload if absent, then calls:
#   pl envelope op=wrap actor=lucidota/<lane> claim_id=fullsend:<wave>/<lane> status=claimed payload='<json>'
#
# Fail-closed: exits non-zero if the authority key is unavailable, the payload
# is malformed, or lane/wave mismatch. NEVER logs key material.
set -euo pipefail

PL_BIN="${PL_BIN:-$HOME/workspace/proof-ledger/rs/target/debug/pl}"

if [ "$#" -lt 3 ]; then
  echo "usage: sign-receipt.sh <payload.json> <lane> <wave> [out.done.json]" >&2
  exit 2
fi
PAYLOAD="$1"; LANE="$2"; WAVE="$3"; OUT="${4:-/dev/stdout}"

[ -x "$PL_BIN" ] || { echo "sign-receipt: pl binary not executable at $PL_BIN" >&2; exit 3; }
[ -f "$PAYLOAD" ] || { echo "sign-receipt: payload file not found: $PAYLOAD" >&2; exit 3; }

# Normalize payload: verify lane/wave match, inject ts if absent.
NORMED="$(mktemp)"
trap 'rm -f "$NORMED"' EXIT
python3 - "$PAYLOAD" "$LANE" "$WAVE" "$NORMED" <<'PY'
import json, sys, datetime
payload_path, lane, wave, out = sys.argv[1:5]
with open(payload_path) as f:
    p = json.load(f)
if not isinstance(p, dict):
    sys.exit("payload must be a JSON object")
if p.get("lane") != lane:
    sys.exit(f"payload.lane {p.get('lane')!r} != {lane!r}")
if p.get("wave") != wave:
    sys.exit(f"payload.wave {p.get('wave')!r} != {wave!r}")
if p.get("status") not in ("done", "failed", "blocked"):
    sys.exit(f"payload.status must be done|failed|blocked, got {p.get('status')!r}")
if "ts" not in p:
    p["ts"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with open(out, "w") as f:
    json.dump(p, f)
PY

PAYLOAD_JSON="$(cat "$NORMED")"
# Wrap in the envelope. The envelope code reads the authority key from
# $PL_SIG_KEY or ~/workspace/keys/PL_SIG_KEY (mode 600) and fails closed
# without it. Key material never appears in argv here beyond the file path.
"$PL_BIN" envelope op=wrap \
  "actor=lucidota/$LANE" \
  "claim_id=fullsend:$WAVE/$LANE" \
  status=claimed \
  "payload=$PAYLOAD_JSON" > "$OUT"
echo "sign-receipt: sealed $WAVE/$LANE -> $OUT" >&2
