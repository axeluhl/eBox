#!/bin/bash
latitude_in_degrees=$1
longitude_in_degrees=$2
inclination_in_degrees=$3
offset_from_south_in_degrees=$4
peak_power_in_kilowatts=$5
version_tag=$6
db_host=$7
database_name=$8
curl -H 'Accept: application/json' "https://api.forecast.solar/estimate/${latitude_in_degrees}/${longitude_in_degrees}/${inclination_in_degrees}/${offset_from_south_in_degrees}/${peak_power_in_kilowatts}" \
  | jq '.result.watts' \
  | tail -n +2 \
  | head -n -1 \
  | sed -e 's/"\([-0-9]*\) \([:0-9]*\)": \([0-9]*\),\?/\1T\2 \3/' \
  | while read t w; do
    influx -host ${db_host} -database ${database_name} -execute "insert forecasts,version=\"${version_tag}\" watts=${w} $(date --date ${t} +%s)000000000"
  done
