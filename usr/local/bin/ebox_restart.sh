#!/bin/bash
if [ -z "$1" ]; then
  echo "Usage: $0 [ -u {username} ] [ -p {password} ] [ -h {hostname} ]"
  echo "The default username is \"admin\"; the default hostname is \"ebox.axeluhl.de\""
  echo "The username may also be specified using the EBOX_USERNAME environment variable."
  echo "The password may also be specified using the EBOX_PASSWORD environment variable."
  echo "The username may also be specified using the EBOX_HOSTNAME environment variable."
fi
options=':u:p:h:'
while getopts $options option
do
    case $option in
        u) EBOX_USERNAME=$OPTARG;;
        p) EBOX_PASSWORD=$OPTARG;;
        h) EBOX_HOSTNAME=$OPTARG;;
        \?) echo "Invalid option"
            exit 4;;
    esac
done
shift $((OPTIND-1))
if [ -z "${EBOX_HOSTNAME}" ]; then
  EBOX_HOSTNAME="ebox.axeluhl.de"
fi
if [ -z "${EBOX_USERNAME}" ]; then
  EBOX_USERNAME="admin"
fi
if [ -z "${EBOX_PASSWORD}" ]; then
  echo "No password specified. Aborting!" >&2
  exit 2
fi
ECU_SESSION_COOKIE=$( curl -D - -s -o /dev/null -k 'https://'${EBOX_HOSTNAME}'/cgi_c_login' -X POST -H 'Content-Type: application/x-www-form-urlencoded' --data-raw 'username='${EBOX_USERNAME}'&password='${EBOX_PASSWORD} | grep "Set-Cookie: ecu_session=" | sed -e 's/^Set-Cookie: //' | tr -d '\r' )
curl -k -s -i -H 'Cookie: '${ECU_SESSION_COOKIE} 'https://'${EBOX_HOSTNAME}'/cgi_s_system.reset' >/dev/null
curl -k -s -i -H 'Cookie: '${ECU_SESSION_COOKIE} 'https://'${EBOX_HOSTNAME}'/cgi_c_system.reset-trigger_restart' -X POST --data-raw 'restart=1' | grep "<div class=\"box\">" | tail -1
