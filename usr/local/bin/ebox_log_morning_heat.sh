#!/bin/bash
firstOfNovember2021=1635744600
week=0
while [ "1" ]; do
  for day in 0 1 2 3 4; do
    time=$(( ${firstOfNovember2021} + (7*week + day)*24*3600 ))
    date="$( date --date @${time} )"
    now=$(date +%s)
    if [ ${time} -gt ${now} ]; then
      exit 0
    fi
    influx -host klo -format json -execute "use kostal
    select sum(CurrentPhase1) from ebox where time>${time}000000000 and time<$(( ${time} + 60*30 ))000000000" | tail -n -1 | jq -r '[.results[0].series[0].values[0][0], '${day}', "'"${date}"'", .results[0].series[0].values[0][1]] | tostring' | sed -e 's/^\[\(.*\)\]$/\1/'
  done
  week=$(( ${week} + 1 ))
done
