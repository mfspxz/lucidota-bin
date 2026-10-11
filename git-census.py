#!/usr/bin/env python3
"""Git census: branch, dirtiness, remotes, ahead/behind, last commit. JSON lines."""
import os, sys, json, subprocess

def run(repo, *args, timeout=20):
    try:
        r = subprocess.run(['git', '-C', repo] + list(args),
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return '', str(e), 99

def census(repo):
    d = {'repo': repo}
    out, err, rc = run(repo, 'rev-parse', '--is-inside-work-tree')
    if rc != 0:
        d['error'] = err[:120]; return d
    br, _, _ = run(repo, 'branch', '--show-current')
    d['branch'] = br or '(detached)'
    st, _, _ = run(repo, 'status', '--porcelain')
    lines = [l for l in st.split('\n') if l.strip()]
    d['dirty_files'] = len(lines)
    d['dirty_sample'] = lines[:5]
    rem, _, _ = run(repo, 'remote', '-v')
    remotes = {}
    for l in rem.split('\n'):
        if l.strip():
            parts = l.split()
            if len(parts) >= 2:
                remotes.setdefault(parts[0], parts[1])
    d['remotes'] = remotes
    # ahead/behind vs upstream
    up, _, rc = run(repo, 'rev-parse', '--abbrev-ref', '@{upstream}')
    if rc == 0 and up:
        d['upstream'] = up
        ab, _, _ = run(repo, 'rev-list', '--left-right', '--count', 'HEAD...@{upstream}')
        try:
            a, b = ab.split()
            d['ahead'] = int(a); d['behind'] = int(b)
        except Exception:
            d['ahead'] = d['behind'] = None
    else:
        d['upstream'] = None; d['ahead'] = d['behind'] = None
    lc, _, _ = run(repo, 'log', '-1', '--format=%ci %h %s')
    d['last_commit'] = lc[:100]
    return d

repos = [l.strip() for l in sys.stdin if l.strip()]
for r in repos:
    try:
        print(json.dumps(census(r)), flush=True)
    except Exception as e:
        print(json.dumps({'repo': r, 'error': str(e)[:120]}), flush=True)
