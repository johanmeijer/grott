#
# grottconf  process command parameter and settings file
# Updated: 2020-11-09
# Version 2.2.4

import configparser, sys, argparse, os, json, io
import ipaddress
from os import walk
from grottdata import format_multi_line

class Conf : 

    def __init__(self, vrm): 
        self.verrel = vrm

        #Set default variables 
        self.verbose = False
        self.trace = False
        self.cfgfile = "grott.ini"
        self.minrecl = 100
        self.decrypt = True
        self.compat = False
        self.blockcmd = False                                                                       #Block Inverter and Shine configure commands                
        self.noipf = False                                                                          #Allow IP change if needed
        self.gtime  = "auto"                                                                        #time used =  auto: use record time or if not valid server time, alternative server: use always server time 
        self.sendbuf = True                                                                         # enable / disable sending historical data from buffer
        self.valueoffset = 6 
        self.inverterid = "automatic" 
        self.mode = "proxy"
        self.grottport = 5279
        self.grottip = "default"                                                                    #connect to server IP adress     
        self.outfile ="sys.stdout"

        #Growatt server default 
        self.growattip = "47.91.67.66"
        self.growattport = 5279

        #MQTT default
        self.mqttip = "localhost"
        self.mqttport = 1883
        self.mqtttopic= "energy/growatt"
        self.nomqtt = False                                                                          #not in ini file, can only be changed via start parms
        self.mqttauth = False
        self.mqttuser = "grott"
        self.mqttpsw = "growatt2020"

        #pvoutput default 
        self.pvoutput = False
        self.pvurl = "https://pvoutput.org/service/r2/addstatus.jsp"
        self.pvapikey = "yourapikey"
        self.pvsystemid = "12345"

        print("Grott Growatt logging monitor : " + self.verrel)    

        #Set parm's 
        #prio: 1.Command line parms, 2.env. variables, 3.config file 4.program default
        #process command settings that set processing values (verbose, trace, output, config, nomqtt)
        self.parserinit() 
        
        #Process config file
        self.procconf()
        
        #Process environmental variable
        self.procenv()

        #Process environmental variable to override config and environmental settings
        self.parserset() 

        #print settings
        #print()

        #self.setparm()

        #Prepare invert settings
        self.SN = "".join(['{:02x}'.format(ord(x)) for x in self.inverterid])
        self.offset = 6 
        if self.compat: self.offset = int(self.valueoffset)                                       #set offset for older inverter types or after record change by Growatt
        
        #prepare MQTT security
        if not self.mqttauth: self.pubauth = None
        else: self.pubauth = dict(username=self.mqttuser, password=self.mqttpsw)
        
        #define recordlayouts 
        self.set_reclayouts()

        #define record whitlist (if blocking / filtering enabled 
        self.set_recwl()

    def print(self): 
        print("\nGrott settings:\n")
        print("_Generic:")
        print("\tversion:     \t",self.verrel)
        print("\tverbose:     \t",self.verbose)
        print("\ttrace:       \t",self.trace)
        print("\tconfig file: \t",self.cfgfile)
        print("\tminrecl:     \t",self.minrecl)
        print("\tdecrypt:     \t",self.decrypt)
        print("\tcompat:      \t",self.compat)
        print("\tblockcmd:    \t",self.blockcmd)
        print("\tnoipf:       \t",self.noipf)
        print("\ttime:        \t",self.gtime)
        print("\tsendbuf:     \t",self.sendbuf)
        print("\tvalueoffset: \t",self.valueoffset)
        print("\toffset:      \t",self.offset)
        print("\tinverterid:  \t",self.inverterid)
        print("\tmode:        \t",self.mode)
        print("\tgrottip      \t",self.grottip)
        print("\tgrottport    \t",self.grottport)
        #print("\tSN           \t",self.SN)
        print("_MQTT:")
        print("\tnomqtt       \t",self.nomqtt)
        print("\tmqttip:      \t",self.mqttip)
        print("\tmqttport:    \t",self.mqttport)
        print("\tmqtttopic:   \t",self.mqtttopic)
        print("\tmqtttauth:   \t",self.mqttauth)
        print("\tmqttuser:    \t",self.mqttuser)
        print("\tmqttpsw:     \t",self.mqttpsw)                       #scramble output if tested!
        print("_Growatt server:")
        print("\tgrowattip:   \t",self.growattip)
        print("\tgrowattport: \t",self.growattport)
        print("_PVOutput:")
        print("\tpvoutput:    \t",self.pvoutput)
        print("\tpvurl:       \t",self.pvurl)
        print("\tpvapikey:    \t",self.pvapikey)
        print("\tpvsystemid:  \t",self.pvsystemid)
        print()


    def parserinit(self): 
        #Process commandline parameters init (read args, process c,v,o settings)
        parser = argparse.ArgumentParser(prog='grott')
        parser.add_argument('-v','--verbose',help="set verbose",action='store_true')
        parser.add_argument('--version', action='version', version=self.verrel)
        parser.add_argument('-c',help="set config file if not specified config file is grott.ini",metavar="[config file]")
        parser.add_argument('-o',help="set output file, if not specified output is stdout",metavar="[output file]")
        parser.add_argument('-m',help="set mode (sniff or proxy), if not specified mode is sniff",metavar="[mode]")
        parser.add_argument('-i',help="set inverterid, if not specified inverterid of .ini file is used",metavar="[inverterid]")
        parser.add_argument('-nm','--nomqtt',help="disable mqtt send",action='store_true')
        parser.add_argument('-t','--trace',help="enable trace, use in addition to verbose option (only available in sniff mode)",action='store_true')
        parser.add_argument('-p','--pvoutput',help="enable pvoutput send (True/False)",action='store_true')
        parser.add_argument('-b','--blockcmd',help="block Growatt configure commands",action='store_true')
        parser.add_argument('-n','--noipf',help="Allow IP change from growatt website",action='store_true')
        
      
        args, unknown = parser.parse_known_args()

        if (args.c != None) : self.cfgfile=args.c
        #if (args.o != None) : sys.stdout = open(args.o, 'wb',0) changed to support unbuffered output in windows !!!
        if (args.o != None) : sys.stdout = io.TextIOWrapper(open(args.o, 'wb', 0), write_through=True)
        self.verbose = args.verbose
        self.anomqtt = args.nomqtt
        self.apvoutput = args.pvoutput 
        self.trace = args.trace
        self.ablockcmd = args.blockcmd
        self.anoipf = args.noipf
                
        if (args.m != None) : 
            #print("mode: ",args.m)
            if (args.m == "proxy") : 
                self.amode = "proxy"
            else :
                self.amode = "sniff"                                        # default
        if (args.i != None and args.i != "none") :                          # added none for docker support 
            self.ainverterid = args.i             

        if self.verbose : 
            print("\nGrott Command line parameters processed:")
            print("\tverbose:     \t", self.verbose)    
            print("\tconfig file: \t", self.cfgfile)
            print("\toutput file: \t", sys.stdout)
            print("\tnomqtt:      \t", self.anomqtt)
            print("\tinverterid:  \t", self.inverterid)
            print("\tpvoutput:    \t", self.apvoutput)
            print("\tblockcmd:    \t", self.ablockcmd)
            print("\tnoipf:       \t", self.noipf)

    def parserset(self):
        print("\nGrott override settings if set in commandline") 
        if hasattr(self, "amode"): 
            self.mode = self.amode          
        if hasattr(self, "ablockcmd") and self.ablockcmd == True: 
            self.blockcmd = self.ablockcmd  
        if hasattr(self, "anoipf") and self.anoipf == True: 
            self.noipf = self.anoipf      
        if hasattr(self, "ainverterid"): 
            self.inverterid = self.ainverterid 
        if hasattr(self, "anomqtt") and self.anomqtt: 
            self.nomqtt = self.anomqtt                       
        if hasattr(self, "apvoutput") and self.apvoutput: 
            self.pvoutput = self.apvoutput      
        #Correct Bool if changed to string during parsing process
        if self.verbose == True or self.verbose == "True" : self.verbose = True  
        else : self.verbose = False 
        if self.trace == True or self.trace == "True" : self.trace = True  
        else : self.trace = False 
        if self.decrypt == False or self.decrypt == "False" : self.decrypt = False 
        else : self.decrypt = True         
        if self.compat == True or self.compat == "True" : self.compat = True  
        else : self.compat = False      
        if self.blockcmd == True or self.blockcmd == "True" : self.blockcmd = True             
        else : self.blockcmd = False      
        if self.sendbuf == False or self.sendbuf == "False" : self.sendbuf = False 
        else : self.sendbuf = True      
        if self.pvoutput == True or self.pvoutput == "True" : self.pvoutput = True
        else : self.pvoutput = False
        if self.nomqtt == False or self.nomqtt == "False" : self.nomqtt = False 
        else : self.nomqtt = True         
        if self.mqttauth in ("True", "true", True) : 
            self.mqttauth = True
            print(self.mqttauth)      
        else : self.mqttauth = False         
        
    def procconf(self): 
        print("\nGrott process configuration file")
        config = configparser.ConfigParser()
        config.read(self.cfgfile)
        if config.has_option("Generic","minrecl"): self.minrecl = config.getint("Generic","minrecl")
        if config.has_option("Generic","verbose"): self.verbose = config.getboolean("Generic","verbose")
        if config.has_option("Generic","decrypt"): self.decrypt = config.getboolean("Generic","decrypt")
        if config.has_option("Generic","compat"): self.compat = config.getboolean("Generic","compat")
        if config.has_option("Generic","inverterid"): self.inverterid = config.get("Generic","inverterid")
        if config.has_option("Generic","blockcmd"): self.blockcmd = config.get("Generic","blockcmd")
        if config.has_option("Generic","noipf"): self.noipf = config.get("Generic","noipf")
        if config.has_option("Generic","time"): self.gtime = config.get("Generic","time")
        if config.has_option("Generic","sendbuf"): self.sendbuf = config.get("Generic","sendbuf")
        if config.has_option("Generic","mode"): self.mode = config.get("Generic","mode")
        if config.has_option("Generic","ip"): self.grottip = config.get("Generic","ip")
        if config.has_option("Generic","port"): self.grottport = config.getint("Generic","port")
        if config.has_option("Generic","valueoffset"): self.valueoffset = config.get("Generic","valueoffset")
        if config.has_option("Growatt","ip"): self.growattip = config.get("Growatt","ip") 
        if config.has_option("Growatt","port"): self.growattport = config.getint("Growatt","port")
        if config.has_option("MQTT","nomqtt"): self.nomqtt = config.get("MQTT","nomqtt")
        if config.has_option("MQTT","ip"): self.mqttip = config.get("MQTT","ip")
        if config.has_option("MQTT","port"): self.mqttport = config.getint("MQTT","port")
        if config.has_option("MQTT","topic"): self.mqtttopic = config.get("MQTT","topic")
        if config.has_option("MQTT","auth"): self.mqttauth = config.getboolean("MQTT","auth")
        if config.has_option("MQTT","user"): self.mqttuser = config.get("MQTT","user")
        if config.has_option("MQTT","password"): self.mqttpsw = config.get("MQTT","password")
        if config.has_option("PVOutput","pvoutput"): self.pvoutput = config.get("PVOutput","pvoutput")
        if config.has_option("PVOutput","apikey"): self.pvapikey = config.get("PVOutput","apikey")
        if config.has_option("PVOutput","systemid"): self.pvsystemid = config.get("PVOutput","systemid")

    def procenv(self): 
        print("\nGrott process environmental variables")
        #print(os.getenv('gmode'))
        if os.getenv('gmode') in ("sniff", "proxy") :  self.mode = os.getenv('gmode')
        if os.getenv('gverbose') in ("True", "False"):  self.verbose = os.getenv('verbose')
        if os.getenv('gminrecl') != None : 
            if 0 <= int(os.getenv('gminrecl')) <= 255  :     self.minrecl = os.getenv('gminrecl')
        if os.getenv('gdecrypt') in ("True", "False") : self.decrypt = os.getenv('gdecrypt') 
        if os.getenv('gcompat') in ("True", "False") :  self.compat = os.getenv('gcompat')
        if os.getenv('gblockcmd') in ("True", "False") : self.blockcmd = os.getenv('gblockcmd')
        if os.getenv('gnoipf') in ("True", "False") : self.noipf = os.getenv('gnoipf')    
        if os.getenv('gtime') in ("auto", "server") : self.gtime = os.getenv('gtime')   
        if os.getenv('gsendbuf') in ("True", "False") : self.sendbuf = os.getenv('gsendbuf')   
        if os.getenv('ginverterid') != None :  self.inverterid = os.getenv('ginverterid')
        if os.getenv('ggrottip') != None : 
            try: 
                ipaddress.ip_address(os.getenv('ggrottip'))
                self.grottip = os.getenv('ggrottip') 
            except: 
                if self.verbose : print("\nGrott IP address env invalid")
        if os.getenv('ggrottport') != None : 
            if 0 <= int(os.getenv('ggrottport')) <= 65535  :  self.grottport = os.getenv('ggrottport')
        if os.getenv('gvalueoffset') != None :     
            if 0 <= int(os.getenv('gvalueoffset')) <= 255  :  self.valueoffset = os.getenv('gvalueoffset')
        if os.getenv('ggrowattip') != None :    
            try: 
                ipaddress.ip_address(os.getenv('ggrowattip'))
                self.growattip = os.getenv('ggrowattip') 
            except: 
                if self.verbose : print("\nGrott Growatt server IP address env invalid")
        if os.getenv('ggrowattport') != None :     
            if 0 <= int(os.getenv('ggrowattport')) <= 65535  :  self.growattport = os.getenv('ggrowattport')
        if os.getenv('gnomqtt') in ("True", "False") :  self.nomqtt = os.getenv('gnomqtt')    
        if os.getenv('gmqttip') != None :    
            try: 
                ipaddress.ip_address(os.getenv('gmqttip'))
                self.mqttip = os.getenv('gmqttip') 
            except: 
                if self.verbose : print("\nGrott MQTT server IP address env invalid")
        if os.getenv('gmqttport') != None :     
            if 0 <= int(os.getenv('gmqttport')) <= 65535  :  self.mqttport = os.getenv('gmqttport')
        if os.getenv('gmqttauth') in ("True", "true", True, False, "false", "False") :  self.mqttauth = os.getenv('gmqttauth')
        if os.getenv('gmqtttopic') != None :  self.mqtttopic = os.getenv('gmqtttopic')
        if os.getenv('gmqttuser') != None :  self.mqttuser = os.getenv('gmqttuser')
        if os.getenv('gmqttpassword') != None : self.mqttpsw = os.getenv('gmqttpassword')
        if os.getenv('gpvoutput') in ("True", "False") :  self.pvoutput = os.getenv('gpvoutput') 
        if os.getenv('gpvapikey') != None :  self.pvapikey = os.getenv('gpvapikey')   
        if os.getenv('gpvsystemid') != None :  self.pvsystemid = os.getenv('gpvsystemid')   
        
    def set_recwl(self):    
        #define record that will not be blocked or inspected if blockcmd is specified
        self.recwl = {"0103",                                    #announce record
                         "0104",                                    #data record    
                         "0116",                                    #ping    
                         "0119",                                    #identify                       
                         "0150",                                    #Archived record
                         "5003",                                    #announce record
                         "5004",                                    #data record    
                         "5016",                                    #ping    
                         "5019",                                    #identify
                         "5050",                                    #Archived record
                         "5103",                                    #announce record
                         "5104",                                    #data record                          
                         "5116",                                    #ping    
                         "5119",                                    #identify
                         "5150"                                     #Archived record
                         
        } 

        try: 
            with open('recwl.txt') as f:
                self.recwl = f.read().splitlines()
            if self.verbose : print("\nGrott external record whitelist: 'recwl.txt' read")
        except:
            if self.verbose: print("\nGrott external record whitelist 'recwl.txt' not found")
        if self.verbose: print("\nGrott records whitelisted : ", self.recwl)  

    def set_reclayouts(self):    
        #define record layout to be used based on byte 4,6,7 of the header T+byte4+byte6+byte7     
        self.recorddict = {} 
        
        self.recorddict1 = {"T020104": {
            "decrypt"           : "False",
            "pvserial"          : 36,
            "date"              : 0,
            "pvstatus"          : 78, 
            "pvpowerin"         : 82,    
            "pv1voltage"        : 90,    
            "pv1current"        : 94,            
            "pv1watt"           : 98,           
            "pv2voltage"        : 106,        
            "pv2current"        : 110,        
            "pv2watt"           : 114,        
            "pvpowerout"        : 122,        
            "pvfrequentie"      : 130,        
            "pvgridvoltage"     : 134,        
            "pvenergytoday"     : 182,         
            "pvenergytotal"     : 190,         
            "pvtemperature"     : 206,         
            "pvipmtemperature"  : 242,        
            } } 

        self.recorddict2 = {"T050104": {
            "decrypt"           : "True",
            "pvserial"          : 36,
            "date"              : 56,
            "pvstatus"          : 78, 
            "pvpowerin"         : 82,    
            "pv1voltage"        : 90,    
            "pv1current"        : 94,            
            "pv1watt"           : 98,           
            "pv2voltage"        : 106,        
            "pv2current"        : 110,        
            "pv2watt"           : 114,        
            "pvpowerout"        : 122,        
            "pvfrequentie"      : 130,        
            "pvgridvoltage"     : 134,        
            "pvenergytoday"     : 182,         
            "pvenergytotal"     : 190,         
            "pvtemperature"     : 206,         
            "pvipmtemperature"  : 242,        
            } } 
        
        self.recorddict4 = {"T055104X": {
            "decrypt"           : "True",
            "pvserial"          : 36,
            "date"              : 0,
            "pvstatus"          : 78, 
            "pvpowerin"         : 82,    
            "pv1voltage"        : 90,    
            "pv1current"        : 94,            
            "pv1watt"           : 98,           
            "pv2voltage"        : 106,        
            "pv2current"        : 110,        
            "pv2watt"           : 114,        
            "pvpowerout"        : 170,        
            "pvfrequentie"      : 178,        
            "pvgridvoltage"     : 182,        
            "pvenergytoday"     : 274,         
            "pvenergytotal"     : 282,         
            "pvtemperature"     : 450,         
            "pvipmtemperature"  : 454,         
            } }   

        self.recorddict3 = {"T060104": {
            "decrypt"           : "True",
            "pvserial"          : 76,
            "date"              : 136,
            "pvstatus"          : 158, 
            "pvpowerin"         : 162,    
            "pv1voltage"        : 170,    
            "pv1current"        : 174,            
            "pv1watt"           : 178,           
            "pv2voltage"        : 186,        
            "pv2current"        : 190,        
            "pv2watt"           : 194,        
            "pvpowerout"        : 202,        
            "pvfrequentie"      : 210,        
            "pvgridvoltage"     : 214,        
            "pvenergytoday"     : 262,         
            "pvenergytotal"     : 270,         
            "pvtemperature"     : 286,         
            "pvipmtemperature"  : 322,         
            } } 

        self.recorddict5 = {"T060104X": {
            "decrypt"           : "True",
            "pvserial"          : 76,
            "date"              : 136,
            "pvstatus"          : 158, 
            "pvpowerin"         : 162,    
            "pv1voltage"        : 170,    
            "pv1current"        : 174,            
            "pv1watt"           : 178,           
            "pv2voltage"        : 186,        
            "pv2current"        : 190,        
            "pv2watt"           : 194,        
            "pvpowerout"        : 250,        
            "pvfrequentie"      : 258,        
            "pvgridvoltage"     : 262,        
            "pvenergytoday"     : 354,         
            "pvenergytotal"     : 362,         
            "pvtemperature"     : 530,         
            "pvipmtemperature"  : 534         
            } } 

        self.recorddict6 =  {"T065004X": {
            "decrypt"           : "True",
            "pvserial"          : 76,
            "date"              : 116,
            "pvstatus"          : 158, 
            "pvpowerin"         : 162,    
            "pv1voltage"        : 170,    
            "pv1current"        : 174,            
            "pv1watt"           : 178,           
            "pv2voltage"        : 186,        
            "pv2current"        : 190,          
            "pv2watt"           : 194,        
            "pvpowerout"        : 250,        
            "pvfrequentie"      : 258,        
            "pvgridvoltage"     : 262,        
            "pvenergytoday"     : 354,         
            "pvenergytotal"     : 362,         
            "pvtemperature"     : 530,         
            "pvipmtemperature"  : 534  
            } } 

        self.recorddict7 =  {"T020150": {
            "decrypt"           : "False",
            "pvserial"          : 36,
            "date"              : 56,
            "pvstatus"          : 78, 
            "pvpowerin"         : 82,    
            "pv1voltage"        : 90,    
            "pv1current"        : 94,            
            "pv1watt"           : 98,           
            "pv2voltage"        : 106,        
            "pv2current"        : 110,        
            "pv2watt"           : 114,        
            "pvpowerout"        : 122,        
            "pvfrequentie"      : 130,        
            "pvgridvoltage"     : 134,        
            "pvenergytoday"     : 182,         
            "pvenergytotal"     : 190,         
            "pvtemperature"     : 206,         
            "pvipmtemperature"  : 242        
            }}

        self.recorddict8 =  {"T050150": {
            "decrypt"           : "True",
            "pvserial"          : 36,
            "date"              : 0,
            "pvstatus"          : 78, 
            "pvpowerin"         : 82,    
            "pv1voltage"        : 90,    
            "pv1current"        : 94,            
            "pv1watt"           : 98,           
            "pv2voltage"        : 106,        
            "pv2current"        : 110,        
            "pv2watt"           : 114,        
            "pvpowerout"        : 122,        
            "pvfrequentie"      : 130,        
            "pvgridvoltage"     : 134,        
            "pvenergytoday"     : 182,         
            "pvenergytotal"     : 190,         
            "pvtemperature"     : 206,         
            "pvipmtemperature"  : 242        
            }}

        self.recorddict9 =  {"T055150X": {
            "decrypt"           : "True",
            "pvserial"          : 36,
            "date"              : 0,
            "pvstatus"          : 78, 
            "pvpowerin"         : 82,    
            "pv1voltage"        : 90,    
            "pv1current"        : 94,            
            "pv1watt"           : 98,           
            "pv2voltage"        : 106,        
            "pv2current"        : 110,        
            "pv2watt"           : 114,        
            "pvpowerout"        : 170,        
            "pvfrequentie"      : 178,        
            "pvgridvoltage"     : 182,        
            "pvenergytoday"     : 274,         
            "pvenergytotal"     : 282,         
            "pvtemperature"     : 450,         
            "pvipmtemperature"  : 454         
            }}

        self.recorddict10 =  {"T060150": {
            "decrypt"           : "True",
            "pvserial"          : 76,
            "date"              : 136,
            "pvstatus"          : 158, 
            "pvpowerin"         : 162,    
            "pv1voltage"        : 170,    
            "pv1current"        : 174,            
            "pv1watt"           : 178,           
            "pv2voltage"        : 186,        
            "pv2current"        : 190,        
            "pv2watt"           : 194,        
            "pvpowerout"        : 202,        
            "pvfrequentie"      : 210,        
            "pvgridvoltage"     : 214,        
            "pvenergytoday"     : 262,         
            "pvenergytotal"     : 270,         
            "pvtemperature"     : 286,         
            "pvipmtemperature"  : 322         
            }}

        self.recorddict11 =  {"T060150X": {
            "decrypt"           : "True",
            "pvserial"          : 76,
            "date"              : 136,
            "pvstatus"          : 158, 
            "pvpowerin"         : 162,    
            "pv1voltage"        : 170,    
            "pv1current"        : 174,            
            "pv1watt"           : 178,           
            "pv2voltage"        : 186,        
            "pv2current"        : 190,        
            "pv2watt"           : 194,        
            "pvpowerout"        : 250,        
            "pvfrequentie"      : 258,        
            "pvgridvoltage"     : 262,        
            "pvenergytoday"     : 354,         
            "pvenergytotal"     : 362,         
            "pvtemperature"     : 530,         
            "pvipmtemperature"  : 534         
            }}

        self.recorddict12 =  {"T065050X": {
            "decrypt"           : "True",
            "pvserial"          : 76,
            "date"              : 136,
            "pvstatus"          : 158, 
            "pvpowerin"         : 162,    
            "pv1voltage"        : 170,    
            "pv1current"        : 174,            
            "pv1watt"           : 178,           
            "pv2voltage"        : 186,        
            "pv2current"        : 190,          
            "pv2watt"           : 194,        
            "pvpowerout"        : 250,        
            "pvfrequentie"      : 258,        
            "pvgridvoltage"     : 262,        
            "pvenergytoday"     : 354,         
            "pvenergytotal"     : 362,         
            "pvtemperature"     : 530,         
            "pvipmtemperature"  : 534  
            }}     
        
        self.recorddict13 =  {"T065104X": {
            "decrypt"           : "True",
            "pvserial"          : 76,
            "date"              : 116,
            "pvstatus"          : 158, 
            "pvpowerin"         : 162,    
            "pv1voltage"        : 170,    
            "pv1current"        : 174,            
            "pv1watt"           : 178,           
            "pv2voltage"        : 186,        
            "pv2current"        : 190,        
            "pv2watt"           : 194,        
            "pvpowerout"        : 250,        
            "pvfrequentie"      : 258,        
            "pvgridvoltage"     : 262,        
            "pvenergytoday"     : 354,         
            "pvenergytotal"     : 362,         
            "pvtemperature"     : 530,         
            "pvipmtemperature"  : 534    
            }}     

        self.recorddict14 =  {"T065150X": {    
            "decrypt"           : "True",
            "pvserial"          : 76,
            "date"              : 116,
            "pvstatus"          : 158, 
            "pvpowerin"         : 162,    
            "pv1voltage"        : 170,    
            "pv1current"        : 174,            
            "pv1watt"           : 178,           
            "pv2voltage"        : 186,        
            "pv2current"        : 190,        
            "pv2watt"           : 194,        
            "pvpowerout"        : 250,        
            "pvfrequentie"      : 258,        
            "pvgridvoltage"     : 262,        
            "pvenergytoday"     : 354,         
            "pvenergytotal"     : 362,         
            "pvtemperature"     : 530,         
            "pvipmtemperature"  : 534    
            }}  

        self.recorddict15 = {"T020404": {
            "decrypt"           : "False",
            "pvserial"          : 36,
            "date"              : 0,
            "pvstatus"          : 78, 
            "pvpowerin"         : 82,    
            "pv1voltage"        : 90,    
            "pv1current"        : 94,            
            "pv1watt"           : 98,           
            "pv2voltage"        : 106,        
            "pv2current"        : 110,        
            "pv2watt"           : 114,        
            "pvpowerout"        : 122,        
            "pvfrequentie"      : 130,        
            "pvgridvoltage"     : 134,        
            "pvenergytoday"     : 182,         
            "pvenergytotal"     : 190,         
            "pvtemperature"     : 206,         
            "pvipmtemperature"  : 242,        
            } } 

        self.recorddict.update(self.recorddict1)
        self.recorddict.update(self.recorddict2)
        self.recorddict.update(self.recorddict3)
        self.recorddict.update(self.recorddict4)
        self.recorddict.update(self.recorddict5)
        self.recorddict.update(self.recorddict6)
        self.recorddict.update(self.recorddict7)
        self.recorddict.update(self.recorddict8)
        self.recorddict.update(self.recorddict9)
        self.recorddict.update(self.recorddict10)
        self.recorddict.update(self.recorddict11)
        self.recorddict.update(self.recorddict12)
        self.recorddict.update(self.recorddict13)
        self.recorddict.update(self.recorddict14)
        self.recorddict.update(self.recorddict15)

        f = []
        print("\nGrott process json layout files")
        for (dirpath, dirnames, filenames) in walk('.'):            
            f.extend(filenames)
            break   
        for x in f:
            if ((x[0] == 't' or x[0] == 'T') and x.find('.json') > 0):   
                print(x)
                with open(x) as json_file: 
                    dicttemp = json.load(json_file) 
                    #print(dicttemp)
                    self.recorddict.update(dicttemp)
                
                
        if self.verbose: print("\nGrott layout records loaded")
        for key in self.recorddict :
            if self.verbose : print(key, " : ")
            if self.verbose : print(self.recorddict[key])  

