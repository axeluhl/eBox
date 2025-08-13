#!/bin/bash
# For regular (typically every minute) execution, e.g., through a cron job.
# Reads the config file and if a balanced strategy is used adjusts the maximum
# wallbox charging power according to excess power available.
# Furthermore, home battery discharging may be blocked if the wallbox charging power exceeds the value
# provided in the BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS configuration variable.
# To disable this blocking behavior, set BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS
# to a charging power value your wallbox may never exceed, e.g., 500000 (Watts)
#
# It is important to note the following boundary conditions for the Innogy eBox Professional,
# at least at its firmware version 1.3.38:
#  - when setting MaxCurrentPhase[1-3], all three phases will effectively be set to the
#    minimum of the values set for the three phases; e.g., 6/0/0 will effectively result
#    in 0/0/0 being set; or 6/9/9 will result in 6/6/6 being set. This means, in particular,
#    that there is no point in trying to dynamically switch off one or two phases to reduce
#    total charging current below 3*6A in case three-phase charging is possible.
#  - when trying to adjust the number of phases used for charging, an "app restart"
#    is required; this, in turn, requires both cable ends to be unplugged. Therefore,
#    we're stuck with the number of phases in this rather short-term control loop.
#  - at least with a Skoda Superb iV (2024 model), two-phase charging does not work
#
# Strategy 0: full throttle
# Strategy 1: split excess PV energy evenly between home battery and wallbox: (PV production - Home Usage w/o Wallbox)/2
# Special cases:
#  - car not connected or full; setting MaxCurrentPhase[123] won't make the wallbox consume energy in this case
#  - home battery SOC >= ${SOC_THRESHOLD_FOR_FULL_EXCESS}%: allow car to take all excess PV energy (PV production - Home Usage + Wallbox), capped at 32A
# Strategy 2: charge car only with energy otherwise ingested to grid, preferring home battery charging
#  - as soon as 5min average of (PV production - Charge Power - Home Usage w/o Wallbox) is positive, increase wallbox power limit, min 6A,
#    max (PV production - Charge Power - Home Usage + Wallbox), capped at 32A
# Strategy 3: allow all excess PV power to go into car (PV production - Home Usage w/o Wallbox)
# Strategy 4: pump all excess PV plus available home battery energy into car, avoiding use of grid and make room in home battery
CONFIG_FILE=/etc/ebox_defaults.conf
if [ -f ${CONFIG_FILE} ]; then
  source "${CONFIG_FILE}"
else
  STRATEGY=0
  MAX_HOME_BATTERY_CHARGE_POWER_IN_WATTS=5560
  MAXIMUM_CURRENT_PER_PHASE_IN_AMPS=50
  SOC_THRESHOLD_FOR_FULL_EXCESS=98
  MIN_HOME_BATTERY_SOC_PERCENT=8
  MINIMUM_CURRENT_PER_PHASE_IN_AMPS=6
  MAX_INVERTER_POWER_IN_WATTS=8100
fi
if [ -z "${NUMBER_OF_PHASES_USED_FOR_CHARGING}" ]; then
  NUMBER_OF_PHASES_USED_FOR_CHARGING=$( ebox_get_number_of_phases.sh )
  # sometimes it seems this doesn't work, for whatever reason; then default to 3:
  if [ -z "${NUMBER_OF_PHASES_USED_FOR_CHARGING}" ]; then
    NUMBER_OF_PHASES_USED_FOR_CHARGING=3
    echo "Couldn't determine the number of phases used for charging. Defaulting to ${NUMBER_OF_PHASES_USED_FOR_CHARGING}"
  fi
fi
# The maximum home battery discharge power defaults to its maximum charge power:
if [ -z "${MAX_HOME_BATTERY_DISCHARGE_POWER_IN_WATTS}" ]; then
  MAX_HOME_BATTERY_DISCHARGE_POWER_IN_WATTS=${MAX_HOME_BATTERY_CHARGE_POWER_IN_WATTS}
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
           echo "           4 means to use all excess PV power plus home battery as long as SOC > MIN_HOME_BATTERY_SOC_PERCENT, but not more than MAX_INVERTER_POWER_IN_WATTS-home consumption"
           echo "           Default is ${STRATEGY}."
           exit 5;;
        \?) echo "Invalid option"
            exit 4;;
    esac
done
INFLUXDB_HOSTNAME=yourinfluxhost.example.com
influx -host "${INFLUXDB_HOSTNAME}" -database kostal -execute 'select mean("PV production"), mean("Home own consumption"), mean("Act. state of charge"), mean("Battery Charge") from pv where time > now()-2m' | tail -1 | while read time pvProductionInWatts homeOwnConsumptionInWatts SOCInPercent batteryDischargePowerInWatts; do
  influx -host "${INFLUXDB_HOSTNAME}" -database kostal -execute 'select mean(CurrentPhase1)+mean(CurrentPhase2)+mean(CurrentPhase3) from ebox where time > now()-2m' | tail -1 | while read time eBoxCurrentInAmps; do
    eBoxPowerInWatts=$( echo "${eBoxCurrentInAmps} * 230.0" | bc )
    integerSOCInPercent=$( echo "${SOCInPercent}" | sed -e 's/\..*$//' )
    homeConsumptionWithoutWallboxInWatts=$( echo "${homeOwnConsumptionInWatts} - ${eBoxCurrentInAmps} * 230.0" | bc )
    pvExcessPowerInWatts=$( echo "${pvProductionInWatts} - ${homeConsumptionWithoutWallboxInWatts}" | bc )
    # Debug output:
    echo "Number of phases:         ${NUMBER_OF_PHASES_USED_FOR_CHARGING}"
    echo "PV Production:            ${pvProductionInWatts}W"
    echo "Home w/ wallbox:          ${homeOwnConsumptionInWatts}W"
    echo "Integer SOC:              ${integerSOCInPercent}%"
    echo "Discharge power:          ${batteryDischargePowerInWatts}W"
    echo "eBox Current:             ${eBoxCurrentInAmps}A"
    echo "eBox Power:               ${eBoxPowerInWatts}W"
    echo "Home w/o wallbox:         ${homeConsumptionWithoutWallboxInWatts}W"
    echo "PV Excess Power:          ${pvExcessPowerInWatts}W"
    # Strategy evaluation, computing eboxAllowedPowerInWatts and from it effectiveMaxCurrentPerPhaseInAmps[]:
    if [ "${STRATEGY}" = "0" ]; then
      echo "Strategy 0: full throttle, ${MAXIMUM_CURRENT_PER_PHASE_IN_AMPS}A"
      effectiveMaxCurrentPerPhaseInAmps=(${MAXIMUM_CURRENT_PER_PHASE_IN_AMPS} ${MAXIMUM_CURRENT_PER_PHASE_IN_AMPS} ${MAXIMUM_CURRENT_PER_PHASE_IN_AMPS})
    else
      # another strategy where wallbox may need throttling, depending on available power
      # from PV and/or home battery: start determining the eBoxAllowedPowerInWatts, then
      # determine how to map that to the phases available and assign to
      # effectiveMaxCurrentPerPhaseInAmps
      if [ "${STRATEGY}" = "1" ]; then
        echo "Strategy 1:"
        if [ ${integerSOCInPercent} -ge ${SOC_THRESHOLD_FOR_FULL_EXCESS} ]; then
          echo "SOC >= ${SOC_THRESHOLD_FOR_FULL_EXCESS}%: allow all excess PV power ${pvExcessPowerInWatts}W"
          eBoxAllowedPowerInWatts=${pvExcessPowerInWatts}
        else
          echo "SOC < ${SOC_THRESHOLD_FOR_FULL_EXCESS}%: allow half of the excess PV power ${pvExcessPowerInWatts}W in order to split evenly with home battery"
          eBoxAllowedPowerInWatts=$( echo "scale=2
                                     ${pvExcessPowerInWatts} / 2" | bc )
        fi
      elif [ "${STRATEGY}" = "2" ]; then
        echo "Strategy 2:"
        if [ ${integerSOCInPercent} -ge ${SOC_THRESHOLD_FOR_FULL_EXCESS} ]; then
          echo "SOC >= ${SOC_THRESHOLD_FOR_FULL_EXCESS}%: allow all excess PV power ${pvExcessPowerInWatts}W"
          eBoxAllowedPowerInWatts=${pvExcessPowerInWatts}
        else
          echo "SOC < ${SOC_THRESHOLD_FOR_FULL_EXCESS}%: allow excess PV power ${pvExcessPowerInWatts}W beyond what home battery can accept \(${MAX_HOME_BATTERY_CHARGE_POWER_IN_WATTS}W\)"
          eBoxAllowedPowerInWatts=$( echo "${pvExcessPowerInWatts} - ${MAX_HOME_BATTERY_CHARGE_POWER_IN_WATTS}" | bc )
        fi
      elif [ "${STRATEGY}" = "3" ]; then
        echo "Strategy 3: allow all excess PV power ${pvExcessPowerInWatts}W"
        eBoxAllowedPowerInWatts=${pvExcessPowerInWatts}
      elif [ "${STRATEGY}" = "4" ]; then
        integerHomeConsumptionWithoutWallboxInWatts=$( echo "${homeConsumptionWithoutWallboxInWatts}" | sed -e 's/\..*$//' )
        echo "Strategy 4: use PV excess and home battery if SOC > MIN_HOME_BATTERY_SOC_PERCENT, but no more than MAX_INVERTER_POWER_IN_WATTS-homeConsumptionWithoutWallboxInWatts"
        echo "            so no more than ${MAX_INVERTER_POWER_IN_WATTS}W-${homeConsumptionWithoutWallboxInWatts}W=$(( MAX_INVERTER_POWER_IN_WATTS - integerHomeConsumptionWithoutWallboxInWatts ))W"
        if [ ${integerSOCInPercent} -ge ${MIN_HOME_BATTERY_SOC_PERCENT} ]; then
          eBoxAllowedPowerInWatts=$( echo "${pvExcessPowerInWatts} + ${MAX_HOME_BATTERY_DISCHARGE_POWER_IN_WATTS}" | bc )
          echo "            SOC >= ${MIN_HOME_BATTERY_SOC_PERCENT}%; using PV excess ${pvExcessPowerInWatts}W + ${MAX_HOME_BATTERY_DISCHARGE_POWER_IN_WATTS}W = ${eBoxAllowedPowerInWatts}W"
        else
          eBoxAllowedPowerInWatts=${pvExcessPowerInWatts}
          echo "            SOC < ${MIN_HOME_BATTERY_SOC_PERCENT}%; using only PV excess ${pvExcessPowerInWatts}W"
        fi
        integerEBoxAllowedPowerInWatts=$( echo "${eBoxAllowedPowerInWatts}" | sed -e 's/\..*$//' )
        if [ ${integerEBoxAllowedPowerInWatts} -ge $(( MAX_INVERTER_POWER_IN_WATTS - integerHomeConsumptionWithoutWallboxInWatts )) ]; then
          echo "            reducing to MAX_INVERTER_POWER_IN_WATTS - homeConsumptionWithoutWallboxInWatts, so ${MAX_INVERTER_POWER_IN_WATTS}W - ${integerHomeConsumptionWithoutWallboxInWatts}W = $(( MAX_INVERTER_POWER_IN_WATTS - integerHomeConsumptionWithoutWallboxInWatts ))W"
          eBoxAllowedPowerInWatts=$(( MAX_INVERTER_POWER_IN_WATTS - integerHomeConsumptionWithoutWallboxInWatts ))
        fi
      else
        echo "Strategy ${STRATEGY} not known. Leaving wallbox configuration unchanged."
        exit 1
      fi
      echo "Allowed eBox Power:       ${eBoxAllowedPowerInWatts}W"
      maxTotalCurrent=$( echo "scale=2
                         ${eBoxAllowedPowerInWatts} / 230" | bc )
      maxCurrentPerPhase=$( echo "scale=2
                            ${eBoxAllowedPowerInWatts} / 230 / ${NUMBER_OF_PHASES_USED_FOR_CHARGING}" | bc )
      echo "Max current per phase:    ${maxCurrentPerPhase}A"
      echo "Max total current:        ${maxTotalCurrent}A"
      integerMaxTotalCurrent=$( echo "${maxTotalCurrent}" | sed -e 's/\..*$//' | sed -e 's/^-\?$/0/' )
      integerMaxCurrentPerPhaseInAmps=$( echo "${maxCurrentPerPhase}" | sed -e 's/\..*$//' | sed -e 's/^-\?$/0/' )
      echo "Integer max cur./phase:   ${integerMaxCurrentPerPhaseInAmps}"
      # Now map the total current to the phases available, considering the 6A current minimum on each phase.
      # Unfortunately, we can only have equal current limit for all three phases, especially with three-phase
      # charging, so there our lower limit for charging power is 6A*230V*3=4140W
      # Anything less than at least half the minimum current possible (6A/2=3A) on a single phase only
      # shall not lead to car charging as it would drain the home battery too much.
      HALF_MINIMUM_CURRENT_PER_PHASE_IN_AMPS=$(( MINIMUM_CURRENT_PER_PHASE_IN_AMPS / 2 ))
      echo "Minimum current per phase: ${MINIMUM_CURRENT_PER_PHASE_IN_AMPS}A; half minimum current per phase: ${HALF_MINIMUM_CURRENT_PER_PHASE_IN_AMPS=}A"
      if [ ${integerMaxCurrentPerPhaseInAmps} -lt ${HALF_MINIMUM_CURRENT_PER_PHASE_IN_AMPS} ]; then
        echo "Less than half minimum current on single phase \(${HALF_MINIMUM_CURRENT_PER_PHASE_IN_AMPS}A\); stopping charge"
        effectiveMaxCurrentPerPhaseInAmps=(0 0 0)
      elif [ ${integerMaxCurrentPerPhaseInAmps} -lt ${MINIMUM_CURRENT_PER_PHASE_IN_AMPS} ]; then
        echo "Using minimum current on each available phase"
        effectiveMaxCurrentPerPhaseInAmps=(${MINIMUM_CURRENT_PER_PHASE_IN_AMPS} ${MINIMUM_CURRENT_PER_PHASE_IN_AMPS} ${MINIMUM_CURRENT_PER_PHASE_IN_AMPS})
      elif [ ${integerMaxCurrentPerPhaseInAmps} -ge ${MAXIMUM_CURRENT_PER_PHASE_IN_AMPS} ]; then
        effectiveMaxCurrentPerPhaseInAmps=(${MAXIMUM_CURRENT_PER_PHASE_IN_AMPS} ${MAXIMUM_CURRENT_PER_PHASE_IN_AMPS} ${MAXIMUM_CURRENT_PER_PHASE_IN_AMPS})
      else
        effectiveMaxCurrentPerPhaseInAmps=(${maxCurrentPerPhase} ${maxCurrentPerPhase} ${maxCurrentPerPhase})
      fi
    fi
    echo "Effective max cur./phase: ${effectiveMaxCurrentPerPhaseInAmps[0]}A ${effectiveMaxCurrentPerPhaseInAmps[1]}A ${effectiveMaxCurrentPerPhaseInAmps[2]}A"
    logger -t ebox_control "Setting maximum current per phase for eBox wallbox to ${effectiveMaxCurrentPerPhaseInAmps[0]}A, ${effectiveMaxCurrentPerPhaseInAmps[1]}A, ${effectiveMaxCurrentPerPhaseInAmps[2]}A"
    `dirname "${0}"`/ebox_write.py ${effectiveMaxCurrentPerPhaseInAmps[0]} ${effectiveMaxCurrentPerPhaseInAmps[1]} ${effectiveMaxCurrentPerPhaseInAmps[2]}
    if [ -n "${BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS}" ]; then
      integerEBoxPowerInWatts=$( echo "${eBoxPowerInWatts}" | sed -e 's/\..*$//' )
      if [ ${integerEBoxPowerInWatts} -gt ${BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS} ]; then
        logger -t ebox_control "Blocking home battery discharge because wallbox power \(${integerEBoxPowerInWatts}W\) exceeds ${BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS}W as set in ${CONFIG_FILE} in the variable BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS"
        kostal-interval.py block | logger -t ebox_control
      else
        # TODO if the battery was blocked for this interval, e.g., to save battery capacity for noon time, keep it at that!
        logger -t ebox_control "Allowing home battery to discharge because wallbox power \(${integerEBoxPowerInWatts}W\) does not exceed ${BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS}W as set in ${CONFIG_FILE} in the variable BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS"
        kostal-interval.py revert | logger -t ebox_control
      fi
    fi
  done
done
