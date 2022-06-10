#!/bin/bash
CONFIG_FILE=/etc/ebox_defaults.conf
if [ -f ${CONFIG_FILE} ]; then
  source ${CONFIG_FILE}
fi
if [ "$1" = "" ]; then
  echo "Current maximum power from battery for wallbox is ${BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS}"
  echo "Call like this to change:"
  echo "   $0 <new-maximum-power-from-battery-for-wallbox-in-watts>"
  echo "Example: $0 2000"
  echo "  blocks home battery discharge if wallbox draws more than 2000W"
else
  if [ -f ${CONFIG_FILE} ]; then
    newConfigFileContents=$( cat "${CONFIG_FILE}" | sed -e 's/BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS=.*$/BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS='${1}'/' )
    echo "${newConfigFileContents}" >"${CONFIG_FILE}"
  else
    echo "BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS=$1" >"${CONFIG_FILE}"
    chgrp ebox "${CONFIG_FILE}"
    chmod 664 "${CONFIG_FILE}"
  fi
  logger -t ${0} "User `whoami` set maximum power wallbox can draw from home battery to ${1}"
fi
