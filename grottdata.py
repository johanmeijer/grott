#grottdata.py processing data  functions
# Updated: 2020-05-22

import time
import sys
import struct
import textwrap
from itertools import cycle # to support "cycling" the iterator
import json, datetime, codecs

#import mqtt                       
import paho.mqtt.publish as publish

# Formats multi-line data
def format_multi_line(prefix, string, size=80):
    size -= len(prefix)
    if isinstance(string, bytes):
        string = ''.join(r'\x{:02x}'.format(byte) for byte in string)
        if size % 2:
            size -= 1
    return '\n'.join([prefix + line for line in textwrap.wrap(string, size)])

def procdata(conf,data):
    if conf.verbose: 
        print("\t - " + "Growatt original Data:") 
        print(format_multi_line("\t\t ", data))
    #self.channel[self.s].send(data)
    serialfound = False 
    if conf.decrypt: 
        message = list(data)
        nmessage = len(message)

        # Create mask and convert to hexadecimal
        mask = "Growatt"
        hex_mask = ['{:02x}'.format(ord(x)) for x in mask]
        nmask = len(hex_mask)
                                                    
        # Determine how many bytes are left if we cycle mask N times over the message
        remainder = nmessage % nmask
        
        # We will now try applying the bitmask from the start of the message, and if not succesful shift one byte per loop until something readable comes out
        for i in range(0,nmask):
            # Determine size of startarray and endarray
            if remainder == 0:
                startarray = []
                endarray = []
            elif i == 0:
                startarray = []
                endarray = message[nmessage-remainder:nmessage]
            else:
                startarray = message[0:i]
                endarray = message[nmessage-remainder+i:nmessage]
            
            # Decode message. Note: this also applies the bitmask to the header info of the TCP dump, i.e. IP info etc. I don't mind, but if you do you need to change this
            testresult = []
            for i,j in zip(range(i,nmessage),cycle(range(0,nmask))):
                testresult = testresult + [message[i] ^ int(hex_mask[j],16)]                          
            
            result = startarray + testresult + endarray
            # Check if message contains SN. If so we have applied the bitmask correctly. If not try next i
                                                                
            #Uncomment result below for testing masked data with known invertid 
            #result = [0,17,114,106,119,184,117,112,74,80,67,50,56,49,56,51,51,66,81,77,66,50,56,50,51,50,54,49,18,12,3,15,21,43,2,0,0,0,44,0,0,0,0,0,0,7,174,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,19,134,9,69,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0,0,3,82,0,30,208,7,0,214,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,7,196,0,0,0,0,0,45,0,89,78,32,0,0,0,0,0,0,0,17,0,0,3,126,0,0,0,0,0,0,0,0,0,0,3,126,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,0,1,9,140,5,3,5,13,0,20,9,240,64,116,0,0,14,135,0,0,13,191,0,0,0,3,0,42,0,0,0,0,0,0,0,0,171,61]
            
            result_string = "".join("{:02x}".format(n) for n in result)  
            
            if(result_string.find(conf.SN) > -1):
                serialfound = True
                if conf.verbose: print("\t - " + "Growatt scrambled data processed for: ", bytearray.fromhex(conf.SN).decode())
                break                            
        
    else: 

        result_string = data.hex()                           
                                            
        if(result_string.find(conf.SN) > -1):
            serialfound = True
            if conf.verbose: print("\t - " + 'Growatt unscrambled data processed for: ', bytearray.fromhex(conf.SN).decode())
        else: 
            if conf.verbose: print("\t - " + 'Growatt unscrambled data processed no matching inverter id found')
            
    if conf.verbose: 
        print("\t -" + 'Growatt plain data:')
        print(format_multi_line("\t\t ", result_string)) 
                
    if serialfound == True:
        #Change in trace in future
            
        if conf.verbose: print("\t -" + 'Growatt processing values for: ', bytearray.fromhex(conf.SN).decode())
        
        #Retrieve values 
        snstart = result_string.find(conf.SN)  
        pvserial = result_string[snstart:snstart+20]
        pvstatus = int(result_string[snstart+conf.offset*2+15*2:snstart+conf.offset*2+15*2+4],16)
        #Only process value if pvstatus is oke (this is because unexpected pvstatus of 257)
        if pvstatus == 0 or pvstatus == 1:
            pvpowerin = int(result_string[snstart+conf.offset*2+17*2:snstart+conf.offset*2+17*2+8],16)
            pv1voltage = int(result_string[snstart+conf.offset*2+21*2:snstart+conf.offset*2+21*2+4],16)
            pv1current = int(result_string[snstart+conf.offset*2+23*2:snstart+conf.offset*2+23*2+4],16)
            pv1watt    = int(result_string[snstart+conf.offset*2+25*2:snstart+conf.offset*2+25*2+8],16)
            pv2voltage = int(result_string[snstart+conf.offset*2+29*2:snstart+conf.offset*2+29*2+4],16)
            pv2current = int(result_string[snstart+conf.offset*2+31*2:snstart+conf.offset*2+31*2+4],16)
            pv2watt    = int(result_string[snstart+conf.offset*2+33*2:snstart+conf.offset*2+33*2+8],16)
            pvpowerout = int(result_string[snstart+conf.offset*2+37*2:snstart+conf.offset*2+37*2+8],16)
            pvfrequentie = int(result_string[snstart+conf.offset*2+41*2:snstart+conf.offset*2+41*2+4],16)
            pvgridvoltage = int(result_string[snstart+conf.offset*2+43*2:snstart+conf.offset*2+43*2+4],16)
            pvenergytoday= int(result_string[snstart+conf.offset*2+67*2:snstart+conf.offset*2+67*2+8],16)
            pvenergytotal= int(result_string[snstart+conf.offset*2+71*2:snstart+conf.offset*2+71*2+8],16)
            pvtemperature = int(result_string[snstart+conf.offset*2+79*2:snstart+conf.offset*2+79*2+4],16)
            pvipmtemperature = int(result_string[snstart+conf.offset*2+97*2:snstart+conf.offset*2+97*2+4],16)
                
            if conf.verbose:
                print("\t\t - " + "pvserial:         ", codecs.decode(pvserial, "hex").decode('utf-8'))
                print("\t\t - " + "pvstatus:         ", pvstatus) 
                print("\t\t - " + "pvpowerin:        ", pvpowerin/10)
                print("\t\t - " + "pvpowerout:       ", pvpowerout/10)
                print("\t\t - " + "pvenergytoday:    ", pvenergytoday/10)
                print("\t\t - " + "pvenergytotal:    ", pvenergytotal/10)
                print("\t\t - " + "pv1watt:          ", pv1watt/10)
                print("\t\t - " + "pv2watt:          ", pv2watt/10)
                print("\t\t - " + "pvfrequentie:     ", pvfrequentie/100)
                print("\t\t - " + "pvgridvoltage:    ", pvgridvoltage/10)
                print("\t\t - " + "pv1voltage:       ", pv1voltage/10)
                print("\t\t - " + "pv1current:       ", pv1current/10)
                print("\t\t - " + "pv2voltage:       ", pv2voltage/10)
                print("\t\t - " + "pv2current:       ", pv2current/10)
                print("\t\t - " + "pvtemperature:    ", pvtemperature/10)
                print("\t\t - " + "pvipmtemperature: ", pvipmtemperature/10)
                
            #create JSON message                          
            jsonmsg = json.dumps({"device":conf.inverterid,"time":datetime.datetime.utcnow().replace(microsecond=0).isoformat(),
                "values":{
                            "pvstatus":pvstatus,
                            "pv1watt":pv1watt,
                            "pv2watt":pv2watt,
                            "pvpowerin":pvpowerin,
                            "pvpowerout":pvpowerout,
                            "pvfrequentie":pvfrequentie,
                            "pvgridvoltage":pvgridvoltage,                             
                            "pvenergytoday":pvenergytoday,
                            "pvenergytotal":pvenergytotal,
                            "pv1voltage":pv1voltage,
                            "pv2voltage":pv2voltage,
                            "pv1current":pv1current,
                            "pv2current":pv2current,
                            "pvtemperature":pvtemperature,
                            "pvipmtemperature":pvipmtemperature}                                
                            })
            if conf.verbose:
                print("\t - " + "MQTT jsonmsg: ")        
                #print("\t\t - " + jsonmsg)     
                print(format_multi_line("\t\t\t ", jsonmsg))   
                
            if not conf.nomqtt:
                try: 
                    publish.single(conf.mqtttopic, payload=jsonmsg, qos=0, retain=False, hostname=conf.mqttip,port=conf.mqttport, client_id=conf.inverterid, keepalive=60, auth=conf.pubauth)
                    if conf.verbose: print("\t - " + 'MQTT message message sent') 
                except TimeoutError:     
                    if conf.verbose: print("\t - " + 'MQTT connection time out error') 
                except ConnectionRefusedError:     
                    if conf.verbose: print("\t - " + 'MQTT connection refused by target')     
                except BaseException as error:     
                    if conf.verbose: print("\t - "+ 'MQTT send failed:', str(error)) 
            else:
                if conf.verbose: print("\t - " + 'No MQTT message sent, MQTT disabled') 
        else:
            if conf.verbose: print("\t - " + 'No valid monitor data, PV status: :', pvstatus)    
        
    else:   
        if conf.verbose: print("\t - "+ 'No Growatt data processed or SN not found:')
        if conf.trace: 
            print("\t - "+ 'Growatt unprocessed Data:')
            print(format_multi_line("\t\t - ", result_string))