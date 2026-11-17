#!/bin/sh
# tablet-sleep-cycles.sh FILE [CYCLES]: runs on the tablet; puts it to sleep CYCLES times (default 10), each time
# waiting for the wake, and writes one line per cycle to FILE.
#
# The network is not needed while it runs: Wi-Fi does not come back by itself after a wake, so an SSH session cannot
# drive the cycles. With the lid open the 60 s timer wakes the tablet; a key press during the 30 s before the sleep
# cancels that cycle, which the line then says ("no sleep").
#
# A line: the cycle, when `pmset sleepnow` ran, kern.sleeptime and kern.waketime after it, the sleep count, the
# WindowServer pid. The kernel's own lines (`sheng sleep: woke by ...`) are read afterwards with
#   /usr/bin/log show --start '<date time>' --info | grep -E 'sheng sleep|IOCPUSleepKernel|panel back'
#
#   scp tablet-sleep-cycles.sh to the tablet, then on the tablet:
#   nohup sh tablet-sleep-cycles.sh ~/unixnu-capture/sleep-cycles-$(date +%H%M).log >/dev/null 2>&1 &
set -u
file=${1:?usage: tablet-sleep-cycles.sh FILE [CYCLES]}
cycles=${2:-10}
mkdir -p "$(dirname "$file")"
seconds() { sysctl -n "$1" | sed -E 's/^\{ sec = ([0-9]+).*/\1/'; }
clock() { sysctl -n "$1" | sed -E 's/.* ([0-9]{2}:[0-9]{2}:[0-9]{2}) .*/\1/'; }
count() { pmset -g stats | sed -n 's/^Sleep Count://p'; }
server() { ps -axo pid,comm | awk '$2 ~ /WindowServer$/ { print $1 }'; }
echo "# $(date '+%Y-%m-%d %H:%M:%S') start: $cycles cycles, sleep count $(count), WindowServer $(server)" >> "$file"
cycle=0
while [ "$cycle" -lt "$cycles" ]; do
  cycle=$(( cycle + 1 ))
  woke=$(seconds kern.waketime)
  asked=$(date +%H:%M:%S)
  pmset sleepnow >/dev/null 2>&1
  # The script stops with the system and goes on at the wake; 300 s covers the 30 s before the sleep and the 60 s timer.
  waited=0
  while [ "$(seconds kern.waketime)" = "$woke" ] && [ "$waited" -lt 150 ]; do
    sleep 2
    waited=$(( waited + 1 ))
  done
  if [ "$(seconds kern.waketime)" = "$woke" ]; then
    echo "cycle $cycle asked $asked: no sleep within 300 s; sleep count $(count), WindowServer $(server)" >> "$file"
  else
    echo "cycle $cycle asked $asked: slept $(clock kern.sleeptime), woke $(clock kern.waketime); sleep count $(count), WindowServer $(server)" >> "$file"
  fi
  # Past the 10 s the system holds itself awake after a wake on power.
  sleep 20
done
echo "# $(date '+%Y-%m-%d %H:%M:%S') done: sleep count $(count), WindowServer $(server)" >> "$file"
