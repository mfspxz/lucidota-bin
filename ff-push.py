#!/usr/bin/env python3
"""Push a local worktree to GitHub as a single fast-forward commit via the Git Data API.

Proxy-safe: uses urllib (OpenSSL), not git's GnuTLS libcurl.
Usage: ff-push.py <owner/repo> <worktree> <branch> <parent-sha> <message>
"""
import base64
import json
import os
import sys
import urllib.request
import urllib.error

REPO, WORKTREE, BRANCH, PARENT, MESSAGE = sys.argv[1:6]
PAT = open("/home/hatch/workspace/keys/GITHUB_PAT").read().strip()
API = f"https://api.github.com/repos/{REPO}"
SKIP_DIRS = {".git", "target", "node_modules", "__pycache__"}


def api(method, path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        API + path, method=method, data=body,
        headers={"Authorization": f"Bearer {PAT}",
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json",
                 "User-Agent": "ff-push"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r) if r.status != 204 else None
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on {method} {path}: {e.read()[:300]}", file=sys.stderr)
        raise


def collect(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            out.append((os.path.relpath(full, root), full))
    return out


def main():
    files = collect(WORKTREE)
    print(f"{len(files)} files -> {REPO}@{BRANCH} (parent {PARENT[:12]})", flush=True)
    tree = []
    for rel, full in files:
        with open(full, "rb") as f:
            raw = f.read()
        try:
            content = raw.decode("utf-8")
            blob = api("POST", "/git/blobs", {"content": content, "encoding": "utf-8"})
        except (UnicodeDecodeError, Exception):
            blob = api("POST", "/git/blobs",
                       {"content": base64.b64encode(raw).decode(), "encoding": "base64"})
        tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    print(f"blobs done: {len(tree)}", flush=True)
    tree_obj = api("POST", "/git/trees", {"tree": tree})
    print(f"tree: {tree_obj['sha'][:12]}", flush=True)
    commit = api("POST", "/git/commits",
                 {"message": MESSAGE, "tree": tree_obj["sha"], "parents": [PARENT]})
    print(f"commit: {commit['sha'][:12]}", flush=True)
    ref = api("PATCH", f"/git/refs/heads/{BRANCH}", {"sha": commit["sha"]})
    print(f"ref updated: {ref['object']['sha'][:12]}", flush=True)


if __name__ == "__main__":
    main()
