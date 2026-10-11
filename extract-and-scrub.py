#!/usr/bin/env python3
# DEPRECATED (2026-10-10, rust-audit): ported to Rust — see
# ~/workspace/rust-audit/rs/src/bin/extract-and-scrub-rs.rs
# Archive-don't-delete: this file still runs, but new work goes to the Rust binary.
"""extract-and-scrub.py — save secrets to a locked vault file, then scrub them.

Usage: extract-and-scrub.py <vault-path> <files...>
- Finds candidate secrets via contextual + prefix + entropy patterns.
- Appends {file, line, label, value} records to the vault (JSON list).
- Replaces each value in-place with [REDACTED:<label>].
- chmod 600 on the vault. NEVER prints values, only counts and labels.
"""
import json, math, os, re, sys
from collections import Counter

def shannon(s):
    if not s: return 0.0
    c = Counter(s); n = len(s)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

PREFIX = re.compile(
    r'(?<![A-Za-z0-9_])(?:sk-[A-Za-z0-9_\-]{8,}|ghp_[A-Za-z0-9]{8,}|gho_[A-Za-z0-9]{8,}|'
    r'ghu_[A-Za-z0-9]{8,}|xox[bpras]-[A-Za-z0-9\-]{8,}|AKIA[A-Z0-9]{16}|'
    r'cfut_[A-Za-z0-9_\-]{8,}|cfat_[A-Za-z0-9_\-]{8,}|AIza[A-Za-z0-9_\-]{8,}|'
    r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----)')
# credential-context assignments: password/api_key/secret/token = value
# value may be `backtick`, "double", 'single' quoted (may contain commas etc), or bare
CTX = re.compile(
    r'(?i)(root\s+password|password|passwd|api[_-]?key|apikey|secret|token|bearer)\s*'
    r'[:=]\s*(?:`([^`]+)`|"([^"]+)"|\'([^\']+)\'|([^\s,;}\]]+))')
# JSON "key": "value" where key looks credential-ish
JSONCTX = re.compile(
    r'"((?:[^"]*(?:password|passwd|secret|api[_-]?key|token|private[_-]?key)[^"]*))"\s*:\s*"([^"]{4,})"',
    re.I)

def label_for(kind, ctx):
    ctx = re.sub(r'[^a-z0-9]+', '-', ctx.lower()).strip('-')[:24]
    return f"{kind}:{ctx}" if ctx else kind

def find_secrets(text):
    """Yield (start, end, label, value)."""
    out = []
    for m in PREFIX.finditer(text):
        out.append((m.start(), m.end(), 'prefix-token', m.group(0)))
    for m in CTX.finditer(text):
        v = m.group(2) or m.group(3) or m.group(4) or m.group(5)
        if not v or v.lower() in ('null', 'undefined', 'true', 'false'):
            continue
        # value span: find which group matched
        for gi in (2, 3, 4, 5):
            if m.group(gi) is not None:
                vs = m.start(gi); break
        if len(v) >= 4:
            out.append((vs, vs+len(v), label_for('cred', m.group(1)), v))
    for m in JSONCTX.finditer(text):
        v = m.group(2)
        vs = m.start(2)
        out.append((vs, vs+len(v), label_for('json', m.group(1)), v))
    # dedupe overlapping, keep longest
    out.sort(key=lambda x: (x[0], -(x[1]-x[0])))
    ded = []
    for s, e, l, v in out:
        if ded and s < ded[-1][1]:
            continue
        # entropy sanity for bare values: skip obvious non-secrets
        if l.startswith('cred:') or l.startswith('json:'):
            if len(v) < 6 and shannon(v) < 3.0:
                continue
        ded.append((s, e, l, v))
    return ded

def main():
    vault_path, files = sys.argv[1], sys.argv[2:]
    vault = []
    if os.path.exists(vault_path):
        vault = json.load(open(vault_path))
    total, per_file = 0, {}
    for fp in files:
        with open(fp, encoding='utf-8', errors='replace') as f:
            text = f.read()
        matches = find_secrets(text)
        if not matches:
            continue
        # scrub from the end so offsets stay valid
        labels = []
        for s, e, label, value in sorted(matches, key=lambda x: -x[0]):
            lineno = text.count('\n', 0, s) + 1
            vault.append({'file': os.path.basename(fp), 'line': lineno,
                          'label': label, 'value': value})
            text = text[:s] + f'[REDACTED:{label}]' + text[e:]
            labels.append(label)
            total += 1
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(text)
        per_file[os.path.basename(fp)] = labels
    with open(vault_path, 'w', encoding='utf-8') as f:
        json.dump(vault, f, indent=1)
    os.chmod(vault_path, 0o600)
    print(f'vault: {vault_path} ({len(vault)} records, mode 600)')
    print(f'scrubbed {total} values across {len(per_file)} files')
    for fp, labels in per_file.items():
        uniq = sorted(set(labels))
        print(f'  {fp}: {len(labels)} values [{", ".join(uniq[:6])}]')

if __name__ == '__main__':
    main()
