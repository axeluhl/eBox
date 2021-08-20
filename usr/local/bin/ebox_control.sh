#!/bin/bash
# Strategy 0: full throttle
# Strategy 1: split excess PV energy evenly between home battery and wallbox: (PV production - Home Usage + Wallbox)/2
# Special cases:
#  - car not connected or full; setting MaxCurrentPhase[123] won't make the wallbox consume energy in this case
#  - home battery SOC >= 99%: allow car to take all excess PV energy (PV production - Home Usage + Wallbox), capped at 32A
# Strategy 2: charge car only with energy otherwise ingested to grid, preferring home battery charging
#  - as soon as 5min average of (PV production - Charge Power - Home Usage + Wallbox) is positive, increase wallbox power limit, min 6A,
#    max (PV production - Charge Power - Home Usage + Wallbox), capped at 32A
# Strategy 3: allow all excess PV power to go into car (PV production - Home Usage + Wallbox)
CONFIG_FILE=/etc/ebox_defaults.conf
if [ -f ${CONFIG_FILE} ]; then
  source "${CONFIG_FILE}"
else
  STRATEGY=0
  NUMBER_OF_PHASES_USED_FOR_CHARGING=1
  MAX_HOME_BATTERY_CHARGE_POWER_IN_WATTS=5560
  MAXIMUM_CURRENT_PER_PHASE_IN_AMPS=50
fi
# Command line option handling:
options=':s:p:mh'
while getopts $options option
do
    case $option in
        s) STRATEGY=$OPTARG;;
        m) MAX_HOME_BATTERY_CHARGE_POWER_IN_WATTS=$OPTARG;;
        p) NUMBER_OF_PHASES_USED_FOR_CHARGING=$OPTARG;;
        h) echo "Usage: $0 [ -s <STRATEGY> ] [ -m <MAX_HOME_BATTERY_CHARGE_POWER_IN_WATTS> ] [ -p <NUMBER_OF_PHASES_USED_FOR_CHARGING> ]"
           echo " STRATEGY: 0 means to open the wallbox throttle entirely; ${MAXIMUM_CURRENT_PER_PHASE_IN_AMPS}A"
           echo "           1 means to split excess PV energy evenly between home battery and wallbox;"
           echo "           2 means to prefer home battery charging and only send to wallbox what would otherwise be ingested to grid."
           echo "           3 means to prefer car charging and only send to the home battery what would otherwise be ingested to grid."
           echo "           Default is ${STRATEGY}."
           exit 5;;
        \?) echo "Invalid option"
            exit 4;;
    esac
done

influx -host yourinfluxhost.example.com -database kostal -execute 'select mean("PV production"), mean("Home own consumption"), mean("Act. state of charge"), mean("Battery Charge") from pv where time > now()-5m' | tail -1 | while read time pvProductionInWatts homeOwnConsumptionInWatts SOCInPercent batteryDischargePowerInWatts; do
  influx -host yourinfluxhost.example.com -database kostal -execute 'select mean(CurrentPhase1)+mean(CurrentPhase2)+mean(CurrentPhase3) from ebox where time > now()-5m' | tail -1 | while read time eBoxCurrentInAmps; do
    eBoxPowerInWatts=$( echo "${eBoxCurrentInAmps} * 230.0" | bc )
    integerSOCInPercent=$( echo "${SOCInPercent}" | sed -e 's/\..*$//' )
    homeConsumptionWithoutWallboxInWatts=$( echo "${homeOwnConsumptionInWatts} - ${eBoxCurrentInAmps} * 230.0" | bc )
    pvExcessPowerInWatts=$( echo "${pvProductionInWatts} - ${homeConsumptionWithoutWallboxInWatts}" | bc )

    # Debug output:
    echo "PV Production:            ${pvProductionInWatts}W"
    echo "Home w/ wallbox:          ${homeOwnConsumptionInWatts}W"
    echo "Integer SOC:              ${integerSOCInPercent}%"
    echo "Discharge power:          ${batteryDischargePowerInWatts}W"
    echo "eBox Current:             ${eBoxCurrentInAmps}A"
    echo "eBox Power:               ${eBoxPowerInWatts}W"
    echo "Home w/o wallbox:         ${homeConsumptionWithoutWallboxInWatts}W"
    echo "PV Excess Power:          ${pvExcessPowerInWatts}W"

    if [ "${STRATEGY}" = "0" ]; then
      echo "Strategy 0: full throttle, ${MAXIMUM_CURRENT_PER_PHASE_IN_AMPS}A"
      effectiveMaxCurrentPerPhaseInAmps=${MAXIMUM_CURRENT_PER_PHASE_IN_AMPS}
    else
      if [ "${STRATEGY}" = "1" ]; then
        echo "Strategy 1:"
        if [ ${integerSOCInPercent} -ge 99 ]; then
          echo "SOC >= 99%: allow all excess PV power ${pvExcessPowerInWatts}W"
          eBoxAllowedPowerInWatts=${pvExcessPowerInWatts}
        else
          echo "SOC < 99%: allow half of the excess PV power ${pvExcessPowerInWatts}W in order to split evenly with home battery"
          eBoxAllowedPowerInWatts=$( echo "scale=2
                                     ${pvExcessPowerInWatts} / 2" | bc )
        fi
      elif [ "${STRATEGY}" = "2" ]; then
        echo "Strategy 2:"
        if [ ${integerSOCInPercent} -ge 99 ]; then
          echo "SOC >= 99%: allow all excess PV power ${pvExcessPowerInWatts}W"
          eBoxAllowedPowerInWatts=${pvExcessPowerInWatts}
        else
          echo "SOC < 99%: allow excess PV power ${pvExcessPowerInWatts}W beyond what home battery can accept (${MAX_HOME_BATTERY_CHARGE_POWER_IN_WATTS}W)"
          eBoxAllowedPowerInWatts=$( echo "${pvExcessPowerInWatts} - ${MAX_HOME_BATTERY_CHARGE_POWER_IN_WATTS}" | bc )
        fi
      elif [ "${STRATEGY}" = "3" ]; then
        echo "Strategy 3: allow all excess PV power ${pvExcessPowerInWatts}W"
        eBoxAllowedPowerInWatts=${pvExcessPowerInWatts}
      else
        echo "Strategy ${STRATEGY} not known. Leaving wallbox configuration unchanged."
        exit 1
      fi
      echo "Allowed eBox Power:       ${eBoxAllowedPowerInWatts}W"
      maxCurrentPerPhase=$( echo "scale=2
                            ${eBoxAllowedPowerInWatts} / 230 / ${NUMBER_OF_PHASES_USED_FOR_CHARGING}" | bc )
      echo "Max current per phase:    ${maxCurrentPerPhase}A"
      integerMaxCurrentPerPhaseInAmps=$( echo "${maxCurrentPerPhase}" | sed -e 's/\..*$//' )
      echo "Integer max cur./phase:   ${integerMaxCurrentPerPhaseInAmps}"
      if [ ${integerMaxCurrentPerPhaseInAmps} -le 0 ]; then
        effectiveMaxCurrentPerPhaseInAmps=0
      elif [ ${integerMaxCurrentPerPhaseInAmps} -le 6 ]; then
        effectiveMaxCurrentPerPhaseInAmps=6
      elif [ ${integerMaxCurrentPerPhaseInAmps} -ge 50 ]; then
        effectiveMaxCurrentPerPhaseInAmps=50
      else
        effectiveMaxCurrentPerPhaseInAmps=${maxCurrentPerPhase}
      fi
    fi
    echo "Effective max cur./phase: ${effectiveMaxCurrentPerPhaseInAmps}A"
    logger -t ebox_control "Setting maximum current per phase for eBox wallbox to ${effectiveMaxCurrentPerPhaseInAmps}A"
    `dirname "${0}"`/ebox_write.py ${effectiveMaxCurrentPerPhaseInAmps} ${effectiveMaxCurrentPerPhaseInAmps} ${effectiveMaxCurrentPerPhaseInAmps}
  done
done