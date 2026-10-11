#!/usr/bin/env python3
"""Stage only mechanical CallOk `.output`-insertion edits from a dirty tree.

Usage: stage-callok.py <repo-dir>
For every tracked modified .rs file: take `git diff -U0`, keep only
changed-line pairs where new == old with ".output" inserted (zero semantic
change), apply those hunks to the index. Prints staged/unstaged summary.
"""
import re, subprocess, sys, pathlib

repo = pathlib.Path(sys.argv[1])

def sh(*a):
    return subprocess.run(a, cwd=repo, capture_output=True, text=True)

files = sh("git", "diff", "--name-only").stdout.split()
staged_total = 0
skipped = []
for f in files:
    if not f.endswith(".rs"):
        continue
    d = sh("git", "diff", "-U0", "--", f).stdout
    hunks = []          # (old_start, removed[], added[])
    cur = None
    for line in d.splitlines():
        m = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if m:
            cur = (int(m.group(1)), [], [])
            hunks.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("-") and not line.startswith("---"):
            cur[1].append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            cur[2].append(line[1:])
    patch = []
    for old_start, removed, added in hunks:
        keep = []
        # match each removed line to an added line that equals it plus ".output" insertions
        pool = list(added)
        for i, old in enumerate(removed):
            ln = old_start + i
            match = None
            for j, cand in enumerate(pool):
                if ".output" in cand and cand.replace(".output", "") == old:
                    match = pool.pop(j)
                    break
            if match is not None:
                keep.append((ln, old, match))
            else:
                skipped.append((f, ln, old[:60]))
        for ln2, old, new in keep:
            patch.append(f"@@ -{ln2},1 +{ln2},1 @@\n-{old}\n+{new}\n")
    if patch:
        hdr = f"diff --git a/{f} b/{f}\n--- a/{f}\n+++ b/{f}\n"
        r = subprocess.run(["git", "apply", "--cached", "--unidiff-zero", "-"],
                           cwd=repo, input=hdr + "".join(patch),
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            print(f"{f}: APPLY FAILED: {r.stderr[:300]}")
        else:
            staged_total += len(patch)
print(f"staged {staged_total} mechanical hunks")
for f, ln, txt in skipped[:15]:
    print(f"skipped (not mine): {f}:{ln}: {txt}")
