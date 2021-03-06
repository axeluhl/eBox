# eBox
Python and Bash example scripts that combine a photovoltaic solar generator, inverter and Innogy eBox Professional with Modbus access

TL;DR:

Ensure an InfluxDB is installed where the host on which you're doing this can access it and where a new ``kostal`` DB can be created.

In the scripts under eBox/usr/local/bin and in crontab replace ``yourinfluxhost.example.com`` with the hostname or IP address of the host where your InfluxDB is running, ``yourebox.example.com`` with the hostname or IP address of your Innogy/E.ON eBox Professional, and ``yourkostalinverter.example.com`` with the hostname or IP address of your Kostal inverter. Make sure to have Modbus enabled on your Kostal inverter and your eBox Pro. If your ports deviate from 1502 and 5555, respectively, adjust them in the ``eBox/usr/local/bin/kostal_modbusquery.py`` / ``eBox/usr/local/bin/ebox_modbusquery.py`` / ``ebox/usr/local/bin/ebox_write.py`` scripts, respectively.

You may also want to adjust your latitude, longitude and PV parameters in the calls to /usr/local/bin/forecast_solar.sh in crontab so they match your location and PV parameters as the defaults of 49N 8E with 45deg inclination, 10deg off south and a peak power of 9.6kWp may not match your installation.

Then
```
git clone git@github.com:axeluhl/eBox.git
sudo ln -s eBox/usr/local/bin/* /usr/local/bin
sudo ln -s eBox/etc* /etc
sudo echo "$( crontab -l; cat crontab )" | crontab -
```

Use ``/usr/local/bin/ebox_default_strategy.sh`` to adjust your charging strategy:
```
$ ebox_default_strategy.sh
Current default strategy is 1
Call like this to change default strategy:
   /usr/local/bin/ebox_default_strategy.sh <new-default-strategy>
Example: /usr/local/bin/ebox_default_strategy.sh 2
  sets 2 as the new default strategy
For strategies see the online help of ebox_control.sh
Usage: /usr/local/bin/ebox_control.sh [ -s <STRATEGY> ] [ -m <MAX_HOME_BATTERY_CHARGE_POWER_IN_WATTS> ] [ -p <NUMBER_OF_PHASES_USED_FOR_CHARGING> ]
 STRATEGY: 0 means to open the wallbox throttle entirely; 50A
           1 means to split excess PV energy evenly between home battery and wallbox;
           2 means to prefer home battery charging and only send to wallbox what would otherwise be ingested to grid.
           3 means to prefer car charging and only send to the home battery what would otherwise be ingested to grid.
           Default is 1.
```

## Background

As an owner of a photovoltaic (PV) solar generator with a Kostal Plenticore 8.5 inverter and a BYD battery I recently participated in the SAP Charge@Home program and ordered a plugin hybrid electric vehicle (PHEV). After some hassle with the wallbox ordering and installation process (see also related JAM articles) I finally have a set-up that allows me to play with logging, charting, controlling and automating things.

One recent goal was controlling the wallbox's power output based on PV output and home battery state. Furthermore, I wanted to block home battery discharging in case the wallbox power exceeds a certain threshold because then, over time, home battery wear and losses would be greater than desirable. I've played with a bit of Bash and Python scripting to come up with a first solution that provides some utility to me. I'm sharing it here for anyone to use, copy, augment, extend and improve. No warranty, no nothing. You brick your eBox or you BBQ your inverter...? Don't blame me.

My set-up consists of an InfluxDB to which I'm logging my Kostal inverter's Modbus values every five seconds, triggered by a cron job that runs every minute and repeats twelve times, every five seconds. The crontab line could look something like this:

```
* * * * *	/usr/local/bin/kostal_modbusquery.py 12 5 >/var/log/kostal_modbusquery.out 2>/var/log/kostal_modbusquery.err
```

The second and third crontab entries then looks like this:

```
* * * * *	/usr/local/bin/ebox_modbusquery.py >/var/log/ebox_modbusquery.out 2>/var/log/ebox_modbusquery.err
* * * * *	/usr/local/bin/ebox_control.sh 2>/var/log/ebox_control.err | logger -t ebox_control
```

where the ``ebox_modbusquery.py`` script logs the Innogy/E.ON eBox Professional's Modbus values to InfluxDB, and the ``ebox_control.sh`` script uses the InfluxDB content to configure the maximum power allowed for the eBox, reading configuration data---particularly on the strategy to use---from ``/etc/ebox_defaults.conf``. The ``BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS`` property in the file controls the wallbox power output threshold above which home battery discharging will be blocked by the ``ebox_control.sh`` script. Remove the property if you want to disable this behavior. It currently defaults to 2000W.

Additionally, there is a script ``ebox_default_strategy.sh`` that outputs or updates the strategy in ``/etc/ebox_defaults.conf`` for granting energy to the wallbox. I created a group ``ebox`` who is the group owner of ``/etc/ebox_defaults.conf`` with that file being group-writable, so that members of that group can run ``ebox_default_strategy.sh`` to update the ``STRATEGY`` variable in that file from where ``ebox_control.sh`` picks it up.

For home battery discharge blocking there is a dependency on [https://github.com/axeluhl/kostal-RESTAPI](https://github.com/axeluhl/kostal-RESTAPI), in particular the ``kostal-interval.py`` script. It helps with blocking discharging for time intervals, recording the corresponding state in a file, and reverting the blocking if it is no longer required. If you don't want this behavior, or you don't have the script linked to a typical PATH directory such as ``/usr/local/bin``, remove the ``BLOCK_HOME_BATTERY_DISCHARGE_IF_WALLBOX_POWER_EXCEEDS_WATTS`` property from ``/etc/ebox_defaults.conf``.

## Grafana

I use Grafana to monitor PV and wallbox. Not being a Grafana expert, the best I could come up with so far in order to share the dashboards I've assembled was exporting them as JSON files. You can find them in the ``grafana/`` folder. My take is that to make those work for you, you'd have to create an InfluxDB data source in your Grafana installation that uses the ``kostal`` DB that the scripts write to. It also seems that during importing the dashboard JSON files, Grafana allows you to bind the data source. Let me know how this works for you.

## Thoughts on Designing Disabling Battery Discharge upon High Wallbox Demand

The following thoughts have led to the ``kostal-interval.py`` script that is now used by the ``ebox_control.sh`` script to control blocking / unblocking of the home battery discharging based on the wallbox current output power.

Especially during the winter time it is quite frustrating to see the car being plugged in when the PV production is close to nothing and the home battery is filled well. Then, the car sucks energy from the home battery with 3.7kW for our PHEV, and much more (up to 22kW in the future) if we open up the wallbox from its 11kW to its full 22kW and use it to charge a BEV with it. Despite not having been able to derive it from my inverter's stats, I surmise that drawing power from the home battery at high rates may have a number of disadvantages. It may create greater losses than when discharging at smaller rates. And it may wear the battery in fewer cycles.

As a first solution I've come up with a script https://github.com/axeluhl/kostal-RESTAPI/blob/master/kostal-noDischarge which disables home battery discharge for a configurable duration. When combined with, e.g., ``ebox_control.sh 0`` (the "full throttle" strategy), it may be used to disable home battery discharge for an estimated duration of high-power car charging. But this is flawed in several ways: users have to remember to use it, especially during winter where "full throttle" is the default strategy set for the wallbox; then, users would have to calculate the duration of high power charging expected as towards the end of the charging cycle the car reduces the charging power, and charging duration of course depends on the car battery's SOC.

Instead, I'd like to have a logic in place that observes the wallbox power and disables home battery discharge temporarily during the times when high wallbox charging powers (above a threshold configurable) are observed. This, however, comes with a few challenges:

- Wallbox read-outs arrive every minute with the current cron job, but inverter battery control works based on 15 minute slots
- Inverter users may have configured a charging/discharging blocking pattern that they don't want to get permanently overwritten
- We don't want short unblock / block cycles at interval boundaries, e.g., because a 15 minute interval ends and then it takes a few seconds for a cron job to react in order to block the next 15 minutes interval

This implies that any modification applied to the charging/discharging blocking state needs to have the original state recorded and needs to revert to that state after the interval is over or the wallbox-implied power consumption has decreased below a threshold specified.

Algorithm sketch:

- read out wallbox power
- if wallbox power exceeds threshold:
  - block current interval (meaning current and next if next is less than a minute away)
- remember original state of interval before blocking, and remember which intervals (up to two; the current and the next, or the previous and the current) have been blocked
- if wallbox power is below threshold, revert all intervals to original blocking state and remove intervals from set of blocked intervals
- revert any interval that was blocked and now has expired to its original state and remove interval from set of blocked intervals

Additional features:

- Stopping this, reverting all intervals blocked to their original state immediately
- (Re-)starting this as a cron job / loop running in the background somehow

Breaking things down to smaller functions:

- data structure for intervals blocked including their original state and how it is stored in the FS
- check if interval has expired
- restoring interval to original state and purge interval after it has been restored
- record original state of interval
- block interval in inverter
- check if timestamp is less than one minute (the wallbox sampling interval) away from next interval
- check if interval has already been blocked before, with original state recorded

While in the https://github.com/axeluhl/kostal-RESTAPI/blob/master/kostal-noDischarge script the state to which to revert is stored in a background task it seems more appropriate here to use the file system to keep track of the state. Something under /var/cache or /var/run may be adequate. The persistent state needs to keep track of the intervals blocked and their original state. A mechanism is needed to map this to the blocking state-describing JSON documents of the form

```
$ kostal-RESTAPI -ReadBatteryTimeControl 1
{"Battery:TimeControl:ConfThu": "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "Battery:TimeControl:ConfWed": "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "Battery:TimeControl:ConfMon": "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000022", "Battery:TimeControl:ConfFri": "000000000000000000000000000000000000000000000000000000000000000000000000002222222222222222000000", "Battery:TimeControl:ConfSat": "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "Battery:TimeControl:ConfSun": "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "Battery:TimeControl:ConfTue": "222222222222220000000000000000000000000000000000000000000000000000000000000000000000000000000000"}
```

where each digit represents a 15 minute interval on the day identified by the ``Conf...`` field name. The kostal-RESTAPI.py script contains a method called ``getUpdatedTimeControls`` which handles some mapping between time stamps and the string handling for weekdays as well as the daily digit strings. It deals with 15 minutes intervals, can map time points to their weekday and interval and can manipulate a digit string by mapping the interval to its corresponding digit in the string. This functionality should be extracted and then be used in order to manage blocking and state recording and restoring by interval.

An interval could be modeled as an object identifying a time point and an interval length. Assuming that intervals start at time points whose time of the day divides evenly by the interval duration, the day of week and the index in the digit string with each digit representing an interval during the day of week can be inferred. Additionally, the interval object should have a field capturing its original state and whether it was blocked.

Fields Operations an interval object could support, are:
- constructor(timepoint:timepoint); builds an interval for the timepoint specified that has blocked=false and originalState=null
- constructor(timepoint:timepoint, blocked:boolean, originalState:char); builds an interval that may optionally be initialized as blocked, with an original state; this may be used, e.g., to parse a file system representation of such an interval into a runtime object
- timepoint:timepoint
- originalState:char (0, 1, 2, null)
- blocked:boolean
- getStart():timepoint; returns the start time point of this interval
- getEnd():timepoint; returns the end time point of this interval
- isExpired():boolean; tells if getEnd() is after the current point in time
- block(new_state:char); blocks this interval with the new_state (e.g., 2) and if it wasn't marked as blocked yet records the original state in originalState and sets the blocked field to true
- revert(); reverts the interval to its originalState and sets blocked to false
