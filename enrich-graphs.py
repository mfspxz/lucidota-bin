#!/usr/bin/env python3
# DEPRECATED (2026-10-10, rust-audit): ported to Rust — see
# ~/workspace/rust-audit/rs/src/bin/enrich-graphs-rs.rs
# Archive-don't-delete: this file still runs, but new work goes to the Rust binary.
"""Enrich all dev graphs with granular current-state nodes + build master graph.
Idempotent: merges by id, never overwrites an existing node's status.
Also writes dashboard data files.
"""
import json, os, glob, datetime

WS = os.path.expanduser('~/workspace')
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

def load(slug):
    p = f'{WS}/goals/{slug}/hidden_files/dev-graph.json'
    with open(p) as f: return json.load(f), p

def save(g, p):
    g['last_updated'] = NOW
    with open(p, 'w') as f: json.dump(g, f, indent=1)

def merge_nodes(g, nodes):
    existing = {n['id']: n for n in g['nodes']}
    for n in nodes:
        if n['id'] in existing:
            # enrich label/type but never regress status
            for k in ('label', 'type', 'owner', 'evidence'):
                if k in n: existing[n['id']][k] = n[k]
        else:
            g['nodes'].append(n)

def merge_edges(g, edges):
    seen = {(e.get('from'), e.get('to'), e.get('type')) for e in g['edges']}
    for e in edges:
        if (e.get('from'), e.get('to'), e.get('type')) not in seen:
            g['edges'].append(e); seen.add((e.get('from'), e.get('to'), e.get('type')))

def N(id, label, type='task', status='open', evidence='UNKNOWN', owner='lucidota'):
    return {'id': id, 'label': label, 'type': type, 'status': status,
            'owner': owner, 'evidence': evidence}

def E(frm, to, type='part_of'):
    return {'from': frm, 'to': to, 'type': type}

# ---------------------------------------------------------------- litebox
g, p = load('litebox-library-os-organelle-execution-substrate')
merge_nodes(g, [
    N('task-assess-userland', 'Assess linux-userland: build, tests, 9P, /proc, PID virt', 'task', 'done', 'PROVEN'),
    N('task-harden-host', 'Build hardened organelle host (namespaces+seccomp+watchdog)', 'task', 'done', 'PROVEN'),
    N('task-coop-test', 'Cooperative guest run: echo hello, receipt, artifact hash', 'task', 'done', 'PROVEN'),
    N('task-hostile-tests', 'Hostile tests: mem, raw-syscall, socket, write, exhaustion', 'task', 'open', 'UNKNOWN'),
    N('task-hostile-blocked', 'BLOCKED: safety system refused int $0x80 probe compile', 'risk', 'open', 'PROVEN'),
    N('task-threat-model', 'Threat model: enforced/assumed/unmitigated', 'deliverable', 'done', 'PROVEN'),
    N('task-telemetry-patch', 'LiteBox shim telemetry patches (additive)', 'task', 'done', 'PROVEN'),
    N('epic-integration', 'Integrate host into exocortex execution path', 'epic', 'open', 'UNKNOWN'),
])
merge_edges(g, [
    E('task-assess-userland', 'goal-root'), E('task-harden-host', 'goal-root'),
    E('task-coop-test', 'task-harden-host', 'tests'), E('task-threat-model', 'task-harden-host', 'informs'),
    E('task-hostile-blocked', 'task-hostile-tests', 'mitigates'),
    E('epic-integration', 'goal-root'), E('task-harden-host', 'epic-integration', 'enables'),
])
save(g, p)

# ---------------------------------------------------------------- indy-reads
g, p = load('indy-reads-phone-assistant-as-a-real-personal-agent')
merge_nodes(g, [
    N('task-voice-demo', 'Voice demo live on Vercel (voice.html)', 'deliverable', 'done', 'PROVEN'),
    N('task-nvidia-brain', 'NVIDIA brain live on ai-router (dual-router failover)', 'task', 'done', 'PROVEN'),
    N('task-cf-migration', 'Cloudflare migration: worker + KV assets + secret', 'task', 'in_progress', 'PROVEN'),
    N('task-cf-route-blocked', 'BLOCKED: workers.dev route not attaching (need dashboard/token)', 'risk', 'open', 'PROVEN'),
    N('task-vercel-cleanup', 'Vercel cleanup AFTER Cloudflare verified', 'task', 'open', 'UNKNOWN'),
    N('task-wasm-shadow', 'WASM shadow validation (not yet authoritative)', 'task', 'in_progress', 'UNKNOWN'),
    N('task-phone-proof', 'Real Android pass: barge-in, mic/TTS, viseme', 'task', 'open', 'UNKNOWN'),
    N('task-pl-chain', 'Full proof chain: receipt → verified result', 'epic', 'open', 'UNKNOWN'),
])
merge_edges(g, [
    E('task-voice-demo', 'goal-root'), E('task-nvidia-brain', 'goal-root'),
    E('task-cf-migration', 'goal-root'), E('task-cf-route-blocked', 'task-cf-migration', 'mitigates'),
    E('task-cf-migration', 'task-vercel-cleanup', 'enables'),
    E('task-phone-proof', 'goal-root'), E('task-pl-chain', 'goal-root'),
])
save(g, p)

# ---------------------------------------------------------------- artifacts / wreck
g, p = load('cloudflare-artifacts-competition-agent-git-platform')
merge_nodes(g, [
    N('task-deep-dive', 'Artifacts deep dive: API, pricing, limits', 'research', 'done', 'PROVEN'),
    N('task-tech-risks', 'Tech risks: events, queue, conflicts, builds', 'research', 'done', 'PROVEN'),
    N('task-judging', 'Judging research: competitor artifacts-os found', 'research', 'done', 'PROVEN'),
    N('task-plan', 'MERGEGOVERNOR plan written', 'plan', 'done', 'PROVEN'),
    N('task-paid-gate', '$5/mo Workers Paid approved by Zack', 'decision', 'done', 'PROVEN'),
    N('task-wreck-build', 'Build wreck: protocol + governor + adapters', 'epic', 'in_progress', 'PROVEN'),
    N('task-demo-video', '5-10 min demo video', 'deliverable', 'open', 'UNKNOWN'),
    N('task-submit', 'Submit by Oct 14', 'milestone', 'open', 'UNKNOWN'),
])
merge_edges(g, [
    E('task-deep-dive', 'goal-root'), E('task-tech-risks', 'task-plan', 'informs'),
    E('task-judging', 'task-plan', 'informs'), E('task-plan', 'task-wreck-build', 'enables'),
    E('task-wreck-build', 'task-demo-video', 'enables'), E('task-demo-video', 'task-submit', 'enables'),
])
save(g, p)

# ---------------------------------------------------------------- graph hacks
g, p = load('graph-hacks-2026-context-forge-falkordb-agent')
merge_nodes(g, [
    N('task-directive', 'Build directive: tracks, acceptance test, constraints', 'plan', 'done', 'PROVEN'),
    N('task-no-impl', 'HARD RULE: no implementation before Oct 15', 'decision', 'done', 'PROVEN'),
    N('task-ontology', 'Ontology + Cypher design (pre-event allowed)', 'design', 'open', 'UNKNOWN'),
    N('task-demo-script', 'Demo script + benchmark (pre-event allowed)', 'task', 'open', 'UNKNOWN'),
])
merge_edges(g, [E('task-directive', 'goal-root'), E('task-no-impl', 'goal-root')])
save(g, p)

# ---------------------------------------------------------------- exocortex (master)
g, p = load('fail-fast-asymmetric-exocortex')
merge_nodes(g, [
    N('task-charter', 'Master charter: 27 sections', 'deliverable', 'done', 'PROVEN'),
    N('task-exchange-live', 'Free Compute Exchange live (NVIDIA+OpenRouter)', 'deliverable', 'done', 'PROVEN'),
    N('task-108-lanes', '108 free lanes: 2 safe, 50 conditional, 56 gated', 'task', 'in_progress', 'PROVEN'),
    N('task-eventd', 'eventd: tokio event bus live', 'deliverable', 'done', 'PROVEN'),
    N('task-governor-est', 'Governor verdict ESTABLISHED (19/19)', 'milestone', 'done', 'PROVEN'),
    N('epic-integration-all', 'Full integration: all subsystems one exocortex', 'epic', 'in_progress', 'UNKNOWN'),
])
merge_edges(g, [
    E('task-charter', 'goal-root'), E('task-exchange-live', 'goal-root'),
    E('task-108-lanes', 'epic-integration-all', 'enables'), E('task-eventd', 'epic-integration-all', 'enables'),
])
save(g, p)

# ---------------------------------------------------------------- thesis defense
g, p = load('thesis-defense-canon-pl-proven-indy-reads-slice')
merge_nodes(g, [
    N('task-work-order', '50-step work order, gates 0-7', 'plan', 'done', 'PROVEN'),
    N('task-canon-min', 'CANON minimum viable', 'task', 'open', 'UNKNOWN'),
    N('task-slice', 'One fully proven Indy_Reads vertical slice', 'epic', 'open', 'UNKNOWN'),
])
merge_edges(g, [E('task-work-order', 'goal-root')])
save(g, p)

# ---------------------------------------------------------------- recovery (transcripts feed stolen-ssd-recovery)
g, p = load('stolen-ssd-recovery')
merge_nodes(g, [
    N('task-transcript-archive', 'Claude transcript archive: 25 sessions indexed', 'deliverable', 'done', 'PROVEN'),
    N('task-transcript-indexer', 'Indexer script: specs/outcomes/files per session', 'task', 'done', 'PROVEN'),
    N('task-former-work-map', 'Former-work map: pivot outward from transcripts', 'research', 'in_progress', 'PROVEN'),
    N('task-recovery-dossier', 'Technical recovery dossier (Oct 6)', 'deliverable', 'done', 'PROVEN'),
])
merge_edges(g, [
    E('task-transcript-archive', 'goal-root'), E('task-transcript-indexer', 'task-transcript-archive', 'enables'),
    E('task-transcript-archive', 'task-former-work-map', 'enables'),
])
save(g, p)

# ---------------------------------------------------------------- money
g, p = load('bougie-apartment-fund')
merge_nodes(g, [
    N('task-pedicab', 'Pedicab income (New West, licenses in hand)', 'task', 'in_progress', 'UNKNOWN'),
    N('task-marketplace', 'Marketplace listings prep', 'task', 'open', 'UNKNOWN'),
    N('task-deal-watch', 'Deal-watch: 10-cents-on-dollar mispricings', 'task', 'open', 'UNKNOWN'),
])
merge_edges(g, [E('task-pedicab', 'goal-root')])
save(g, p)

# ---------------------------------------------------------------- cutecity + tentacle
for slug in ('cutecity-operational-launch', 'cute-tentacle-cloud-city-autonomous-build'):
    g, p = load(slug)
    merge_nodes(g, [N('task-status', 'Status review pending', 'task', 'open', 'UNKNOWN')])
    save(g, p)

# ---------------------------------------------------------------- MASTER GRAPH
projects = []
for slug in sorted(glob.glob(f'{WS}/goals/*/hidden_files/dev-graph.json')):
    with open(slug) as f: g = json.load(f)
    goal_slug = slug.split('/goals/')[1].split('/')[0]
    nodes, edges = g['nodes'], g['edges']
    done = sum(1 for n in nodes if n.get('status') == 'done')
    prog = sum(1 for n in nodes if n.get('status') == 'in_progress')
    blocked = sum(1 for n in nodes if 'BLOCKED' in n.get('label', ''))
    root = next((n for n in nodes if n.get('type') == 'goal'), nodes[0] if nodes else {})
    projects.append({'slug': goal_slug,
                     'title': root.get('label', goal_slug),
                     'nodes': len(nodes), 'done': done,
                     'in_progress': prog, 'blocked': blocked})
master = {'graph_id': 'master-exocortex', 'last_updated': NOW, 'projects': projects,
          'edges': [
              {'from': 'litebox-library-os-organelle-execution-substrate', 'to': 'fail-fast-asymmetric-exocortex', 'type': 'enables'},
              {'from': 'cloudflare-artifacts-competition-agent-git-platform', 'to': 'fail-fast-asymmetric-exocortex', 'type': 'enables'},
              {'from': 'indy-reads-phone-assistant-as-a-real-personal-agent', 'to': 'thesis-defense-canon-pl-proven-indy-reads-slice', 'type': 'enables'},
              {'from': 'graph-hacks-2026-context-forge-falkordb-agent', 'to': 'fail-fast-asymmetric-exocortex', 'type': 'informs'},
              {'from': 'stolen-ssd-recovery', 'to': 'fail-fast-asymmetric-exocortex', 'type': 'informs'},
              {'from': 'bougie-apartment-fund', 'to': 'fail-fast-asymmetric-exocortex', 'type': 'informs'},
          ]}
os.makedirs(f'{WS}/dashboard/data', exist_ok=True)
with open(f'{WS}/dev-graph/master.json', 'w') as f: json.dump(master, f, indent=1)

# ---------------------------------------------------------------- dashboard data: graphs.json
graphs = {'projects': []}
for slug in sorted(glob.glob(f'{WS}/goals/*/hidden_files/dev-graph.json')):
    with open(slug) as f: g = json.load(f)
    goal_slug = slug.split('/goals/')[1].split('/')[0]
    root = next((n for n in g['nodes'] if n.get('type') == 'goal'), {})
    graphs['projects'].append({
        'id': goal_slug, 'title': root.get('label', goal_slug),
        'nodes': [{'id': n['id'], 'label': n['label'], 'type': n.get('type'),
                   'status': n.get('status'), 'evidence': n.get('evidence', 'UNKNOWN')}
                  for n in g['nodes']],
        'edges': [{'from': e.get('from'), 'to': e.get('to'), 'type': e.get('type', 'part_of')} for e in g['edges']],
    })
graphs['master'] = master
with open(f'{WS}/dashboard/data/graphs.json', 'w') as f: json.dump(graphs, f, indent=1)

# ---------------------------------------------------------------- dashboard data: integrations.json
integrations = {'components': [
    {'id': 'phone', 'name': 'Indy_Reads (phone)', 'status': 'in_progress',
     'description': 'Voice control surface. Demo live; Cloudflare migration blocked on route.'},
    {'id': 'eventd', 'name': 'eventd + hooks', 'status': 'done',
     'description': 'Tokio event bus. Agents wake on events, never timers.'},
    {'id': 'governor', 'name': 'Governor + court', 'status': 'done',
     'description': 'Deterministic allocator. Verdict ESTABLISHED, 19/19 tests.'},
    {'id': 'exchange', 'name': 'Free Compute Exchange', 'status': 'done',
     'description': 'Live. NVIDIA + OpenRouter verified. 108 lanes: 2 safe, 50 conditional, 56 gated.'},
    {'id': 'organelles', 'name': 'Organelles (LiteBox hosts)', 'status': 'in_progress',
     'description': 'Hardened host built, cooperative runs proven. Hostile tests blocked.'},
    {'id': 'wreck', 'name': 'wreck (change governance)', 'status': 'in_progress',
     'description': 'Deterministic merge authority. Artifacts competition entry, due Oct 14.'},
    {'id': 'pl', 'name': 'Proof Ledger', 'status': 'done',
     'description': 'Rust hash-chained receipts. lucidota-receipt/1 envelope.'},
    {'id': 'canon', 'name': 'CANON', 'status': 'open',
     'description': 'Authority: what is true, allowed, and why it changed.'},
], 'flows': [
    {'from': 'phone', 'to': 'eventd', 'label': 'voice commands'},
    {'from': 'eventd', 'to': 'governor', 'label': 'events'},
    {'from': 'governor', 'to': 'exchange', 'label': 'task allocation'},
    {'from': 'exchange', 'to': 'organelles', 'label': 'execution'},
    {'from': 'organelles', 'to': 'pl', 'label': 'receipts'},
    {'from': 'governor', 'to': 'wreck', 'label': 'code changes'},
    {'from': 'wreck', 'to': 'pl', 'label': 'merge seals'},
    {'from': 'pl', 'to': 'canon', 'label': 'truth updates'},
]}
with open(f'{WS}/dashboard/data/integrations.json', 'w') as f: json.dump(integrations, f, indent=1)

# ---------------------------------------------------------------- dashboard data: ledger.json (recent entries)
import subprocess
led = []
try:
    files = sorted(glob.glob(os.path.expanduser('~/ledger/ledger-*.jsonl')))[-3:]
    for fp in files:
        out = subprocess.run(['tail', '-200', fp], capture_output=True, text=True).stdout
        for line in out.strip().split('\n'):
            try: o = json.loads(line); led.append(o)
            except: pass
    led = led[-300:]
    slim = [{'seq': o.get('seq'), 'timestamp': o.get('ts') or o.get('timestamp'),
             'actor': o.get('actor'), 'claim': str(o.get('claim') or o.get('summary') or o.get('action'))[:200],
             'evidence_grade': o.get('evidence_grade') or o.get('verdict') or 'UNKNOWN'}
            for o in led]
except Exception as e:
    slim = [{'error': str(e)}]
with open(f'{WS}/dashboard/data/ledger.json', 'w') as f: json.dump(slim, f, indent=1)

print(f'graphs enriched; master: {len(projects)} projects; dashboard data written')
for pr in projects:
    print(f"  {pr['slug'][:45]:45} nodes={pr['nodes']:3} done={pr['done']:3} ip={pr['in_progress']} blocked={pr['blocked']}")
