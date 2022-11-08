#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#  kostal_modbusquery - Read only query of the Kostal Plenticore Inverters using TCP/IP modbus protocol
#  Copyright (C) 2018  Kilian Knoll 
#  
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#  Please note that any incorrect or careless usage of this module as well as errors in the implementation can damage your Inverter!
#  Therefore, the author does not provide any guarantee or warranty concerning to correctness, functionality or performance and does not accept any liability for damage caused by this module, examples or mentioned information.
#  Thus, use it at your own risk!
#
#
#  Purpose: 
#           Query values from Kostal inverter 
#           Used with Kostal Plenticore Plus 10
#  Based on the documentation provided by Kostal:
#           https://www.kostal-solar-electric.com/en-gb/download/download#PLENTICORE%20plus/PLENTICORE%20plus%204.2/Worldwide/Interfaces%20protocols/
#
# Requires pymodbus
# Tested with:
#           python 3.5   
#           pymodbus 2.10
# Please change the IP address of your Inverter (e.g. 192.168.178.41 and Port (default 1502) to suite your environment - see below)
#
import pymodbus
import argparse
import time
import sys
import datetime
from time import sleep
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from influxdb import InfluxDBClient

class kostal_modbusquery:
    def __init__(self, inverter, port):
        # Change the IP address and port to suite your environment:
        self.inverter_ip=inverter
        self.inverter_port=port
        # No more changes required beyond this point
        self.KostalRegister = []
        self.Adr = []
        self.Adr.append([6, "Inverter article number", "Strg8", 0])
        self.Adr.append([46, "Software-Version IO-Controller (IOC)", "Strg8", 0])
        self.Adr.append([56, "Inverter state", "U16_2", 0])
        self.Adr.append([100, "Total DC power", "Float", 0])
        self.Adr.append([104, "State of energy manager U32", "U32", 0])
        self.Adr.append([106, "Home own consumption from battery", "Float", 0])
        self.Adr.append([108, "Home own consumption from grid", "Float", 0])
        self.Adr.append([110, "Total home consumption PV", "Float", 0])
        self.Adr.append([112, "Total home consumption Grid", "Float", 0])
        self.Adr.append([114, "Total home consumption Battery", "Float", 0])
        self.Adr.append([116, "Home own consumption from PV", "Float", 0])
        self.Adr.append([118, "Total home consumption", "Float", 0])
        self.Adr.append([120, "Isolation resistance", "Float", 0])
        self.Adr.append([122, "Power limit from EVU", "Float", 0])
        self.Adr.append([124, "Total home consumption rate", "Float", 0])
        self.Adr.append([144, "Worktime", "Float", 0])
        self.Adr.append([150, "Actual cos phi", "Float", 0])
        self.Adr.append([152, "Grid frequency", "Float", 0])
        self.Adr.append([154, "Current Phase 1", "Float", 0])
        self.Adr.append([156, "Active power Phase 1", "Float", 0])
        self.Adr.append([158, "Voltage Phase 1", "Float", 0])
        self.Adr.append([160, "Current Phase 2", "Float", 0])
        self.Adr.append([162, "Active power Phase 2", "Float", 0])
        self.Adr.append([164, "Voltage Phase 2", "Float", 0])
        self.Adr.append([166, "Current Phase 3", "Float", 0])
        self.Adr.append([168, "Active power Phase 3", "Float", 0])
        self.Adr.append([170, "Voltage Phase 3", "Float", 0])
        self.Adr.append([172, "Total AC active power", "Float", 0])
        self.Adr.append([174, "Total AC reactive power", "Float", 0])
        self.Adr.append([178, "Total AC apparent power", "Float", 0])
        self.Adr.append([190, "Battery charge current", "Float", 0])
        self.Adr.append([194, "Number of battery cycles", "Float", 0])
        self.Adr.append([200, "Actual battery charge -minus or discharge -plus current", "Float", 0])
        self.Adr.append([202, "PSSB fuse state", "Float", 0])
        self.Adr.append([208, "Battery ready flag", "Float", 0])
        self.Adr.append([210, "Act. state of charge", "Float", 0])
        self.Adr.append([214, "Battery temperature", "Float", 0])
        self.Adr.append([216, "Battery voltage", "Float", 0])
        self.Adr.append([100, "Cos phi (powermeter)", "Float", 0])
        self.Adr.append([220, "Frequency (powermeter)", "Float", 0])
        self.Adr.append([222, "Current phase 1 (powermeter)", "Float", 0])
        self.Adr.append([224, "Active power phase 1 (powermeter)", "Float", 0])
        self.Adr.append([226, "Reactive power phase 1 (powermeter)", "Float", 0])
        self.Adr.append([228, "Apparent power phase 1 (powermeter)", "Float", 0])
        self.Adr.append([230, "Voltage phase 1 (powermeter)", "Float", 0])
        self.Adr.append([232, "Current phase 2 (powermeter)", "Float", 0])
        self.Adr.append([234, "Active power phase 2 (powermeter)", "Float", 0])
        self.Adr.append([236, "Reactive power phase 2 (powermeter)", "Float", 0])
        self.Adr.append([238, "Apparent power phase 2 (powermeter)", "Float", 0])
        self.Adr.append([240, "Voltage phase 2 (powermeter)", "Float", 0])
        self.Adr.append([242, "Current phase 3 (powermeter)", "Float", 0])
        self.Adr.append([244, "Active power phase 3 (powermeter)", "Float", 0])
        self.Adr.append([246, "Reactive power phase 3 (powermeter)", "Float", 0])
        self.Adr.append([248, "Apparent power phase 3 (powermeter)", "Float", 0])
        self.Adr.append([250, "Voltage phase 3 (powermeter)", "Float", 0])
        self.Adr.append([252, "Total active power (powermeter)", "Float", 0])
        self.Adr.append([254, "Total reactive power (powermeter)", "Float", 0])
        self.Adr.append([256, "Total apparent power (powermeter)", "Float", 0])
        self.Adr.append([258, "Current DC1", "Float", 0])
        self.Adr.append([260, "Power DC1", "Float", 0])
        self.Adr.append([100, "Voltage DC1", "Float", 0])
        self.Adr.append([268, "Current DC2", "Float", 0])
        self.Adr.append([270, "Power DC2", "Float", 0])
        self.Adr.append([276, "Voltage DC2", "Float", 0])
        self.Adr.append([278, "Current DC3", "Float", 0])
        self.Adr.append([280, "Power DC3", "Float", 0])
        self.Adr.append([286, "Voltage DC3", "Float", 0])
        self.Adr.append([320, "Total yield", "Float", 0])
        self.Adr.append([322, "Daily yield", "Float", 0])
        self.Adr.append([324, "Yearly yield", "Float", 0])
        self.Adr.append([326, "Monthly yield", "Float", 0])
        self.Adr.append([514, "Battery actual SOC", "U16_1", 0])
        self.Adr.append([531, "Inverter Max Power", "U16_1", 0])
        self.Adr.append([575, "Inverter Generation Power (actual)", "S16", 0])
        self.Adr.append([582, "Actual battery charge-discharge power", "S16", 0])
        # 2020-10-31: Values now available starting with firmware release 1.44
        self.Adr.append([1024, "Battery charge power (AC) setpoint", "S16", 0])
        self.Adr.append([1025, "Power Scale Factor", "S16", 0])
        self.Adr.append([1026, "Battery charge power (AC) setpoint, absolute", "R32", 0])
        self.Adr.append([1028, "Battery charge current (DC) setpoint, relative", "R32", 0])
        self.Adr.append([1030, "Battery charge power (AC) setpoint, relative", "R32", 0])
        self.Adr.append([1032, "Battery charge current (DC) setpoint, absolute", "R32", 0])
        self.Adr.append([1034, "Battery charge power (DC) setpoint, absolute", "R32", 0])
        self.Adr.append([1036, "Battery charge power (DC) setpoint, relative", "R32", 0])
        self.Adr.append([1038, "Battery max. charge power limit, absolute", "R32", 0])
        self.Adr.append([1040, "Battery max. discharge power limit, absolute", "R32", 0])
        self.Adr.append([1042, "Minimum SOC", "R32", 0])
        self.Adr.append([1044, "Maximum SOC", "R32", 0])
        self.Adr.append([1046, "Total DC charge energy (DC-side to battery) (f32)", "R32", 0])
        self.Adr.append([1048, "Total DC discharge energy (DC-side from battery) (f32)", "R32", 0])
        self.Adr.append([1050, "Total AC charge energy (AC-side to battery) (f32)", "R32", 0])
        self.Adr.append([1052, "Total AC discharge energy (battery to grid) (f32)", "R32", 0])
        self.Adr.append([1054, "Total AC charge energy (grid to battery) (f32)", "R32", 0])
        self.Adr.append([1056, "Total DC PV energy (sum of all PV inputs) (f32)", "R32", 0])
        self.Adr.append([1058, "Total DC energy from PV1 (f32)", "R32", 0])
        self.Adr.append([1060, "Total DC energy from PV2 (f32)", "R32", 0])
        self.Adr.append([1062, "Total DC energy from PV3 (f32)", "R32", 0])
        self.Adr.append([1064, "Total energy AC-side to grid (f32)", "R32", 0])
        self.Adr.append([1066, "Total DC power (sum of all PV inputs) (f32)", "R32", 0])
        self.Adr.append([1068, "Battery work capacity (f32)", "R32", 0])
        self.Adr.append([1076, "Maximum charge power limit (read-out from battery)", "R32", 0])
        self.Adr.append([1078, "Maximum discharge power limit (read-out from battery)", "R32", 0])
      
    #-----------------------------------------
    # Routine to read a string from one address with n registers 
    def ReadStr(self,myadr_dec,n):
        r1=self.client.read_holding_registers(myadr_dec,n,unit=71)
        STRGRegister = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big)
        result_STRGRegister =STRGRegister.decode_string(n)      
        return(result_STRGRegister) 
    #-----------------------------------------
    # Routine to read a string from one address with 8 registers 
    def ReadStr8(self,myadr_dec):
        return self.ReadStr(myadr_dec,8)
    #-----------------------------------------
    # Routine to read a string from one address with 16 registers 
    def ReadStr16(self,myadr_dec):
        return self.ReadStr(myadr_dec,16)
    #-----------------------------------------
    # Routine to read a string from one address with 8 registers 
    def ReadStr32(self,myadr_dec):
        return self.ReadStr(myadr_dec,32)
    #-----------------------------------------
    # Routine to read a Float from one address with 2 registers     
    def ReadFloat(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,2,unit=71)
        FloatRegister = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        result_FloatRegister =round(FloatRegister.decode_32bit_float(),2)
        return(result_FloatRegister)   
    #-----------------------------------------
    # Routine to read a U16 from one address with 1 register 
    def ReadU16_1(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,1,unit=71)
        U16register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        result_U16register = U16register.decode_16bit_uint()
        return(result_U16register)
    #-----------------------------------------
    # Routine to read a U16 from one address with 2 registers 
    def ReadU16_2(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,2,unit=71)
        U16register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        result_U16register = U16register.decode_16bit_uint()
        return(result_U16register)
    #-----------------------------------------
    # Routine to read an R32 from one address with 2 registers 
    def ReadR32(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,2,unit=71)
        R32register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        result_R32register = R32register.decode_32bit_float()
        return(result_R32register)
    #-----------------------------------------
    # Routine to read a U32 from one address with 2 registers 
    def ReadU32(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,2,unit=71)
        U32register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Big)
        result_U32register = U32register.decode_32bit_uint()
        return(result_U32register)
    #-----------------------------------------
    # Routine to read a S16 from one address with 2 registers 
    def ReadS16(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,1,unit=71)
        S16register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        result_S16register = S16register.decode_16bit_int()
        return(result_S16register)
        
    try:
        def run(self):
            self.client = ModbusTcpClient(self.inverter_ip,port=self.inverter_port)            
            self.client.connect()
            self.KostalRegister=[]
            for adr in self.Adr:
                print ("Handling "+str(adr))
                if adr[2] == "Strg8":
                    adr[3] = self.ReadStr8(adr[0])
                elif adr[2] == "Strg16":
                    adr[3] = self.ReadStr16(adr[0])
                elif adr[2] == "Strg32":
                    adr[3] = self.ReadStr32(adr[0])
                elif adr[2] == "Float":
                    adr[3] = self.ReadFloat(adr[0])
                elif adr[2] == "U16_1":
                    adr[3] = self.ReadU16_1(adr[0])
                elif adr[2] == "U16_2":
                    adr[3] = self.ReadU16_2(adr[0])
                elif adr[2] == "U32":
                    adr[3] = self.ReadU32(adr[0])
                elif adr[2] == "R32":
                    adr[3] = self.ReadR32(adr[0])
                    print ("Read an R32 for "+adr[1]+": "+str(adr[3]))
                elif adr[2] == "S16":
                    adr[3] = self.ReadS16(adr[0])
                else:
                  print ("Format "+adr[2]+" unknown")
                self.KostalRegister.append(adr)
            self.client.close()

    except Exception as ex:
            print ("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            print ("XXX- Hit the following error :From subroutine kostal_modbusquery :", ex)
            print ("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
#-----------------------------


if __name__ == "__main__":  
  my_parser = argparse.ArgumentParser()
  my_parser.add_argument('--inverter', default='kostal',
                      help='The host name or IP address of your inverter; defaults to "kostal"')
  my_parser.add_argument('--modbusport', default='1502',
                      help='The Modbus port of your inverter; defaults to 1502')
  my_parser.add_argument('--influx', default='klo.axeluhl.de',
                      help='The host name or IP address where your InfluxDB database for storing your inverter values is running; defaults to "klo.axeluhl.de"')
  my_parser.add_argument('--db', default='kostal',
                      help='The InfluxDB database name for storing your inverter values; defaults to "kostal"')
  my_parser.add_argument('repetitions', nargs='?', default='1',
                      help='The number of times to poll the Modbus values; defaults to 1')
  my_parser.add_argument('intervalInSeconds', nargs='?', default='0',
                      help='The time between polling the Modbus values; defaults to 0')
  args = vars(my_parser.parse_args())
  repetitions=int(args['repetitions'])
  intervalInSeconds=int(args['intervalInSeconds'])
  for i in range(0, repetitions):
    start=time.time()
    print ("Starting QUERY #"+str(i+1)+"...")
    try:
        Kostalvalues =[]
        Kostalquery = kostal_modbusquery(args['inverter'], int(args['modbusport']))
        Kostalquery.run()
    except Exception as ex:
        print (traceback.format_exc())
        print ("Issues querying Kostal Plenticore -ERROR :", ex)
    influx_json_body = [
            {
                "measurement": "pv",
                "tags": {"inverter": Kostalquery.inverter_ip},
                "time": int(time.time()),
                "fields": {
                }
            }
            ]
    for elements in Kostalquery.KostalRegister:
        print ( elements[1], ":", elements[3], "Type:", elements[2])
        if elements[2].startswith("Strg"):
            influx_json_body[0]["fields"][elements[1]] = "\""+str(elements[3])[2:len(elements[3])-1]+"\""
        else:
            influx_json_body[0]["fields"][elements[1]] = elements[3]
    print ("Done...")
    ##########################################
    print ("----------------------------------")
    print ("Doing some Calculations of the received information:")
    KostalVal ={}
    for elements in Kostalquery.KostalRegister:
        KostalVal.update({elements[1]: elements[3]})
    LeftSidePowerGeneration= round((KostalVal['Power DC1']+ KostalVal['Power DC2']),1)
    print ("Left Side Raw Power Generation of Panles :", LeftSidePowerGeneration)
    BatteryCharge = round(KostalVal['Battery voltage']* KostalVal['Actual battery charge -minus or discharge -plus current'],1)
    print ("BatteryCharge (-) / Discharge(+) is      :", BatteryCharge)
    TotalHomeconsumption =round((KostalVal['Home own consumption from battery'] + KostalVal['Home own consumption from grid'] + KostalVal['Home own consumption from PV']),1)
    PowertoGrid = round(KostalVal['Inverter Generation Power (actual)'] - TotalHomeconsumption,1)
    print ("Powerfromgrid (-) /To Grid (+) is        :", PowertoGrid)
    print ("Total current Home consumption is        :", TotalHomeconsumption)
    ####### InfluxDB Stuff ######
    print ("Adding to InfluxDB...")
    influx_json_body[0]["fields"]['Home own consumption'] = TotalHomeconsumption
    influx_json_body[0]["fields"]['PV production'] = LeftSidePowerGeneration
    influx_json_body[0]["fields"]['Battery Charge'] = BatteryCharge
    print ("The data is: ", influx_json_body)
    influx_client = InfluxDBClient(host=args['influx'], database=args['db'])
    influx_client.create_database(args['db'])
    try:
        if not influx_client.write_points(influx_json_body, time_precision='s'):
            print ("Some problem (but no exception) inserting data into InfluxDB")
    except Exception as ex:
        print ("Problem inserting into InfluxDB:", ex)
    waitTimeInSeconds=start+intervalInSeconds-time.time()
    if waitTimeInSeconds > 0:
        sleep(waitTimeInSeconds)
