#!/bin/bash
# Watch for a reply from the ManageStrata.ca founder (prospective client #1).
# Zack's top interrupt priority (2026-10-10): the moment his email comes back,
# surface it immediately. Fire-only-on-new-hit; silent otherwise.
# Outreach: contact-form message via managestrata.ca/contact as Zachary Cameron
# (Zack@cutecity.cc). Replies route to Zack@cutecity.cc -> forwarded to Gmail.
SEEN_FILE="$HOME/workspace/inference-burn/../growth-agency/.managestrata-reply-seen"
mkdir -p "$(dirname "$SEEN_FILE")"
touch "$SEEN_FILE"

# Inbound mail to the outreach address in the last day, excluding our own sends.
RESULTS=$(hatch_gws_cli gmail +triage --query 'to:Zack@cutecity.cc newer_than:1d -from:me' --max 20 --format json 2>/dev/null)
if [ -z "$RESULTS" ]; then
  echo "NO_HIT (query empty/failed)"
  exit 0
fi

HITS=$(echo "$RESULTS" | python3 -c "
import json,sys,re
seen = set(open('$SEEN_FILE').read().split())
try:
    data = json.load(sys.stdin)
except Exception:
    print('QUERY_PARSE_FAIL'); sys.exit()
msgs = data if isinstance(data, list) else data.get('messages', data.get('results', []))
new = []
for m in msgs:
    mid = str(m.get('id', m.get('message_id', '')))
    frm = str(m.get('from', m.get('sender',''))).lower()
    subj = str(m.get('subject','')).lower()
    snip = str(m.get('snippet','')).lower()
    blob = frm + ' ' + subj + ' ' + snip
    if mid and mid not in seen and re.search(r'managestrata|strata', blob):
        new.append((mid, m.get('from', m.get('sender','?')), m.get('subject','(no subject)'), m.get('date', m.get('internal_date','?'))))
for mid, frm, subj, dt in new:
    print(f'HIT|{mid}|{frm}|{subj}|{dt}')
    seen.add(mid)
open('$SEEN_FILE','w').write('\n'.join(sorted(seen)))
" 2>/dev/null)

if [ -z "$HITS" ] || [ "$HITS" = "QUERY_PARSE_FAIL" ]; then
  echo "NO_HIT"
  exit 0
fi
echo "$HITS"
