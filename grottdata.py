# grottdata.py processing data  functions
# Version 2.7.6
# Updated: 2022-08-27

#import time
from datetime import datetime, timedelta
from os import times_result
#import pytz
import time
import sys
import struct
import textwrap
from itertools import cycle # to support "cycling" the iterator
import json, codecs
from typing import Dict
# requests

#import mqtt                       
import paho.mqtt.publish as publish


class GrottPvOutLimit:

    def __init__(self):
        self.register: Dict[str, int] = {}

    def ok_send(self, pvserial: str, conf) -> bool:
        now = time.perf_counter()
        ok = False
        if self.register.get(pvserial):
            ok = True if self.register.get(pvserial) + conf.pvuplimit * 60 < now else False
            if ok:
                self.register[pvserial] = int(now)
            else:
                if conf.verbose: print(f'\t - PVOut: Update refused for {pvserial} due to time limitation')
        else:
            self.register.update({pvserial: int(now)})
            ok = True
        return ok


pvout_limit = GrottPvOutLimit()


# Formats multi-line data
def format_multi_line(prefix, string, size=80):
    size -= len(prefix)
    if isinstance(string, bytes):
        string = ''.join(r'\x{:02x}'.format(byte) for byte in string)
        if size % 2:
            size -= 1
    return '\n'.join([prefix + line for line in textwrap.wrap(string, size)])

#decrypt data. 
def decrypt(decdata) :   

    ndecdata = len(decdata)

    # Create mask and convert to hexadecimal
    mask = "Growatt"
    hex_mask = ['{:02x}'.format(ord(x)) for x in mask]    
    nmask = len(hex_mask)

    #start decrypt routine 
    unscrambled = list(decdata[0:8])                                            #take unscramble header
    
    for i,j in zip(range(0,ndecdata-8),cycle(range(0,nmask))): 
        unscrambled = unscrambled + [decdata[i+8] ^ int(hex_mask[j],16)]
    
    result_string = "".join("{:02x}".format(n) for n in unscrambled)
    
    print("\t - " + "Growatt data decrypted V2")   
    return result_string        

def str2bool(defstr):
    if defstr in ("True", "true", "TRUE", "y", "Y", "yes", "YES", 1, "1") : defret = True 
    if defstr in ("False", "false", "FALSE", "n", "N", "no", "NO", 0, "0") : defret = False 
    if 'defret' in locals():
        return(defret)
    else : return()

def procdata(conf,data):    
    if conf.verbose: 
        print("\t - " + "Growatt original Data:") 
        print(format_multi_line("\t\t ", data))

    header = "".join("{:02x}".format(n) for n in data[0:8])
    ndata = len(data)
    buffered = "nodetect"                                               # set buffer detection to nodetect (for compat mode), wil in auto detection changed to no or yes        
    is_smart_meter = header[14:16] in ("20","1b")

    # automatic detect protocol (decryption and protocol) only if compat = False!
    novalidrec = False
    if conf.compat is False : 
        if conf.verbose : 
            print("\t - " + "Grott automatic protocol detection")  
            print("\t - " + "Grott data record length", ndata)
        #print(header)
        layout = "T" + header[6:8] + header[12:14] + header[14:16]
        #v270 add X for extended except for smart monitor records
        if ((ndata > 375) and not is_smart_meter) :  layout = layout + "X"

        #v270 no invtype added to layout for smart monitor records
        if (conf.invtype != "default") and not is_smart_meter :
                layout = layout + conf.invtype.upper()

        if header[14:16] == "50" : buffered = "yes"
        else: buffered = "no" 

        if conf.verbose : print("\t - " + "layout   : ", layout)
        try:            
            # does record layout record exists? 
            test = conf.recorddict[layout]
        except:
            #try generic if generic record exist
            if conf.verbose : print("\t - " + "no matching record layout found, try generic")
            if header[14:16] in ("04","50") :
                layout = layout.replace(header[12:16], "NNNN")
                try:
                    # does generic record layout record exists? 
                    test = conf.recorddict[layout]
                except:
                    #no valid record fall back on old processing? 
                    if conf.verbose : print("\t - " + "no matching record layout found, standard processing performed")
                    layout = "none"
                    novalidrec = True  
            else:         
                novalidrec = True     
    
        conf.layout = layout
        if conf.verbose : print("\t - " + "Record layout used : ", layout)
    
    #Decrypt 
    try: 
        #see if decrypt keyword is defined
        conf.decrypt =  str2bool(conf.recorddict[layout]["decrypt"]["value"])
    except:   
        #if decrypt not defined, default is decypt
        conf.decrypt = True  
    
    if conf.decrypt: 
        result_string = decrypt(data) 
        if conf.verbose : print("\t - " + "Grott Growatt data decrypted")        
    else: 
        #do not decrypt 
        result_string = data.hex()
        if conf.verbose: print("\t - " + "Grott Growatt unencrypted data used")                                      
                                                        
    if conf.verbose: 
        print("\t - " + 'Growatt plain data:')
        print(format_multi_line("\t\t ", result_string))
        #debug only: print(result_string)

    # test position : 
    # print(result_string.find('0074' ))

    # Test length if < 12 it is a data ack record, if novalidrec flag is true it is not a (recognized) data record  
    if ndata < 12 or novalidrec == True: 
        if conf.verbose : print("\t - " + "Grott data ack record or data record not defined no processing done") 
        return

    # Inital flag to detect off real data is processed     
    dataprocessed = False
    
    # define dictonary for key values. 
    definedkey = {}


    if conf.compat is False: 
        # new method if compat = False (automatic detection):  
       
        if (conf.invtype == "default") :
            # Handle systems with mixed invtype
            if (ndata > 50) and not is_smart_meter:
                # There is enough data for an inverter serial number
                inverterType = "default"

                inverterSerial = None
                try:
                    inverterSerial = codecs.decode(result_string[76:96], "hex").decode('ASCII')
                    if conf.verbose:
                        print("\t - Possible Inverter serial", inverterSerial)
                except UnicodeDecodeError:
                    # In case of problem (eg: new record type with different serial placement)
                    pass

                if inverterSerial:
                    # Lookup inverter type based on inverter serial
                    try:
                        inverterType = conf.invtypemap[inverterSerial]
                        print("\t - Matched inverter serial to inverter type", inverterType)
                    except:
                        inverterType = "default"
                        print("\t - Inverter serial not recognised - using inverter type", inverterType)

                if (inverterType != "default") :
                    layout = layout + inverterType.upper()
                    # Update the conf.layout like done earlier
                    conf.layout = layout

        if conf.verbose: 
           print("\t - " + 'Growatt new layout processing')
           print("\t\t - " + "decrypt       : ",conf.decrypt)
           print("\t\t - " + "offset        : ", conf.offset)
           print("\t\t - " + "record layout : ", layout)
           print()

        
        
        try:
            #v270 try if logstart and log fields are defined, if yes prepare log fields 
            logstart = conf.recorddict[layout]["logstart"]["value"] 
            logdict = {}
            logdict = bytes.fromhex(result_string[conf.recorddict[layout]["logstart"]["value"]:len(result_string)-4]).decode("ASCII").split(",")
        except:
            pass

        #v270 log data record processing (SDM630 smart monitor with railog 
        #if rectype == "data" : 
        for keyword in  conf.recorddict[layout].keys() :
            
            if keyword not in ("decrypt","date","logstart","device") :  
                #try if keyword should be included 
                include=True
                try:
                    #try if key type is specified 
                    if conf.recorddict[layout][keyword]["incl"] == "no" : 
                        include=False
                except: 
                    #no include statement keyword should be process, set include to prevent except errors
                    include = True
                #process only keyword needs to be included (default):     
                try: 
                    if ((include) or (conf.includeall)): 
                        try:
                            #try if key type is specified  
                            keytype = conf.recorddict[layout][keyword]["type"]           
                        except: 
                            #if not default is num
                            keytype = "num"               
                        if keytype == "text" :
                            definedkey[keyword] = result_string[conf.recorddict[layout][keyword]["value"]:conf.recorddict[layout][keyword]["value"]+(conf.recorddict[layout][keyword]["length"]*2)]
                            definedkey[keyword] = codecs.decode(definedkey[keyword], "hex").decode('utf-8')
                            #print(definedkey[keyword])
                        if keytype == "num" :
                        #else:                    
                            definedkey[keyword] = int(result_string[conf.recorddict[layout][keyword]["value"]:conf.recorddict[layout][keyword]["value"]+(conf.recorddict[layout][keyword]["length"]*2)],16)                                     
                        if keytype == "numx" :
                            #process signed integer 
                            keybytes = bytes.fromhex(result_string[conf.recorddict[layout][keyword]["value"]:conf.recorddict[layout][keyword]["value"]+(conf.recorddict[layout][keyword]["length"]*2)])
                            definedkey[keyword] = int.from_bytes(keybytes, byteorder='big', signed=True)
                        if keytype == "log" :
                            # Proces log fields
                            definedkey[keyword] = logdict[conf.recorddict[layout][keyword]["pos"]-1]
                        if keytype == "logpos" :
                        #only display this field if positive    
                            # Proces log fields
                            if float(logdict[conf.recorddict[layout][keyword]["pos"]-1]) > 0 : 
                                definedkey[keyword] = logdict[conf.recorddict[layout][keyword]["pos"]-1]
                            else : definedkey[keyword] = 0
                        if keytype == "logneg" :
                        #only display this field if negative    
                            # Proces log fields
                            if float(logdict[conf.recorddict[layout][keyword]["pos"]-1]) < 0 : 
                                definedkey[keyword] = logdict[conf.recorddict[layout][keyword]["pos"]-1]    
                            else : definedkey[keyword] = 0
                except: 
                    if conf.verbose : print("\t - grottdata - error in keyword processing : ", keyword + " ,data processing stopped") 
                    return(8) 
                                 
        # test if pvserial was defined, if not take inverterid from config.
        device_defined = False 
        try:    
            definedkey["device"] = conf.recorddict[layout]["device"]["value"]
            device_defined = True
        except:         
            # test if pvserial was defined, if not take inverterid from config.     
            try: 
                test = definedkey["pvserial"]
            except: 
                definedkey["pvserial"] = conf.inverterid
                conf.recorddict[layout]["pvserial"] = {"value" : 0, "type" : "text"}
                if conf.verbose : print("\t - pvserial not found and device not specified used configuration defined invertid:", definedkey["pvserial"] ) 
     
        # test if dateoffset is defined, if not take set to 0 (no futher date retrieval processing) . 
        try: 
            # test of date is specified in layout
            dateoffset = int(conf.recorddict[layout]["date"]["value"]) 
        except:
            # no date specified, default no date specified
            dateoffset = 0        

        #proces date value if specifed 
        if dateoffset > 0 and (conf.gtime != "server" or buffered == "yes"):
            if conf.verbose: print("\t - " + 'Grott data record date/time processing started')
            #date
            pvyearI =  int(result_string[dateoffset:dateoffset+2],16)
            if pvyearI < 10 : pvyear = "200" + str(pvyearI)
            else: pvyear = "20" + str(pvyearI) 
            pvmonthI = int(result_string[dateoffset+2:dateoffset+4],16)
            if pvmonthI < 10 : pvmonth = "0" + str(pvmonthI)
            else: pvmonth = str(pvmonthI) 
            pvdayI = int(result_string[dateoffset+4:dateoffset+6],16)
            if pvdayI < 10 : pvday = "0" + str(pvdayI)
            else: pvday = str(pvdayI) 
            #Time
            pvhourI = int(result_string[dateoffset+6:dateoffset+8],16)
            if pvhourI < 10 : pvhour = "0" + str(pvhourI)
            else: pvhour = str(pvhourI) 
            pvminuteI = int(result_string[dateoffset+8:dateoffset+10],16)
            if pvminuteI < 10 : pvminute = "0" + str(pvminuteI)
            else: pvminute = str(pvminuteI) 
            pvsecondI = int(result_string[dateoffset+10:dateoffset+12],16)
            if pvsecondI < 10 : pvsecond = "0" + str(pvsecondI)
            else: pvsecond = str(pvsecondI) 
            # create date/time is format
            pvdate = pvyear + "-" + pvmonth + "-" + pvday + "T" + pvhour + ":" + pvminute + ":" + pvsecond
            # test if valid date/time in data record
            try:
                testdate = datetime.strptime(pvdate, "%Y-%m-%dT%H:%M:%S")
                jsondate = pvdate
                if conf.verbose : print("\t - date-time: ", jsondate) 
                timefromserver = False                                              # Indicate of date/time is from server (used for buffered data)           
            except ValueError:
                # Date could not be parsed - either the format is different or it's not a
                # valid date
                if conf.verbose : print("\t - " + "no or no valid time/date found, grott server time will be used (buffer records not sent!)")  
                timefromserver = True          
                jsondate = datetime.now().replace(microsecond=0).isoformat()
        else:
            if conf.verbose: print("\t - " + "Grott server date/time used") 
            jsondate = datetime.now().replace(microsecond=0).isoformat()   
            timefromserver = True     

        dataprocessed = True

    else:
        # old data processing only here for compatibility 
        serialfound = False 
        if(result_string.find(conf.SN) > -1):
            serialfound = True   

        if serialfound == True:
            
            jsondate = datetime.now().replace(microsecond=0).isoformat()
            timefromserver = True 

            if conf.verbose: print("\t - " + 'Growatt processing values for: ', bytearray.fromhex(conf.SN).decode())
            
            #Retrieve values 
            snstart = result_string.find(conf.SN)  
            definedkey["pvserial"] = result_string[snstart:snstart+20]
            definedkey["pvstatus"] = int(result_string[snstart+conf.offset*2+15*2:snstart+conf.offset*2+15*2+4],16)
            #Only process value if pvstatus is oke (this is because unexpected pvstatus of 257)
            if definedkey["pvstatus"] == 0 or definedkey["pvstatus"] == 1:
                definedkey["pvpowerin"] = int(result_string[snstart+conf.offset*2+17*2:snstart+conf.offset*2+17*2+8],16)
                definedkey["pv1voltage"] = int(result_string[snstart+conf.offset*2+21*2:snstart+conf.offset*2+21*2+4],16)
                definedkey["pv1current"] = int(result_string[snstart+conf.offset*2+23*2:snstart+conf.offset*2+23*2+4],16)
                definedkey["pv1watt"]    = int(result_string[snstart+conf.offset*2+25*2:snstart+conf.offset*2+25*2+8],16)
                definedkey["pv2voltage"] = int(result_string[snstart+conf.offset*2+29*2:snstart+conf.offset*2+29*2+4],16)
                definedkey["pv2current"] = int(result_string[snstart+conf.offset*2+31*2:snstart+conf.offset*2+31*2+4],16)
                definedkey["pv2watt"]    = int(result_string[snstart+conf.offset*2+33*2:snstart+conf.offset*2+33*2+8],16)
                definedkey["pvpowerout"] = int(result_string[snstart+conf.offset*2+37*2:snstart+conf.offset*2+37*2+8],16)
                definedkey["pvfrequentie"] = int(result_string[snstart+conf.offset*2+41*2:snstart+conf.offset*2+41*2+4],16)
                definedkey["pvgridvoltage"] = int(result_string[snstart+conf.offset*2+43*2:snstart+conf.offset*2+43*2+4],16)
                definedkey["pvenergytoday"] = int(result_string[snstart+conf.offset*2+67*2:snstart+conf.offset*2+67*2+8],16)
                definedkey["pvenergytotal"] = int(result_string[snstart+conf.offset*2+71*2:snstart+conf.offset*2+71*2+8],16)
                definedkey["pvtemperature"] = int(result_string[snstart+conf.offset*2+79*2:snstart+conf.offset*2+79*2+4],16)
                definedkey["pvipmtemperature"] = int(result_string[snstart+conf.offset*2+97*2:snstart+conf.offset*2+97*2+4],16)
                dataprocessed = True
                
            else:
                if conf.verbose: print("\t - " + 'No valid monitor data, PV status: :', definedkey["pvstatus"])                            
            
        else:   
            if conf.verbose: print("\t - "+ 'No Growatt data processed or SN not found:')
            if conf.trace: 
                print("\t - "+ 'Growatt unprocessed Data:')
                print(format_multi_line("\t\t - ", result_string))  
        
    if dataprocessed: 
        # only sendout data to MQTT if it is processed. 
        
        # Print values 
        if conf.verbose: 
            if conf.compat :
                #print in compatibility mode
                definedkey["pvserial"] = codecs.decode(definedkey["pvserial"], "hex").decode('utf-8') 
                print("\t - " + "Grott values retrieved:")
                print("\t\t - " + "pvserial:         ", definedkey["pvserial"])
                print("\t\t - " + "pvstatus:         ", definedkey["pvstatus"]) 
                print("\t\t - " + "pvpowerin:        ", definedkey["pvpowerin"]/10)
                print("\t\t - " + "pvpowerout:       ", definedkey["pvpowerout"]/10)
                print("\t\t - " + "pvenergytoday:    ", definedkey["pvenergytoday"]/10)
                print("\t\t - " + "pvenergytotal:    ", definedkey["pvenergytotal"]/10)
                print("\t\t - " + "pv1watt:          ", definedkey["pv1watt"]/10)
                print("\t\t - " + "pv2watt:          ", definedkey["pv2watt"]/10)
                print("\t\t - " + "pvfrequentie:     ", definedkey["pvfrequentie"]/100)
                print("\t\t - " + "pvgridvoltage:    ", definedkey["pvgridvoltage"]/10)
                print("\t\t - " + "pv1voltage:       ", definedkey["pv1voltage"]/10)
                print("\t\t - " + "pv1current:       ", definedkey["pv1current"]/10)
                print("\t\t - " + "pv2voltage:       ", definedkey["pv2voltage"]/10)
                print("\t\t - " + "pv2current:       ", definedkey["pv2current"]/10)
                print("\t\t - " + "pvtemperature:    ", definedkey["pvtemperature"]/10)
                print("\t\t - " + "pvipmtemperature: ", definedkey["pvipmtemperature"]/10)      
            else: 
                #dynamic print 
                print("\t - " + "Grott values retrieved:")
                for key in definedkey : 
                    # test if there is an divide factor is specifed 
                    try:  
                        #print(keyword)
                        keydivide =  conf.recorddict[layout][key]["divide"]
                        #print(keydivide)
                    except:
                        #print("error")
                        keydivide = 1  
        
                    if type(definedkey[key]) != type(str()) and keydivide != 1 :
                        printkey = "{:.1f}".format(definedkey[key]/keydivide)          
                    else :
                        printkey = definedkey[key]
                    print("\t\t - ",key.ljust(20) + " : ",printkey)              

        #create JSON message  (first create obj dict and then convert to a JSON message)                   

        
       
        # filter invalid 0120 record (0 < voltage_l1 > 500 ) 
        if header[14:16] == "20" :
            if (definedkey["voltage_l1"]/10 > 500) or (definedkey["voltage_l1"]/10 < 0) :
                print("\t - " + "Grott invalid 0120 record processing stopped") 
                return 

        #v270
        #compatibility with prev releases for "20" smart monitor record!
        #if device is not specified in layout record datalogserial is used as device (to distinguish record from inverter record)

        if device_defined == True:         
            deviceid = definedkey["device"]

        else : 
            if header[14:16] not in ("20","1b") :
                deviceid = definedkey["pvserial"]           
            else : 
                deviceid = definedkey["datalogserial"]
            
        jsonobj = {
                        "device" : deviceid,
                        "time" : jsondate, 
                        "buffered" : buffered,
                        "values" : {}
                    }

        for key in definedkey : 

            #if key != "pvserial" : 
                #if conf.recorddict[layout][key]["type"] == "num" : 
                # only add int values to the json object 
                #print(definedkey[key])
                #print(type(definedkey[key]))                                 
                #if type(definedkey[key]) == type(1) :                                                                     
                #    jsonobj["values"][key] = definedkey[key]
            jsonobj["values"][key] = definedkey[key]
                     
        jsonmsg = json.dumps(jsonobj) 
        
        if conf.verbose:
            print("\t - " + "MQTT jsonmsg: ")        
            print(format_multi_line("\t\t\t ", jsonmsg))   

        #do not process invalid records (e.g. buffered records with time from server) or buffered records if sendbuf = False
        if (buffered == "yes") : 
            if (conf.sendbuf == False) or (timefromserver == True) :
                if conf.verbose: print("\t - " + 'Buffered record not sent: sendbuf = False or invalid date/time format')  
                return

        if conf.nomqtt != True:
            #if meter data use mqtttopicname topic
            if (header[14:16] in ("20","1b")) and (conf.mqttmtopic == True) :
                mqtttopic = conf.mqttmtopicname 
            else : 
                #test if invertid needs to be added to topic
                if conf.mqttinverterintopic : 
                    mqtttopic = conf.mqtttopic + "/" + deviceid    
                else: mqtttopic = conf.mqtttopic    
            print("\t - " + 'Grott MQTT topic used : ' + mqtttopic)   
            
            if conf.mqttretain:
               if conf.verbose: print("\t - " + 'Grott MQTT message retain enabled')  

            try:
                #v2.7.1 add retrain variable  
                publish.single(mqtttopic, payload=jsonmsg, qos=0, retain=conf.mqttretain, hostname=conf.mqttip,port=conf.mqttport, client_id=conf.inverterid, keepalive=60, auth=conf.pubauth)
                if conf.verbose: print("\t - " + 'MQTT message message sent') 
            except TimeoutError:     
                if conf.verbose: print("\t - " + 'MQTT connection time out error') 
            except ConnectionRefusedError:     
                if conf.verbose: print("\t - " + 'MQTT connection refused by target')     
            except BaseException as error:     
                if conf.verbose: print("\t - "+ 'MQTT send failed:', str(error)) 
        else:
            if conf.verbose: print("\t - " + 'No MQTT message sent, MQTT disabled') 

        # process pvoutput if enabled
        if conf.pvoutput :      
            import requests
 
            pvidfound = False    
            if  conf.pvinverters == 1 :  
                pvssid = conf.pvsystemid[1]
                pvidfound = True    
            else:  
                for pvnum, pvid in conf.pvinverterid.items():  
                    if pvid == definedkey["pvserial"] :
                       print(pvid)
                       pvssid = conf.pvsystemid[pvnum]
                       pvidfound = True    
 
            if not pvidfound:
                if conf.verbose : print("\t - " + "pvsystemid not found for inverter : ", definedkey["pvserial"])   
                return
            if not pvout_limit.ok_send(definedkey["pvserial"], conf):
                # Will print a line for the refusal in verbose mode (see GrottPvOutLimit at the top)
                return
            if conf.verbose : print("\t - " + "Grott send data to PVOutput systemid: ", pvssid, "for inverter: ", definedkey["pvserial"]) 
            pvheader = { 
                "X-Pvoutput-Apikey"     : conf.pvapikey,
                "X-Pvoutput-SystemId"   : pvssid
            }
            
            pvodate = jsondate[:4] +jsondate[5:7] + jsondate[8:10]
            # debug: pvodate = jsondate[:4] +jsondate[5:7] + "16" 
            pvotime = jsondate[11:16] 
            # debug: pvotime = "09:05" 
            # if record is a smart monitor record sent smart monitor data to PVOutput
            if header[14:16] != "20" :
                pvdata = { 
                    "d"     : pvodate,
                    "t"     : pvotime,
                #2.7.1    "v1"    : definedkey["pvenergytoday"]*100,
                    "v2"    : definedkey["pvpowerout"]/10,
                    "v6"    : definedkey["pvgridvoltage"]/10
                    }
                if not conf.pvdisv1 :
                    pvdata["v1"] = definedkey["pvenergytoday"]*100
                else:   
                    if conf.verbose :  print("\t - " + "Grott PVOutput send V1 disabled") 
    
                if conf.pvtemp :
                    pvdata["v5"] = definedkey["pvtemperature"]/10
                
                #print(pvdata)
                if conf.verbose : print("\t\t - ", pvheader)
                if conf.verbose : print("\t\t - ", pvdata)
                reqret = requests.post(conf.pvurl, data = pvdata, headers = pvheader)
                if conf.verbose :  print("\t - " + "Grott PVOutput response: ") 
                if conf.verbose : print("\t\t - ", reqret.text)
            else: 
                # send smat monitor data c1 = 3 indiates v3 is lifetime energy (day wil be calculated), n=1 indicates is net data (import /export)
                # value seprated because it is not allowed to sent combination at once
                pvdata1 = { 
                    "d"     : pvodate,
                    "t"     : pvotime,
                    "v3"    : definedkey["pos_act_energy"]*100,
                    "c1"    : 3, 
                    "v6"    : definedkey["voltage_l1"]/10
                    }          
                    
                pvdata2 = { 
                   "d"     : pvodate,
                   "t"     : pvotime,
                   "v4"    : definedkey["pos_rev_act_power"]/10,
                   "v6"    : definedkey["voltage_l1"]/10,
                   "n"     : 1
                   }                       
                    #"v4"    : definedkey["pos_act_power"]/10,
                #print(pvheader)
                if conf.verbose : print("\t\t - ", pvheader)
                if conf.verbose : print("\t\t - ", pvdata1)
                if conf.verbose : print("\t\t - ", pvdata2)
                reqret = requests.post(conf.pvurl, data = pvdata1, headers = pvheader)
                if conf.verbose :  print("\t - " + "Grott PVOutput response SM1: ") 
                if conf.verbose : print("\t\t - ", reqret.text)
                reqret = requests.post(conf.pvurl, data = pvdata2, headers = pvheader)
                if conf.verbose :  print("\t - " + "Grott PVOutput response SM2: ") 
                if conf.verbose : print("\t\t - ", reqret.text)
        else: 
            if conf.verbose : print("\t - " + "Grott Send data to PVOutput disabled ") 

    # influxDB processing 
    if conf.influx:      
        if conf.verbose :  print("\t - " + "Grott InfluxDB publihing started")
        try:  
            import  pytz             
        except: 
            if conf.verbose :  print("\t - " + "Grott PYTZ Library not installed in Python, influx processing disabled")    
            conf.inlyx = False
            return
        try: 
            local = pytz.timezone(conf.tmzone) 
        except : 
            if conf.verbose :  
                if conf.tmzone ==  "local":  print("\t - " + "Timezone local specified default timezone used")
                else : print("\t - " + "Grott unknown timezone : ",conf.tmzone,", default timezone used")
            conf.tmzone = "local"
            local = int(time.timezone/3600)
            #print(local)

        if conf.tmzone == "local": 
           curtz = time.timezone 
           utc_dt = datetime.strptime (jsondate, "%Y-%m-%dT%H:%M:%S") + timedelta(seconds=curtz) 
        else :      
            naive = datetime.strptime (jsondate, "%Y-%m-%dT%H:%M:%S")
            local_dt = local.localize(naive, is_dst=None)
            utc_dt = local_dt.astimezone(pytz.utc)
        
        ifdt = utc_dt.strftime ("%Y-%m-%dT%H:%M:%S")
        if conf.verbose :  print("\t - " + "Grott original time : ",jsondate,"adjusted UTC time for influx : ",ifdt)
    
        # prepare influx jsonmsg dictionary    

        # if record is a smart monitor record use datalogserial as measurement (to distinguish from solar record) 
        if header[14:16] != "20" :
            ifobj = {
                        "measurement" : definedkey["pvserial"],
                        "time" : ifdt,
                        "fields" : {}
                    }    
        else: 
            ifobj = {
                                "measurement" : definedkey["datalogserial"],
                                "time" : ifdt,
                               "fields" : {}
                    }    

        for key in definedkey : 
            if key != "date" : 
                ifobj["fields"][key] = definedkey[key]
        
        #Create list for influx
        ifjson = [ifobj]

        print("\t - " + "Grott influxdb jsonmsg: ")        
        print(format_multi_line("\t\t\t ", str(ifjson)))   
        #if conf.verbose :  print("\t - " + "Grott InfluxDB publihing started")
  
        try: 
            if (conf.influx2):
                if conf.verbose :  print("\t - " + "Grott write to influxdb v2") 
                ifresult = conf.ifwrite_api.write(conf.ifbucket,conf.iforg,ifjson)   
                #print(ifresult)
            else: 
                if conf.verbose :  print("\t - " + "Grott write to influxdb v1") 
                ifresult = conf.influxclient.write_points(ifjson)
        #except : 
        except Exception as e:
            # if  conf.verbose: 
                print("\t - " + "Grott InfluxDB error ")
                print(e) 
                raise SystemExit("Grott Influxdb write error, grott will be stopped") 
            
    else: 
            if conf.verbose : print("\t - " + "Grott Send data to Influx disabled ")      

    if conf.extension : 
        
        if conf.verbose :  print("\t - " + "Grott extension processing started : ", conf.extname)
        import importlib
        try: 
            module = importlib.import_module(conf.extname, package=None)
        except :
            if conf.verbose : print("\t - " + "Grott import extension failed:", conf.extname)      
            return

        try:
            ext_result = module.grottext(conf,result_string,jsonmsg) 
            if conf.verbose :  
                print("\t - " + "Grott extension processing ended : ", ext_result)
        except Exception as e:
            print("\t - " + "Grott extension processing error:", repr(e))
            if conf.verbose:
                import traceback
                print("\t - " + traceback.format_exc())
            #print("\t - " + "Grott extension processing error ")
            #print(e) 
            #return

        #if conf.verbose :  
            #print("\t - " + "Grott extension processing ended : ", ext_result)
            ##print("\t -", ext_result)
    else: 
            if conf.verbose : print("\t - " + "Grott extension processing disabled ")      

