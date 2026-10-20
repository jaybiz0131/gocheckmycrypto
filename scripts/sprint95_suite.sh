#!/bin/bash
# usage: suite.sh <repo> <tree publish dir> <log> <title>
REPO=$1; TREE=$2; LOG=$3; TITLE=$4
cd "$REPO" || exit 2
echo "$TITLE" > "$LOG"
n=0; bad=0
run() {
  local label="$1"; shift
  echo "===== $label (exit pending)" >> "$LOG.tmp"
  "$@" > "$LOG.out" 2>&1; local rc=$?
  echo "===== $label (exit $rc)" >> "$LOG"; cat "$LOG.out" >> "$LOG"
  n=$((n+1)); [ $rc -ne 0 ] && bad=$((bad+1))
}
run "scripts/btc_hilo_test.py --tree $TREE" python3 scripts/btc_hilo_test.py --tree "$TREE"
run "scripts/canary_clean_test.py " python3 scripts/canary_clean_test.py
run "scripts/chartmaster_publish_test.py" python3 scripts/chartmaster_publish_test.py
run "scripts/coin_pages_test.py --site $TREE" python3 scripts/coin_pages_test.py --site "$TREE"
run "scripts/color_truth_test.py " python3 scripts/color_truth_test.py
run "scripts/etf_floor_test.py " python3 scripts/etf_floor_test.py
run "scripts/masthead_test.py " python3 scripts/masthead_test.py
run "scripts/morning_test.py " python3 scripts/morning_test.py
run "scripts/slot_guard_test.py " python3 scripts/slot_guard_test.py
run "scripts/sprint81_test.py " python3 scripts/sprint81_test.py
run "scripts/sprint82_test.py " python3 scripts/sprint82_test.py
run "scripts/sprint91_test.py " python3 scripts/sprint91_test.py
run "scripts/sprint92_test.py " python3 scripts/sprint92_test.py
run "scripts/sprint93_test.py " python3 scripts/sprint93_test.py
run "scripts/sprint94_test.py " python3 scripts/sprint94_test.py
run "scripts/sprint95_test.py --tree $TREE" python3 scripts/sprint95_test.py --tree "$TREE"
run "scripts/sprint96_test.py --tree $TREE" python3 scripts/sprint96_test.py --tree "$TREE"
run "scripts/twins_gate_test.py " python3 scripts/twins_gate_test.py
rm -f "$LOG.tmp" "$LOG.out"
echo "SUITE: $n scripts, $bad with a non-zero exit" >> "$LOG"
