# eBox
Python and Bash example scripts that combine a photovoltaic solar generator, inverter and Innogy eBox Professional with Modbus access

TL;DR:

Ensure an InfluxDB is installed where the host on which you're doing this can access it and where a new ``kostal`` DB can be created. Then
```
git clone git@github.wdf.sap.corp:d043530/eBox.git
sudo ln -s eBox/usr/local/bin/* /usr/local/bin
sudo ln -s eBox/etc* /etc
sudo echo "$( crontab -l; cat crontab )" | crontab -
```
Replace ``yourinfluxhost.example.com`` with the hostname or IP address of the host where your InfluxDB is running, ``yourebox.example.com`` with the hostname or IP address of your Innogy/E.ON eBox Professional, and ``yourkostalinverter.example.com`` with the hostname or IP address of your Kostal inverter.

## Background

As an owner of a photovoltaic (PV) solar generator with a Kostal Plenticore 8.5 inverter and a BYD battery I recently participated in the SAP Charge@Home program and ordered a plugin hybrid electric vehicle (PHEV). After some hassle with the wallbox ordering and installation process (see also related JAM articles) I finally have a set-up that allows me to play with logging, charting, controlling and automating things.

One recent goal was controlling the wallbox's power output based on PV output and home battery state. I've played with a bit of Bash and Python scripting to come up with a first solution that provides some utility to me. I'm sharing it here for anyone to use, copy, augment, extend and improve. No warranty, no nothing. You brick your eBox or you BBQ your inverter...? Don't blame me.

My set-up consists of an InfluxDB to which I'm logging my Kostal inverter's Modbus values every five seconds, triggered by a cron job that runs every minute and repeats twelve times, every five seconds. The crontab line could look something like this:

```
* * * * *       /usr/local/bin/kostal_modbusquery.py 12 5 >/var/log/kostal_modbusquery.out 2>/var/log/kostal_modbusquery.err
```

The second and third crontab entries then looks like this:

```
* * * * *       /usr/local/bin/ebox_modbusquery.py >/var/log/ebox_modbusquery.out 2>/var/log/ebox_modbusquery.err
*/5 * * * *       /usr/local/bin/ebox_control.sh 2>/var/log/ebox_control.err | logger -t ebox_control
```

where the ``ebox_modbusquery.py`` script logs the Innogy/E.ON eBox Professional's Modbus values to InfluxDB, and the ``ebox_control.sh`` script uses the InfluxDB content to configure the maximum power allowed for the eBox, reading configuration data---particularly on the strategy to use---from ``/etc/ebox_defaults.conf``.

Additionally, there is a script ``ebox_default_strategy.sh`` that outputs or updates the strategy in ``/etc/ebox_defaults.conf`` for granting energy to the wallbox. I created a group ``ebox`` who is the group owner of ``/etc/ebox_defaults.conf`` with that file being group-writable, so that members of that group can run ``ebox_default_strategy.sh`` to update the ``STRATEGY`` variable in that file from where ``ebox_control.sh`` picks it up.
