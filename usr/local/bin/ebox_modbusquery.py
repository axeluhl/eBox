#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#  kostal_modbusquery - Read only query of the Ebox Plenticore Inverters using TCP/IP modbus protocol
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
#           Query values from Ebox wallbox
#           Used with Innogy eBox Professional
#  Based on the documentation provided by Ebox:
#           https://www.innogy-emobility.com/content/dam/revu-global/emobility-solutions/neue-website-feb-2021/downloadcenter/digital-services/eld_instman_modbustcpde.pdf
#
# Requires pymodbus
# Tested with:
#           python 3.5   
#           pymodbus 2.10
# Please change the IP address of your Inverter (e.g. 192.168.178.41 and Port (default 1502) to suite your environment - see below)
#
import traceback
import pymodbus
import time
import sys
import datetime
from time import sleep
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from influxdb import InfluxDBClient

class ebox_modbusquery:
    def __init__(self):
        # Change the IP address and port to suite your environment:
        self.ebox_ip='yourebox.example.com'
        self.ebox_port="5555"
        # No more changes required beyond this point
        self.EboxRegister = []
        self.Adr = []
        self.Adr.append([0, "ChargeBoxID", "IR_Strg25", 0])
        self.Adr.append([25, "SerialNumber", "IR_Strg25", 0])
        self.Adr.append([50, "ActiveProtocol", "IR_Strg25", 0])
        self.Adr.append([100, "Manufacturer", "IR_Strg25", 0])
        self.Adr.append([125, "PlatformType", "IR_Strg25", 0])
        self.Adr.append([150, "ProductType", "IR_Strg25", 0])
        self.Adr.append([175, "ModbusTableVersion", "IR_U16_1", 0])
        self.Adr.append([200, "FirmwareVersion", "IR_Strg25", 0])
        self.Adr.append([225, "NumberOfSockets", "IR_U16_1", 0])
        self.Adr.append([250, "OcppState", "IR_U16_1", 0])
        self.Adr.append([275, "Socket1Mode3State", "IR_Strg25", 0])
        self.Adr.append([300, "Socket1CableState", "IR_U16_1", 0])
        self.Adr.append([1000, "ActualMaxCurrentPhase1", "IR_Float", 0])
        self.Adr.append([1002, "ActualMaxCurrentPhase2", "IR_Float", 0])
        self.Adr.append([1004, "ActualMaxCurrentPhase3", "IR_Float", 0])
        self.Adr.append([1006, "CurrentPhase1", "IR_Float", 0])
        self.Adr.append([1008, "CurrentPhase2", "IR_Float", 0])
        self.Adr.append([1010, "CurrentPhase3", "IR_Float", 0])
        self.Adr.append([1012, "MaxCurrentPhase1", "Float", 0])
        self.Adr.append([1014, "MaxCurrentPhase2", "Float", 0])
        self.Adr.append([1016, "MaxCurrentPhase3", "Float", 0])
        self.Adr.append([1018, "FallbackMaxCurrent1", "Float", 0])
        self.Adr.append([1020, "FallbackMaxCurrent2", "Float", 0])
        self.Adr.append([1022, "FallbackMaxCurrent3", "Float", 0])
        self.Adr.append([1024, "RemaningTimeBeforeFallback", "U16_1", 0])
        self.Adr.append([1025, "StationPhaseSetupL1", "U16_1", 0])
        self.Adr.append([1026, "StationPhaseSetupL2", "U16_1", 0])
        self.Adr.append([1027, "StationPhaseSetupL3", "U16_1", 0])
        self.Adr.append([1028, "Availability", "U16_1", 0])
      
    #-----------------------------------------
    # Routine to read a string from one address with n registers 
    def ReadStr(self,myadr_dec,n):
        r1=self.client.read_holding_registers(myadr_dec,n,unit=1)
        STRGRegister = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big)
        result_STRGRegister =STRGRegister.decode_string(n)      
        return(result_STRGRegister) 
    #-----------------------------------------
    # Routine to read a string from one address with n input registers 
    def Read_IR_Str(self,myadr_dec,n):
        r1=self.client.read_input_registers(myadr_dec,n,unit=1)
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
    # Routine to read a string from one address with 25 registers 
    def ReadStr25(self,myadr_dec):
        return self.ReadStr(myadr_dec,25)
    #-----------------------------------------
    # Routine to read a string from one address with 25 registers 
    def Read_IR_Str25(self,myadr_dec):
        return self.Read_IR_Str(myadr_dec,25)
    #-----------------------------------------
    # Routine to read a string from one address with 8 registers 
    def ReadStr32(self,myadr_dec):
        return self.ReadStr(myadr_dec,32)
    #-----------------------------------------
    # Routine to read a Float from one address with 2 registers     
    def ReadFloat(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,2,unit=1)
        FloatRegister = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Big)
        result_FloatRegister = round(FloatRegister.decode_32bit_float(), 2)
        return(result_FloatRegister)   
    #-----------------------------------------
    # Routine to read a Float from one address with 2 input registers
    def Read_IR_Float(self,myadr_dec):
        r1=self.client.read_input_registers(myadr_dec,2,unit=1)
        FloatRegister = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Big)
        result_FloatRegister = round(FloatRegister.decode_32bit_float(), 2)
        return(result_FloatRegister)   
    #-----------------------------------------
    # Routine to read a U16 from one address with 1 register 
    def ReadU16_1(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,1,unit=1)
        U16register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        result_U16register = U16register.decode_16bit_uint()
        return(result_U16register)
    #-----------------------------------------
    # Routine to read a U16 from one address with 1 input register 
    def Read_IR_U16_1(self,myadr_dec):
        r1=self.client.read_input_registers(myadr_dec,1,unit=1)
        U16register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        result_U16register = U16register.decode_16bit_uint()
        return(result_U16register)
    #-----------------------------------------
    # Routine to read a U16 from one address with 2 registers 
    def ReadU16_2(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,2,unit=1)
        U16register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        result_U16register = U16register.decode_16bit_uint()
        return(result_U16register)
    #-----------------------------------------
    # Routine to read an R32 from one address with 2 registers 
    def ReadR32(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,2,unit=1)
        R32register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        result_R32register = R32register.decode_32bit_float()
        return(result_R32register)
    #-----------------------------------------
    # Routine to read a U32 from one address with 2 registers 
    def ReadU32(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,2,unit=1)
        U32register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        result_U32register = U32register.decode_32bit_float()
        return(result_U32register)
    #-----------------------------------------
    # Routine to read a S16 from one address with 2 registers 
    def ReadS16(self,myadr_dec):
        r1=self.client.read_holding_registers(myadr_dec,1,unit=1)
        S16register = BinaryPayloadDecoder.fromRegisters(r1.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        result_S16register = S16register.decode_16bit_int()
        return(result_S16register)
        
    try:
        def run(self):
            self.client = ModbusTcpClient(self.ebox_ip,port=self.ebox_port)            
            self.client.connect()
            self.EboxRegister=[]
            for adr in self.Adr:
                #print ("Handling "+str(adr))
                if adr[2] == "Strg8":
                    adr[3] = self.ReadStr8(adr[0])
                elif adr[2] == "Strg16":
                    adr[3] = self.ReadStr16(adr[0])
                elif adr[2] == "Strg25":
                    adr[3] = self.ReadStr25(adr[0])
                elif adr[2] == "IR_Strg25":
                    adr[3] = self.Read_IR_Str25(adr[0])
                elif adr[2] == "Strg32":
                    adr[3] = self.ReadStr32(adr[0])
                elif adr[2] == "Float":
                    adr[3] = self.ReadFloat(adr[0])
                elif adr[2] == "IR_Float":
                    adr[3] = self.Read_IR_Float(adr[0])
                elif adr[2] == "U16_1":
                    adr[3] = self.ReadU16_1(adr[0])
                elif adr[2] == "IR_U16_1":
                    adr[3] = self.Read_IR_U16_1(adr[0])
                elif adr[2] == "U16_2":
                    adr[3] = self.ReadU16_2(adr[0])
                elif adr[2] == "U32":
                    adr[3] = self.ReadU32(adr[0])
                elif adr[2] == "R32":
                    adr[3] = self.ReadR32(adr[0])
                    #print ("Read an R32 for "+adr[1]+": "+str(adr[3]))
                elif adr[2] == "S16":
                    adr[3] = self.ReadS16(adr[0])
                else:
                  print ("Format "+adr[2]+" unknown")
                self.EboxRegister.append(adr)
            self.client.close()

    except Exception as ex:
            print ("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            print ("XXX- Hit the following error :From subroutine ebox_modbusquery :", ex)
            print ("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
#-----------------------------


if __name__ == "__main__":  
  if len(sys.argv) <= 1:
    repetitions=1
    intervalInSeconds=0
  else:
    repetitions=int(sys.argv[1])
    intervalInSeconds=int(sys.argv[2])
  for i in range(0, repetitions):
    start=time.time()
    #print ("Starting QUERY #"+str(i+1)+"...")
    try:
        Eboxvalues = []
        Eboxquery = ebox_modbusquery()
        Eboxquery.run()
    except Exception as ex:
        print (traceback.format_exc())
        print ("Issues querying Ebox:", ex)
    influx_json_body = [
            {
                "measurement": "ebox",
                "tags": {"wallbox": Eboxquery.ebox_ip},
                "time": int(time.time()),
                "fields": {
                }
            }
            ]
    for elements in Eboxquery.EboxRegister:
        print ( elements[1], ":", elements[3], "Type:", elements[2])
        if elements[2].startswith("Strg"):
            influx_json_body[0]["fields"][elements[1]] = "\""+str(elements[3])[2:len(elements[3])-1]+"\""
        else:
            influx_json_body[0]["fields"][elements[1]] = elements[3]
    for elements in Eboxquery.EboxRegister:
        print ( elements[1], ":", elements[3], "Type:", elements[2])
    #print ("Done...")
    ##########################################
    #print ("----------------------------------")
    #print ("Doing some Calculations of the received information:")
    EboxVal = {}
    for elements in Eboxquery.EboxRegister:
        EboxVal.update({elements[1]: elements[3]})
    ####### InfluxDB Stuff ######
    print ("Adding to InfluxDB...")
    print ("The data is: ", influx_json_body)
    influx_client = InfluxDBClient(host='yourinfluxhost.example.com', database='kostal')
    influx_client.create_database('kostal')
    try:
        if not influx_client.write_points(influx_json_body, time_precision='s'):
            print ("Some problem (but no exception) inserting data into InfluxDB")
    except Exception as ex:
        print ("Problem inserting into InfluxDB:", ex)
    waitTimeInSeconds=start+intervalInSeconds-time.time()
