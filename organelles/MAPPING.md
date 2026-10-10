# bin — organelle mapping decisions

Operator scripts repo (`~/workspace/bin`). Doctrine: one manifest per script
GROUP (grouped by what the scripts do), each group a purpose-built organelle
with its own codon. Prior wave-5 pass stamped all 7 groups with one shared
codon `bn` (host-registry collision: 7 organelles, one identity) and mapped
`verify` to the wrong script (`sign-receipt.sh`); both fixed here.

## Capability units found (from the actual scripts)

| Unit | Scripts | Organelle ops | Decision |
|---|---|---|---|
| bin-backup (`bk`) | `backup-s22-proof.sh` | `backup` | **Bespoke.** Tier-0 tarballs + tier-1 git bundles with sha256 manifest, keep-4 rotation (BACKUP-PROTOCOL.md). No ref organelle does backup rotation. |
| bin-checkpoint-compute (`bc`) | `checkpoint-compute.sh` | `checkpoint` | **Bespoke.** Compute-state checkpoint (queue/ledger/budget snapshots). Domain snapshotting, not kv/file-cas. |
| bin-coding-agents (`be`) | `coding-agents-env.sh` | `env` | **Bespoke.** Prints shell exports wiring gemini/copilot/gh CLIs (PATH, GEMINI_API_KEY source, trust flags). ReadOnly, Proven-deterministic output shape. No ref organelle emits env setup. |
| bin-graph-etl (`bg`) | `devgraph.py`, `enrich-graphs.py`, `drive-etl-watchdog.sh` | `etl_devgraph`, `etl_enrich`, `etl_watchdog` | **Bespoke.** Entity-graph ETL over dev data + Drive watchdog (resume-safe pipeline supervision). Not scrape-extract (no web extraction; local graph building). |
| bin-keyman-vault (`bv`) | `keyman.py`, `vault-export.py`, `vault-to-keepassxc.py` | `manage`, `export_vault`, `export_keepassxc` | **Bespoke.** Key lifecycle (sync/rotate to Cloudflare worker secrets) + vault export to KeePassXC. ExternalEffect on rotate (hits Cloudflare API). Secrets-adjacent: manifests carry capability NAMES only; the adapter never logs values (see adapter.py `scrub_values`). |
| bin-receipt-tools (`br`) | `sign-receipt.sh`, `verify-receipt.sh` | `sign`, `verify` | **Bespoke.** Wraps/verifies full-send lane receipts in the lucidota-receipt/1 envelope via the `pl` binary + anti-replay binding (lane/wave must match filename/dir). Uses the envelope's hash-sealing internally, but the contract is the receipt-envelope protocol, not the generic `ref-hash-seal` primitive — same reasoning as compute-envelope. |
| bin-secret-scrub (`bs`) | `secret-scrub.py`, `extract-and-scrub.py` | `scrub`, `extract_scrub` | **Bespoke.** Fail-closed pre-commit scrubber (value-greps + label-scans + LONG_PAT entropy gate). A scanner/mutator, not `ref-text-transform` (which transforms text, not detect secrets). |
| bin-shamir (`bm`) | `shamir/shamir-vetted.py` | `split`, `combine` | **Bespoke.** Audited Trezor SLIP-0039 mnemonic share split/combine for vault-root splitting. No ref organelle does secret sharing. Ops take secret input via FILE PATH only, never inline values. |

## Reference-organelle check (all 12 considered)

- `ref-kv-store`: keyman *stores* keys in `~/workspace/keys/` files, but its
  contract is key lifecycle (sync/rotate/export), not put/get/delete.
- `ref-hash-seal`: receipt-tools and secret-scrub use sha256 internally, but
  neither contract IS "seal a value with its sha256".
- `ref-file-cas`: backup writes tarballs, but rotation/retention policy is
  the contract, not content-addressed storage.
- `ref-text-transform`, `ref-json-validate`, `ref-http-fetch`,
  `ref-time-oracle`, `ref-geo-point`, `ref-ledger-append`, `ref-notify`,
  `ref-scrape-extract`, `ref-model-call`: no overlap with any unit.
- Verdict: all 8 units genuinely bespoke. Nothing reinvented.

## Deliberate exclusions

- `git` (PATH shim, 4.8 KB bash): operator PATH wrapper that strips
  `~/workspace/bin` from PATH before delegating to real git — not an
  independently callable capability; its "ops" are arbitrary git passthrough.
- `shamir/venv/`: Python venv for the shamir tool — environment, not a unit.
- `__pycache__/`: bytecode cache.
- `.secrets-allowlist`: config for the scrubber, not a capability.

## Execution facts

- Valence: all Candidate (shell scripts / external effects / secrets-adjacent).
  `env` (coding-agents) is ReadOnly; `verify` (receipt-tools) is ReadOnly.
- fs allowlist: `~/workspace/bin`, `/tmp`. keyman-vault additionally
  `~/workspace/keys` (read) — declared in execution.json per-unit overrides.
- network: none, except keyman `manage` rotate (egress to Cloudflare API —
  declared; rotate is operator-gated upstream by the secret-freeze rule).
- kill: suspend drains in-flight script; kill = SIGTERM to child, final
  receipt emitted by the adapter (interim sha256 receipt id until the host
  issues chain receipts at registration).
- Envelopes per unit in execution.json (backup gets a longer wall-time).
