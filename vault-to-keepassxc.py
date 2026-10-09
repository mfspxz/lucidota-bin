#!/usr/bin/env python3
"""vault-to-keepassxc.py — import enriched vault records into KeePassXC.

Usage: vault-to-keepassxc.py --db <db.kdbx> --db-pass-file <locked-file>
                             --enriched <enriched.json> [--state <state.json>]
                             [--group <group-name>]
- Idempotent: tracks imported provenances in state file, imports only new.
- Layout: <group>/<service>/<kind>[-n], username + provenance in notes.
- DB password read from a mode-600 file, passed via stdin. NEVER in chat.
- Entry passwords passed via stdin (db-pass, entry-pass, entry-pass-confirm).
"""
import argparse, hashlib, json, os, subprocess, sys

def run(cmd, stdin_lines):
    p = subprocess.run(cmd, input='\n'.join(stdin_lines) + '\n',
                       capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr

def db_pass(pass_file):
    st = os.stat(pass_file)
    if st.st_mode & 0o077:
        sys.exit(f'REFUSED: {pass_file} is not mode 600')
    return open(pass_file).read().strip()

def db_auth_args(a):
    """Return (extra_cli_args, db_password_stdin). Keyfile mode: -k + --no-password."""
    if a.key_file:
        return (['-k', a.key_file, '--no-password'], '')
    return ([], db_pass(a.db_pass_file))

def ensure_group(a, group):
    extra, pw = db_auth_args(a)
    parts = group.split('/')
    for i in range(1, len(parts) + 1):
        sub = '/'.join(parts[:i])
        run(['keepassxc-cli', 'mkdir', '-q'] + extra + [a.db, sub], [pw])
    return 0

def add_entry(a, path, username, secret, notes):
    extra, pw = db_auth_args(a)
    rc, out, err = run(
        ['keepassxc-cli', 'add', '-p', '-q'] + extra + [a.db, path,
         '-u', username, '--notes', notes],
        [pw, secret, secret])
    return rc, err

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--db-pass-file', default=None,
                    help='mode-600 file holding the DB password')
    ap.add_argument('--key-file', default=None,
                    help='keyfile for the DB (keyfile-only mode)')
    ap.add_argument('--enriched', required=True)
    ap.add_argument('--state', default=os.path.expanduser('~/.vault-kpxc-state.json'))
    ap.add_argument('--group', default='transcript-secrets')
    a = ap.parse_args()

    records = json.load(open(a.enriched))
    state = json.load(open(a.state)) if os.path.exists(a.state) else {}
    done = set(state.get('imported', []))

    new = [r for r in records if r['provenance'] not in done]
    print(f'{len(records)} records, {len(new)} new to import')

    groups_made, added, failed = set(), 0, []
    # dedupe entry names within service
    seen_names = {}
    for r in records:
        key = (r['service'], r['kind'])
        n = seen_names.get(key, 0) + 1
        seen_names[key] = n
        r['_entry'] = f"{r['kind']}" if n == 1 else f"{r['kind']}-{n}"

    for r in new:
        group = f"{a.group}/{r['service']}"
        if group not in groups_made:
            ensure_group(a, group)
            groups_made.add(group)
        path = f"{group}/{r['_entry']}"
        notes = f"provenance: {r['provenance']}\naccount: {r['account']}"
        rc, err = add_entry(a, path,
                            r['username'] or '(none)', r['value'], notes)
        if rc == 0:
            done.add(r['provenance']); added += 1
        else:
            failed.append((path, err.strip()[:120]))

    state['imported'] = sorted(done)
    with open(a.state, 'w') as f:
        json.dump(state, f)
    os.chmod(a.state, 0o600)
    print(f'imported {added}, failed {len(failed)}')
    for p, e in failed[:5]:
        print(f'  FAIL {p}: {e}')

if __name__ == '__main__':
    main()
