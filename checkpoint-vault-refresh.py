#!/usr/bin/env python3
"""checkpoint-vault-refresh.py — the ONLY authorized writer to the OOB checkpoint vault.

Owned by: eventd watch `checkpoint-refresh` (file watch on the falsification
chain, debounce 180s). Run as an eventd action subprocess — NEVER imported or
called by pipeline code.

What it does (exit codes are the eventd contract):
  0 — no-op: live tail seq already pinned by the latest vault bundle.
  2 — a new CHECKPOINT-*.json bundle was written (eventd emits checkpoint.refresh).
  1 — error or POLICY VIOLATION (eventd emits watch.error).

The refresh pins: falsification seq + head_hash + legacy_prefix_sha256,
and the proof-ledger entry count + head hash. verify() is run first and its
result is pinned HONESTLY in the bundle — a broken chain pins a broken claim,
never a clean one.

Write-path guard (policy, checked on every run before any write):
  no Python file under the pipeline source tree may reference the vault path.
  If one does, that is a write-path violation and the refresh REFUSES (exit 1).
  The vault directory itself stays 555 / files 444 (tripwire only — root walks
  straight through permission bits; measured 2026-10-10).

Usage: python3 checkpoint-vault-refresh.py [--force]
  --force: write a new bundle even if the tail seq is already pinned.
"""
import argparse
import glob
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
VAULT = HOME / "workspace" / "checkpoint-vault"
LOG = HOME / "workspace" / "compute" / "falsification.jsonl"
LEDGER = HOME / "workspace" / "proof-ledger" / "ledger.jsonl"
PIPELINE_CODE = HOME / "workspace" / "compute" / "pipeline"
COMPUTE_PKG = HOME / "workspace" / "compute"
SCHEMA = "oob-checkpoint/1"


def fail(msg: str) -> int:
    print(json.dumps({"ok": False, "error": msg}), file=sys.stderr)
    return 1


def write_path_guard() -> str | None:
    """Refuse if any pipeline Python file references the vault path."""
    needle = str(VAULT)
    hits = []
    for py in PIPELINE_CODE.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if needle in text or "checkpoint-vault" in text:
            hits.append(str(py))
    if hits:
        return ("write-path violation: pipeline code references the "
                f"checkpoint vault: {hits[:5]}")
    return None


def log_tail() -> tuple[int, str]:
    lines = [ln for ln in LOG.read_text(encoding="utf-8").split("\n") if ln.strip()]
    tail = json.loads(lines[-1])
    return int(tail["seq"]), str(tail["entry_hash"])


def latest_bundle() -> tuple[Path | None, dict | None]:
    bundles = sorted(glob.glob(str(VAULT / "CHECKPOINT-*.json")))
    if not bundles:
        return None, None
    p = Path(bundles[-1])
    try:
        return p, json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return p, None


def ledger_head() -> tuple[int, str, str | None]:
    recs = [json.loads(ln) for ln in LEDGER.read_text(encoding="utf-8").split("\n")
            if ln.strip()]
    genesis = recs[0].get("hash") if recs else None
    return len(recs), recs[-1]["hash"], genesis


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    violation = write_path_guard()
    if violation:
        return fail(violation)

    sys.path.insert(0, str(COMPUTE_PKG))
    from pipeline.falsification import (  # noqa: E402
        _legacy_prefix, _sha256_hex, _log_tail, read_ledger_heads, verify,
    )

    live_seq, live_head = log_tail()
    raw = LOG.read_text(encoding="utf-8")
    legacy_bytes, _ = _legacy_prefix(raw)
    legacy_digest = _sha256_hex(legacy_bytes)

    _, pinned = latest_bundle()
    pinned_seq = (pinned or {}).get("chains", {}).get("falsification", {}).get("seq", 0)

    if live_seq <= pinned_seq and not args.force:
        print(json.dumps({"ok": True, "refreshed": False,
                          "reason": "tail seq already pinned",
                          "seq": live_seq}))
        return 0

    # Honest pin: run verify() and record whatever it says.
    violations = verify(LOG)
    verify_state = "OK" if not violations else "BROKEN: " + "; ".join(violations[:5])

    # Integrity status vs the ledger-published head (same semantics as
    # _report_integrity_status: MISMATCH when stale/disagreeing, VERIFIED
    # only on exact match with zero violations, UNKNOWN when unpinned).
    tail_seq, tail_hash = _log_tail(LOG)
    heads = read_ledger_heads()
    if heads:
        h_seq, h_hash, _ = heads[-1]
        if h_seq == tail_seq and h_hash == tail_hash and not violations:
            integrity_status = "VERIFIED"
        else:
            integrity_status = (f"MISMATCH: ledger-published head (seq {h_seq}) "
                                f"vs log tail (seq {tail_seq})")
    else:
        integrity_status = "UNKNOWN: no chain head published to proof-ledger"

    n_entries, ledger_head_hash, genesis_hash = ledger_head()
    taken = datetime.now(timezone.utc)
    bundle = {
        "checkpoint_schema": SCHEMA,
        "taken_at_utc": taken.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "taken_by": "eventd checkpoint-refresh watch (owned automation; brutal-audit rollout round 3)",
        "store": "same-VM event-driven vault: ~/workspace/checkpoint-vault/ (NOT a git repo; NOT inside any pipeline repo)",
        "chains": {
            "falsification": {
                "source_path": str(LOG),
                "seq": live_seq,
                "head_hash": live_head,
                "legacy_prefix_sha256": legacy_digest,
                "verify_state_at_checkpoint": {
                    "verify": verify_state,
                    "integrity_status": integrity_status,
                    "note": ("Checkpoint pins the state HONESTLY as observed. "
                             "A broken pin attests deviation from that broken "
                             "state, not cleanliness."),
                },
            },
            "proof-ledger": {
                "source_path": str(LEDGER),
                "entries": n_entries,
                "head_hash": ledger_head_hash,
                "genesis_first_hash": genesis_hash,
                "verify_state_at_checkpoint": {
                    "chain_links": "pinned count + head hash only",
                    "note": "Signature/timestamp semantics not attested by this checkpoint.",
                },
            },
        },
        "consumer_protocol": ("1) Fetch this bundle. 2) Run verify() on the log. "
                              "3) Require tail seq >= pinned seq, recomputed head "
                              "at pinned seq == pinned head_hash, legacy-prefix "
                              "digest == pinned legacy_prefix_sha256. 4) Missing "
                              "checkpoint -> integrity UNKNOWN. Stale checkpoint "
                              "attests history only up to pinned seq."),
        "independence_note": ("Same VM as the writers. Same-domain tripwire "
                              "upgrade, NOT true independence. Full independence "
                              "still requires Zack's notebook or a second machine. "
                              "A VM-wide attacker who rewrites log + witness + "
                              "this bundle forges consistently (Demo C)."),
        "refresh_policy": ("Event-driven (no timers): eventd watch "
                           "'checkpoint-refresh' fires on falsification-log "
                           "appends (debounce 180s) and runs this script. "
                           "Manual refresh by a parent agent: run this script "
                           "with --force. The PIPELINE must never write here; "
                           "the write-path guard above fails closed on any "
                           "pipeline reference to the vault."),
    }

    name = taken.strftime("CHECKPOINT-%Y-%m-%dT%H%M.json")
    dest = VAULT / name
    if dest.exists():
        i = 2
        while (VAULT / f"{name[:-5]}-{i}.json").exists():
            i += 1
        dest = VAULT / f"{name[:-5]}-{i}.json"

    # Vault is 555 by design; drop to 755 for the atomic write, then back.
    os.chmod(VAULT, 0o755)
    try:
        tmp = VAULT / (dest.name + ".tmp")
        tmp.write_text(json.dumps(bundle, indent=1, sort_keys=True) + "\n",
                       encoding="utf-8")
        os.chmod(tmp, 0o444)
        os.replace(tmp, dest)
        os.chmod(dest, 0o444)
    finally:
        os.chmod(VAULT, 0o555)
    # Verify the tripwire state landed as intended.
    st = os.stat(VAULT)
    assert stat.S_IMODE(st.st_mode) == 0o555, "vault dir not back to 555"

    print(json.dumps({"ok": True, "refreshed": True,
                      "bundle": dest.name,
                      "falsification_seq": live_seq,
                      "falsification_head": live_head[:16] + "...",
                      "proof_ledger_entries": n_entries,
                      "verify": verify_state.split(":")[0]}))
    return 2


if __name__ == "__main__":
    sys.exit(main())
