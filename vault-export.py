#!/usr/bin/env python3
# DEPRECATED (2026-10-10, rust-audit): ported to Rust — see
# ~/workspace/rust-audit/rs/src/bin/vault-export-rs.rs
# Archive-don't-delete: this file still runs, but new work goes to the Rust binary.
"""vault-export.py — enrich vault records with service names, export normalized.

Usage: vault-export.py <vault.json> <transcript-dir> <out.json>
Reads each record's {file, line}, pulls +-6 lines of context from the
(scrubbed) transcript, and infers: service, account, username, kind.
Output: [{service, account, username, kind, value, provenance}] — the
normalized shape every password manager can import. NEVER prints values.
"""
import json, os, re, sys

SERVICES = [
    'vultr', 'reddit', 'cloudflare', 'github', 'openai', 'anthropic', 'gemini',
    'google', 'gmail', 'nvidia', 'openrouter', 'mistral', 'groq', 'deepseek',
    'vercel', 'workers', 'd1', 'r2', 'kv', 'ssh', 'phantom', 'luci', 'lucidota',
    'coinbase', 'stripe', 'twilio', 'discord', 'telegram', 'slack', 'notion',
    'dropbox', 'drive', 'aws', 'azure', 'gcp', 'docker', 'xenforo', 'perb',
    'bcfsa', 'reca', 'calgary', 'alberta', 'kaggle', 'huggingface',
]
SVC_RE = re.compile(r'(?i)\b(' + '|'.join(SERVICES) + r')\b')
USER_RE = re.compile(r'(?i)(?:user(?:name)?|login|account|email)\s*[:=]\s*["\']?([^\s"\',}]+)')

def infer(block, label, fname):
    svc = SVC_RE.search(block)
    service = svc.group(1).lower() if svc else 'unknown'
    # credential-file paths are strong signals: vultr_creds.txt, reddit_sad_bid_creds.json
    m = re.search(r'([a-z0-9_]+)_creds?\.(?:txt|json)', block, re.I)
    if m:
        service = m.group(1).lower()
    um = USER_RE.search(block)
    username = um.group(1) if um else ''
    kind = label.split(':', 1)[1] if ':' in label else label
    if label.startswith('prefix-token'):
        kind = 'api-token'
    return service, username, kind

def main():
    vault_p, tdir, out_p = sys.argv[1], sys.argv[2], sys.argv[3]
    vault = json.load(open(vault_p))
    # cache transcript lines
    cache = {}
    def lines_for(fname):
        if fname not in cache:
            p = os.path.join(tdir, fname)
            cache[fname] = open(p, encoding='utf-8', errors='replace').readlines() \
                if os.path.exists(p) else []
        return cache[fname]
    enriched, stats = [], {}
    for r in vault:
        ls = lines_for(r['file'])
        i = max(0, r['line'] - 7)
        j = min(len(ls), r['line'] + 6)
        block = ''.join(ls[i:j])
        service, username, kind = infer(block, r['label'], r['file'])
        enriched.append({
            'service': service,
            'account': r['file'].replace('claude_code--', '').split('--')[0][:16],
            'username': username,
            'kind': kind,
            'value': r['value'],
            'provenance': f"{r['file']}:{r['line']}",
        })
        stats[service] = stats.get(service, 0) + 1
    json.dump(enriched, open(out_p, 'w'), indent=1)
    os.chmod(out_p, 0o600)
    print(f'enriched {len(enriched)} records -> {out_p} (mode 600)')
    print('service distribution:')
    for s, n in sorted(stats.items(), key=lambda x: -x[1])[:15]:
        print(f'  {s}: {n}')

if __name__ == '__main__':
    main()
