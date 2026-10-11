#!/usr/bin/env python3
"""Audit commit: stage everything except junk patterns, commit, push.
Junk never committed: build outputs, caches, venvs, logs, pycache, binaries.
Usage: audit-commit.py < /tmp/dirty-ahead.txt (one repo path per line)
"""
import subprocess, sys, os

SKIP_FRAGS = ['/__pycache__/', '/.build/', '/backups/', '/stage/', '/receipts/',
              '/hidden_files/', '/.venv', '/target/', '/tmp/', '.pyc',
              '/tests/hostile/', '.log', '/.pip-cache/', '/node_modules/']
SKIP_SUFFIX = ('.pyc', '.log', '.tmp')

def run(repo, *args, timeout=60):
    p = subprocess.run(['git', '-C', repo] + list(args),
                       capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()

def main():
    for line in sys.stdin:
        repo = line.strip()
        if not repo:
            continue
        short = repo.replace('/home/hatch/workspace/', 'w/')
        try:
            # stage all, then unstage junk
            rc, out = run(repo, 'add', '-A')
            rc, out = run(repo, 'status', '--porcelain')
            staged = [l[3:] for l in out.split('\n') if l.strip() and l[:2].strip()]
            unstage = [f for f in staged
                       if any(fr in '/' + f for fr in SKIP_FRAGS)
                       or f.endswith(SKIP_SUFFIX)]
            for f in unstage:
                run(repo, 'reset', '-q', 'HEAD', '--', f)
            rc, out = run(repo, 'status', '--porcelain')
            remaining = [l for l in out.split('\n') if l.strip() and l[0] in 'MADRC']
            if not remaining:
                print(f"SKIP {short}: nothing committable after junk filter", flush=True)
                continue
            # secret scan on staged content (filenames + small files)
            rc, out = run(repo, 'diff', '--cached', '--name-only')
            names = out.split('\n')
            bad = [n for n in names if any(k in n.lower() for k in
                   ['secret', 'token', 'passwd', '.pem', '.key', 'credential'])
                   and 'allowlist' not in n.lower()]
            if bad:
                run(repo, 'reset', '-q')
                print(f"HOLD {short}: secret-like paths {bad[:3]}", flush=True)
                continue
            msg = ("audit 2026-10-11: commit dangling lane work "
                   f"({len(remaining)} files)")
            rc, out = run(repo, '-c', 'user.name=lucidota',
                          '-c', 'user.email=audit@local',
                          'commit', '-qm', msg)
            if rc != 0:
                print(f"COMMIT-FAIL {short}: {out[-200:]}", flush=True)
                continue
            rc, out = run(repo, 'push', timeout=120)
            tail = out.split('\n')[-1][:90] if out else ''
            print(f"{'PUSH-OK' if rc == 0 else 'PUSH-FAIL'} {short}: {tail}", flush=True)
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT {short}", flush=True)
        except Exception as e:
            print(f"ERR {short}: {str(e)[:80]}", flush=True)

main()
