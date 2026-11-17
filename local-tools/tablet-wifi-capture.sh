#!/bin/sh
# tablet-wifi-capture.sh FILE [MINUTES]: runs on the tablet and keeps the Wi-Fi driver's log lines in FILE.
#
# kern.unixnu_wifi_log is a ring of about 500 lines, and the statistics the driver writes every 10 s fill it in about
# 6 minutes. The lines of a scan made while the network is down (after boot, after a wake, after Wi-Fi is switched off and
# on) are gone before an SSH session can read them. This reads the ring every 2 s for MINUTES (default 45) and appends the
# lines it has not written yet, with a `# HH:MM:SS` line of the tablet's clock in front of each batch.
#
# The first field of a line is the driver's time in ms. Lines as old as the newest line already written are written again,
# because more lines can arrive with the same time; read FILE with `awk '!seen[$0]++'`.
#
#   scp tablet-wifi-capture.sh to the tablet, then on the tablet:
#   nohup sh tablet-wifi-capture.sh ~/unixnu-capture/wifi-$(date +%H%M).log >/dev/null 2>&1 &
set -u
file=${1:?usage: tablet-wifi-capture.sh FILE [MINUTES]}
minutes=${2:-45}
mkdir -p "$(dirname "$file")"
last=0
rounds=$(( minutes * 30 ))
while [ "$rounds" -gt 0 ]; do
  rounds=$(( rounds - 1 ))
  batch=$(sysctl -n kern.unixnu_wifi_log 2>/dev/null | awk -v last="$last" '$1 ~ /^[0-9]+$/ && $1 + 0 >= last + 0')
  newest=$(printf '%s\n' "$batch" | awk 'END { print $1 }')
  if [ -n "$newest" ] && [ "$newest" != "$last" ]; then
    { printf '# %s\n' "$(date +%H:%M:%S)"; printf '%s\n' "$batch"; } >> "$file"
    last=$newest
  fi
  sleep 2
done
