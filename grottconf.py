#
# grottconf  process command parameter and settings file
# Updated: 2021-01-09
# Version 2.4.0

import configparser, sys, argparse, os, json, io
import ipaddress
from os import walk
from grottdata import format_multi_line, str2bool

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
        self.tmzone = "local"                                                                       #set timezone (at this moment only used for influxdb)                

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
        self.pvinverters = 1
        self.pvurl = "https://pvoutput.org/service/r2/addstatus.jsp"
        self.pvapikey = "yourapikey"
        self.pvsystemid = {}
        self.pvinverterid = {}
        self.pvsystemid[1] = "systemid1"
        self.pvinverterid[1] = "inverter1"
        
        #influxdb default 
        self.influx = False
        self.influx2 = False
        self.ifdbname = "grottdb"
        self.ifip = "localhost"
        self.ifport = 8086
        self.ifuser = "grott"
        self.ifpsw  = "growatt2020"
        self.iftoken  = "influx_token"
        self.iforg  = "grottorg"
        self.ifbucket = "grottdb" 

        #extension 
        self.extension = False
        self.extname = "grottext"
        #self.extvar = {"ip": "localhost", "port":8000}  
        self.extvar = {"none": "none"}  
        
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

        #prepare influxDB
        if self.influx :  
            if self.ifip == "localhost" : self.ifip = '0.0.0.0'
            if self.influx2 == False: 
                if self.verbose :  print("")
                if self.verbose :  print("\t - " + "Grott InfluxDB V1 initiating started")
                try:     
                    from influxdb import InfluxDBClient
                except: 
                    if self.verbose :  print("\t - " + "Grott Influxdb Library not installed in Python")
                    self.influx = False                       # no influx processing any more till restart (and errors repared)
                    raise SystemExit("Grott Influxdb initialisation error")

                self.influxclient = InfluxDBClient(host=self.ifip, port=self.ifport, timeout=3, username=self.ifuser, password=self.ifpsw)   
                
                try: 
                    databases = [db['name'] for db in self.influxclient.get_list_database()]
                except Exception as e: 
                    if self.verbose :  print("\t - " + "Grott can not contact InfluxDB")   
                    self.influx = False                       # no influx processing any more till restart (and errors repared)
                    print("\t -", e)
                    raise SystemExit("Grott Influxdb initialisation error")

                #print(databases)  
                if self.ifdbname not in databases:
                    if self.verbose :  print("\t - " + "Grott grottdb not yet defined in influx, will  be created")        
                    try: 
                        self.influxclient.create_database(self.ifdbname)
                    except: 
                        if self.verbose :  print("\t - " + "Grott Unable to create or connect to influx database:" ,  self.ifdbname," check user authorisation") 
                        self.influx = False                       # no influx processing any more till restart (and errors repared)
                        raise SystemExit("Grott Influxdb initialisation error")

        
                self.influxclient.switch_database(self.ifdbname)
            else: 

                if self.verbose :  print("")
                if self.verbose :  print("\t - " + "Grott InfluxDB V2 initiating started")
                try:     
                    from influxdb_client import InfluxDBClient
                    from influxdb_client.client.write_api import SYNCHRONOUS
                except: 
                    if self.verbose :  print("\t - " + "Grott Influxdb-client Library not installed in Python")
                    self.influx = False                       # no influx processing any more till restart (and errors repared)
                    raise SystemExit("Grott Influxdb initialisation error")

                #self.influxclient = InfluxDBClient(url='192.168.0.211:8086',org=self.iforg, token=self.iftoken)
                self.influxclient = InfluxDBClient(url=self.ifip + ":" + self.ifport,org=self.iforg, token=self.iftoken)
                self.ifbucket_api = self.influxclient.buckets_api()
                self.iforganization_api = self.influxclient.organizations_api()              
                self.ifwrite_api = self.influxclient.write_api(write_options=SYNCHRONOUS)
                
                try:
                    buckets = self.ifbucket_api.find_bucket_by_name(self.ifbucket)
                    organizations = self.iforganization_api.find_organizations()  
                    #print(organizations)                                         
                    if buckets == None:
                        print("\t - " + "influxDB bucket ", self.ifbucket, "not defined")  
                        self.influx = False      
                        raise SystemExit("Grott Influxdb initialisation error") 
                    orgfound = False    
                    for org in organizations: 
                        if org.name == self.iforg:
                            orgfound = True
                            break
                    if not orgfound: 
                        print("\t - " + "influxDB organization", self.iforg, "not defined or not authorisation to check")  
                        ##self.influx = False  
                        ##raise SystemExit("Grott Influxdb initialisation error")

                except Exception as e:
                    if self.verbose :  print("\t - " + "Grott error: can not contact InfluxDB")   
                    print(e)
                    self.influx = False                       # no influx processing any more till restart (and errors repared)
                    raise SystemExit("Grott Influxdb initialisation error") 
            
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
        print("\ttimezone:    \t",self.tmzone)
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
        print("\tmqttpsw:     \t","**secret**")                       #scramble output if tested!
        #print("\tmqttpsw:     \t",self.mqttpsw)                       #scramble output if tested!
        print("_Growatt server:")
        print("\tgrowattip:   \t",self.growattip)
        print("\tgrowattport: \t",self.growattport)
        print("_PVOutput:")
        print("\tpvoutput:    \t",self.pvoutput)
        print("\tpvurl:       \t",self.pvurl)
        print("\tpvapikey:    \t",self.pvapikey)                
        print("\tpvinverters: \t",self.pvinverters)
        if self.pvinverters == 1 :
            print("\tpvsystemid:  \t",self.pvsystemid[1])
        else: 
            print("\tpvsystemid:  \t",self.pvsystemid)
            print("\tpvinvertid:  \t",self.pvinverterid)
        print("_Influxdb:")
        print("\tinflux:      \t",self.influx)
        print("\tinflux2:     \t",self.influx2)
        print("\tdatabase:    \t",self.ifdbname)
        print("\tip:          \t",self.ifip)
        print("\tport:        \t",self.ifport)
        print("\tuser:        \t",self.ifuser)        
        print("\tpassword:    \t","**secret**")
        #print("\tpassword:    \t",self.ifpsw)
        print("\torganization:\t",self.iforg ) 
        print("\tbucket:      \t",self.ifbucket) 
        print("\ttoken:       \t","**secret**")
        #print("\ttoken:       \t",self.iftoken)  
        
        print("_Extension:")
        print("\textension:   \t",self.extension) 
        print("\textname:     \t",self.extname)  
        print("\textvar:      \t",self.extvar) 
         
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
        # if self.verbose == True or self.verbose == "True" : self.verbose = True  
        # else : self.verbose = False 
        self.verbose = str2bool(self.verbose)        
        self.trace = str2bool(self.trace)        
        self.decrypt = str2bool(self.decrypt)
        self.compat = str2bool(self.compat)
        self.blockcmd = str2bool(self.blockcmd)     
        self.noipf = str2bool(self.noipf) 
        self.sendbuf = str2bool(self.sendbuf)      
        self.pvoutput = str2bool(self.pvoutput)
        self.nomqtt = str2bool(self.nomqtt)        
        self.mqttauth = str2bool(self.mqttauth)
        self.influx = str2bool(self.influx)
        self.influx2 = str2bool(self.influx2)
        self.extension = str2bool(self.extension)
               
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
        if config.has_option("Generic","timezone"): self.tmzone = config.get("Generic","timezone")
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
        if config.has_option("PVOutput","pvinverters"): self.pvinverters = config.getint("PVOutput","pvinverters")
        if config.has_option("PVOutput","apikey"): self.pvapikey = config.get("PVOutput","apikey")
        # if more inverter are installed at the same interface (shinelink) get systemids
        #if self.pvinverters > 1 : 
        for x in range(self.pvinverters+1) : 
            if config.has_option("PVOutput","systemid"+str(x)): self.pvsystemid[x] = config.get("PVOutput","systemid" + str(x))
            if config.has_option("PVOutput","inverterid"+str(x)): self.pvinverterid[x] = config.get("PVOutput","inverterid" + str(x))
        if self.pvinverters == 1 : 
            if config.has_option("PVOutput","systemid"): self.pvsystemid[1] = config.get("PVOutput","systemid")
        #INFLUX
        if config.has_option("influx","influx"): self.influx = config.get("influx","influx")
        if config.has_option("influx","influx2"): self.influx2 = config.get("influx","influx2")
        if config.has_option("influx","dbname"): self.ifdbname = config.get("influx","dbname")
        if config.has_option("influx","ip"): self.ifip = config.get("influx","ip")
        if config.has_option("influx","port"): self.ifport = config.get("influx","port")
        if config.has_option("influx","user"): self.ifuser = config.get("influx","user")
        if config.has_option("influx","password"): self.ifpsw = config.get("influx","password")
        if config.has_option("influx","org"): self.iforg = config.get("influx","org")
        if config.has_option("influx","bucket"): self.ifbucket = config.get("influx","bucket")
        if config.has_option("influx","token"): self.iftoken = config.get("influx","token")
        #extensionINFLUX
        if config.has_option("extension","extension"): self.extension = config.get("extension","extension") 
        if config.has_option("extension","extname"): self.extname = config.get("extension","extname") 
        if config.has_option("extension","extvar"): self.extvar = eval(config.get("extension","extvar")) 
        
    def procenv(self): 
        print("\nGrott process environmental variables")
        if os.getenv('gmode') in ("sniff", "proxy") :  self.mode = os.getenv('gmode')
        if os.getenv('gverbose') != None :  self.verbose = os.getenv('verbose')
        if os.getenv('gminrecl') != None : 
            if 0 <= int(os.getenv('gminrecl')) <= 255  :     self.minrecl = os.getenv('gminrecl')
        if os.getenv('gdecrypt') != None : self.decrypt = os.getenv('gdecrypt') 
        if os.getenv('gcompat') != None :  self.compat = os.getenv('gcompat')
        if os.getenv('gblockcmd') != None : self.blockcmd = os.getenv('gblockcmd')
        if os.getenv('gnoipf') != None : self.noipf = os.getenv('gnoipf')     
        if os.getenv('gtime') in ("auto", "server") : self.gtime = os.getenv('gtime')   
        if os.getenv('gtimezone') != None : self.tmzone = os.getenv('gtimezone')   
        if os.getenv('gsendbuf') != None : self.sendbuf = os.getenv('gsendbuf')   
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
        #handle mqtt environmentals    
        if os.getenv('gnomqtt') != None :  self.nomqtt = os.getenv('gnomqtt')    
        if os.getenv('gmqttip') != None :    
            try: 
                ipaddress.ip_address(os.getenv('gmqttip'))
                self.mqttip = os.getenv('gmqttip') 
            except: 
                if self.verbose : print("\nGrott MQTT server IP address env invalid")
        if os.getenv('gmqttport') != None :     
            if 0 <= int(os.getenv('gmqttport')) <= 65535  :  self.mqttport = os.getenv('gmqttport')
        if os.getenv('gmqttauth') != None :  self.mqttauth = os.getenv('gmqttauth')
        if os.getenv('gmqtttopic') != None :  self.mqtttopic = os.getenv('gmqtttopic')
        if os.getenv('gmqttuser') != None :  self.mqttuser = os.getenv('gmqttuser')
        if os.getenv('gmqttpassword') != None : self.mqttpsw = os.getenv('gmqttpassword')
        #Handle PVOutput variables
        if os.getenv('gpvoutput') != None :  self.pvoutput = os.getenv('gpvoutput') 
        if os.getenv('gpvapikey') != None :  self.pvapikey = os.getenv('gpvapikey')   
        if os.getenv('gpvinverters') != None :  self.pvinverters = int(os.getenv('gpvinverters'))    
        for x in range(self.pvinverters+1) : 
                if os.getenv('gpvsystemid'+str(x)) != None :  self.pvsystemid[x] = os.getenv('gpvsystemid'+ str(x))
                if os.getenv('gpvinverterid'+str(x)) != None :  self.pvinverterid[x] = os.getenv('gpvinverterid'+ str(x))
        if self.pvinverters == 1 : 
            if os.getenv('gpvsystemid') != None :  self.pvsystemid[1] = os.getenv('gpvsystemid')   
        #Handle Influx
        if os.getenv('ginflux') != None :  self.influx = os.getenv('ginflux') 
        if os.getenv('ginflux2') != None :  self.influx2 = os.getenv('ginflux2') 
        if os.getenv('gifdbname') != None :  self.ifdbname = os.getenv('gifdbname') 
        if os.getenv('gifip') != None :  self.ifip = os.getenv('gifip') 
        if os.getenv('gifport') != None :  self.ifport = os.getenv('gifport') 
        if os.getenv('gifuser') != None :  self.ifuser = os.getenv('gifuser') 
        if os.getenv('gifpassword') != None :  self.ifpsw = os.getenv('gifpassword') 
        if os.getenv('giforg') != None :  self.iforg = os.getenv('giforg') 
        if os.getenv('gifbucket') != None :  self.ifbucket = os.getenv('gifbucket') 
        if os.getenv('giftoken') != None :  self.iftoken = os.getenv('giftoken') 
        #Handle Extension
        if os.getenv('gextension') != None :  self.extension = os.getenv('gextension') 
        if os.getenv('gextname') != None :  self.extname = os.getenv('gextname') 
        if os.getenv('gextvar') != None :  self.extvar = eval(os.getenv('gextvar'))
        
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
        
        self.recorddict1 = {"T02NNNN": {
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
            "pvipmtemperature"  : 242,        
            } } 

        self.recorddict2 = {"T05NNNN": {
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
        
        self.recorddict4 = {"T05NNNNX": {
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
            "pvpowerout"        : 170,        
            "pvfrequentie"      : 178,        
            "pvgridvoltage"     : 182,        
            "pvenergytoday"     : 274,         
            "pvenergytotal"     : 282,         
            "pvtemperature"     : 450,         
            "pvipmtemperature"  : 454,         
            } }   

        self.recorddict3 = {"T06NNNN": {
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

        self.recorddict5 = {"T06NNNNX": {
            "decrypt"           : "True",
            "pvserial"          : 76,
            "date"              : 126,
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

        self.recorddict.update(self.recorddict1)
        self.recorddict.update(self.recorddict2)
        self.recorddict.update(self.recorddict3)
        self.recorddict.update(self.recorddict4)
        self.recorddict.update(self.recorddict5)       

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

