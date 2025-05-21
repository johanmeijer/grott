"""grottdata.py processing data functions"""
# Version 3.2.0
# Updated: 2025-05-21
#!change self.vrmdata 3.2.0_20250521 in grott.conf!!
import logging
#import time
from datetime import datetime, timedelta
#from os import times_result
#import pytz
import time
#import sys
#import struct
import textwrap
from itertools import cycle # to support "cycling" the iterator
import json
import codecs
from typing import Dict
#from grottmqtt import MQTTPublisher
from concurrent.futures import ThreadPoolExecutor
import paho.mqtt.client as mqtt
import socket

#set logging
logger = logging.getLogger(__name__)


class MQTTPublisher:
    def __init__(self, hostname, port, client_id, auth=None, socket_timeout=1.0):
        """
        Initialize the MQTT publisher.

        Args:
            hostname (str): MQTT broker hostname or IP address.
            port (int): MQTT broker port (e.g., 1883).
            client_id (str): Unique client ID for the MQTT connection.
            auth (dict, optional): Dictionary with 'username' and 'password' for authentication.
            socket_timeout (float): Socket timeout in seconds for MQTT operations (default: 1.0).
        """
        self.hostname = hostname
        self.port = port
        self.client_id = client_id
        self.auth = auth
        self.socket_timeout = socket_timeout

    def publish(self, topic, payload, qos=0, retain=False, timeout=1.0):
        """
        Publish an MQTT message with a timeout.

        Args:
            topic (str): MQTT topic to publish to.
            payload (str): Message payload (e.g., JSON string).
            qos (int): Quality of Service level (0, 1, or 2; default: 0).
            retain (bool): Whether to retain the message on the broker (default: False).
            timeout (float): Maximum time to wait for the publish operation (default: 1.0 seconds).

        Returns:
            bool: True if the publish succeeded, False if it failed (e.g., due to timeout or error).
        """
        def publish_message():
            client = mqtt.Client(client_id=self.client_id)  # New client per call
            if self.auth:
                client.username_pw_set(self.auth['username'], self.auth['password'])
            start_time = time.time()
            logger.debug("Starting MQTT publish to topic: %s", topic)
            try:
                client.connect(self.hostname, self.port, keepalive=60)
                sock = client.socket()
                if sock is not None:
                    sock.settimeout(self.socket_timeout)
                    logger.debug("Socket timeout set to %.2f seconds", self.socket_timeout)
                else:
                    logger.error("No socket available after connect for topic: %s", topic)
                    raise RuntimeError("MQTT client has no socket")
                client.publish(topic, payload=payload, qos=qos, retain=retain)
                logger.debug("Publish completed in %.2f seconds", time.time() - start_time)
            finally:
                client.disconnect()
                logger.debug("MQTT client disconnected")

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(publish_message)
                future.result(timeout=timeout)
            logger.debug("MQTT message published successfully to topic: %s", topic)
            return True
        except TimeoutError:
            logger.debug("Timeout occurred while publishing to topic: %s", topic)
            return False
        except ConnectionRefusedError:
            logger.debug("Connection refused by MQTT broker for topic: %s", topic)
            return False
        except socket.timeout:
            logger.debug("Socket timeout while publishing to topic: %s", topic)
            return False
        except Exception as e:
            logger.debug("Exception in MQTT publish: %s", e)
            return False

    def __del__(self):
        """
        Destructor to ensure cleanup (no client to disconnect since created per call).
        """
        pass

class GrottPvOutLimit:
    """limit the amount of request sent to pvoutput"""
    def __init__(self):
        self.register: Dict[str, int] = {}

    def ok_send(self, pvserial: str, conf) -> bool:
        """test if it ok to send to pvoutpt"""
        now = time.perf_counter()
        ok = False
        if self.register.get(pvserial):
            ok = True if self.register.get(pvserial) + conf.pvuplimit * 60 < now else False
            if ok:
                self.register[pvserial] = int(now)
            else:
                logger.debug('\t - PVOut: Update refused for %s due to time limitation',{pvserial})
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


def decrypt(decdata) :
    """#decrypt data."""
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

    logger.debug("Growatt data decrypted V2")
    return result_string

def str2bool(defstr):
    """Convert string input to bool """
    if defstr in ("True", "true", "TRUE", "y", "Y", "yes", "YES", 1, "1") :
        defret = True
    if defstr in ("False", "false", "FALSE", "n", "N", "no", "NO", 0, "0") :
        defret = False
    if 'defret' in locals():
        return defret
    else :
        return



def AutoCreateLayout(conf,data,protocol,deviceno,recordtype) :
    """ Auto generate layout definitions from data record """
    # At this moment 3 types of layout description are known:
    # -"Clasic" inverters (eg. 1500-S) for Grott
    # -"New type" Inverters  (TL-X, TL3, MAD, MIX, MAX, MIX, SPA, SPH )
    # -"SPF" Inverters, not yet covered in the AutoCreateLayout, while detection interferes with Classic type detection.
    #
    logger.debug("automatic determine data layout started")
    datalen = len(data)

    # decrypt data if needed
    if protocol in ("05","06") :
        result_string = decrypt(data)
    else : result_string = data.hex()

    # do not process ack records.
    if datalen < conf.mindatarec :
        layout = "none"
        return(layout,result_string)

    #create standard layout
    layout = "T" + protocol + deviceno + recordtype
    #v270 add X for extended except for smart monitor records
    if ((datalen > 375) and recordtype not in conf.smartmeterrec ) :  layout = layout + "X"

    if recordtype  in conf.datarec:
        #for data records create or select layout definition

        inverter_type = conf.invtype.upper()
        if inverter_type == "DEFAULT" :
            logger.debug("determine invertype")
            #is invtypemap defined (map typeing mulitple inverters?) ?
            if any(conf.invtypemap) :
                logger.debug("invtypemap defined: %s",conf.invtypemap)
                #process invetermap defined:
                serialloc = 36
                if protocol == "06" :
                    serialloc = 76
                try:
                    inverter_serial = codecs.decode(result_string[serialloc:serialloc+20], "hex").decode('ASCII')
                    try:
                        inverter_type = conf.invtypemap[inverter_serial].upper()
                        logger.debug("Inverter serial: {0} found in invtypemap - using inverter type {1}".format(inverter_serial,inverter_type))
                    except:
                        logger.debug("Inverter serial: {0} not found invtypemap - using inverter type {1}".format(inverter_serial,inverter_type))

                except:
                    logger.critical("error in inverter_serial retrieval, try without invertypemap")

        if inverter_type == "AUTO" :
            registergrp = {}
            #layout = "AUTOGEN"
            if protocol in ("00","02") : initlayout = "ALO02"
            else : initlayout = "ALO" + protocol
            logger.debug("Base Layout selected %s: ",initlayout)
            layout = codecs.decode(result_string[conf.alodict[initlayout]["pvserial"]["value"]:conf.alodict[initlayout]["pvserial"]["value"]+20], "hex").decode('utf-8')

            try:
               print(layout)
               print(conf.recorddict[layout]["pvserial"]["value"])
               test = conf.recorddict[layout]["pvserial"]["value"]
               logger.debug("layout already exist and will be reused: %s",layout)
               return(layout,result_string)

            except Exception as e:
               print(e)
               logger.debug("layout does not excist and will be created: %s", layout)
               conf.recorddict[layout] = {}

            logger.debug("layout record used:")
            for keyword in conf.alodict[initlayout] :
                conf.recorddict[layout][keyword] = conf.alodict[initlayout][keyword]
                #format debug
                addtab = ""
                if len(keyword) < 5 : addtab = "\t"
                if len(keyword) < 13 : addtab = addtab + "\t"
                logger.debug("\t {0}: \t\t".format(keyword)+addtab+"{0}".format(conf.recorddict[layout][keyword]))

            #Determine register groups used in datarecord  (for now max 5 groups possible)
            registergrp = {}
            #getgroup start from baselayout
            grouploc = conf.recorddict[layout]["datastart"]["value"]
            for group in range(5) :
                groupstart = result_string[grouploc : grouploc+4]
                groupend = result_string[grouploc + 4 : grouploc+8]
                registergrp[group] = { "start" : int(groupstart,16), "end" : int(groupend,16), "grouploc" : grouploc}
                # calculate next group start location (if any)
                grouploc = grouploc + 8 + (int(groupend,16) - int (groupstart,16) +1)*4
                logger.debug("Detected registergroup {0}, values: {1}".format(group,registergrp[group]))
                #is this end of record?
                if grouploc >= len(data)*2-4:
                   break

            #create layout record from register groups:
            # #set basic dataloc:
            # dataloc = conf.recorddict[layout]["datastart"]["value"]
            # #set basic lcoation where first reg starts
            # grouploc = dataloc +8
            # print ("datastart: ", dataloc)
            # print("grouploc: ", grouploc)
            # Check for prot type 1 select different layout, be aware at this time we can detect difference between type = S and type SPF inverters, SPF need to be specified seperate in invtype!!!!!
            layoutversion = ""
            if registergrp[0]["end"] < 45 : layoutversion = "V1"

            for group in registergrp :

                grplayout = "ALO_"+str(registergrp[group]["start"])+"_"+str(registergrp[group]["end"]) + layoutversion
                grouploc = registergrp[group]["grouploc"]

                logger.debug("proces layout file: %s",grplayout)
                logger.debug("groupstart location: %s",registergrp[group]["grouploc"])

                try:
                    test = conf.alodict[grplayout]
                except:
                    logger.warning("layout file doesnot exist, and will not be processed: %s",grplayout)
                    break

                for keyword in conf.alodict[grplayout] :

                    conf.recorddict[layout][keyword] = conf.alodict[grplayout][keyword]
                    #calculate offset value and add/override in layout file.
                    keyloc = grouploc + 8 + ((conf.alodict[grplayout][keyword]["register"])-registergrp[group]["start"])*4
                    conf.recorddict[layout][keyword]["value"] = keyloc
                    #format debug
                    addtab = ""
                    if len(keyword) < 5 : addtab = "\t"
                    if len(keyword) < 13 : addtab = addtab + "\t"
                    logger.debug("\t {0}: \t".format(keyword)+addtab+"{0}".format(conf.recorddict[layout][keyword]))


        if inverter_type.upper() not in ("DEFAULT", "AUTO") and recordtype not in conf.smartmeterrec :
                        layout = layout + inverter_type.upper()

        logger.debug("Auto Layout determined : %s", layout)
    try:
        # does record layout record exists?
        test = conf.recorddict[layout]
    except:
        #try generic if generic record exist
        logger.debug("no matching specific record layout found, try generic")
        if recordtype in conf.datarec:
            layout = layout.replace(deviceno+recordtype, "NNNN")
            try:
                # does generic record layout exists?
                test = conf.recorddict[layout]
            except:
                #no valid record fall back on old processing?
                logger.debug("no matching generic inverter record layout found")
                layout = "none"
        #test smartmeter layout
        if recordtype in conf.smartmeterrec:
            print(layout)
            layout = layout.replace(deviceno, "NN")
            print(layout)

            try:
                # does generic record layout exists?
                test = conf.recorddict[layout]
            except:
                #no valid record
                logger.debug("no matching generic smart meter record layout found")
                layout = "none"

    return(layout,result_string)




def procdata(conf,data):
    #(re)set loglevel
    logger.setLevel(conf.loglevel.upper())
    logger.info ("Data processing started")

    header = "".join("{:02x}".format(n) for n in data[0:8])
    buffered = "nodetect"                                               # set buffer detection to nodetect (for compat mode), wil in auto detection changed to no or yes
    protocol = header[6:8]                                              # SET PROTOCOL TYPE(00, 02, 5, 06)
    deviceno = header[12:14]                                            #set devicenumber (for shinewifi ,lan always: 01 for shinelink 5x)
    recordtype =  header[14:16]                                         # SET RECORD TYPE (04, 50 are inverter data records, 20,1b smart meter)

    if recordtype == "50" : buffered = "yes"                            # record type 50 is a historical (buffered) record type
    else: buffered = "no"

    #if not conf.compat :
    #Create layout
    layout,result_string = AutoCreateLayout(conf,data,protocol,deviceno,recordtype)

    if layout == "none" :
        logger.warning("No matching layout found data record will not be processed")
        novalidrec = True

    else : logger.info("Record layout used : %s", layout)
    #save layout in conf to being passed to extension
    conf.layout = layout

    #print data records (original/decrypted)
    logger.debug("Original data:\n{0} \n".format(format_multi_line("\t",data,80)))
    logger.debug("Decrypted data:\n{0} \n".format(format_multi_line("\t",result_string,80)))

    # Test length if < 12 it is a data ack record or no layout record is defined
    if recordtype not in conf.datarec+conf.smartmeterrec or conf.layout == "none":
        logger.debug("Grott data ack record or data record not defined, no processing done")
        return

    # Inital flag to detect off real data is processed
    dataprocessed = False

    # define dictonary for key values.
    definedkey = {}

    #if conf.compat is False:
    # dataprocessing with defined record layout

    if conf.verbose:
        print("\t - " + 'Growatt new layout processing')
        #print("\t\t - " + "decrypt       : ",conf.decrypt)
        #print("\t\t - " + "offset        : ", conf.offset)
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
                #return(8)

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



    if dataprocessed:
        # only sendout data to MQTT if it is processed.

        # Print values
        if conf.verbose:
            # if conf.compat :
            #     #print in compatibility mode
            #     definedkey["pvserial"] = codecs.decode(definedkey["pvserial"], "hex").decode('utf-8')
            #     print("\t - " + "Grott values retrieved:")
            #     print("\t\t - " + "pvserial:         ", definedkey["pvserial"])
            #     print("\t\t - " + "pvstatus:         ", definedkey["pvstatus"])
            #     print("\t\t - " + "pvpowerin:        ", definedkey["pvpowerin"]/10)
            #     print("\t\t - " + "pvpowerout:       ", definedkey["pvpowerout"]/10)
            #     print("\t\t - " + "pvenergytoday:    ", definedkey["pvenergytoday"]/10)
            #     print("\t\t - " + "pvenergytotal:    ", definedkey["pvenergytotal"]/10)
            #     print("\t\t - " + "pv1watt:          ", definedkey["pv1watt"]/10)
            #     print("\t\t - " + "pv2watt:          ", definedkey["pv2watt"]/10)
            #     print("\t\t - " + "pvfrequentie:     ", definedkey["pvfrequentie"]/100)
            #     print("\t\t - " + "pvgridvoltage:    ", definedkey["pvgridvoltage"]/10)
            #     print("\t\t - " + "pv1voltage:       ", definedkey["pv1voltage"]/10)
            #     print("\t\t - " + "pv1current:       ", definedkey["pv1current"]/10)
            #     print("\t\t - " + "pv2voltage:       ", definedkey["pv2voltage"]/10)
            #     print("\t\t - " + "pv2current:       ", definedkey["pv2current"]/10)
            #     print("\t\t - " + "pvtemperature:    ", definedkey["pvtemperature"]/10)
            #     print("\t\t - " + "pvipmtemperature: ", definedkey["pvipmtemperature"]/10)
            # else:

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
            if header[14:16] not in conf.smartmeterrec :
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
               logger.debug("MQTT messaging initialization started")
                # Initialize the MQTT publisher
               logger.debug("MQTT message about to be sent for deviceid: %s", deviceid)
               mqtt_publisher = MQTTPublisher(
                  hostname=conf.mqttip,
                  port=conf.mqttport,
                  client_id=conf.inverterid,
                  auth=conf.pubauth,
                  socket_timeout=1.0
                  )
               # Publish the message
               success = mqtt_publisher.publish(
                    topic=mqtttopic,
                    payload=jsonmsg,
                    qos=0,
                    retain=conf.mqttretain,
                    timeout=1.0
                    )
               if success:
                  logger.debug("MQTT message published for deviceid: %s", deviceid)
               else:
                  logger.debug("MQTT message publishing failed for deviceid: %s", deviceid)
            except TimeoutError:
               if conf.verbose: print("\t - " + 'MQTT connection time out error')
            except ConnectionRefusedError:
               if conf.verbose: print("\t - " + 'MQTT connection refused by target')
            except socket.timeout:
               if conf.verbose: print("\t - " + 'MQTT socket timeout')
            except BaseException as error:
               if conf.verbose: print("\t - " + 'MQTT send failed:', str(error))
            except Exception as e:
               print("\t - " + "Grott MQTT publish error ", str(e))
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
#                with ThreadPoolExecutor(max_workers=5) as executor:
#                      future = executor.submit(
#                          conf.influxclient.write_points,
#                          ifjson
#                )
#                future.result(timeout=1)  # Wait for 1 second, raise TimeoutError if exceeded
#                future.exception(timeout=1)
        #except :
        except Exception as e:
            # if  conf.verbose:
                print("\t - " + "Grott InfluxDB error ")
                print(e)
#                raise SystemExit("Grott Influxdb write error, grott will be stopped")

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

