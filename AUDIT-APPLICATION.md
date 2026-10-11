# Audit Application — ~/workspace/bin

| Field | Value |
|---|---|
| Repo | `~/workspace/bin` |
| Date | 2026-10-10 |
| Auditor | brutal-audit rollout slice 7/8 (parent orchestrator) |
| Scope | Operator scripts; no new Python components beyond glue; scripts edited in place |

## Disposition table

| Finding | Disposition | Summary |
|---|---|---|
| R-1 | Applies | No PROVEN/FIXED claims present; future fix-verification is instance-only until re-attack. |
| R-2 | Applies | secret-scrub.py now carries HONEST BOUNDS; hardening frozen past that bound. Effectiveness UNKNOWN. |
| R-3 | N/A | No hash-chained log in bin. |
| R-4 | Applies | No prior backlog doc; this document creates one. No standing HIGHs. Backlog must not grow. |
| R-5 | Applies | secret-scrub PREFIX_PAT declared best-effort with FIXED complexity budget. |
| R-6 | Applies | secret-scrub has named consumer and enforcement gate; other scripts are operator tools, not detectors. |
| R-7 | Applies | No dedicated test file for secret-scrub; policy documented for future tests. |
| R-8 | Applies | sign/verify are signed; no other provenance claims in bin. |
| R-9 | N/A | No claim/falsification log in bin. |
| R-10 | N/A | Operator scripts are not event records; shamir splits are one-shot operations. |
| R-11 | Applies | Explicit UNKNOWN list included below. |
| R-12 | Applies | GIT-SHIM-README.md spot-check found no unsourced claims; no unsourced oral footnotes. |

---

## R-1 — Fix-verification claims

**Applies.**

No fix-verification claims in this repo are labeled PROVEN or FIXED. Any future claim is instance-only until a dedicated re-attack signs off. Claims and defeats are recorded in this single document. No PROVEN/FIXED status is assigned without a re-attack result.

Status for the changes made today: **UNKNOWN** — they are documentation/header edits and have not been re-attacked.

---

## R-2 — Honest bounds on guardrails

**Applies.**

secret-scrub.py now has a docstring HONEST BOUNDS section:

- **Catches:** known key prefixes and 32+ character high-entropy runs.
- **Cannot catch:** short unprefixed secrets, binary files, split/obfuscated values, new prefixes, allowlist abuse.

It is declared a best-effort tripwire with consumer = pre-commit hook, not a guarantee. Hardening is frozen past this bound. Structural answer is vaulted secrets.

Effectiveness of these catches is **UNKNOWN** — bounded but unmeasured in this pass.

Other guardrails (sign-receipt/verify-receipt) are enforcement gates, not detectors; no catch-bound declaration is required.

---

## R-3 — Out-of-band head copy for hash-chained logs

**N/A — why:** No hash-chained log exists in bin. No tamper-evident claim is made.

---

## R-4 — Triage backlogs

**Applies.**

No backlog document existed. This document now contains the backlog triage. There are no standing HIGHs.

Backlog items:

| ID | Item | Disposition |
|---|---|---|
| B-1 | secret-scrub pattern-expansion | WONT-FIX beyond current budget; structural answer is vaulted secrets |
| B-2 | shamir venv hygiene | QUEUED, low |

The backlog must not grow. Any new item must be triaged with a complexity budget or fix.

---

## R-5 — Signature/denylist/strip games

**Applies.**

secret-scrub.py's PREFIX_PAT pattern list is a signature/denylist game. It is declared best-effort with a FIXED complexity budget. No more pattern-expansion waves will be accepted. Structural answer is vaulted secrets.

Status: **DOCUMENTED**; no effectiveness claim is made.

---

## R-6 — Detector consumer and enforcement gate

**Applies.**

secret-scrub.py is a detector. It has a named consumer (pre-commit hook) and an enforcement gate (pre-commit hook blocks commit). This is conformant.

The remaining scripts are operator tools, not detectors. No detector exists without a consumer and enforcement gate in the same change.

---

## R-7 — Property tests vs change-detection tests

**Applies.**

secret-scrub.py has no dedicated test file. Policy going forward:

- Property tests must state security invariants only (e.g., “known `sk-` prefix is flagged”) and must not use implementation terms.
- Change-detection tests must be explicitly labeled.
- A property test expectation must never be rewritten without adversarial sign-off.

`organelles/test_organelles.py` exists but has not been reviewed or labeled in this pass.

---

## R-8 — Unsigned provenance

**Applies.**

sign-receipt.sh and verify-receipt.sh are signed via an authority key using the `lucidota-receipt/1` envelope, with no second envelope. This is conformant.

No other file in bin claims provenance, so no misleading unsigned provenance exists.

---

## R-9 — Claim/falsification logs

**N/A — why:** No claim/falsification log exists in bin.

---

## R-10 — Record-keeping in the same motion

**N/A — why:** These are operator scripts, not event records. Shamir splits are one-shot operations. No ongoing record-keeping requirement exists.

---

## R-11 — Explicit UNKNOWN list

**Applies.**

| Item | Status | Note |
|---|---|---|
| secret-scrub false-negative rate | UNKNOWN | Unmeasured. |
| keyman.py scope and threat model | UNKNOWN | Read before trusting. |
| shamir/venv committed bytes | UNKNOWN | Provenance of venv bytes unknown; rebuild from requirements instead of trusting. |
| vault-export.py and vault-to-keepassxc.py behavior | UNKNOWN | Unverified in this pass. |

No item on this list is marked PROVEN or DISPROVEN.

---

## R-12 — No unsourced oral footnotes

**Applies.**

GIT-SHIM-README.md was spot-checked for claims. None were flagged as unsourced. No unsourced oral footnotes were found. Standard applied: evidence or UNVERIFIED.

---

## Changes made today

### 1. secret-scrub.py

- Docstring gained HONEST BOUNDS section.
- Declared best-effort tripwire; consumer = pre-commit hook.
- Hardening frozen past stated bound.
- Structural answer = vaulted secrets.
- Answers R-5: PREFIX_PAT pattern list is a signature game with FIXED complexity budget; no more pattern-expansion waves.

### 2. sign-receipt.sh

- Header gained CONSUMER/GATE CHAIN section:
  - Producer.
  - Named consumer = verify-receipt.sh.
  - Enforcement gate = full-send driver + wave-done hook refuses unboarded verdicts.
- Header gained PROVENANCE section:
  - Signed via authority key.
  - Envelope = `lucidota-receipt/1`.
  - No second envelope.

### 3. verify-receipt.sh

- Header gained CONSUMER/GATE CHAIN section:
  - It is the named consumer and the enforcement gate.
  - Exit 1 = REJECT.
- Unsigned-by-default path was deleted from boarding.

---

## Commits

| File | Change | Commit |
|---|---|---|
| secret-scrub.py | HONEST BOUNDS docstring; PREFIX_PAT fixed budget | d8fe785 |
| sign-receipt.sh | CONSUMER/GATE CHAIN + PROVENANCE headers | d8fe785 |
| verify-receipt.sh | CONSUMER/GATE CHAIN; unsigned-by-default path removed | d8fe785 |

Commit `d8fe785`: "brutal-audit: R-2 bounds on secret-scrub + R-5 best-effort declaration; R-6/R-8 consumer+gate+provenance on sign/verify-receipt; AUDIT-APPLICATION.md".

---

## Test counts

- No dedicated test suite exists for the operator scripts.
- `organelles/test_organelles.py` exists; count TBD by author.
- No tests were run or measured in this pass.

Label: **not-run / not-measured**.

---

## Wont-fix / backlog triage

No backlog document existed before this pass. Items:

| ID | Item | Disposition |
|---|---|---|
| B-1 | secret-scrub pattern-expansion | WONT-FIX beyond current budget; structural answer is vaulted secrets |
| B-2 | shamir venv hygiene | QUEUED, low |

No standing HIGHs. The backlog must not grow without triage.

---

## Round 3 (2026-10-11): checkpoint-vault refresh — OWNED + SCHEDULED

**Change:** `checkpoint-vault-refresh.py` (new) — the single authorized writer
to `~/workspace/checkpoint-vault/`. Driven by eventd watch `checkpoint-refresh`
(file watch on `~/workspace/compute/falsification.jsonl`, debounce 180s; NO
timers). Exit 2 → `checkpoint.refresh` outbox event; exit 0 = silent no-op;
exit 1 = error/`watch.error`.

**Rigor disposition:**

| Finding | Disposition | Summary |
|---|---|---|
| R-3 | Applies | bin now OWNS the out-of-band head copy: the refresh action pins falsification seq + head_hash + legacy_prefix_sha256 and proof-ledger count + head into the vault. The vault is NOT a git repo and lives outside all pipeline write paths. |
| R-6 | Applies | Consumer = eventd watch; enforcement = write-path guard in the script (fails closed, exit 1, if any pipeline Python file references the vault path) + 555/444 tripwire perms. Negative test: the lane's live fire test (see below) plus the guard's own refusal path (exercised in design review; a planted reference was used to confirm refusal — see test log). |
| R-7 | Applies | No dedicated unit test file; the live end-to-end test stands as the evidence (measured, this pass). |
| R-8 | Applies | No provenance claims made; bundles are unsigned pin snapshots, documented as such. |
| R-11 | Applies | UNKNOWN list: (a) whether eventd re-registers the watch correctly after every VM replacement (watchdog restarts the daemon; watch config is static TOML — not yet observed across a replacement); (b) long-term bundle accumulation (one bundle per tail advance; ~2.4KB each). |

**Measured evidence (this pass):**
- Manual run: exit 2, bundle `CHECKPOINT-2026-10-11T0401.json` written, pins falsification seq=260 / head `eda2f728…` / prefix `44dcdeca…` (unchanged), proof-ledger 91 entries / head `b631c472…`; verify pinned honestly as BROKEN (line 249) + MISMATCH (stale seq-195 published head).
- Write-path guard: verified zero pipeline references to the vault (`grep -rn checkpoint-vault` over `~/workspace/compute` + pipeline tree: clean). Refusal path verified by planting a temporary reference in a scratch copy — the script exited 1 before any write. Plant removed.
- Live fire: test falsification entry appended → watch fired after debounce → `checkpoint.refresh` event in outbox → new bundle pinned the advanced tail. (Full event evidence in the lane report.)

**Test counts:** live end-to-end 1/1 (manual + event-driven); guard refusal 1/1 (planted). Label: **measured**.

**Standing residual (unchanged from round 2):** same-VM boundary — a log+witness+checkpoint rewrite is undetectable on this VM. True independence needs the operator's notebook/second machine.
