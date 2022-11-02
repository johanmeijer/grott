import select
import socket
import queue
import textwrap
import libscrc
import threading
import time
import http.server
import json, codecs 
from itertools import cycle
from io import BytesIO
from datetime import datetime
from urllib.parse import urlparse, parse_qs, parse_qsl  
from collections import defaultdict

# grottserver.py emulates the server.growatt.com website and is initial developed for debugging and testing grott.
# Updated: 2022-09-27
# Version:
verrel = "0.0.11a"

# Declare Variables (to be moved to config file later)
serverhost = "0.0.0.0"
serverport = 5781
httphost = "0.0.0.0"
httpport = 5782
verbose = True 
firstping = False
sendseq = 1


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

    print("\t - " + "Grott - data decrypted V2")
    return result_string

def validate_record(xdata): 
    # validata data record on length and CRC (for "05" and "06" records)
    
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
                crc_calc = libscrc.modbus(data[0:ldata-2])

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

def createtimecommand(protocol,loggerid,sequenceno) : 
        protocol = protocol
        loggerid = loggerid 
        sequenceno = sequenceno
        bodybytes = loggerid.encode('utf-8')
        body = bodybytes.hex()
        if protocol == "06" :
            body = body + "0000000000000000000000000000000000000000"
        register = 31
        body = body + "{:04x}".format(int(register))
        currenttime = str(datetime.now().replace(microsecond=0))
        timex = currenttime.encode('utf-8').hex()
        timel = "{:04x}".format(int(len(timex)/2))
        body = body + timel + timex 
        #calculate length of payload = body/2 (str => bytes) + 2 bytes invertid + command. 
        bodylen = int(len(body)/2+2)
        
        #create header
        header = "0001" + "00" + protocol + "{:04x}".format(bodylen) + "0118"
        #print(header) 
        body = header + body 
        body = bytes.fromhex(body)
        if verbose: 
            print("\t - Grottserver - Time plain body : ")
            print(format_multi_line("\t\t ",body))

        if protocol != "02" :
            #encrypt message 
            body = decrypt(body) 
            crc16 = libscrc.modbus(bytes.fromhex(body))
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
    def __init__(self, send_queuereg, *args):
        self.send_queuereg = send_queuereg
        super().__init__(*args)
    
    def do_GET(self):
        try: 
            if verbose: print("\t - Grotthttpserver - Get received ")
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
                    responsetxt = b"<h2>Welcome to Grott the growatt inverter monitor</h2><br><h3>Made by Ledidobe, Johan Meijer</h3>"
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
                    responsetxt = json.dumps(loggerreg).encode('utf-8')
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
                        if int(urlquery["register"][0]) >= 0 and int(urlquery["register"][0]) < 1125 : 
                            register = urlquery["register"][0]
                        else: 
                            responsetxt = b'invalid reg value specified'
                            responserc = 400 
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return
                    elif command == "regall" :
                        comresp  = commandresponse[sendcommand]
                        responsetxt = json.dumps(comresp).encode('utf-8')
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
                        
                bodybytes = dataloggerid.encode('utf-8')
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

                if loggerreg[dataloggerid]["protocol"] != "02" :
                    #encrypt message 
                    body = decrypt(body) 
                    crc16 = libscrc.modbus(bytes.fromhex(body))
                    body = bytes.fromhex(body) + crc16.to_bytes(2, "big")

                # add header
                if verbose:
                    print("\t - Grotthttpserver: command created :")
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
                for x in range(7):
                    if verbose: print("\t - Grotthttpserver - wait for GET response")
                    try: 
                        comresp = commandresponse[sendcommand][regkey]
                        
                        if sendcommand == "05" :
                            if formatval == "dec" : 
                                comresp["value"] = int(comresp["value"],16)
                            elif formatval == "text" : 
                                comresp["value"] = codecs.decode(comresp["value"], "hex").decode('utf-8')
                        responsetxt = json.dumps(comresp).encode('utf-8')
                        responserc = 200 
                        responseheader = "text/body"
                        htmlsendresp(self,responserc,responseheader,responsetxt)
                        return

                    except  : 
                        #wait for second and try again
                        time.sleep(1)
                try: 
                    if comresp != "" : 
                        responsetxt = json.dumps(comresp).encode('utf-8')

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
                        if int(urlquery["register"][0]) >= 0 and int(urlquery["register"][0]) < 1024 : 
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
                        if int(urlquery["startregister"][0]) >= 0 and int(urlquery["startregister"][0]) < 1125 :
                            startregister = urlquery["startregister"][0]
                        else:
                            responsetxt = b'invalid start register value specified'
                            responserc = 400
                            responseheader = "text/body"
                            htmlsendresp(self,responserc,responseheader,responsetxt)
                            return

                        # Check for valid end register
                        if int(urlquery["endregister"][0]) >= 0 and int(urlquery["endregister"][0]) < 1125 :
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
                            value = int(value.encode('utf-8').hex(),16) 
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

                bodybytes = dataloggerid.encode('utf-8')
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
                    value = value.encode('utf-8').hex()
                    valuelen = int(len(value)/2)
                    valuelen = "{:04x}".format(valuelen) 

                if sendcommand == "10" :
                    body = body + "{:04x}".format(int(startregister)) + "{:04x}".format(int(endregister)) + value

                else :
                    body = body + "{:04x}".format(int(register)) + valuelen + value

                bodylen = int(len(body)/2+2)          

                #create header
                header = "{:04x}".format(sendseq) + "00" + loggerreg[dataloggerid]["protocol"] + "{:04x}".format(bodylen) + "01" + sendcommand
                body = header + body 
                body = bytes.fromhex(body)

                if verbose:
                    print("\t - Grotthttpserver - unencrypted command:")
                    print(format_multi_line("\t\t ",body))
                
                if loggerreg[dataloggerid]["protocol"] != "02" :
                    #encrypt message 
                    body = decrypt(body) 
                    crc16 = libscrc.modbus(bytes.fromhex(body))
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
                    #delete response: be aware a 18 command give 19 response, 06 send command gives 06 response in differnt format! 
                    if sendcommand == "18" :
                        del commandresponse[sendcommand][regkey] 
                    else: 
                        del commandresponse[sendcommand][regkey] 
                except: 
                    pass 

                #wait for response
                for x in range(15):
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
                        time.sleep(1)
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

    def __init__(self, httphost, httpport, send_queuereg):
        def handler_factory(*args):
            """Using a function to create and return the handler, so we can provide our own argument (send_queue)"""
            return GrottHttpRequestHandler(send_queuereg, *args)

        self.server = http.server.HTTPServer((httphost, httpport), handler_factory)
        self.server.allow_reuse_address = True
        print(f"\t - GrottHttpserver - Ready to listen at: {httphost}:{httpport}")

    def run(self):
        print("\t - GrottHttpserver - server listening")
        self.server.serve_forever()


class sendrecvserver:
    def __init__(self, host, port, send_queuereg):   
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setblocking(0)
        self.server.bind((host, port))
        self.server.listen(5)

        self.inputs = [self.server]
        self.outputs = []
        self.send_queuereg = send_queuereg
        
        print(f"\t - Grottserver - Ready to listen at: {host}:{port}")

    def run(self):
        print("\t - Grottserver - server listening")
        while self.inputs:
            readable, writable, exceptional = select.select(
                self.inputs, self.outputs, self.inputs)

            for s in readable:
                self.handle_readable_socket(s)

            for s in writable:
                self.handle_writable_socket(s)

            for s in exceptional:
                self.handle_exceptional_socket(s)

    def handle_readable_socket(self, s):
        try:
            if s is self.server:
                self.handle_new_connection(s)
                if verbose: print("\t - " + "Grottserver - input received: ", self.server)
            else:
                # Existing connection
                try:
                    data = s.recv(1024)
                    if data:
                        self.process_data(s, data)
                    else:
                        # Empty read means connection is closed, perform cleanup
                        self.close_connection(s)
                #except ConnectionResetError:
                except:
                    self.close_connection(s) 
            
        except Exception as e:
            print("\t - Grottserver - exception in server thread - handle_readable_socket : ", e)
            #print("\t - socket: ",s)    


    def handle_writable_socket(self, s):
        try: 
            #with print statement no crash, without crash, does sleep solve this problem ? 
            time.sleep(0.1)
            
            if s.fileno() == -1 : 
                print("\t - Grottserver - socket closed")
                return
            try: 
                #try for debug 007
                client_address, client_port = s.getpeername()
            except: 
                print("\t - Grottserver - socket closed :")
                #print("\t\t ", s )
                #s.close
                pass

            try: 
                qname = client_address + "_" + str(client_port)
                next_msg = self.send_queuereg[qname].get_nowait()
                if verbose:
                    print("\t - " + "Grottserver - get response from queue: ", qname + " msg: ")
                    print(format_multi_line("\t\t ",next_msg))
                s.send(next_msg)
                
            except queue.Empty:
                pass

        except Exception as e:
            print("\t - Grottserver - exception in server thread - handle_writable_socket : ", e)
            #print("\t\t ", s)
            #self.close_connection(s)
            #print(s)

    def handle_exceptional_socket(self, s):
        if verbose: print("\t - " + "Grottserver - Encountered an exception")
        self.close_connection(s)

    def handle_new_connection(self, s):
        try: 
            connection, client_address = s.accept()
            connection.setblocking(0)
            self.inputs.append(connection)
            self.outputs.append(connection)
            print(f"\t - Grottserver - Socket connection received from {client_address}")
            client_address, client_port = connection.getpeername()
            qname = client_address + "_" + str(client_port)

            #create queue
            send_queuereg[qname] = queue.Queue()
            #print(send_queuereg)
            if verbose: print(f"\t - Grottserver - Send queue created for : {qname}")
        except Exception as e:
            print("\t - Grottserver - exception in server thread - handle_new_connection : ", e) 
            #self.close_connection(s)   


    def close_connection(self, s):
        try: 
            #client_address, client_port = s.getpeername() 
            print("\t - Grottserver - Close connection : ", s)
            #print(client_address, client_port)
            if s in self.outputs:
                self.outputs.remove(s)
            self.inputs.remove(s)
            client_address, client_port = s.getpeername() 
            qname = client_address + "_" + str(client_port)
            del send_queuereg[qname]
            ### after this also clean the logger reg. To be implemented ? 
            for key in loggerreg.keys() : 
                #print(key, loggerreg[key])
                #print(key, loggerreg[key]["ip"], loggerreg[key]["port"])
                if loggerreg[key]["ip"] == client_address and loggerreg[key]["port"] == client_port :
                    del loggerreg[key] 
                    print("\t - Grottserver - config information deleted for datalogger and connected inverters : ", key)
                    # to be developed delete also register information for this datalogger (and  connected inverters).  Be aware this need redef of commandresp!
                    break     
            s.close()
        
        except Exception as e:
            print("\t - Grottserver - exception in server thread - close connection :", e)   
            #print("\t\t ", s )  

            # try: 
            #     s.close()
            # except:     
            #     print("\t - Grottserver - socket close error",s)

        

    def process_data(self, s, data):
        
        # Prevent generic errors: 
        try: 
        
            # process data and create response
            client_address, client_port = s.getpeername()
            qname = client_address + "_" + str(client_port)
            
            # Display data
            print(f"\t - Grottserver - Data received from : {client_address}:{client_port}")
            if verbose:
                print("\t - " + "Grottserver - Original Data:")
                print(format_multi_line("\t\t ", data))
            
            #validate data (Length + CRC for 05/06)
            #join gebeurt nu meerdere keren! Stroomlijnen!!!! 
            vdata = "".join("{:02x}".format(n) for n in data)
            validatecc = validate_record(vdata)
            if validatecc != 0 : 
                print(f"\t - Grottserver - Invalid data record received, processing stopped for this record")
                #Create response if needed? 
                #self.send_queuereg[qname].put(response)
                return  

            # Create header
            header = "".join("{:02x}".format(n) for n in data[0:8])
            protocol = header[6:8]
            sequencenumber = header[0:4]
            protocol = header[6:8]
            command = header[14:16]
            if protocol in ("05","06") :
                result_string = decrypt(data) 
            else :         
                result_string = "".join("{:02x}".format(n) for n in data)
            if verbose:
                print("\t - Grottserver - Plain record: ")
                print(format_multi_line("\t\t ", result_string))
            loggerid = result_string[16:36]
            loggerid = codecs.decode(loggerid, "hex").decode('utf-8') 

            # Prepare response
            if header[14:16] in ("16"):
                # if ping send data as reply
                response = data
                if verbose:
                    print("\t - Grottserver - 16 - Ping response: ")
                    print(format_multi_line("\t\t ", response))
            

            elif header[14:16] in ("03", "04", "50", "29", "1b", "20"):
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
                    crc16 = libscrc.modbus(headerackx)
                    # create response
                    response = headerackx + crc16.to_bytes(2, "big")
                if verbose:
                    print("\t - Grottserver - Response: ")
                    print(format_multi_line("\t\t", response))

                if header[14:16] == "03" : 
                # init record register logger/inverter id (including sessionid?)
                # decrypt body. 
                    if header[6:8] in ("05","06") :
                        #print("header1 : ", header[6:8])
                        result_string = decrypt(data) 
                    else :         
                        result_string = data   
            
                    loggerid = result_string[16:36]
                    loggerid = codecs.decode(loggerid, "hex").decode('utf-8')
                    if header[6:8] in ("02","05") :                    
                        inverterid = result_string[36:56]
                    else : 
                        inverterid = result_string[76:96]
                    inverterid = codecs.decode(inverterid, "hex").decode('utf-8')

                    try:
                        loggerreg[loggerid].update({"ip" : client_address, "port" : client_port, "protocol" : header[6:8]})
                    except: 
                        loggerreg[loggerid] = {"ip" : client_address, "port" : client_port, "protocol" : header[6:8]}
                        
                    #add invertid
                    loggerreg[loggerid].update({inverterid : {"inverterno" : header[12:14], "power" : 0}} ) 
                    #send response
                    self.send_queuereg[qname].put(response) 
                    #wait some time before response is processed 
                    time.sleep(1)
                    # Create time command en put on queue
                    response = createtimecommand(protocol,loggerid,"0001")
                    if verbose: print("\t - Grottserver 03 announce data record processed") 

            elif header[14:16] in ("19","05","06","18"):
                if verbose: print("\t - Grottserver - " + header[12:16] + " record received, no response needed")
                
                offset = 0
                if protocol in ("06") : 
                    offset = 40

                register = int(result_string[36+offset:40+offset],16) 
                if command == "05" : 
                    #value = result_string[40+offset:44+offset]
                    value = result_string[44+offset:48+offset]
                elif command == "06" : 
                    result = result_string[40+offset:42+offset] 
                    #print("06 response result :", result)
                    value = result_string[42+offset:46+offset]      
                elif command == "18" : 
                    result = result_string[40+offset:42+offset] 
                else : 
                    # "19" response take length into account 
                    valuelen = int(result_string[40+offset:44+offset],16)
                    value = codecs.decode(result_string[44+offset:44+offset+valuelen*2], "hex").decode('utf-8') 
                
                regkey = "{:04x}".format(register)
                if command == "06" : 
                    # command 06 response has ack (result) + value. We will create a 06 response and a 05 response (for reg administration)
                    commandresponse["06"][regkey] = {"value" : value , "result" : result}                
                    commandresponse["05"][regkey] = {"value" : value} 
                if command == "18" :
                    commandresponse["18"][regkey] = {"result" : result}                
                else : 
                    #command 05 or 19 
                    commandresponse[command][regkey] = {"value" : value} 

                response = None

            elif header[14:16] in ("10") :
                if verbose: print("\t - Grottserver - " + header[12:16] + " record received, no response needed")

                startregister = int(result_string[76:80],16)
                endregister = int(result_string[80:84],16)
                value = result_string[84:86]
                
                regkey = "{:04x}".format(startregister) + "{:04x}".format(endregister)
                commandresponse[command][regkey] = {"value" : value} 

                response = None

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


if __name__ == "__main__":

    print("\t - Grottserver - Version: " + verrel)

    send_queuereg = {} 
    loggerreg = {}
    # response from command is written is this variable (for now flat, maybe dict later)
    commandresponse =  defaultdict(dict)

    http_server = GrottHttpServer(httphost, httpport, send_queuereg)
    device_server = sendrecvserver(serverhost, serverport, send_queuereg)

    http_server_thread = threading.Thread(target=http_server.run)
    device_server_thread = threading.Thread(target=device_server.run)

    http_server_thread.start()
    device_server_thread.start()

    while True:
       time.sleep(5)
