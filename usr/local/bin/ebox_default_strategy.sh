#!/bin/bash
CONFIG_FILE=/etc/ebox_defaults.conf
if [ -f ${CONFIG_FILE} ]; then
  source ${CONFIG_FILE}
fi
if [ "$1" = "" ]; then
  echo "Current default strategy is ${STRATEGY}"
  echo "Call like this to change default strategy:"
  echo "   $0 <new-default-strategy>"
  echo "Example: $0 2"
  echo "  sets 2 as the new default strategy"
  echo "For strategies see the online help of ebox_control.sh"
  `dirname $0`/ebox_control.sh -h
else
  if [ -f ${CONFIG_FILE} ]; then
    newConfigFileContents=$( cat "${CONFIG_FILE}" | sed -e 's/STRATEGY=.*$/STRATEGY='${1}'/' )
    echo "${newConfigFileContents}" >"${CONFIG_FILE}"
  else
    echo "STRATEGY=$1" >"${CONFIG_FILE}"
    chgrp ebox "${CONFIG_FILE}"
    chmod 664 "${CONFIG_FILE}"
  fi
fi
