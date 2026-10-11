#!/usr/bin/env python3
"""Mechanical CallOk fix: X[..] -> X.output[..] at compiler-flagged sites.

Usage: callok-fix.py <crate-dir>
Runs `cargo test --offline --no-run`, collects E0608 (cannot index into CallOk)
and E0599 (no method `get`/`as_*` on CallOk) sites, inserts `.output` before the
flagged `[` or rewrites `.get(` -> `.output.get(`, then loops until clean.
Zero semantic change: only test/harness code that indexed call() results as Value.
"""
import re, subprocess, sys, pathlib, os, glob

crate = pathlib.Path(sys.argv[1])
# Real toolchain cargo, not the rustup shim (proxy flakes under load).
_TOOLCHAINS = sorted(glob.glob(str(pathlib.Path.home() / ".rustup/toolchains/*/bin/cargo")))
_CARGO = _TOOLCHAINS[-1] if _TOOLCHAINS else str(pathlib.Path.home() / ".cargo/bin/cargo")
_CARGO_ENV = {**os.environ, "PATH": str(pathlib.Path(_CARGO).parent) + ":" + os.environ.get("PATH", ""),
              "RUSTUP_TOOLCHAIN": ""}
# files to consider: only in this crate dir
for round in range(6):
    p = subprocess.run(
        ["cargo", "test", "--offline", "--no-run"],
        cwd=crate, capture_output=True, text=True, env=_CARGO_ENV,
    )
    out = p.stderr + p.stdout
    edits = {}  # (file, lineno) -> list of (col, kind)
    cur_line = None
    cur_msg = ""
    cur_kind = None
    for line in out.splitlines():
        m = re.match(r"^error(\[E\d+\])?: (.*)", line)
        if m:
            cur_kind, cur_msg = m.group(1), m.group(2)
            cur_line = None
            continue
        if cur_line is None and not line.startswith("    -->"):
            # accumulate message lines only until location; keep it simple
            pass
        m = re.match(r"^\s+-->\s+([^:]+):(\d+):(\d+)", line)
        if m and cur_kind in ("[E0608]", "[E0599]") and "CallOk" in cur_msg:
            f, ln, col = m.group(1), int(m.group(2)), int(m.group(3))
            fp = (crate / f).resolve()
            if not fp.exists():
                # compiler prefixes with crate dir name: sec-organelles/src/lib.rs
                parts = pathlib.Path(f).parts
                if parts and parts[0] == crate.name:
                    fp = (crate / pathlib.Path(*parts[1:])).resolve()
            if not str(fp).startswith(str(crate.resolve()) + "/"):
                cur_line = None
                continue
            cur_line = (fp, ln, col)
            continue
        m = re.match(r"^\s+\|\s*\^+", line)
        if m and cur_line and cur_kind in ("[E0608]", "[E0599]") and "CallOk" in cur_msg:
            fp, ln, col = cur_line
            edits.setdefault((fp, ln), []).append((col, cur_kind))
            cur_line = None
    if not edits:
        print(f"round {round}: no CallOk E0608/E0599 edits remain; exit={p.returncode}")
        # verify no other CallOk errors remain at all
        if re.search(r"CallOk", out) and re.search(r"^error", out, re.M):
            print("NOTE: other (non-index/get) CallOk errors may remain — inspect manually")
            break
        break
    n = 0
    for (fp, ln), sites in edits.items():
        lines = fp.read_text().splitlines(keepends=True)
        text = lines[ln - 1]
        for col, kind in sorted(sites, reverse=True):
            idx = col - 1
            if kind == "[E0608]":
                if text[idx] != "[":
                    print(f"WARN {fp}:{ln}:{col} expected '[', got {text[idx]!r}; skipping")
                    continue
                text = text[:idx] + ".output" + text[idx:]
                n += 1
            else:  # E0599: method like `x.get(..)` / `x.as_array()` -> `x.output.get(..)` / `x.output.as_array()`
                head = text[:idx].rstrip()
                # span points at the method name; receiver dot is the last char
                mm = re.search(r"\.$", head)
                if not mm:
                    print(f"WARN {fp}:{ln}:{col} no receiver dot before col; skipping")
                    continue
                ins = mm.start()
                text = text[:ins] + ".output" + text[ins:]
                n += 1
        lines[ln - 1] = text
        fp.write_text("".join(lines))
    print(f"round {round}: applied {n} edits")
else:
    print("STILL DIRTY after 6 rounds")
    sys.exit(1)
