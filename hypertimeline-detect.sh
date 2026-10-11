#!/usr/bin/env bash
# hypertimeline-detect.sh — one-shot completion detector, run by eventd file
# watches (NOT a poll loop). Usage: hypertimeline-detect.sh <audit|scoreboard|falsification|worklogs>
# Prints {"completion": true|false, ...} to stdout; exit 0 always.
# Stateful via ~/workspace/eventd/state/hypertimeline/ so restarts/debounce
# gaps never double-report or lose completions (next fire catches up).
set -euo pipefail

MODE="${1:?usage: hypertimeline-detect.sh <audit|scoreboard|falsification|worklogs>}"
STATE="$HOME/workspace/eventd/state/hypertimeline"
mkdir -p "$STATE"

complete() { printf '{"completion":true,"watch":"%s","detail":%s}\n' "$MODE" "$1"; }
incomplete() { printf '{"completion":false,"watch":"%s","reason":"%s"}\n' "$MODE" "$1"; }

case "$MODE" in
  audit)
    DIR="$HOME/workspace/dogfood/audit"
    SIG_F="$STATE/audit.files"
    cur="$(find "$DIR" -maxdepth 1 -name '*.md' -printf '%f\n' 2>/dev/null | sort | tr '\n' ' ')"
    prev=""; [ -f "$SIG_F" ] && prev="$(cat "$SIG_F")"
    printf '%s' "$cur" > "$SIG_F"
    if [ -z "$prev" ]; then incomplete "initial watermark"; exit 0; fi
    new=""
    for f in $cur; do
      case " $prev " in *" $f "*) ;; *) new="$new $f";; esac
    done
    new="$(printf '%s' "$new" | xargs || true)"
    if [ -n "$new" ]; then
      payload="$(printf '%s' "$new" | tr ' ' '\n' | jq -R . | jq -s -c .)"
      complete "{\"new_files\":$payload}"
    else
      incomplete "no new audit files"
    fi
    ;;
  scoreboard)
    BOARD="$HOME/workspace/dogfood/track-j/SWARM-SCOREBOARD.md"
    HASH_F="$STATE/scoreboard.hash"
    [ -f "$BOARD" ] || { incomplete "scoreboard missing"; exit 0; }
    h="$(sha256sum "$BOARD" | cut -d' ' -f1)"
    prev=""; [ -f "$HASH_F" ] && prev="$(cat "$HASH_F")"
    printf '%s' "$h" > "$HASH_F"
    if [ -z "$prev" ]; then incomplete "initial watermark"; exit 0; fi
    if [ "$h" != "$prev" ]; then
      tail_ctx="$(tail -6 "$BOARD" | cut -c1-300 | jq -R . | jq -s -c .)"
      complete "{\"tail\":$tail_ctx}"
    else
      incomplete "scoreboard unchanged"
    fi
    ;;
  falsification)
    FALS="$HOME/workspace/compute/falsification.jsonl"
    OFF_F="$STATE/falsification.offset"
    [ -f "$FALS" ] || { incomplete "falsification log missing"; exit 0; }
    cur="$(wc -l < "$FALS" | tr -d ' ')"
    first_run=0; [ -f "$OFF_F" ] || first_run=1
    prev=0; [ "$first_run" = "0" ] && prev="$(cat "$OFF_F" | tr -d ' ' || echo 0)"
    printf '%s' "$cur" > "$OFF_F"
    if [ "$first_run" = "1" ]; then incomplete "initial watermark"; exit 0; fi
    if [ "$cur" -gt "$prev" ]; then
      hits="$(tail -n +"$((prev + 1))" "$FALS" | grep -iE 'FIXED|RESOLVED|SUPERSEDED|fix-verification|fix_holds|FIX-HOLDS' | head -10 | cut -c1-400 | jq -R . | jq -s -c . || echo '[]')"
      if [ "$hits" != "[]" ]; then
        complete "{\"new_entries\":$hits}"
      else
        incomplete "new entries but no fix completions"
      fi
    else
      incomplete "no new entries"
    fi
    ;;
  worklogs)
    SIG_F="$STATE/worklogs.sig"
    files="$HOME/workspace/adversarial/WORK-LOG.md
$HOME/workspace/apk-build/WORK-LOG.md
$HOME/workspace/batch-compile/WORK-LOG.md
$HOME/workspace/graph-recalibration/WORK-LOG.md
$HOME/workspace/lifelog/WORK-LOG-2026-10-07.md
$HOME/workspace/marketplace/WORK-LOG.md
$HOME/workspace/tentacle-corp/infra/heartbeat/WORK-LOG.md"
    cur=""
    for f in $files; do
      [ -f "$f" ] && cur+="$f:$(stat -c '%s:%Y' "$f");"
    done
    prev=""; [ -f "$SIG_F" ] && prev="$(cat "$SIG_F")"
    printf '%s' "$cur" > "$SIG_F"
    if [ -z "$prev" ]; then incomplete "initial watermark"; exit 0; fi
    changed=""
    for f in $files; do
      [ -f "$f" ] || continue
      o="$(printf '%s' "$prev" | tr ';' '\n' | grep -F "$f:" || true)"
      n="$(printf '%s' "$cur" | tr ';' '\n' | grep -F "$f:" || true)"
      if [ "$o" != "$n" ]; then
        hits="$(tail -25 "$f" | grep -iE 'complet|DONE|shipped|all green|FIXED|wave.*done' | cut -c1-250 | head -4 | tr '\n' '|')"
        [ -n "$hits" ] && changed+="$f :: $hits"$'\n'
      fi
    done
    if [ -n "$changed" ]; then
      payload="$(printf '%s' "$changed" | jq -R . | jq -s -c .)"
      complete "{\"completions\":$payload}"
    else
      incomplete "worklog changed but no completion markers"
    fi
    ;;
esac
