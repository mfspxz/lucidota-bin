#!/usr/bin/env python3
# DEPRECATED (2026-10-10, rust-audit): ported to Rust — see
# ~/workspace/rust-audit/rs/src/bin/devgraph-rs.rs
# Archive-don't-delete: this file still runs, but new work goes to the Rust binary.
"""devgraph — SOTA dev-graph toolkit for every project.

Usage:
  devgraph.py init <goal-slug> [--title TITLE]
  devgraph.py add-node <slug> <id> <label> <type> [--owner O] [--status S]
  devgraph.py add-edge <slug> <from-id> <rel> <to-id>
  devgraph.py set-status <slug> <id> <open|in_progress|done>
  devgraph.py ready <slug>        # open nodes with all enables-predecessors done
  devgraph.py blocked <slug>      # open nodes with unfinished enables-predecessors
  devgraph.py stats <slug>
  devgraph.py validate <slug>

Graph lives at ~/workspace/goals/<slug>/hidden_files/dev-graph.json
Schema: ~/workspace/dev-graph/SCHEMA.md
"""
import json, os, sys
from collections import Counter
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
RELS = {"part_of", "informs", "enables", "tests", "demos", "targets",
        "mitigates", "decides", "scheduled_for"}
TYPES = {"goal", "track", "feature", "research", "design", "plan", "practice",
         "ktest", "benchmark", "query", "demo_beat", "schema_label", "decision",
         "risk", "deliverable", "milestone", "task", "epic"}
STATUSES = ("open", "in_progress", "done")

def path(slug):
    return os.path.join(HOME, "workspace", "goals", slug, "hidden_files", "dev-graph.json")

def load(slug):
    with open(path(slug)) as f:
        return json.load(f)

def save(slug, d):
    d["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(path(slug), "w") as f:
        json.dump(d, f, indent=2)

def cmd_init(slug, title=None):
    p = path(slug)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p):
        print(f"exists: {p}")
        return
    d = {"graph_id": f"{slug}-dev-graph",
         "nodes": [{"id": "goal-root", "label": title or slug,
                    "type": "goal", "status": "open", "owner": "muse"}],
         "edges": [], "last_updated": ""}
    save(slug, d)
    print(f"initialized {p}")

def cmd_add_node(slug, nid, label, ntype, owner="muse", status="open"):
    assert ntype in TYPES, f"unknown type {ntype}"
    assert status in STATUSES
    d = load(slug)
    if any(n["id"] == nid for n in d["nodes"]):
        print(f"node {nid} exists, skipping")
        return
    d["nodes"].append({"id": nid, "label": label, "type": ntype,
                       "status": status, "owner": owner})
    save(slug, d)
    print(f"added node {nid}")

def cmd_add_edge(slug, frm, rel, to):
    assert rel in RELS, f"unknown rel {rel} (closed vocabulary)"
    d = load(slug)
    ids = {n["id"] for n in d["nodes"]}
    assert frm in ids and to in ids, "dangling edge"
    if any(e["from"] == frm and e["rel"] == rel and e["to"] == to for e in d["edges"]):
        print("edge exists, skipping")
        return
    d["edges"].append({"from": frm, "rel": rel, "to": to})
    save(slug, d)
    print(f"added edge {frm} -{rel}-> {to}")

def cmd_set_status(slug, nid, status):
    assert status in STATUSES
    d = load(slug)
    order = {s: i for i, s in enumerate(STATUSES)}
    for n in d["nodes"]:
        if n["id"] == nid:
            if order[status] < order[n["status"]]:
                print(f"REFUSED: backward transition {n['status']} -> {status}")
                sys.exit(1)
            n["status"] = status
            save(slug, d)
            print(f"{nid} -> {status}")
            return
    print(f"unknown node {nid}")
    sys.exit(1)

def _pred_done(d, nid):
    """True if all enables-predecessors of nid are done."""
    preds = [e["from"] for e in d["edges"]
             if e["to"] == nid and e["rel"] == "enables"]
    st = {n["id"]: n["status"] for n in d["nodes"]}
    return all(st.get(p) == "done" for p in preds)

def cmd_ready(slug):
    d = load(slug)
    out = [n for n in d["nodes"]
           if n["status"] == "open" and _pred_done(d, n["id"])
           and n["type"] not in ("goal", "milestone")]
    for n in out:
        print(f"{n['id']} [{n['type']}] {n['label']}")
    if not out:
        print("nothing ready")

def cmd_blocked(slug):
    d = load(slug)
    st = {n["id"]: n["status"] for n in d["nodes"]}
    out = [n for n in d["nodes"]
           if n["status"] in ("open", "in_progress")
           and not _pred_done(d, n["id"])]
    for n in out:
        preds = [e["from"] for e in d["edges"]
                 if e["to"] == n["id"] and e["rel"] == "enables"
                 and st.get(e["from"]) != "done"]
        print(f"{n['id']} [{n['status']}] waiting on: {', '.join(preds)}")
    if not out:
        print("nothing blocked")

def cmd_stats(slug):
    d = load(slug)
    print(f"nodes: {len(d['nodes'])}, edges: {len(d['edges'])}")
    print("by type:", dict(Counter(n["type"] for n in d["nodes"])))
    print("by status:", dict(Counter(n["status"] for n in d["nodes"])))

def cmd_validate(slug):
    d = load(slug)
    ids = {n["id"] for n in d["nodes"]}
    errs = []
    for e in d["edges"]:
        if e["from"] not in ids or e["to"] not in ids:
            errs.append(f"dangling edge {e}")
        if e["rel"] not in RELS:
            errs.append(f"unknown rel {e['rel']}")
    for n in d["nodes"]:
        if n["type"] not in TYPES:
            errs.append(f"unknown type {n['type']} on {n['id']}")
        if n["status"] not in STATUSES:
            errs.append(f"bad status {n['status']} on {n['id']}")
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    print(f"valid: {len(d['nodes'])} nodes, {len(d['edges'])} edges")

CMDS = {"init": cmd_init, "add-node": cmd_add_node, "add-edge": cmd_add_edge,
        "set-status": cmd_set_status, "ready": cmd_ready, "blocked": cmd_blocked,
        "stats": cmd_stats, "validate": cmd_validate}

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=list(CMDS))
    ap.add_argument("args", nargs="*")
    ap.add_argument("--title", default=None)
    ap.add_argument("--owner", default="muse")
    ap.add_argument("--status", default="open")
    a = ap.parse_args()
    if a.cmd == "init":
        cmd_init(a.args[0], a.title)
    elif a.cmd == "add-node":
        cmd_add_node(a.args[0], a.args[1], a.args[2], a.args[3],
                     owner=a.owner, status=a.status)
    elif a.cmd == "add-edge":
        cmd_add_edge(a.args[0], a.args[1], a.args[2], a.args[3])
    elif a.cmd == "set-status":
        cmd_set_status(a.args[0], a.args[1], a.args[2])
    elif a.cmd in ("ready", "blocked", "stats", "validate"):
        CMDS[a.cmd](a.args[0])
