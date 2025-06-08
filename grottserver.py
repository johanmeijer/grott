import select
import socket
import queue
import textwrap
#import libscrc
import threading
import time
import http.server
import json, codecs
from itertools import cycle
#from io import BytesIO
from datetime import datetime
from urllib.parse import urlparse, parse_qs, parse_qsl
from collections import defaultdict
import logging
import os,psutil
from grottdata import procdata

#set logging definities
#logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# grottserver.py emulates the server.growatt.com website and is initial developed for debugging and testing grott.
# Updated: 2025-04-11
# Version:
vrmserver = "3.2.1_20250608"

loggerreg = {}
commandresponse =  defaultdict(dict)

# Declare Variables (to be moved to config file later)
#serverhost = "0.0.0.0"
#serverport = 5781
httphost = "0.0.0.0"
#httpport = 5782
verbose = True
#firstping = False
sendseq = 1
#Time to sleep waiting on API response
#apirespwait = 0.1
#Totaal time in seconds to wait on Iverter Response
#inverterrespwait = 10

#Totaal time in seconds to wait on Datalogger Response
#dataloggerrespwait = 5
#ConnectionTimeout = 300 is now configurable in grott.ini

def addLoggingLevel(levelName, levelNum, methodName=None):
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError("{} already defined in logging module".format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError("{} already defined in logging module".format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError("{} already defined in logger class".format(methodName))

    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)

class Miniconf:
    """ this class is only there to enable backward compatibility with
    grottserver runs standalone with no other Grott components available"""

    def __init__(self, vrmserver):
            """set default configuration settings"""
            self.verrel = vrmserver
            self.loglevel = "DEBUG"
            self.verbose = True
            self.mode = "serversa"
            self.serverpassthrough = False
            self.serverip = "0.0.0.0"
            self.serverport = 5781
            #self.serverip = "0.0.0.0"
            self.httpport = 5782
            self.apirespwait = 0.1                                                                  #Time to sleep waiting on API response
            self.inverterrespwait = 10                                                              #Totaal time in seconds to wait on Iverter Response
            self.dataloggerrespwait = 5

# Formats multi-line data
def format_multi_line(prefix, string, size=80):
    size -= len(prefix)
    if isinstance(string, bytes):
        string = ''.join(r'\x{:02x}'.format(byte) for byte in string)
        if size % 2:
            size -= 1
    return '\n'.join([prefix + line for line in textwrap.wrap(string, size)])


# encrypt / decrypt data.
def decrypt(decdata):

    ndecdata = len(decdata)

    # Create mask and convert to hexadecimal
    mask = "Growatt"
    hex_mask = ['{:02x}'.format(ord(x)) for x in mask]
    nmask = len(hex_mask)

    # start decrypt routine
    unscrambled = list(decdata[0:8])  # take unscramble header

    for i, j in zip(range(0, ndecdata-8), cycle(range(0, nmask))):
        unscrambled = unscrambled + [decdata[i+8] ^ int(hex_mask[j], 16)]

    result_string = "".join("{:02x}".format(n) for n in unscrambled)

    logger.debugv("\t - " + "Grott - data decrypted V2")
    return result_string

def calc_crc(data):
    #calculate CR16, Modbus.
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for i in range(8):
            if ((crc & 1) != 0):
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc

def validate_record(xdata):
    # validata data record on length and CRC (for "05" and "06" records)
    logger.debug("validate data record")
    data = bytes.fromhex(xdata)
    ldata = len(data)
    len_orgpayload = int.from_bytes(data[4:6],"big")
    header = "".join("{:02x}".format(n) for n in data[0:8])
    protocol = header[6:8]

    if protocol in ("05","06"):
        lcrc = 4
        crc = int.from_bytes(data[ldata-2:ldata],"big")
    else:
        lcrc = 0

    len_realpayload = (ldata*2 - 12 -lcrc) / 2

    if protocol != "02" :
                crc_calc = calc_crc(data[0:ldata-2])

    if len_realpayload == len_orgpayload :
        returncc = 0
        if protocol != "02" and crc != crc_calc:
            returncc = 8
    else :
        returncc = 8

    return(returncc)

def htmlsendresp(self, responserc, responseheader,  responsetxt) :
        #send response
        self.send_response(responserc)
        self.send_header('Content-type', responseheader)
        self.end_headers()
        self.wfile.write(responsetxt)
        if verbose: print("\t - Grotthttpserver - http response send: ", responserc, responseheader, responsetxt)

def createtimecommand(self, protocol,deviceid,loggerid,sequenceno) :
        protocol = protocol
        loggerid = loggerid
        #override diviceid (always send time to logger)
        deviceid = "01"
        sequenceno = sequenceno
        bodybytes = loggerid.encode('ISO-8859-1')
        body = bodybytes.hex()
        if protocol == "06" :
            body = body + "0000000000000000000000000000000000000000"
        register = 31
        body = body + "{:04x}".format(int(register))
        currenttime = str(datetime.now().replace(microsecond=0))
        timex = currenttime.encode('ISO-8859-1').hex()
        timel = "{:04x}".format(int(len(timex)/2))
        body = body + timel + timex
        #calculate length of payload = body/2 (str => bytes) + 2 bytes invertid + command.
        bodylen = int(len(body)/2+2)

        #create header
        header = "0001" + "00" + protocol + "{:04x}".format(bodylen) + deviceid + "18"
        #print(header)
        body = header + body
        body = bytes.fromhex(body)
        if verbose:
            print("\t - Grottserver - Time plain body : ")
            print(format_multi_line("\t\t ",body))

        if protocol != "02" :
            #encrypt message
            body = decrypt(body)
            crc16 = calc_crc(bytes.fromhex(body))
            body = bytes.fromhex(body) + crc16.to_bytes(2, "big")

        if verbose:
            print("\t - Grottserver - Time command created :")
            print(format_multi_line("\t\t ",body))

        #just to be sure delete register info
        try:
            del commandresponse["18"]["001f"]
        except:
            pass

        return(body)

class GrottHttpRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, conf, send_queuereg, *args):
        self.send_queuereg = send_queuereg
        self.conf=conf
        super().__init__(*args)

    def do_GET(self):
        try:
            if verbose: print("\t - Grotthttpserver - Get received ")
            #print(self.conf)
            #parse url
            url = urlparse(self.path)
            urlquery = parse_qs(url.query)

            if self.path == '/':
                self.path = "grott.html"

            #only allow files from current directory
            if self.path[0] == '/':
                self.path =self.path[1:len(self.path)]

            #if self.path.endswith(".html") or self.path.endswith(".ico"):
            if self.path == "grott.html" or self.path == "favicon.ico":
                try:
                    f = open(self.path, 'rb')
                    self.send_response(200)
                    if self.path.endswith(".ico") :
                        self.send_header('Content-type', 'image/x-icon')
                    else:
                        self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(f.read())
                    f.close()
                    return
                except IOError:
                    responsetxt = b"<h2>Welcome to Grott the growatt inverter monitor: " + str.encode(vrmserver) + b"</h2><br><h3>Made by Ledidobe, Johan Meijer</h3>"
                    responserc = 200
                    responseheader = "text/html"
                    htmlsendresp(self,responserc,responseheader,responsetxt)
                    return

            elif self.path.startswith("info"):
                    #retrieve grottserver status
                    if verbose: print("\t - Grotthttpserver - Status requested")


                    print("\t - Grottserver #active threads count: ", threading.active_count())
                    activethreads = threading.enumerate()
                    for idx, item in enumerate(activethreads):
                        print("\t - ", item)

                    try:
                        import os, psutil
                        #print(os.getpid())
                        print("\t - Grottserver memory in use : ", psutil.Process(os.getpid()).memory_info().rss/1024**2)

                    except:
                        print("\t - Grottserver PSUTIL not available no process information can be printed")

                    #retrieve grottserver status
                    print("\t - Grottserver connection queue : ")
                    print("\t - ", list(self.send_queuereg.keys()))
                    #responsetxt = json.dumps(list(send_queuereg.keys())).encode('ISO-8859-1')
                    responsetxt = b"<h2>Grottserver info generated, see log for details</h2>"
                    responserc = 200
                    responseheader = "text/html"
                    htmlsendresp(self,responserc,responseheader,responsetxt)
                    return

            elif self.path.startswith("datalogger") or self.path.startswith("inverter") :
                if self.path.startswith("datalogger"):
                    if verbose: print("\t - " + "Grotthttpserver - datalogger get received : ", urlquery)
                    sendcommand = "19"
                else:
                    if verbose: print("\t - " + "Grotthttpserver - inverter get received : ", urlquery)
                    sendcommand = "05"

                #validcommand = False
                if urlquery == {} :
                    #no command entered return loggerreg info:
                    responsetxt = json.dumps(loggerreg).encode('ISO-8859-1')
                    responserc = 200
                    responseheader = "text/html"
                    htmlsendresp(self,responserc,responseheader,responsetxt)
                    return

                else:

                    try:
                        #is valid command specified?
                        command = urlquery["command"][0]
                        #print(command)
                        if command in ("register", "regall") :
                            if verbose: print("\t - " + "Grotthttpserver: get command: ", command)
                        else :
                            #no valid command entered
                            responsetxt = b'no valid command entered'
                            responserc = 400
                            responseheader = "text/html"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return
                    except:
                        responsetxt = b'no command entered'
                        responserc = 400
                        responseheader = "text/html"
                        htmlsendresp(self,responserc,responseheader,responsetxt)
                        return

                    # test if datalogger  and / or inverter id is specified.
                    try:
                        if sendcommand == "05" :
                            inverterid_found = False
                            try:
                                #test if inverter id is specified and get loggerid
                                inverterid = urlquery["inverter"][0]
                                for key in loggerreg.keys() :
                                    for key2 in loggerreg[key].keys() :
                                        if key2 == inverterid :
                                            dataloggerid = key
                                            inverterid_found = True
                                            break
                            except :
                                inverterid_found = False

                            if not inverterid_found :
                                responsetxt = b'no or no valid invertid specified'
                                responserc = 400
                                responseheader = "text/html"
                                htmlsendresp(self,responserc,responseheader,responsetxt)
                                return

                            try:
                                # is format keyword specified? (dec, text, hex)
                                formatval = urlquery["format"][0]
                                if formatval not in ("dec", "hex","text") :
                                    responsetxt = b'invalid format specified'
                                    responserc = 400
                                    responseheader = "text/body"
                                    htmlsendresp(self,responserc,responseheader,responsetxt)
                                    return
                            except:
                                # no set default format op dec.
                                formatval = "dec"

                        if sendcommand == "19" :
                            # if read datalogger info.
                            dataloggerid = urlquery["datalogger"][0]

                            try:
                                # Verify dataloggerid is specified
                                dataloggerid = urlquery["datalogger"][0]
                                test = loggerreg[dataloggerid]
                            except:
                                responsetxt = b'invalid datalogger id '
                                responserc = 400
                                responseheader = "text/body"
                                htmlsendresp(self,responserc,responseheader,responsetxt)
                                return
                    except:
                            # do not think we will come here
                            responsetxt = b'no datalogger or inverterid specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return

                    # test if register is specified and set reg value.
                    if command == "register":
                        #test if valid reg is applied
                        if int(urlquery["register"][0]) >= 0 and int(urlquery["register"][0]) < 4096 :
                            register = urlquery["register"][0]
                        else:
                            responsetxt = b'invalid reg value specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return
                    elif command == "regall" :
                        comresp  = commandresponse[sendcommand]
                        responsetxt = json.dumps(comresp).encode('ISO-8859-1')
                        responserc = 200
                        responseheader = "text/body"
                        htmlsendresp(self,responserc,responseheader,responsetxt)
                        return


                    else:
                        responsetxt = b'command not defined or not available yet'
                        responserc = 400
                        responseheader = "text/body"
                        htmlsendresp(self,responserc,responseheader,responsetxt)
                        return

                bodybytes = dataloggerid.encode('ISO-8859-1')
                body = bodybytes.hex()

                if loggerreg[dataloggerid]["protocol"] == "06" :
                    body = body + "0000000000000000000000000000000000000000"
                body = body + "{:04x}".format(int(register))
                #assumption now only 1 reg query; other put below end register
                body = body + "{:04x}".format(int(register))
                #calculate length of payload = body/2 (str => bytes) + 2 bytes invertid + command.
                bodylen = int(len(body)/2+2)

                #device id for datalogger is by default "01" for inverter deviceid is inverterid!
                deviceid = "01"
                # test if it is inverter command and set
                if sendcommand == "05":
                    deviceid = (loggerreg[dataloggerid][inverterid]["inverterno"])
                    print("\t - Grotthttpserver: selected deviceid :", deviceid)

                header = "{:04x}".format(sendseq) + "00" + loggerreg[dataloggerid]["protocol"] + "{:04x}".format(bodylen) + deviceid + sendcommand
                body = header + body
                body = bytes.fromhex(body)

                if verbose:
                    print("\t - Grotthttpserver - unencrypted get command:")
                    print(format_multi_line("\t\t ",body))

                if loggerreg[dataloggerid]["protocol"] != "02" :
                    #encrypt message
                    body = decrypt(body)
                    crc16 = calc_crc(bytes.fromhex(body))
                    body = bytes.fromhex(body) + crc16.to_bytes(2, "big")

                # add header
                if verbose:
                    print("\t - Grotthttpserver: Get command created :")
                    print(format_multi_line("\t\t ",body))

                # queue command
                qname = loggerreg[dataloggerid]["ip"] + "_" + str(loggerreg[dataloggerid]["port"])
                self.send_queuereg[qname].put(body)
                responseno = "{:04x}".format(sendseq)
                regkey = "{:04x}".format(int(register))
                try:
                    del commandresponse[sendcommand][regkey]
                except:
                    pass


                #wait for response
                #Set #retry waiting loop for datalogger or inverter
                if sendcommand == "05" :
                   wait = round(self.conf.inverterrespwait/self.conf.apirespwait)
                   #if verbose: print("\t - Grotthttpserver - wait Cycles:", wait )
                else :
                    wait = round(self.conf.dataloggerrespwait/self.conf.apirespwait)
                    #if verbose: print("\t - Grotthttpserver - wait Cycles:", wait )

                for x in range(wait):
                    if verbose: print("\t - Grotthttpserver - wait for GET response")
                    try:
                        comresp = commandresponse[sendcommand][regkey]

                        if sendcommand == "05" :
                            if formatval == "dec" :
                                comresp["value"] = int(comresp["value"],16)
                            elif formatval == "text" :
                                comresp["value"] = codecs.decode(comresp["value"], "hex").decode('ISO-8859-1')
                        responsetxt = json.dumps(comresp).encode('ISO-8859-1')
                        responserc = 200
                        responseheader = "text/body"
                        htmlsendresp(self,responserc,responseheader,responsetxt)
                        return

                    except  :
                        #wait for second and try again
                         #Set retry waiting cycle time loop for datalogger or inverter

                        time.sleep(self.conf.apirespwait)

                try:
                    if comresp != "" :
                        responsetxt = json.dumps(comresp).encode('ISO-8859-1')

                        responserc = 200
                        responseheader = "text/body"
                        htmlsendresp(self,responserc,responseheader,responsetxt)
                        return

                except :
                    responsetxt = b'no or invalid response received'
                    responserc = 400
                    responseheader = "text/body"
                    htmlsendresp(self,responserc,responseheader,responsetxt)
                    return

                responsetxt = b'OK'
                responserc = 200
                responseheader = "text/body"
                if verbose: print("\t - " + "Grott: datalogger command response :", responserc, responsetxt, responseheader)
                htmlsendresp(self,responserc,responseheader,responsetxt)
                return

            elif self.path == 'help':
                responserc = 200
                responseheader = "text/body"
                responsetxt = b'No help available yet'
                htmlsendresp(self,responserc,responseheader,responsetxt)
                return
            else:
                self.send_error(400, "Bad request")

        except Exception as e:
            print("\t - Grottserver - exception in httpserver thread - get occured : ", e)

    def do_PUT(self):
        try:
            #if verbose: print("\t - Grott: datalogger PUT received")

            url = urlparse(self.path)
            urlquery = parse_qs(url.query)

            #only allow files from current directory
            if self.path[0] == '/':
                self.path =self.path[1:len(self.path)]

            if self.path.startswith("datalogger") or self.path.startswith("inverter") :
                if self.path.startswith("datalogger"):
                    if verbose: print("\t - Grotthttpserver - datalogger PUT received : ", urlquery)
                    sendcommand = "18"
                else:
                    if verbose: print("\t - Grotthttpserver - inverter PUT received : ", urlquery)
                    # Must be an inverter. Use 06 for now. May change to 10 later.
                    sendcommand = "06"

                if urlquery == "" :
                    #no command entered return loggerreg info:
                    responsetxt = b'empty put received'
                    responserc = 400
                    responseheader = "text/html"
                    htmlsendresp(self,responserc,responseheader,responsetxt)
                    return

                else:

                    try:
                        #is valid command specified?
                        command = urlquery["command"][0]
                        if command in ("register", "multiregister", "datetime") :
                            if verbose: print("\t - Grotthttpserver - PUT command: ", command)
                        else :
                            responsetxt = b'no valid command entered'
                            responserc = 400
                            responseheader = "text/html"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return
                    except:
                        responsetxt = b'no command entered'
                        responserc = 400
                        responseheader = "text/html"
                        htmlsendresp(self,responserc,responseheader,responsetxt)
                        return

                    # test if datalogger  and / or inverter id is specified.
                    try:
                        if sendcommand == "06" :
                            inverterid_found = False
                            try:
                                #test if inverter id is specified and get loggerid
                                inverterid = urlquery["inverter"][0]
                                for key in loggerreg.keys() :
                                    for key2 in loggerreg[key].keys() :
                                        if key2 == inverterid :
                                            dataloggerid = key
                                            inverterid_found = True
                                            break
                            except :
                                inverterid_found = False

                            if not inverterid_found :
                                responsetxt = b'no or invalid invertid specified'
                                responserc = 400
                                responseheader = "text/html"
                                htmlsendresp(self,responserc,responseheader,responsetxt)
                                return

                        if sendcommand == "18" :
                            # if read datalogger info.
                            dataloggerid = urlquery["datalogger"][0]

                            try:
                                # Verify dataloggerid is specified
                                dataloggerid = urlquery["datalogger"][0]
                                test = loggerreg[dataloggerid]

                            except:
                                responsetxt = b'invalid datalogger id '
                                responserc = 400
                                responseheader = "text/body"
                                htmlsendresp(self,responserc,responseheader,responsetxt)
                                return
                    except:
                            # do not think we will come here
                            responsetxt = b'no datalogger or inverterid specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return

                    # test if register is specified and set reg value.

                    if command == "register":
                        #test if valid reg is applied
                        if int(urlquery["register"][0]) >= 0 and int(urlquery["register"][0]) < 4096 :
                            register = urlquery["register"][0]
                        else:
                            responsetxt = b'invalid reg value specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return

                        try:
                            value = urlquery["value"][0]
                        except:
                            responsetxt = b'no value specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return

                        if value == "" :
                            responsetxt = b'no value specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return

                    elif command == "multiregister" :
                        # Switch to multiregister command
                        sendcommand = "10"

                        # TODO: Too much copy/paste here. Refactor into methods.

                        # Check for valid start register
                        if int(urlquery["startregister"][0]) >= 0 and int(urlquery["startregister"][0]) < 4096 :
                            startregister = urlquery["startregister"][0]
                        else:
                            responsetxt = b'invalid start register value specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return

                        # Check for valid end register
                        if int(urlquery["endregister"][0]) >= 0 and int(urlquery["endregister"][0]) < 4096 :
                            endregister = urlquery["endregister"][0]
                        else:
                            responsetxt = b'invalid end register value specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return

                        try:
                            value = urlquery["value"][0]
                        except:
                            responsetxt = b'no value specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return

                        if value == "" :
                            responsetxt = b'no value specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return

                        # TODO: Check the value is the right length for the given start/end registers

                    elif command == "datetime" :
                        #process set datetime, only allowed for datalogger!!!
                        if sendcommand == "06" :
                            responsetxt = b'datetime command not allowed for inverter'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return
                        #prepare datetime
                        register = 31
                        value = str(datetime.now().replace(microsecond=0))

                    else:
                        # Start additional command processing here,  to be created: translate command to register (from list>)
                        responsetxt = b'command not defined or not available yet'
                        responserc = 400
                        responseheader = "text/body"
                        htmlsendresp(self,responserc,responseheader,responsetxt)
                        return

                    #test value:
                    if sendcommand == "06" :
                        try:
                            # is format keyword specified? (dec, text, hex)
                            formatval = urlquery["format"][0]
                            if formatval not in ("dec", "hex","text") :
                                responsetxt = b'invalid format specified'
                                responserc = 400
                                responseheader = "text/body"
                                htmlsendresp(self,responserc,responseheader,responsetxt)
                                return
                        except:
                            # no set default format op dec.
                            formatval = "dec"

                        #convert value if necessary
                        if formatval == "dec" :
                            #input in dec (standard)
                            value = int(value)
                        elif formatval == "text" :
                            #input in text
                            value = int(value.encode('ISO-8859-1').hex(),16)
                        else :
                            #input in Hex
                            value = int(value,16)

                        if value < 0 and value > 65535 :
                            responsetxt = b'invalid value specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return


                # start creating command

                bodybytes = dataloggerid.encode('ISO-8859-1')
                body = bodybytes.hex()

                if loggerreg[dataloggerid]["protocol"] == "06" :
                    body = body + "0000000000000000000000000000000000000000"

                if sendcommand == "06" :
                    value = "{:04x}".format(value)
                    valuelen = ""

                elif sendcommand == "10" :
                    # Value is already in hex format
                    pass

                else:
                    value = value.encode('ISO-8859-1').hex()
                    valuelen = int(len(value)/2)
                    valuelen = "{:04x}".format(valuelen)

                if sendcommand == "10" :
                    body = body + "{:04x}".format(int(startregister)) + "{:04x}".format(int(endregister)) + value

                else :
                    body = body + "{:04x}".format(int(register)) + valuelen + value

                bodylen = int(len(body)/2+2)

                #device id for datalogger is by default "01" for inverter deviceid is inverterid!
                deviceid = "01"
                # test if it is inverter command and set deviceid
                if sendcommand in ("06","10") :
                    deviceid = (loggerreg[dataloggerid][inverterid]["inverterno"])
                print("\t - Grotthttpserver: selected deviceid :", deviceid)

                #create header
                header = "{:04x}".format(sendseq) + "00" + loggerreg[dataloggerid]["protocol"] + "{:04x}".format(bodylen) + deviceid + sendcommand
                body = header + body
                body = bytes.fromhex(body)

                if verbose:
                    print("\t - Grotthttpserver - unencrypted put command:")
                    print(format_multi_line("\t\t ",body))

                if loggerreg[dataloggerid]["protocol"] != "02" :
                    #encrypt message
                    body = decrypt(body)
                    crc16 = calc_crc(bytes.fromhex(body))
                    body = bytes.fromhex(body) + crc16.to_bytes(2, "big")

                # queue command
                qname = loggerreg[dataloggerid]["ip"] + "_" + str(loggerreg[dataloggerid]["port"])
                self.send_queuereg[qname].put(body)
                responseno = "{:04x}".format(sendseq)
                if sendcommand == "10":
                    regkey = "{:04x}".format(int(startregister)) + "{:04x}".format(int(endregister))
                else :
                    regkey = "{:04x}".format(int(register))

                try:
                    #delete response: be aware a 18 command give 19 response, 06 send command gives 06 response in different format!
                    if sendcommand == "18" :
                        del commandresponse[sendcommand][regkey]
                    else:
                        del commandresponse[sendcommand][regkey]
                except:
                    pass

                #wait for response
                #Set #retry waiting loop for datalogger or inverter
                if sendcommand == "06" :
                   wait = round(self.conf.inverterrespwait/self.conf.apirespwait)
                   #if verbose: print("\t - Grotthttpserver - wait Cycles:", wait )
                else :
                   wait = round(self.conf.dataloggerrespwait/self.conf.apirespwait)
                   #if verbose: print("\t - Grotthttpserver - wait Cycles:", wait )

                for x in range(wait):
                    if verbose: print("\t - Grotthttpserver - wait for PUT response")
                    try:
                        #read response: be aware a 18 command give 19 response, 06 send command gives 06 response in differnt format!
                        if sendcommand == "18" :
                            comresp = commandresponse["18"][regkey]
                        else:
                            comresp = commandresponse[sendcommand][regkey]
                        if verbose: print("\t - " + "Grotthttperver - Commandresponse ", responseno, register, commandresponse[sendcommand][regkey])
                        break
                    except:
                        #wait for second and try again
                        #Set retry waiting cycle time loop for datalogger or inverter
                        time.sleep(self.conf.apirespwait)
                try:
                    if comresp != "" :
                        responsetxt = b'OK'
                        responserc = 200
                        responseheader = "text/body"
                        htmlsendresp(self,responserc,responseheader,responsetxt)
                        return

                except :
                    responsetxt = b'no or invalid response received'
                    responserc = 400
                    responseheader = "text/body"
                    htmlsendresp(self,responserc,responseheader,responsetxt)
                    return


                responsetxt = b'OK'
                responserc = 200
                responseheader = "text/body"
                if verbose: print("\t - " + "Grott: datalogger command response :", responserc, responsetxt, responseheader)
                htmlsendresp(self,responserc,responseheader,responsetxt)
                return

        except Exception as e:
            print("\t - Grottserver - exception in httpserver thread - put occured : ", e)


class GrottHttpServer:
    """This wrapper will create an HTTP server where the handler has access to the send_queue"""

    def __init__(self, conf, httphost, httpport, send_queuereg):
        def handler_factory(*args):
            """Using a function to create and return the handler, so we can provide our own argument (send_queue)"""
            return GrottHttpRequestHandler(conf, send_queuereg, *args)
        self.server = http.server.HTTPServer((httphost, httpport), handler_factory)
        self.server.allow_reuse_address = True
        logger.info(f"GrottHttpserver - Ready to listen at: {httphost}:{httpport}")

    def run(self,conf):
        try:
            logger.info("GrottHttpserver - server listening")
            logger.info("GrottHttpserver - Response interval wait time: %s", conf.apirespwait)
            logger.info("GrottHttpserver - Datalogger ResponseWait: %s", conf.dataloggerrespwait)
            logger.info("GrottHttpserver - Inverter ResponseWait: %s", conf.inverterrespwait)
            self.server.serve_forever()
        except Exception as e:
            logger.info("httpserver start error %s",e)

class sendrecvserver:
    def __init__(self, conf, host, port, send_queuereg):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setblocking(0)
        self.server.bind((host, port))
        self.server.listen(5)

        self.inputs = {}
        self.outputs = {}
        self.exceptional ={}
        self.send_queuereg = send_queuereg
        self.channel = {}
        self.lastmessage = {}                                                   #to detect inactive connections

        logger.info(f"Grottserver - Ready to listen at: {host}:{port}")

    def run(self,conf):
        logger.info("Grottserver - server listening")
        trname = conf.serverip+"_"+str(conf.serverport)
        self.inputs[trname] = [self.server]
        self.outputs[trname] = [self.server]
        self.exceptional[trname] = [self.server]
        while self.inputs:
            readable, writable, exceptional = select.select(
                self.inputs[trname], self.outputs[trname], self.exceptional[trname])

            for s in readable:
                self.handle_readable_socket(conf,s,trname)

            for s in writable:
                self.handle_writable_socket(conf,s,trname)

            for s in exceptional:
                self.handle_exceptional_socket(conf,s,trname)

    def handle_client(self,conf,conn,qname,trname):
        # Start seperate thread per connectiob

        s = conn
        self.inputs[qname] = [s]
        self.outputs[qname] = [s]
        self.exceptional[qname] = [s]

        try:
            logger.debug("[thread: {0}] starting".format(trname))

            while self.inputs[qname]:

                if s.fileno() == -1 :
                    logger.debug("handle_client({0}), socket closed".format(trname))
                    break
                readable, writable, exceptional = select.select(
                self.inputs[qname], self.outputs[qname], self.exceptional[qname])

                for s in readable:
                    self.handle_readable_socket(conf,s,trname)

                for s in writable:
                    self.handle_writable_socket(conf,s,trname)

                for s in exceptional:
                    self.handle_exceptional_socket(conf,s)
        except Exception as e:
            logger.info("Socket closed: %s", e)

        logger.info("thread for: {0} ending".format(trname))

    def handle_readable_socket(self, conf, s, trname):
        logger.debug("handle_readble_socket, input received on socket : %s",s)
        # test if comming from growatt server and set flag

        try:
            if s is self.server:
                logger.debug("handle_readable_socket, no connection with peer yet, will be established")
                self.handle_new_connection(conf,s)

            else:
                # Existing connection
                try:
                    #read buffer until empty!!!!
                    msgbuffer = b''
                    buffsize = 1024
                    while True:
                        part = s.recv(buffsize)
                        msgbuffer += part
                        if len(part) < buffsize:
                        # either 0 or end of data
                            break
                    logger.debug(f"received data before buffersplit processing:")
                    logger.debug("\n{0}".format(format_multi_line("\t", msgbuffer)))
                    #process the data
                    if msgbuffer:
                        #split buffer if contain multiple records
                        logger.debug("start message buffer processing")
                        reclength = int.from_bytes(msgbuffer[4:6],"big")
                        buflength = len(msgbuffer)
                        header = "".join("{:02x}".format(n) for n in msgbuffer[0:8])
                        protocol = header[6:8]
                        #set recordlength correction header + crc (if included).
                        if protocol in ("05","06"):
                           lcrc = 8
                        else:
                            lcrc = 6
                        buflength = len(msgbuffer)
                        if reclength + lcrc > buflength:
                            logger.debug("Invalid Record (length) detected")
                            return
                        while reclength + lcrc <= buflength:
                            logger.debug("Process message buffer split processing")
                            #get first message
                            data = msgbuffer[0:reclength+lcrc]
                            #set last reference time (for removing inactive connections)
                            self.lastmessage[s] = time.time()
                            header = "".join("{:02x}".format(n) for n in data[0:8])
                            rectype = header[14:16]
                            seqno = header[0:4]
                            # pass data to growatt
                            try:
                                if conf.serverpassthrough:
                                    sRaddr = s.getpeername()
                                    if sRaddr[0] == conf.growattip and sRaddr[1] == int(conf.growattport) :
                                        logger.debug("handle_readble_socket, data from growatt server will be ignored")
                                        logger.debug("handle_readble_socket, original data:\n{0} \n".format(format_multi_line("\t",data,80)))
                                        #no further processing needed
                                        return()
                                    else:
                                        logger.debug("handle_readble_socket, process data to sent to growatt server")

                                        if rectype in ("03", "04", "16","50", "1b", "19","20","29"):
                                            #forward only specific recordtypes
                                            #get qname for growatt server based on growatt address and client addres
                                            gLaddr = self.channel[s].getsockname()
                                            qname = gLaddr[0]+"_"+str(gLaddr[1])

                                            try:
                                                logger.debug("handle_readble_socket, put data on growatt queue: %s",qname)
                                                self.send_queuereg[qname].put(data)
                                            except Exception as e:
                                                logger.warning("handle_readble_socket, exception in data forwarding %s", e)
                                                return()

                                            logger.debug("handle_readble_socket, data forwarded to growatt server")
                                            #wait for ack from growatt server
                                            if rectype == "03":
                                                self.waitsync(seqno,s,2)
                                            #    time.sleep(0.1)
                                        else:
                                            logger.debug("handle_readble_socket, data filtered and not forwarded to growatt server:")

                            except Exception as e:
                                logger.warning("handle_readble_socket, Growatt passthrough error: %s",e)
                                logger.warning("handle_readble_socket, continue without forwarding")

                            #Process the data
                            self.process_data(conf,s, data)
                            #create buffer with remaining messages
                            if buflength > reclength+lcrc:
                                logger.debug("handle_readble_socket, process additional messages in buffer")
                                msgbuffer = msgbuffer[reclength+lcrc:buflength]
                                reclength = int.from_bytes(msgbuffer[4:6],"big")
                                buflength = len(msgbuffer)
                            else: break
                    else:
                        # Empty read means connection is closed, perform cleanup
                        logger.warning("handle_readble_socket, empty read, close connection")
                        self.close_connection(conf,s)

                #except ConnectionResetError:
                except Exception as e:
                    logger.warning("handle_readble_socket, ConnectionResetError exception: %s",e)
                    #close client and passthrough connection
                    self.close_connection(conf,s)

        except Exception as e:
            logger.warning("handle_readble_socket, generic exception, closing connection: %s",e)
            self.close_connection(conf,s)


    def handle_writable_socket(self, conf, s, trname):
        #logger.debug("handle_writable_socket for: %s",s)
        try:
            #with print statement no crash, without crash, does sleep solve this problem ?
            time.sleep(0.1)

            if s.fileno() == -1 :
                logger.info("handle_writable_socket ({0}), socket already closed".format(trname))
                return
            try:
                #try for debug 007
                client_address, client_port = s.getpeername()
                if conf.serverpassthrough:
                    if client_address == self.forwardip and client_port == int(self.forwardport):
                        client_address, client_port = s.getsockname()
            except Exception as e:
                logger.warning("handle_writable_socket, socket error: %s",e)
                self.close_connection(conf,s)
                return

            try:
                qname = client_address + "_" + str(client_port)
                next_msg = self.send_queuereg[qname].get_nowait()
                logger.debug("handle_writable_socket, get response from queue: %s \n", qname)
                logger.debug("\n{0}".format(format_multi_line("\t",next_msg,80)))
                s.send(next_msg)

            except queue.Empty:
                #Do not activate logger entry here will full-up the log!!!!!
                #wait before handling next message
                #time.sleep(0.1)
                pass

            # calculate last message send and close connection if iddle for more then 90s (ping frequency)
            try:
                logger.debugv("handle_writable_connection, Start calculate timeout routine %s", s)

                try:
                    timeout =  time.time()-self.lastmessage[s]
                    logger.debugv("handle_writable_connection: {0}, timer: {1}, connectiontimeout: {2}".format(trname,timeout,conf.ConnectionTimeout))
                except Exception as e:
                    #no lastmessage for this connection yet, set lastmessage skip processing
                    self.lastmessage[s] = time.time()
                    timeout =  0

                if timeout > conf.ConnectionTimeout:

                    logger.debug("time out > {0} for {1}".format(conf.ConnectionTimeout,s))
                    if s.fileno() != -1 :
                        logger.info("handle_writable_connection, inactive socket will be closed: {0}, {1}".format({s}, {timeout}))
                        self.close_connection(conf,s)
                    else :
                        logger.info(f"handle_writable_connection, inactive socket already closed: {s}")

            except Exception as e:
                logger.debug("handle_writable_connection, error in calculate timeout routine %s",e)

        except Exception as e:
            logger.warning("handle_writable_socket, exception: %s", e)
            self.close_connection(conf,s)


    def handle_exceptional_socket(self, conf, s):
        logger.warning("handle_exceptional_socket, exception or socket: %s", s)
        self.close_connection(conf,s)

    def handle_new_connection(self, conf, s):
        try:
            logger.debug("handle_new_connection, new connection request received: \n\t %s",s)
            connection, client_address = s.accept()
            #connection.setblocking(0)

            client_address, client_port = connection.getpeername()
            qname = client_address + "_" + str(client_port)

            #create queue
            self.send_queuereg[qname] = queue.Queue()
            logger.debug("handle_new_connection, send queue created for: %s", qname)

            if conf.serverpassthrough:
                #start thread for handling forward connection before client thread!!
                forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                forward.connect((conf.growattip, conf.growattport))
                logger.info(f"forward, connection with growatt server established: {conf.growattip}:{conf.growattport}")
                logger.debug(f"forward, socket: {forward}")
                gLaddr = forward.getsockname()
                gqname =  gLaddr[0] + "_" + str(gLaddr[1])
                #get actual growatt server address if DNS name is used in .ini settings
                self.forwardip, self.forwardport = forward.getpeername()
                self.send_queuereg[gqname] = queue.Queue()

                #create forward channel pair
                self.channel[connection] = forward
                self.channel[forward] = connection
                #self.gwserver =  Forward.start(self,conf.growattip, conf.growattport)
                trfname = "forward_"+ gLaddr[0] + ":" + str(gLaddr[1])
                tf = threading.Thread(target=self.handle_client, args=[conf,forward,gqname,trfname],name=trfname)
                tf.start()


            # create processing thread
            trname = "client_"+ client_address + ":" + str(client_port)
            t = threading.Thread(target=self.handle_client, args=[conf,connection,qname,trname],name=trname)
            t.start()
            #


        except Exception as e:
            logger.warning("handle_new_connection exception:  %s \n\t", e)

    def close_connection(self, conf, s):
        logger.debug("Close Connection for socket: {0}".format(s))

        #retrieve information about connection
        logger.debugv("retrieve connection information")

        close_fd = s.fileno()
        for x in self.inputs :

                if  close_fd == self.inputs[x][0].fileno() :
                    qname = x
                    break

        try:
            logger.debug("Close Connection for socket: {0}".format(s))
            #Test if endpoint still exist?
            s.close()
        except Exception as e:
            logger.debug("close connection error:  %s", e)

        try:
            logger.debugv("clean connection queues")
            if qname in self.outputs:
                del self.outputs[qname]
            if qname in self.inputs:
                del self.inputs[qname]
            if qname in self.exceptional:
                del self.exceptional[qname]
            if s in self.lastmessage :
                del self.lastmessage[s]
            del self.send_queuereg[qname]
        except Exception as e:
            logger.debugv("clean connection queues error:  %s", e)

        if conf.serverpassthrough:
            logger.debug("Close  Passthough Connection")
            pt_socket = self.channel[s]
            pt_address, pt_port = pt_socket.getsockname()
            pt_qname = pt_address + "_" + str(pt_port)
            try:
                logger.debugv("Close Passtrough Connection socket: {0}".format(pt_socket))
                #Test if endpoint still exist?
                pt_socket.close()
            except Exception as e:
                logger.error("close Passthrough connection error:  %s", e)

        try:
            logger.debugv("clean Passthrough connection queues")
            if conf.serverpassthrough:
                if pt_qname in self.outputs:
                    del self.outputs[pt_qname]
                if pt_qname in self.inputs:
                    del self.inputs[pt_qname]
                if pt_qname in self.exceptional:
                    del self.exceptional[pt_qname]
                if s in self.lastmessage :
                    del self.lastmessage[pt_socket]
                del self.send_queuereg[pt_qname]

        except Exception as e:
            logger.debugv("clean connection queues error:  %s", e)

        #clean channels
        if s in self.channel:
                del self.channel[s]
        if conf.serverpassthrough:
            if pt_socket in self.channel:
                del self.channel[pt_socket]

    def waitsync(self,sequencenumber,sendersock,timeout=1):
        #this routine will wait on (ack/nack) response for a message
        #wil lbe crteadted in the future, no only perform a wait to give the remote (e.g. client or growatt server) the time to response.
        logger.debug("waitsync, wait for response on msg:{0} from: {1}".format(sequencenumber,sendersock))
        time.sleep(timeout)

    def process_data_record(self,conf,data):
        """this routine will process the growatt datarecords"""
        procdata(conf,data)
        logger.debug("process_data_record initiated")
        returncc = 0
        return(returncc)

    def process_data(self, conf, s, data):

        #self.send_queuereg[qname].put(response)

        # Prevent generic errors:
        try:

            # process data and create response
            client_address, client_port = s.getpeername()
            qname = client_address + "_" + str(client_port)

            #V0.0.14: default response on record to none (ignore record)
            response = None

            # Display data
            logger.debug(f"process_data, data received from : {client_address}:{client_port}")
            logger.debug("\n{0}".format(format_multi_line("\t", data)))

            #validate data (Length + CRC for 05/06)
            #join gebeurt nu meerdere keren! Stroomlijnen!!!!
            vdata = "".join("{:02x}".format(n) for n in data)
            validatecc = validate_record(vdata)
            #validatecc = 0
            if validatecc != 0 :
                logger.debug("process_data, invalid data record received, processing stopped for this record returncode: %s",validatecc)
                #Create response if needed?
                #self.send_queuereg[qname].put(response)
                return

            # Create header
            header = "".join("{:02x}".format(n) for n in data[0:8])
            protocol = header[6:8]
            sequencenumber = header[0:4]
            deviceid = header[12:14]
            protocol = header[6:8]
            #command = header[14:16]
            rectype = header[14:16]
            if protocol in ("05","06") :
                result_string = decrypt(data)
            else :
                result_string = "".join("{:02x}".format(n) for n in data)
            logger.debug(f"process_data, plain record: ")
            logger.debug("\n{0}".format(format_multi_line("\t", result_string)))
            loggerid = result_string[16:36]
            loggerid = codecs.decode(loggerid, "hex").decode('ISO-8859-1')

            # Prepare response
            if rectype in ("16"):
                # if ping send data as reply
                response = data
                logger.debug(f"process_data, 16- ping response:")
                logger.debug("\n{0}".format(format_multi_line("\t\t ", response)))

                #     #v0.0.14a: create temporary also logger record at ping (to support shinelink without inverters)

                try:
                    loggerreg[loggerid].update({"ip" : client_address, "port" : client_port, "protocol" : header[6:8]})
                except:
                    loggerreg[loggerid] = {"ip" : client_address, "port" : client_port, "protocol" : header[6:8]}
                    logger.debug(f"process_data, datalogger id: {loggerid} added by ping: {loggerreg[loggerid]}")


            #v0.0.14: remove "29" (no response will be sent for this record!)
            elif rectype in ("03", "04", "50", "1b", "20"):
                # if datarecord send ack.
                print("\t - Grottserver - " + header[12:16] + " data record received")

                # create ack response
                if header[6:8] == '02':
                    #protocol 02, unencrypted ack
                    response = bytes.fromhex(header[0:8] + '0003' + header[12:16] + '00')
                else:
                    # protocol 05/06, encrypted ack
                    headerackx = bytes.fromhex(header[0:8] + '0003' + header[12:16] + '47')
                    # Create CRC 16 Modbus
                    crc16 = calc_crc(headerackx)
                    # create response
                    response = headerackx + crc16.to_bytes(2, "big")
                if verbose:
                    print("\t - Grottserver - Response: ")
                    print(format_multi_line("\t\t", response))

                if conf.mode=="server" :
                    procdatarc = self.process_data_record(conf,data)
                    logger.debug("data record process ended with renturncode: %s",procdatarc)

                if rectype in ("03") :
                # init record register logger/inverter id (including sessionid?)
                # decrypt body.
                    if header[6:8] in ("05","06") :
                        #print("header1 : ", header[6:8])
                        result_string = decrypt(data)
                    else :
                        result_string = data.hex()

                    loggerid = result_string[16:36]
                    loggerid = codecs.decode(loggerid, "hex").decode('ISO-8859-1')
                    if header[6:8] in ("02","05") :
                        inverterid = result_string[36:56]
                    else :
                        inverterid = result_string[76:96]
                    inverterid = codecs.decode(inverterid, "hex").decode('ISO-8859-1')

                    try:
                        loggerreg[loggerid].update({"ip" : client_address, "port" : client_port, "protocol" : header[6:8]})
                    except:
                        loggerreg[loggerid] = {"ip" : client_address, "port" : client_port, "protocol" : header[6:8]}
                        logger.debug("Datalogger id added by: %s", loggerid)

                    #add invertid
                    loggerreg[loggerid].update({inverterid : {"inverterno" : deviceid, "power" : 0}} )
                    logger.debug("Inverter id added: %s", inverterid)
                    #send response
                    self.send_queuereg[qname].put(response)
                    #wait some time before response on announcement is processed (maybe create a waitsync routine?)
                    #self.waitsync(sequencenumber,s)
                    #time.sleep(5)
                    # Create time command en put on queue
                    response = createtimecommand(self,protocol,deviceid,loggerid,"0001")
                    if verbose: print("\t - Grottserver 03 announce data record processed")

            elif rectype in ("19","05","06","18"):
                if verbose: print("\t - Grottserver - " + header[12:16] + " Command Response record received, no response needed")

                offset = 0
                if protocol in ("06") :
                    offset = 40

                register = int(result_string[36+offset:40+offset],16)
                if rectype == "05" :
                    #value = result_string[40+offset:44+offset]
                    #v0.0.14: test if empty response is sent (this will give CRC code as values)
                    #print("length resultstring:", len(result_string))
                    #print("result starts on:", 48+offset)
                    if len(result_string) == 48+offset :
                        if verbose: print("\t - Grottserver - empty register get response recieved, response ignored")
                    else:
                        value = result_string[44+offset:48+offset]
                elif rectype == "06" :
                    result = result_string[40+offset:42+offset]
                    #print("06 response result :", result)
                    value = result_string[42+offset:46+offset]
                elif rectype == "18" :
                    result = result_string[40+offset:42+offset]
                else :
                    # "19" response take length into account
                    valuelen = int(result_string[40+offset:44+offset],16)

                    #value = codecs.decode(result_string[44+offset:44+offset+valuelen*2], "hex").decode('ISO-8859-1')
                    value = codecs.decode(result_string[44+offset:44+offset+valuelen*2], "hex").decode('ISO-8859-1')

                regkey = "{:04x}".format(register)
                if rectype == "06" :
                    # command 06 response has ack (result) + value. We will create a 06 response and a 05 response (for reg administration)
                    commandresponse["06"][regkey] = {"value" : value , "result" : result}
                    commandresponse["05"][regkey] = {"value" : value}
                if rectype == "18" :
                    commandresponse["18"][regkey] = {"result" : result}
                else :
                    #rectype 05 or 19
                    commandresponse[rectype][regkey] = {"value" : value}

                response = None

            elif rectype in ("10") :
                if verbose: print("\t - Grottserver - " + header[12:16] + " record received, no response needed")

                startregister = int(result_string[76:80],16)
                endregister = int(result_string[80:84],16)
                value = result_string[84:86]

                regkey = "{:04x}".format(startregister) + "{:04x}".format(endregister)
                commandresponse[rectype][regkey] = {"value" : value}

                response = None

            elif rectype in ("29") :
                if verbose: print("\t - Grottserver - " + header[12:16] + " record received, no response needed")
                response = None

            #elif rectype in ("99") :
                #placeholder for communicating from html server to sendrecv server
            #    if verbose:
            #    response = None

            else:
                if verbose: print("\t - Grottserver - Unknown record received:")

                response = None

            if response is not None:
                #qname = client_address + "_" + str(client_port)
                if verbose:
                    print("\t - Grottserver - Put response on queue: ", qname, " msg: ")
                    print(format_multi_line("\t\t ", response))
                self.send_queuereg[qname].put(response)
        except Exception as e:
            print("\t - Grottserver - exception in main server thread occured : ", e)


class Server :

    def __init__(self, conf):
        #set loglevel
        logger.setLevel(conf.loglevel.upper())
        conf.vrmserver = vrmserver
        logger.info("Grottserver inititialisation started, grottserver version %s",conf.vrmserver)

    def main(self,conf):
        #set loglevel
        self.conf=conf
        logger.setLevel(conf.loglevel.upper())
        logger.info("Grott server started")
        logger.info("mode: %s",conf.mode)
        send_queuereg = {}
        #loggerreg = {}
        # response from command is written is this variable (for now flat, maybe dict later)
        #commandresponse =  defaultdict(dict)

        http_server = GrottHttpServer(conf, conf.serverip, conf.httpport, send_queuereg)
        #connection_server = sendrecvserver(conf.serverip, conf.serverport, send_queuereg)
        connection_server = sendrecvserver(conf,"0.0.0.0", conf.serverport, send_queuereg)
        httpname = "httpserver_" + conf.serverip + ":" + str(conf.httpport)
        servername = "conserver_" + conf.serverip + ":" + str(conf.serverport)
        connection_server_thread = threading.Thread(target=connection_server.run,name=servername,args=[conf])
        http_server_thread = threading.Thread(target=http_server.run,name=httpname,args=[conf])
        http_server_thread.start()
        connection_server_thread.start()


        while True:
            time.sleep(60)
            #start maintance processing

            #list active connections/threads
            logger.debug("Main, available connections:")
            p = psutil.Process()
            clist = p.connections(kind='inet')
            for item in clist:
                logger.debug(item)
            logger.debug("Main, available threads:")
            for thread in threading.enumerate():
                logger.debug("\t- %s",thread.name)

if __name__ == "__main__":
    """main module: be aware this is only exectuted if grottserver runs standalone!"""
    addLoggingLevel("DEBUGV", logging.DEBUG - 5)
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Grottserver Version: %s",vrmserver)

    #set gmode environment to override mode to standalone
    os.environ["gmode"] = "serversa"

    try:
        test = Conf.mode
        logger.debug("Grottserver initiated via Grott Main")
    except NameError :
        logger.info("Grottserver will run in standalone mode")
        try:
            # process config file:
            from grottconf import Conf
            confserver = True
            conf = Conf(vrmserver)
            logger.debug("Configuration being set by grottconf")
            #change loglevel might be changed after config processing.
            logger.setLevel(conf.loglevel.upper())
        except Exception as e:
            logger.info("Minimal pre-defined default configuration being used: %s",e)
            conf = Miniconf(vrmserver)

    server = Server(conf)
    try:
        server.main(conf)
    except KeyboardInterrupt:
        logger.info("Ctrl C - Stopping server")
        exit()

        # try:
        #     logger.info("closeport")
        #     #proxy.on_close(conf)
        # except:
        #     logger.info("\t - no ports to close")
