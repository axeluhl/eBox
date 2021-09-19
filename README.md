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

One recent goal was controlling the wallbox's power output based on PV output and home battery state. I've played with a bit of Bash and Python scripting to come up with a first solution that provides some utility to me. I'm sharing it here for anyone to use, copy, augment, extend and improve. No warranty, no nothing. You brick your eBox or you BBQ your inverter...? Don't blame me.

My set-up consists of an InfluxDB to which I'm logging my Kostal inverter's Modbus values every five seconds, triggered by a cron job that runs every minute and repeats twelve times, every five seconds. The crontab line could look something like this:

```
* * * * *	/usr/local/bin/kostal_modbusquery.py 12 5 >/var/log/kostal_modbusquery.out 2>/var/log/kostal_modbusquery.err
```

The second and third crontab entries then looks like this:

```
* * * * *	/usr/local/bin/ebox_modbusquery.py >/var/log/ebox_modbusquery.out 2>/var/log/ebox_modbusquery.err
* * * * *	/usr/local/bin/ebox_control.sh 2>/var/log/ebox_control.err | logger -t ebox_control
```

where the ``ebox_modbusquery.py`` script logs the Innogy/E.ON eBox Professional's Modbus values to InfluxDB, and the ``ebox_control.sh`` script uses the InfluxDB content to configure the maximum power allowed for the eBox, reading configuration data---particularly on the strategy to use---from ``/etc/ebox_defaults.conf``.

Additionally, there is a script ``ebox_default_strategy.sh`` that outputs or updates the strategy in ``/etc/ebox_defaults.conf`` for granting energy to the wallbox. I created a group ``ebox`` who is the group owner of ``/etc/ebox_defaults.conf`` with that file being group-writable, so that members of that group can run ``ebox_default_strategy.sh`` to update the ``STRATEGY`` variable in that file from where ``ebox_control.sh`` picks it up.

## Grafana

I use Grafana to monitor PV and wallbox. Not being a Grafana expert, the best I could come up with so far in order to share the dashboards I've assembled was exporting them as JSON files. You can find them in the ``grafana/`` folder. My take is that to make those work for you, you'd have to create an InfluxDB data source in your Grafana installation that uses the ``kostal`` DB that the scripts write to. It also seems that during importing the dashboard JSON files, Grafana allows you to bind the data source. Let me know how this works for you.
