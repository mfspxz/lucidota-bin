#!/bin/bash
# usage: burn-receipt.sh provider model purpose tokens_in tokens_out ok note
python3 - <<'PY' "$@"
import json, sys, datetime
prov, model, purpose, ti, to, ok, note = sys.argv[1:8]
line = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
 "lane":"track7-dossier","provider":prov,"model":model,"purpose":purpose,
 "tokens_in":int(ti),"tokens_out":int(to),"ok": ok.lower()=="true","note":note}
open("/home/hatch/workspace/inference-burn/burn.jsonl","a").write(json.dumps(line)+"\n")
print("receipted", prov, model, ok)
PY
