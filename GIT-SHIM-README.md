# git-guard shim (`~/workspace/bin/git`)

Second-layer defense against the **20:51Z incident (2026-10-08)**: a lane ran
`git reset --hard` twice in the shared compute repo and vaporized uncommitted
`ledger.py` work (the twotier `verify_envelopes` rewrite + `record()`
validation) plus uncommitted falsification entries. Redteam-4 caught it
(RT4-001..006); recovery cost a full lane.

Layer 1 is dispatch-time: `full-send/brief-lint.sh` rejects lane briefs that
authorize forbidden ops. This shim is layer 2: it catches the bad command at
**execution time**, even if it never appeared in a brief.

## What it blocks

| Command | Condition | Why |
|---|---|---|
| `git reset --hard` | uncommitted tracked changes exist | destroys work tree-wide |
| `git reset` (pathspec-free, not `--soft`) | uncommitted tracked changes exist | moves HEAD / resets the index |
| `git stash` / `push` / `save` (bare) | always | parks work where a reset can lose it — use selective staging |
| `git clean -f` / `-fd` | always | deletes untracked files (fixtures/evidence/WIP are untracked by design) |
| `git checkout/switch --force` / `-f` | always | overwrites local modifications without asking |
| `git push --force` / `-f` | always | rewrites shared history (`--force-with-lease` still allowed) |
| `git rebase`, `git pull --rebase`, `git commit --amend`, `git filter-branch`, `git filter-repo` | always | history is append-only |

Explicitly **allowed**: `git reset --soft`, `git reset -- <path>` (unstage),
`git stash list/show/apply/pop/branch`, `git clean -n` (dry run),
`git push --force-with-lease`, and every non-listed subcommand, which passes
straight through to the real git untouched.

`git reset --hard` on a **clean** tree is allowed (harmless no-op) — the
shim refuses only when there is work to lose, per the brief.

## Install

```bash
export PATH="$HOME/workspace/bin:$PATH"   # ~/workspace/bin FIRST
```

Add it to your shell rc (`~/.bashrc`) to make it permanent. Verify:

```bash
command -v git   # → /home/hatch/workspace/bin/git
```

The shim resolves the real git by stripping its own directory from PATH and
re-resolving, falling back to `/usr/bin/git`. It never recurses.

## Escape hatch

Deliberate, never accidental — call the real git by absolute path:

```bash
/usr/bin/git reset --hard
```

There is no environment-variable bypass. If you need the hatch, you type it.

## Limits (honest)

- Only active when `~/workspace/bin` precedes the real git on PATH.
- A caller invoking `/usr/bin/git` directly bypasses it (that is the
  documented escape hatch, not a bug).
- `git -c alias.reset=...` style trickery and `GIT_*` env vars are out of
  scope — the threat model is accidental invocation, not adversarial evasion.

## Testing

All behavior is demonstrated on scratch repos under `/tmp` (never the shared
tree). See the lane receipt `waves/wave-8/reset-hard-precommit-guard.done.json`
for the test matrix results.
