#Grott Growatt monitor based on TCPIP sniffing 
#       Monitor needs to run on a (linux) system that is abble to see TCPIP that is sent from inverter to Growatt Server
#       This can be achieved by rerouting the growatt WIFI data via a Linux server with port forwarding
#       For more information how to see aditional documentation
#       Monitor can run in forground and as a standard service!
#
#Done in 1.0.4
#       Clean up coding 
#       Test with real data 
#       implemetd mqtt 
#       implemented scrambled vs nonscrambled (needs to be tested in with old inverter)
#       Growatt old wifi release support (needs to be tested with old inverter)           
#       Read config file and commandline parms 
#       Verbose vs non verbose 
#       Enable running as a services and automatic startup after reboot 
#       Code review by peer
#       Added in github: https://github.com/johanmeijer/grott
#       Document and add service example to git
#
#Done   in 1.0.5
#V      Changed some verbose print output to trace ouput to keep verbose messages clean and lean 
#V      Add more relevant values to JSON message
#V      Make print data unbufferd to see messages direct in journal when running as as service (python -u parm added in grott.service )
#V      MQTT error handling improved
#V      Process and sent values only if PVstatus is 0 or 1. Detected unexpected values while pvstatus was 257. This an quick fix. Has to look for realroot cause reason (probably not a monitor record) 
#V      included messages for problem detection / solving of unexpected PVSTATUS = 257 issue
#
#Done   in 1.0.6
#       Resolved problem with specifing offset in .ini. Change in record by growatt (Since 23 March 2020) now need a offset of 26! 
#       Specify valueoffset = 26 and compat = True in ini file!
#Done   in 1.0.7
#       Resolved problem with unecrypted records
#       added authentication (user / password) for MQTT, specify in MQTT section of ini auth = False (default ) or True and user = "xxxxxxx" (grott : default) password = "xxxxx" (default : growatt2020)
#Done   in 1.0.8
#       Really solved problem with unecrypted records

verrel = "1.0.8"

import socket
import struct
import textwrap
import configparser, sys, argparse
from itertools import cycle # to support "cycling" the iterator
import time, json, datetime, codecs

#Decide wish MQTT will be used. use client if continuous connection is wanted 
#import paho.mqtt.client as mqtt                       
import paho.mqtt.publish as publish

#Set default variables 
verbose = True
trace = False
cfgfile = "grott.ini"
minrecl = 100
decrypt = True
compat = False
valueoffset = 4 
inverterid = "ABC1234567" 

#Growatt server default 
growattip = "47.91.67.66"
growattport = 5279

#MQTT default
mqttip = "localhost"
mqttport = 1883
mqtttopic= "energy/growatt"
nomqtt = False                                                                          #not in ini file, can only be changed via start parms
mqttauth = True;
mqttuser = "grott";
mqttpsw = "growatt2020";

#Set print formatting options
TAB_1 = '\t - '
TAB_2 = '\t\t - '
TAB_3 = '\t\t\t - '
TAB_4 = '\t\t\t\t - '

DATA_TAB_1 = '\t   '
DATA_TAB_2 = '\t\t   '
DATA_TAB_3 = '\t\t\t   '
DATA_TAB_4 = '\t\t\t\t   '

print("Grott Growatt logging monitor : " + verrel)    

#Proces commandline parameters
parser = argparse.ArgumentParser(prog='grott')
parser.add_argument('-v','--verbose',help="set verbose",action='store_true')
parser.add_argument('--version', action='version', version=verrel)
parser.add_argument('-c',help="set config file if not specified config file is grott.ini",metavar="[config file]")
parser.add_argument('-o',help="set output file, if not specified output is stdout",metavar="[output file]")
parser.add_argument('-nm','--nomqtt',help="disable mqtt send",action='store_true')
parser.add_argument('-t','--trace',help="enable trace, use in addition to verbose option",action='store_true')

#parser.print_help()
args = parser.parse_args()
verbose = args.verbose
nomqtt = args.nomqtt
trace = args.trace
if (args.c != None) : cfgfile=args.c
if (args.o != None) : sys.stdout = open(args.o, 'w')

if verbose : 
    print("\nGrott Command line parameters processed:")
    print("\tverbose:     \t", verbose)    
    print("\tconfig file: \t", cfgfile)
    print("\toutput file: \t", sys.stdout)
    print("\tnomqtt:      \t", nomqtt)
    print("\ttrace:       \t", trace)

#proces configuration file
config = configparser.ConfigParser()
config.read(cfgfile)
if config.has_option("Generic","minrecl"): minrecl = config.getint("Generic","minrecl")
if config.has_option("Generic","decrypt"): decrypt = config.getboolean("Generic","decrypt")
if config.has_option("Generic","compat"): compat = config.getboolean("Generic","compat")
if config.has_option("Generic","inverterid"): inverterid = config.get("Generic","inverterid")
if config.has_option("Generic","valueoffset"): valueoffset = config.get("Generic","valueoffset")
if config.has_option("Growatt","ip"): growattip = config.get("Growatt","ip")
if config.has_option("Growatt","port"): growattport = config.getint("Growatt","port")
if config.has_option("MQTT","ip"): mqttip = config.get("MQTT","ip")
if config.has_option("MQTT","port"): mqttport = config.getint("MQTT","port")
if config.has_option("MQTT","topic"): mqtttopic = config.get("MQTT","topic")
if config.has_option("MQTT","auth"): mqttauth = config.getboolean("MQTT","auth")
if config.has_option("MQTT","user"): mqttuser = config.get("MQTT","user")
if config.has_option("MQTT","password"): mqttpsw = config.get("MQTT","password")

#Print processed settings 
if verbose : 
    print("\nGrott configuration file processed:\n")
    print("\tminrecl:     \t",minrecl)
    print("\tdecrypt:     \t",decrypt)
    print("\tcompat:      \t",compat)
    print("\tvalueoffset: \t",valueoffset)
    print("\tinverterid:  \t",inverterid)
    print("\tmqttip:      \t",mqttip)
    print("\tmqttport:    \t",mqttport)
    print("\tmqtttopic:   \t",mqtttopic)
    print("\tmqtttauth:   \t",mqttauth)
    print("\tmqttuser:    \t",mqttuser)
    print("\tmqttpsw:     \t",mqttpsw)                       #scramble output if tested!
    print("\tgrowattip:   \t",growattip)
    print("\tgrowattport: \t",growattport)

#Prepare invert settings
SN = "".join(['{:02x}'.format(ord(x)) for x in inverterid])
offset = 6 
#if compat == "True": offset = valueoffset                          #set offset for older inverter types or after record change by Growatt
if compat: offset = int(valueoffset)                                #set offset for older inverter types or after record change by Growatt
if verbose: print("\nGrott value location offset: ", offset,"\tCompat mode: ", compat)

#prepare MQTT security
if not mqttauth: pubauth = None;
else: pubauth = dict(username=mqttuser, password=mqttpsw) 

def main():
    conn = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
    if verbose: print("\nGrott monitoring started\n")    
    while True:
        raw_data, addr = conn.recvfrom(65535)
        eth = Ethernet(raw_data)
        if trace:     
            print("\n" + TAB_1 + 'Ethernet Frame:')
            print(TAB_1 + 'Destination: {}, Source: {}, Protocol: {}'.format(eth.dest_mac, eth.src_mac, eth.proto))    
        # IPv4
        if eth.proto == 8:
            ipv4 = IPv4(eth.data)
            if trace:     
                print(TAB_1 + 'IPv4 Packet protocol 8 :')
                print(TAB_2 + 'Version: {}, Header Length: {}, TTL: {},'.format(ipv4.version, ipv4.header_length, ipv4.ttl))
                print(TAB_2 + 'Protocol: {}, Source: {}, Target: {}'.format(ipv4.proto, ipv4.src, ipv4.target))

# ICMP  (Not used in this monitor)
            if ipv4.proto == 1:
                icmp = ICMP(ipv4.data)
                if trace:     
                    print(TAB_1 + 'ICMP Packet:')
                    print(TAB_2 + 'Type: {}, Code: {}, Checksum: {},'.format(icmp.type, icmp.code, icmp.checksum))
                    print(TAB_2 + 'ICMP Data:')
                    print(format_multi_line(DATA_TAB_3, icmp.data))

# TCP
            elif ipv4.proto == 6:
                tcp = TCP(ipv4.data)
                if trace:
                        print(TAB_1 + 'TCP Segment protocol 6 found')
                        print(TAB_2 + 'Source Port: {}, Destination Port: {}'.format(tcp.src_port, tcp.dest_port))
                        print(TAB_2 + 'Source IP: {}, Destination IP: {}'.format(ipv4.src, ipv4.target))
                        
                if tcp.dest_port == growattport and ipv4.target == growattip:
                    if verbose:
                        print(TAB_1 + 'TCP Segment Growatt:')
                        print(TAB_2 + 'Source Port: {}, Destination Port: {}'.format(tcp.src_port, tcp.dest_port))
                        print(TAB_2 + 'Source IP: {}, Destination IP: {}'.format(ipv4.src, ipv4.target))
                        print(TAB_2 + 'Sequence: {}, Acknowledgment: {}'.format(tcp.sequence, tcp.acknowledgment))
                        print(TAB_2 + 'Flags:')
                        print(TAB_3 + 'URG: {}, ACK: {}, PSH: {}'.format(tcp.flag_urg, tcp.flag_ack, tcp.flag_psh))
                        print(TAB_3 + 'RST: {}, SYN: {}, FIN:{}'.format(tcp.flag_rst, tcp.flag_syn, tcp.flag_fin))

                    if len(tcp.data) < minrecl :
                        if verbose: print(TAB_1 + 'TCP Data less then minimum record length, data not processed') 
                    else: 
                        if verbose: print(TAB_2 + 'Growatt Monitor Data detected')
                        #Change in trace in future
                        if verbose: 
                            print(TAB_2 + 'Growatt original Data:')
                            print(format_multi_line(DATA_TAB_3, tcp.data))

#changed 1.08           message = list(tcp.data)
#changed 1.08           nmessage = len(message)
#changed 1.08
#changed 1.08           # Create mask and convert to hexadecimal
#changed 1.08           mask = "Growatt"
#changed 1.08           hex_mask = ['{:02x}'.format(ord(x)) for x in mask]
#changed 1.08           nmask = len(hex_mask)
#changed 1.08                                                           
#changed 1.08           # Determine how many bytes are left if we cycle mask N times over the message
#changed 1.08           remainder = nmessage % nmask
                        
                        # reset serialnumber found flag  
                        serialfound = False 
                        if decrypt: 
                            
                            message = list(tcp.data)
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
                                
                                if(result_string.find(SN) > -1):
                                    serialfound = True
                                    if verbose: print(TAB_2 + 'Growatt scrambled data processed for: ', bytearray.fromhex(SN).decode())
                                    break
                                    
                            
                        
                        else: 
#changed 1.07               result_string = message;                                                                                        
#changed 1.08               result_string = message.hex(); 
                            result_string = tcp.data.hex();                           
                                                                
                            if(result_string.find(SN) > -1):
                                serialfound = True
                                if verbose: print(TAB_2 + 'Growatt unscrambled data processed for: ', bytearray.fromhex(SN).decode())
#changed 1.08                   break
                            else: 
                                if verbose: print(TAB_2 + 'Growatt unscrambled data processed no matching inverter id found')
                                
                        if verbose: 
                                    print(TAB_2 + 'Growatt plain data:')
                                    print(format_multi_line(DATA_TAB_3, result_string)) 
                                    
                        if serialfound == True:
                            #Change in trace in future
#changed 1.08               if verbose: 
#changed 1.08                  print(TAB_2 + 'Growatt unscrambled data:')
#changed 1.08                  print(format_multi_line(DATA_TAB_3, result_string))     
                                
                            if verbose: print(TAB_2 + 'Growatt processing values for: ', bytearray.fromhex(SN).decode())
                            
                            #Retrieve values 
                            snstart = result_string.find(SN)  
                            pvserial = result_string[snstart:snstart+20]
                            pvstatus = int(result_string[snstart+offset*2+15*2:snstart+offset*2+15*2+4],16)
                            #Only process value if pvstatus is oke (this is because unexpected pvstatus of 257)
                            if pvstatus == 0 or pvstatus == 1:
                                pv1watt    = int(result_string[snstart+offset*2+25*2:snstart+offset*2+25*2+8],16)
                                pv2watt    = int(result_string[snstart+offset*2+33*2:snstart+offset*2+33*2+8],16)
                                pvpowerout = int(result_string[snstart+offset*2+37*2:snstart+offset*2+37*2+8],16)
                                pvfrequentie = int(result_string[snstart+offset*2+41*2:snstart+offset*2+41*2+4],16)
                                pvgridvoltage = int(result_string[snstart+offset*2+43*2:snstart+offset*2+43*2+4],16)
                                pvenergytoday= int(result_string[snstart+offset*2+67*2:snstart+offset*2+67*2+8],16)
                                pvenergytotal= int(result_string[snstart+offset*2+71*2:snstart+offset*2+71*2+8],16)
                                
                                if verbose:
                                    print(TAB_3 + "pvserial:      ", codecs.decode(pvserial, "hex").decode('utf-8'))
                                    print(TAB_3 + "pvstatus:      ", pvstatus) 
                                    print(TAB_3 + "pvpowerout:    ", pvpowerout/10)
                                    print(TAB_3 + "pvenergytoday: ", pvenergytoday/10)
                                    print(TAB_3 + "pvenergytotal: ", pvenergytotal/10)
                                    print(TAB_3 + "pv1watt:       ", pv1watt/10)
                                    print(TAB_3 + "pv2watt:       ", pv2watt/10)
                                    print(TAB_3 + "pvfrequentie:  ", pvfrequentie/100)
                                    print(TAB_3 + "pvgridvoltage: ", pvgridvoltage/10)
                                
                                #create JSON message                          
                                jsonmsg = json.dumps({"device":inverterid,"time":datetime.datetime.utcnow().replace(microsecond=0).isoformat(),
                                    "values":{
                                                "pvstatus":pvstatus,
                                                "pv1watt":pv1watt,
                                                "pv2watt:":pv2watt,
                                                "pvpowerout":pvpowerout,
                                                "pvfrequentie":pvfrequentie,
                                                "pvgridvoltage":pvgridvoltage,                             
                                                "pvenergytoday":pvenergytoday,
                                                "pvenergytotal":pvenergytotal}
                                                })
                                if verbose:
                                    print(TAB_2 + "MQTT jsonmsg: ")        
                                    print(TAB_3 + jsonmsg)        
                                
                                #send MQTT (use publish to keep connection active, single for sendig message and disconnect)
                                #    mqttclient.publish(mqtttopic, payload=jsonmsg, qos=0, retain=False)   
                                if not nomqtt:
                                    try: 
#changed in v1.07                       publish.single(mqtttopic, payload=jsonmsg, qos=0, retain=False, hostname=mqttip,port=mqttport, client_id=inverterid, keepalive=5)
                                        publish.single(mqtttopic, payload=jsonmsg, qos=0, retain=False, hostname=mqttip,port=mqttport, client_id=inverterid, keepalive=5, auth=pubauth)
                                        if verbose: print(TAB_2 + 'MQTT message message sent') 
                                    except TimeoutError:     
                                        if verbose: print(TAB_2 + 'MQTT connection time out error') 
                                    except ConnectionRefusedError:     
                                        if verbose: print(TAB_2 + 'MQTT connection refused by target')     
                                    except BaseException as error:     
                                        if verbose: print(TAB_2 + 'MQTT send failed:', str(error)) 
                                else:
                                    if verbose: print(TAB_2 + 'No MQTT message sent, MQTT disabled') 
                            else:
                                if verbose: print(TAB_2 + 'No valid monitor data, PV status: :', pvstatus)    
                          
                        else:   
                            if verbose: print(TAB_2 + 'No Growatt data processed or SN not found:')
                            if trace: 
                                print(TAB_2 + 'Growatt unprocessed Data:')
                                print(format_multi_line(DATA_TAB_3, result_string))
                    
# UDP Not used
            elif ipv4.proto == 17:
                udp = UDP(ipv4.data)
                if trace:
                    print(TAB_1 + 'UDP Segment:')
                    print(TAB_2 + 'Source Port: {}, Destination Port: {}, Length: {}'.format(udp.src_port, udp.dest_port, udp.size))

# Other IPv4 Not used 
            else:
                if trace:
                    print(TAB_1 + 'Other IPv4 Data:')
                    print(format_multi_line(DATA_TAB_2, ipv4.data))

        else: 
            if trace: 
                print(TAB_1 + 'No IPV4 Ethernet Data:')
                print(TAB_1 + format_multi_line(DATA_TAB_1, eth.data))


#Unpack ethernet packet
class Ethernet:
    def __init__(self, raw_data):

        dest, src, prototype = struct.unpack('! 6s 6s H', raw_data[:14])

        self.dest_mac = get_mac_addr(dest)
        self.src_mac = get_mac_addr(src)
        self.proto = socket.htons(prototype)
        self.data = raw_data[14:]
        
# Returns MAC as string from bytes (ie AA:BB:CC:DD:EE:FF)
def get_mac_addr(mac_raw):
    byte_str = map('{:02x}'.format, mac_raw)
    mac_addr = ':'.join(byte_str).upper()
    return mac_addr

#Unpacks IPV4 packet
class IPv4:

    def __init__(self, raw_data):
        version_header_length = raw_data[0]
        self.version = version_header_length >> 4
        self.header_length = (version_header_length & 15) * 4
        self.ttl, self.proto, src, target = struct.unpack('! 8x B B 2x 4s 4s', raw_data[:20])
        self.src = self.ipv4addr(src)
        self.target = self.ipv4addr(target)
        self.data = raw_data[self.header_length:]

# Returns properly formatted IPv4 address
    def ipv4addr(self, addr):
        return '.'.join(map(str, addr))    

# Unpack TCP Segment
class TCP:

    def __init__(self, raw_data):
        (self.src_port, self.dest_port, self.sequence, self.acknowledgment, offset_reserved_flags) = struct.unpack(
            '! H H L L H', raw_data[:14])
        offset = (offset_reserved_flags >> 12) * 4
        self.flag_urg = (offset_reserved_flags & 32) >> 5
        self.flag_ack = (offset_reserved_flags & 16) >> 4
        self.flag_psh = (offset_reserved_flags & 8) >> 3
        self.flag_rst = (offset_reserved_flags & 4) >> 2
        self.flag_syn = (offset_reserved_flags & 2) >> 1
        self.flag_fin = offset_reserved_flags & 1
        self.data = raw_data[offset:]    

# Unpack UDP Segment
class UDP:

    def __init__(self, raw_data):
        self.src_port, self.dest_port, self.size = struct.unpack('! H H 2x H', raw_data[:8])
        self.data = raw_data[8:]        

# Unpack ICMP Segment        
class ICMP:

    def __init__(self, raw_data):
        self.type, self.code, self.checksum = struct.unpack('! B B H', raw_data[:4])
        self.data = raw_data[4:]        

# Formats multi-line data
def format_multi_line(prefix, string, size=80):
    size -= len(prefix)
    if isinstance(string, bytes):
        string = ''.join(r'\x{:02x}'.format(byte) for byte in string)
        if size % 2:
            size -= 1
    return '\n'.join([prefix + line for line in textwrap.wrap(string, size)])
 
main()