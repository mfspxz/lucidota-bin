#!/usr/bin/env bash
# verify-receipt.sh — verify a signed full-send lane receipt before boarding.
#
# Checks (ALL must pass):
#   1. The file is a valid lucidota-receipt/1 envelope with a good authority sig
#      (via `pl envelope op=verify` — the existing envelope verifier).
#   2. Anti-replay: payload.wave matches the wave directory the file was found
#      in, and payload.lane matches the filename (<lane>.done.json).
#   3. payload.status is one of done|failed|blocked; payload.ts is present.
#
# Usage: verify-receipt.sh <receipt.done.json>
# Exit 0 = ACCEPT (prints payload JSON to stdout for the driver).
# Exit 1 = REJECT (reason on stderr). Exit 2 = usage/tooling error.
#
# This is what closes RT-SWEEP-2026-10-08-002: the hook and driver run this
# before boarding any lane verdict. Unsigned, tampered, or replayed receipts
# are rejected here — forging a verdict now requires the authority key, not
# just workspace write access.
set -euo pipefail

PL_BIN="${PL_BIN:-$HOME/workspace/proof-ledger/rs/target/debug/pl}"

if [ "$#" -ne 1 ]; then
  echo "usage: verify-receipt.sh <receipt.done.json>" >&2
  exit 2
fi
RECEIPT="$1"

[ -x "$PL_BIN" ] || { echo "verify-receipt: pl binary not executable at $PL_BIN" >&2; exit 2; }
[ -f "$RECEIPT" ] || { echo "verify-receipt: not found: $RECEIPT" >&2; exit 2; }

# 1. Envelope signature verification (fail-closed on missing/bad key too).
if ! "$PL_BIN" envelope op=verify "file=$RECEIPT" >/dev/null 2>&1; then
  echo "verify-receipt: REJECT $RECEIPT: envelope signature invalid or missing" >&2
  exit 1
fi

# 2+3. Anti-replay binding + payload sanity, via python (no key material touched).
python3 - "$RECEIPT" <<'PY'
import json, sys, os, re
path = sys.argv[1]
env = json.load(open(path))
p = env.get("payload", {})
# expected wave = parent dir name, expected lane = filename minus .done.json
wave_dir = os.path.basename(os.path.dirname(path))
fname = os.path.basename(path)
m = re.fullmatch(r"(.+)\.done\.json", fname)
if not m:
    sys.exit(f"REJECT: filename {fname!r} is not <lane>.done.json")
lane_file = m.group(1)
problems = []
if p.get("wave") != wave_dir:
    problems.append(f"payload.wave {p.get('wave')!r} != directory {wave_dir!r} (replay?)")
if p.get("lane") != lane_file:
    problems.append(f"payload.lane {p.get('lane')!r} != filename lane {lane_file!r}")
if p.get("status") not in ("done", "failed", "blocked"):
    problems.append(f"payload.status {p.get('status')!r} not done|failed|blocked")
if not p.get("ts"):
    problems.append("payload.ts missing (no freshness element)")
if not env.get("ts"):
    problems.append("envelope.ts missing")
if problems:
    sys.exit("REJECT: " + "; ".join(problems))
# ACCEPT: emit the payload for the driver.
print(json.dumps(p))
PY
