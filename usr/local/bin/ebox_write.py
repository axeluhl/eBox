#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import traceback
import pymodbus
import time
import sys
import datetime
from time import sleep
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder

class ebox_modbusquery:
    def __init__(self):
        # Change the IP address and port to suite your environment:
        self.ebox_ip='yourebox.example.com'
        self.ebox_port="5555"
        
    try:
        def run(self, maxCurrentPhase1, maxCurrentPhase2, maxCurrentPhase3):
            fallbackCurrentInAmps=32
            timeoutForFallbackInSeconds=3600
            self.client = ModbusTcpClient(self.ebox_ip,port=self.ebox_port)            
            self.client.connect()
            builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
            builder.add_32bit_float(maxCurrentPhase1)
            builder.add_32bit_float(maxCurrentPhase2)
            builder.add_32bit_float(maxCurrentPhase3)
            builder.add_32bit_float(fallbackCurrentInAmps)
            builder.add_32bit_float(fallbackCurrentInAmps)
            builder.add_32bit_float(fallbackCurrentInAmps)
            builder.add_16bit_uint(timeoutForFallbackInSeconds)
            payload = builder.build()
            result = self.client.write_registers(1012, payload, skip_encode=True, unit=1)
            print("Write result: "+str(result))
            self.client.close()
    except Exception as ex:
            print ("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            print ("XXX- Hit the following error :From subroutine ebox_modbusquery :", ex)
            print ("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

if __name__ == "__main__":  
  if len(sys.argv) <= 3:
    print("Usage: "+sys.argv[0]+" {maxCurrentPhase1InAmps} {maxCurrentPhase2InAmps} {maxCurrentPhase3InAmps}")
  else:
    maxCurrentPhase1=float(sys.argv[1])
    maxCurrentPhase2=float(sys.argv[2])
    maxCurrentPhase3=float(sys.argv[3])
    try:
        Eboxvalues = []
        Eboxquery = ebox_modbusquery()
        Eboxquery.run(maxCurrentPhase1, maxCurrentPhase2, maxCurrentPhase3)
    except Exception as ex:
        print (traceback.format_exc())
        print ("Issues writing to Ebox:", ex)
