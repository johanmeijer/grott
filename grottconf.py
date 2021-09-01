#
# grottconf  process command parameter and settings file
# Updated: 2021-09-01 
# Version 2.6.1a

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
        self.invtype = "default"                                                                    #specify sepcial invertype default (spf, sph)
        self.includeall = False                                                                      #Include all defined keys from layout (also incl = no)
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
                self.influxclient = InfluxDBClient(url="{}:{}".format(self.ifip, self.ifport),org=self.iforg, token=self.iftoken)
                
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
                        print("\t - " + "influxDB organization", self.iforg, "not defined or no authorisation to check")  
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
        print("\tinvtype:     \t",self.invtype)
        print("\tinclude_all: \t",self.includeall)
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
        self.includeall = str2bool(self.includeall)
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
        if config.has_option("Generic","includeall"): self.includeall = config.getboolean("Generic","includeall")
        if config.has_option("Generic","invtype"): self.invtype = config.get("Generic","invtype")
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
        if config.has_option("influx","port"): self.ifport = int(config.get("influx","port"))
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
        if os.getenv('gincludeall') != None :  self.includeall = os.getenv('gincludeall')
        if os.getenv('ginvtype') != None :  self.invtype = os.getenv('ginvtype')
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
            if 0 <= int(os.getenv('ggrowattport')) <= 65535  :  self.growattport = int(os.getenv('ggrowattport'))
            else : 
               if self.verbose : print("\nGrott Growatt server Port address env invalid")   
        #handle mqtt environmentals    
        if os.getenv('gnomqtt') != None :  self.nomqtt = os.getenv('gnomqtt')    
        if os.getenv('gmqttip') != None :    
            try: 
                ipaddress.ip_address(os.getenv('gmqttip'))
                self.mqttip = os.getenv('gmqttip') 
            except: 
                if self.verbose : print("\nGrott MQTT server IP address env invalid")
        if os.getenv('gmqttport') != None :     
            if 0 <= int(os.getenv('gmqttport')) <= 65535  :  self.mqttport = int(os.getenv('gmqttport'))
            else : 
                if self.verbose : print("\nGrott MQTT server Port address env invalid")
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
        if os.getenv('gifip') != None :    
            try: 
                ipaddress.ip_address(os.getenv('gifip'))
                self.ifip = os.getenv('gifip') 
            except: 
                if self.verbose : print("\nGrott InfluxDB server IP address env invalid")
        if os.getenv('gifport') != None :     
            if 0 <= int(os.getenv('gifport')) <= 65535  :  self.ifport = int(os.getenv('gifport'))
            else : 
                if self.verbose : print("\nGrott InfluxDB server Port address env invalid")      
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
                         "0120",                                    #Smart Monitor Record
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
            "decrypt"           : {"value" :"False"},
            "pvserial"          : {"value" :36, "length" : 10, "type" : "text", "divide" : 10},
            "date"              : {"value" :56, "divide" : 10}, 
            "recortype1"        : {"value" :70, "length" : 2, "type" : "num","incl" : "no"}, 
            "recortype2"        : {"value" :74, "length" : 2, "type" : "num","incl" : "no"}, 
            "pvstatus"          : {"value" :78, "length" : 2, "type" : "num"},  
            "pvpowerin"         : {"value" :82, "length" : 4, "type" : "num", "divide" : 10},        
            "pv1voltage"        : {"value" :90, "length" : 2, "type" : "num", "divide" : 10},        
            "pv1current"        : {"value" :94, "length" : 2, "type" : "num", "divide" : 10},                        
            "pv1watt"           : {"value" :98, "length" : 4, "type" : "num", "divide" : 10},                      
            "pv2voltage"        : {"value" :106, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2current"        : {"value" :110, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2watt"           : {"value" :114, "length" : 4, "type" : "num", "divide" : 10},                
            "pvpowerout"        : {"value" :122, "length" : 4, "type" : "num", "divide" : 10},                
            "pvfrequentie"      : {"value" :130, "length" : 2, "type" : "num", "divide" : 100},                
            "pvgridvoltage"     : {"value" :134, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent"     : {"value" :138, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower"       : {"value" :142, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage2"    : {"value" :150, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent2"    : {"value" :154, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower2"      : {"value" :158, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage3"    : {"value" :166, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent3"    : {"value" :170, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower3"      : {"value" :174, "length" : 4, "type" : "num", "divide" : 10},                
            "pvenergytoday"     : {"value" :182, "length" : 4, "type" : "num", "divide" : 10},                  
            "pvenergytotal"     : {"value" :190, "length" : 4, "type" : "num", "divide" : 10},
            "totworktime"       : {"value" :198, "length" : 4, "type" : "num", "divide" : 7200},         
            "pvtemperature"     : {"value" :206, "length" : 2, "type" : "num", "divide" : 10},                 
            "isof"              : {"value" :210, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "gfcif"             : {"value" :214, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "dcif"              : {"value" :218, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "vpvfault"          : {"value" :222, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "vacfault"          : {"value" :226, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "facfault"          : {"value" :230, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "tmpfault"          : {"value" :234, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "faultcode"         : {"value" :238, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "pvipmtemperature"  : {"value" :242, "length" : 2, "type" : "num", "divide" : 10},          
            "pbusvolt"          : {"value" :246, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},                  
            "nbusvolt"          : {"value" :250, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},                
            "epv1today"         : {"value" :278, "length" : 4, "type" : "num", "divide" : 10},                
            "epv1total"         : {"value" :286, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2today"         : {"value" :294, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2total"         : {"value" :302, "length" : 4, "type" : "num", "divide" : 10},                
            "epvtotal"          : {"value" :310, "length" : 4, "type" : "num", "divide" : 10},                
            "rac"               : {"value" :318, "length" : 4, "type" : "num", "divide" : 1,"incl" : "no"},                
            "eractoday"         : {"value" :326, "length" : 4, "type" : "num", "divide" : 1,"incl" : "no"},                
            "eractotal"         : {"value" :334, "length" : 4, "type" : "num", "divide" : 1,"incl" : "no"} 
            } } 

        self.recorddict2 = {"T05NNNN": {
            "decrypt"           : {"value" :"True"},
            "pvserial"          : {"value" :36, "length" : 10, "type" : "text", "divide" : 10},
            "date"              : {"value" :56, "divide" : 10}, 
            "recortype1"        : {"value" :70, "length" : 2, "type" : "num","incl" : "no"}, 
            "recortype2"        : {"value" :74, "length" : 2, "type" : "num","incl" : "no"}, 
            "pvstatus"          : {"value" :78, "length" : 2, "type" : "num"},  
            "pvpowerin"         : {"value" :82, "length" : 4, "type" : "num", "divide" : 10},        
            "pv1voltage"        : {"value" :90, "length" : 2, "type" : "num", "divide" : 10},        
            "pv1current"        : {"value" :94, "length" : 2, "type" : "num", "divide" : 10},                        
            "pv1watt"           : {"value" :98, "length" : 4, "type" : "num", "divide" : 10},                      
            "pv2voltage"        : {"value" :106, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2current"        : {"value" :110, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2watt"           : {"value" :114, "length" : 4, "type" : "num", "divide" : 10},                
            "pvpowerout"        : {"value" :122, "length" : 4, "type" : "numx", "divide" : 10},                
            "pvfrequentie"      : {"value" :130, "length" : 2, "type" : "num", "divide" : 100},                
            "pvgridvoltage"     : {"value" :134, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent"     : {"value" :138, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower"       : {"value" :142, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage2"    : {"value" :150, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent2"    : {"value" :154, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower2"      : {"value" :158, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage3"    : {"value" :166, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent3"    : {"value" :170, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower3"      : {"value" :174, "length" : 4, "type" : "num", "divide" : 10},                
            "pvenergytoday"     : {"value" :182, "length" : 4, "type" : "num", "divide" : 10},                  
            "pvenergytotal"     : {"value" :190, "length" : 4, "type" : "num", "divide" : 10},
            "totworktime"       : {"value" :198, "length" : 4, "type" : "num", "divide" : 7200},         
            "pvtemperature"     : {"value" :206, "length" : 2, "type" : "num", "divide" : 10},                 
            "isof"              : {"value" :210, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "gfcif"             : {"value" :214, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "dcif"              : {"value" :218, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "vpvfault"          : {"value" :222, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "vacfault"          : {"value" :226, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "facfault"          : {"value" :230, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "tmpfault"          : {"value" :234, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "faultcode"         : {"value" :238, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "pvipmtemperature"  : {"value" :242, "length" : 2, "type" : "num", "divide" : 10},          
            "pbusvolt"          : {"value" :246, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},                  
            "nbusvolt"          : {"value" :250, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},                
            "epv1today"         : {"value" :278, "length" : 4, "type" : "num", "divide" : 10},                
            "epv1total"         : {"value" :286, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2today"         : {"value" :294, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2total"         : {"value" :302, "length" : 4, "type" : "num", "divide" : 10},                
            "epvtotal"          : {"value" :310, "length" : 4, "type" : "num", "divide" : 10},                
            "rac"               : {"value" :318, "length" : 4, "type" : "num", "divide" : 1,"incl" : "no"},                
            "eractoday"         : {"value" :326, "length" : 4, "type" : "num", "divide" : 1,"incl" : "no"},                
            "eractotal"         : {"value" :334, "length" : 4, "type" : "num", "divide" : 1,"incl" : "no"}  
            } } 
        
        self.recorddict4 = {"T05NNNNX": {
            "decrypt"           : {"value" :"True"},
            "pvserial"          : {"value" :36, "length" : 10, "type" : "text", "divide" : 10},
            "date"              : {"value" :56, "divide" : 10}, 
            "recortype1"        : {"value" :70, "length" : 2, "type" : "num","incl" : "no"}, 
            "recortype2"        : {"value" :74, "length" : 2, "type" : "num","incl" : "no"}, 
            "pvstatus"          : {"value" :78, "length" : 2, "type" : "num"},  
            "pvpowerin"         : {"value" :82, "length" : 4, "type" : "num", "divide" : 10},        
            "pv1voltage"        : {"value" :90, "length" : 2, "type" : "num", "divide" : 10},        
            "pv1current"        : {"value" :94, "length" : 2, "type" : "num", "divide" : 10},                        
            "pv1watt"           : {"value" :98, "length" : 4, "type" : "num", "divide" : 10},                      
            "pv2voltage"        : {"value" :106, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2current"        : {"value" :110, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2watt"           : {"value" :114, "length" : 4, "type" : "num", "divide" : 10},                
            "pvpowerout"        : {"value" :170, "length" : 4, "type" : "numx", "divide" : 10},                
            "pvfrequentie"      : {"value" :178, "length" : 2, "type" : "num", "divide" : 100},                
            "pvgridvoltage"     : {"value" :182, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent"     : {"value" :186, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower"       : {"value" :190, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage2"    : {"value" :198, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent2"    : {"value" :202, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower2"      : {"value" :206, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage3"    : {"value" :214, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent3"    : {"value" :218, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower3"      : {"value" :222, "length" : 4, "type" : "num", "divide" : 10},  
            "totworktime"       : {"value" :266, "length" : 4, "type" : "num", "divide" : 7200},
            "pvenergytoday"     : {"value" :274, "length" : 4, "type" : "num", "divide" : 10},                  
            "pvenergytotal"     : {"value" :282, "length" : 4, "type" : "num", "divide" : 10},
            "epvtotal"          : {"value" :290, "length" : 4, "type" : "num", "divide" : 10},
            "epv1today"         : {"value" :298, "length" : 4, "type" : "num", "divide" : 10},                
            "epv1total"         : {"value" :306, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2today"         : {"value" :314, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2total"         : {"value" :322, "length" : 4, "type" : "num", "divide" : 10},                           
            "pvtemperature"     : {"value" :450, "length" : 2, "type" : "num", "divide" : 10},                 
            "pvipmtemperature"  : {"value" :466, "length" : 2, "type" : "num", "divide" : 10},          
            "pbusvolt"          : {"value" :470, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},                  
            "nbusvolt"          : {"value" :474, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"}  
            } }   
            
        self.recorddict3 = {"T06NNNN": {
            "decrypt"           : {"value" :"True"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text", "divide" : 10},
            "date"              : {"value" :136, "divide" : 10}, 
            "recortype1"        : {"value" :150, "length" : 2, "type" : "num","incl" : "no"}, 
            "recortype2"        : {"value" :154, "length" : 2, "type" : "num","incl" : "no"}, 
            "pvstatus"          : {"value" :158, "length" : 2, "type" : "num"},  
            "pvpowerin"         : {"value" :162, "length" : 4, "type" : "num", "divide" : 10},        
            "pv1voltage"        : {"value" :170, "length" : 2, "type" : "num", "divide" : 10},        
            "pv1current"        : {"value" :174, "length" : 2, "type" : "num", "divide" : 10},                        
            "pv1watt"           : {"value" :178, "length" : 4, "type" : "num", "divide" : 10},                      
            "pv2voltage"        : {"value" :186, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2current"        : {"value" :190, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2watt"           : {"value" :194, "length" : 4, "type" : "num", "divide" : 10},                
            "pvpowerout"        : {"value" :202, "length" : 4, "type" : "numx", "divide" : 10},                
            "pvfrequentie"      : {"value" :210, "length" : 2, "type" : "num", "divide" : 100},                
            "pvgridvoltage"     : {"value" :214, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent"     : {"value" :218, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower"       : {"value" :222, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage2"    : {"value" :230, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent2"    : {"value" :234, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower2"      : {"value" :238, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage3"    : {"value" :246, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent3"    : {"value" :250, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower3"      : {"value" :254, "length" : 4, "type" : "num", "divide" : 10},                
            "pvenergytoday"     : {"value" :262, "length" : 4, "type" : "num", "divide" : 10},                  
            "pvenergytotal"     : {"value" :270, "length" : 4, "type" : "num", "divide" : 10},
            "totworktime"       : {"value" :278, "length" : 4, "type" : "num", "divide" : 7200},         
            "pvtemperature"     : {"value" :286, "length" : 2, "type" : "num", "divide" : 10},                 
            "isof"              : {"value" :290, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "gfcif"             : {"value" :294, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "dcif"              : {"value" :298, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "vpvfault"          : {"value" :302, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "vacfault"          : {"value" :306, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "facfault"          : {"value" :310, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "tmpfault"          : {"value" :314, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "faultcode"         : {"value" :318, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},                
            "pvipmtemperature"  : {"value" :322, "length" : 2, "type" : "num", "divide" : 10},          
            "pbusvolt"          : {"value" :326, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},                  
            "nbusvolt"          : {"value" :330, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},                
            "epv1today"         : {"value" :358, "length" : 4, "type" : "num", "divide" : 10},                
            "epv1total"         : {"value" :366, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2today"         : {"value" :374, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2total"         : {"value" :382, "length" : 4, "type" : "num", "divide" : 10},                
            "epvtotal"          : {"value" :390, "length" : 4, "type" : "num", "divide" : 10},      
            } } 

        self.recorddict5 = {"T06NNNNX": {
            "decrypt"           : {"value" :"True"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "divide" : 10,"incl" : "no"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text", "divide" : 10},
            "date"              : {"value" :136, "divide" : 10}, 
            "recortype1"        : {"value" :150, "length" : 2, "type" : "num","incl" : "no"}, 
            "recortype2"        : {"value" :154, "length" : 2, "type" : "num","incl" : "no"}, 
            "pvstatus"          : {"value" :158, "length" : 2, "type" : "num"},  
            "pvpowerin"         : {"value" :162, "length" : 4, "type" : "num", "divide" : 10},        
            "pv1voltage"        : {"value" :170, "length" : 2, "type" : "num", "divide" : 10},        
            "pv1current"        : {"value" :174, "length" : 2, "type" : "num", "divide" : 10},                        
            "pv1watt"           : {"value" :178, "length" : 4, "type" : "num", "divide" : 10},                      
            "pv2voltage"        : {"value" :186, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2current"        : {"value" :190, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2watt"           : {"value" :194, "length" : 4, "type" : "num", "divide" : 10},                
            "pvpowerout"        : {"value" :250, "length" : 4, "type" : "numx", "divide" : 10},                
            "pvfrequentie"      : {"value" :258, "length" : 2, "type" : "num", "divide" : 100},                
            "pvgridvoltage"     : {"value" :262, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent"     : {"value" :266, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower"       : {"value" :270, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage2"    : {"value" :278, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent2"    : {"value" :282, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower2"      : {"value" :286, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage3"    : {"value" :294, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent3"    : {"value" :298, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower3"      : {"value" :302, "length" : 4, "type" : "num", "divide" : 10},  
            "totworktime"       : {"value" :346, "length" : 4, "type" : "num", "divide" : 7200},
            "pvenergytoday"     : {"value" :354, "length" : 4, "type" : "num", "divide" : 10},                  
            "pvenergytotal"     : {"value" :362, "length" : 4, "type" : "num", "divide" : 10},
            "epvtotal"          : {"value" :370, "length" : 4, "type" : "num", "divide" : 10},
            "epv1today"         : {"value" :378, "length" : 4, "type" : "num", "divide" : 10},                
            "epv1total"         : {"value" :386, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2today"         : {"value" :394, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2total"         : {"value" :402, "length" : 4, "type" : "num", "divide" : 10},                           
            "pvtemperature"     : {"value" :530, "length" : 2, "type" : "num", "divide" : 10},                 
            "pvipmtemperature"  : {"value" :546, "length" : 2, "type" : "num", "divide" : 10},          
            "pbusvolt"          : {"value" :550, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},                  
            "nbusvolt"          : {"value" :554, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"}    
            } }     

        self.recorddict6 = {"T06NNNNXSPH": {
            "decrypt"           : {"value" :"True"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text", "divide" : 10},
            "date"              : {"value" :136, "divide" : 10}, 
            "recortype1"        : {"value" :150, "length" : 2, "type" : "num","incl" : "no"}, 
            "recortype2"        : {"value" :154, "length" : 2, "type" : "num","incl" : "no"}, 
            "pvstatus"          : {"value" :158, "length" : 2, "type" : "num"},  
            "pvpowerin"         : {"value" :162, "length" : 4, "type" : "num", "divide" : 10},        
            "pv1voltage"        : {"value" :170, "length" : 2, "type" : "num", "divide" : 10},        
            "pv1current"        : {"value" :174, "length" : 2, "type" : "num", "divide" : 10},                        
            "pv1watt"           : {"value" :178, "length" : 4, "type" : "num", "divide" : 10},                      
            "pv2voltage"        : {"value" :186, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2current"        : {"value" :190, "length" : 2, "type" : "num", "divide" : 10},                
            "pv2watt"           : {"value" :194, "length" : 4, "type" : "num", "divide" : 10},                
            "pvpowerout"        : {"value" :298, "length" : 4, "type" : "numx", "divide" : 10},                
            "pvfrequentie"      : {"value" :306, "length" : 2, "type" : "num", "divide" : 100},                
            "pvgridvoltage"     : {"value" :310, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent"     : {"value" :314, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower"       : {"value" :318, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage2"    : {"value" :326, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent2"    : {"value" :330, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower2"      : {"value" :334, "length" : 4, "type" : "num", "divide" : 10},                
            "pvgridvoltage3"    : {"value" :342, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridcurrent3"    : {"value" :346, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridpower3"      : {"value" :350, "length" : 4, "type" : "num", "divide" : 10},  
            "totworktime"       : {"value" :386, "length" : 4, "type" : "num", "divide" : 7200},
            "eactoday"          : {"value" :370, "length" : 4, "type" : "num", "divide" : 10}, 
            "pvenergytoday"     : {"value" :370, "length" : 4, "type" : "num", "divide" : 10},                  
            "eactotal"          : {"value" :378, "length" : 4, "type" : "num", "divide" : 10},
            "epvtotal"          : {"value" :522, "length" : 4, "type" : "num", "divide" : 10},
            "epv1today"         : {"value" :394, "length" : 4, "type" : "num", "divide" : 10},                
            "epv1total"         : {"value" :402, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2today"         : {"value" :410, "length" : 4, "type" : "num", "divide" : 10},                
            "epv2total"         : {"value" :418, "length" : 4, "type" : "num", "divide" : 10},                           
            "pvtemperature"     : {"value" :530, "length" : 2, "type" : "num", "divide" : 10},                 
            "pvipmtemperature"  : {"value" :534, "length" : 2, "type" : "num", "divide" : 10}, 
            "pvboosttemp"       : {"value" :538, "length" : 2, "type" : "num", "divide" : 10},                   
            "bat_dsp"           : {"value" :546, "length" : 2, "type" : "num", "divide" : 10},
            "pbusvolt"          : {"value" :550, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},                  
            "#nbusvolt"          : {"value" :554, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},  
            "#ipf"               : {"value" :558, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},
            "#realoppercent"     : {"value" :562, "length" : 2, "type" : "num", "divide" : 100,"incl" : "no"}, 
            "#opfullwatt"        : {"value" :566, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "#deratingmode"      : {"value" :574, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},
            "eacharge_today"     : {"value" :606, "length" : 4, "type" : "num", "divide" : 10}, 
            "eacharge_total"     : {"value" :614, "length" : 4, "type" : "num", "divide" : 10}, 
            "batterytype"        : {"value" :634, "length" : 2, "type" : "num", "divide" : 1}, 
            "uwsysworkmode"      : {"value" :666, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword0"   : {"value" :670, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword1"   : {"value" :674, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword2"   : {"value" :678, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword3"   : {"value" :682, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword4"   : {"value" :686, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword5"   : {"value" :690, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword6"   : {"value" :694, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword7"   : {"value" :698, "length" : 2, "type" : "num", "divide" : 1},
            "pdischarge1"        : {"value" :702, "length" : 4, "type" : "num", "divide" : 10}, 
            "p1charge1"          : {"value" :710, "length" : 4, "type" : "num", "divide" : 10}, 
            "vbat"               : {"value" :718, "length" : 2, "type" : "num", "divide" : 10}, 
            "SOC"                : {"value" :722, "length" : 2, "type" : "num", "divide" : 100}, 
            "pactouserr"         : {"value" :726, "length" : 4, "type" : "num", "divide" : 10}, 
            "#pactousers"        : {"value" :734, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"}, 
            "#pactousert"        : {"value" :742, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"}, 
            "pactousertot"       : {"value" :750, "length" : 4, "type" : "num", "divide" : 10},
            "pactogridr"         : {"value" :758, "length" : 4, "type" : "num", "divide" : 10}, 
            "#pactogrids"        : {"value" :766, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"}, 
            "#pactogridt"        : {"value" :774, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"}, 
            "pactogridtot"       : {"value" :782, "length" : 4, "type" : "num", "divide" : 10}, 
            "plocaloadr"         : {"value" :790, "length" : 4, "type" : "num", "divide" : 10}, 
            "#plocaloads"        : {"value" :798, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"}, 
            "#plocaloadt"        : {"value" :806, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"}, 
            "plocaloadtot"       : {"value" :814, "length" : 4, "type" : "num", "divide" : 10},   
            "#ipm"               : {"value" :822, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},   
            "#battemp"           : {"value" :826, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},   
            "spdspstatus"        : {"value" :830, "length" : 2, "type" : "num", "divide" : 10},   
            "spbusvolt"          : {"value" :834, "length" : 2, "type" : "num", "divide" : 10},
            "etouser_tod"        : {"value" :842, "length" : 4, "type" : "num", "divide" : 10}, 
            "etouser_tot"        : {"value" :850, "length" : 4, "type" : "num", "divide" : 10}, 
            "etogrid_tod"        : {"value" :858, "length" : 4, "type" : "num", "divide" : 10}, 
            "etogrid_tot"      : {"value" :866, "length" : 4, "type" : "num", "divide" : 10},
            "edischarge1_tod"  : {"value" :874, "length" : 4, "type" : "num", "divide" : 10}, 
            "edischarge1_tot"  : {"value" :882, "length" : 4, "type" : "num", "divide" : 10}, 
            "eharge1_tod"      : {"value" :890, "length" : 4, "type" : "num", "divide" : 10}, 
            "eharge1_tot"      : {"value" :898, "length" : 4, "type" : "num", "divide" : 10}, 
            "elocalload_tod"  : {"value" :906, "length" : 4, "type" : "num", "divide" : 10}, 
            "elocalload_tot"  : {"value" :914, "length" : 4, "type" : "num", "divide" : 10} 
        } }

        self.recorddict7 = {"T05NNNNSPF": {
            "decrypt"           : {"value" :"True"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "divide" : 10,"incl" : "no"},
            "pvserial"          : {"value" :36, "length" : 10, "type" : "text", "divide" : 10},
            "date"              : {"value" :56, "divide" : 10}, 
            "recortype1"        : {"value" :70, "length" : 2, "type" : "num","incl" : "no"}, 
            "recortype2"        : {"value" :74, "length" : 2, "type" : "num","incl" : "no"}, 
            "pvstatus"          : {"value" :78, "length" : 2, "type" : "num"},  
            "vpv1"              : {"value" :82, "length" : 2, "type" : "num", "divide" : 10},        
            "vpv2"              : {"value" :86, "length" : 2, "type" : "num", "divide" : 10},        
            "ppv1"              : {"value" :90, "length" : 4, "type" : "num", "divide" : 10},                        
            "ppv2"              : {"value" :98, "length" : 4, "type" : "num", "divide" : 10},                      
            "buck1curr"         : {"value" :106, "length" : 2, "type" : "num", "divide" : 10},                
            "buck2curr"         : {"value" :110, "length" : 2, "type" : "num", "divide" : 10},                
            "op_watt"           : {"value" :114, "length" : 4, "type" : "num", "divide" : 10},                
            "pvpowerout"        : {"value" :114, "length" : 4, "type" : "num", "divide" : 10},               
            "op_va"             : {"value" :122, "length" : 4, "type" : "num", "divide" : 10},                
            "acchr_watt"        : {"value" :130, "length" : 4, "type" : "num", "divide" : 10},                
            "acchr_VA"          : {"value" :138, "length" : 4, "type" : "num", "divide" : 10},                
            "bat_Volt"          : {"value" :146, "length" : 2, "type" : "num", "divide" : 100},                
            "batterySoc"        : {"value" :150, "length" : 2, "type" : "num", "divide" : 1},                
            "bus_volt"          : {"value" :154, "length" : 2, "type" : "num", "divide" : 10},                
            "grid_volt"         : {"value" :158, "length" : 2, "type" : "num", "divide" : 10},                
            "line_freq"         : {"value" :162, "length" : 2, "type" : "num", "divide" : 100},                
            "outputvolt"        : {"value" :166, "length" : 2, "type" : "num", "divide" : 10},                
            "pvgridvoltage"     : {"value" :166, "length" : 2, "type" : "num", "divide" : 10},                          
            "outputfreq"        : {"value" :170, "length" : 2, "type" : "num", "divide" : 100},                
            "invtemp"           : {"value" :178, "length" : 2, "type" : "num", "divide" : 10},                  
            "dcdctemp"          : {"value" :182, "length" : 2, "type" : "num", "divide" : 10},
            "loadpercent"       : {"value" :186, "length" : 2, "type" : "num", "divide" : 10},                
            "buck1_ntc"         : {"value" :206, "length" : 2, "type" : "num", "divide" : 10},                
            "buck2_ntc"         : {"value" :210, "length" : 2, "type" : "num", "divide" : 10},                
            "OP_Curr"           : {"value" :214, "length" : 2, "type" : "num", "divide" : 10},                
            "Inv_Curr"          : {"value" :218, "length" : 2, "type" : "num", "divide" : 10},               
            "AC_InWatt"         : {"value" :222, "length" : 4, "type" : "num", "divide" : 10},                
            "AC_InVA"           : {"value" :230, "length" : 4, "type" : "num", "divide" : 10},                
            "faultBit"          : {"value" :238, "length" : 2, "type" : "num", "divide" : 1},                
            "warningBit"        : {"value" :242, "length" : 2, "type" : "num", "divide" : 1},                
            "faultValue"        : {"value" :246, "length" : 2, "type" : "num", "divide" : 1},                
            "warningValue"      : {"value" :250, "length" : 2, "type" : "num", "divide" : 1},                
            "constantPowerOK"   : {"value" :266, "length" : 2, "type" : "num", "divide" : 1},                
            "epvtoday"          : {"value" :274, "length" : 4, "type" : "num", "divide" : 10},                
            "pvenergytoday"     : {"value" :274, "length" : 4, "type" : "num", "divide" : 10}, 
            "epvtotal"          : {"value" :282, "length" : 4, "type" : "num", "divide" : 10}, 
            "eacCharToday"      : {"value" :310, "length" : 4, "type" : "num", "divide" : 10},    
            "eacCharTotal"      : {"value" :318, "length" : 4, "type" : "num", "divide" : 10},  
            "ebatDischarToday"  : {"value" :326, "length" : 4, "type" : "num", "divide" : 10},  
            "ebatDischarTotal"  : {"value" :334, "length" : 4, "type" : "num", "divide" : 10},  
            "eacDischarToday"   : {"value" :342, "length" : 4, "type" : "num", "divide" : 10},  
            "eacDischarTotal"   : {"value" :350, "length" : 4, "type" : "num", "divide" : 10},  
            "ACCharCurr"        : {"value" :358, "length" : 2, "type" : "num", "divide" : 10},  
            "ACDischarWatt"     : {"value" :362, "length" : 4, "type" : "num", "divide" : 10},  
            "ACDischarVA"       : {"value" :370, "length" : 4, "type" : "num", "divide" : 10},  
            "BatDischarWatt"    : {"value" :378, "length" : 4, "type" : "num", "divide" : 10},  
            "BatDischarVA"      : {"value" :386, "length" : 4, "type" : "num", "divide" : 10},  
            "BatWatt"           : {"value" :394, "length" : 4, "type" : "numx", "divide" : 10}                                                 
        } }            

        self.recorddict8 = {"T06NNNNSPF": {
            "decrypt"           : {"value" :"True"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "divide" : 10},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text", "divide" : 10},
            "date"              : {"value" :136, "divide" : 10}, 
            "recortype1"        : {"value" :150, "length" : 2, "type" : "num","incl" : "no"}, 
            "recortype2"        : {"value" :154, "length" : 2, "type" : "num","incl" : "no"}, 
            "pvstatus"          : {"value" :158, "length" : 2, "type" : "num"},  
            "vpv1"              : {"value" :162, "length" : 2, "type" : "num", "divide" : 10},        
            "vpv2"              : {"value" :166, "length" : 2, "type" : "num", "divide" : 10},        
            "ppv1"              : {"value" :170, "length" : 4, "type" : "num", "divide" : 10},                        
            "ppv2"              : {"value" :178, "length" : 4, "type" : "num", "divide" : 10},                      
            "buck1curr"         : {"value" :186, "length" : 2, "type" : "num", "divide" : 10},                
            "buck2curr"         : {"value" :190, "length" : 2, "type" : "num", "divide" : 10},                
            "op_watt"           : {"value" :194, "length" : 4, "type" : "num", "divide" : 10},                
            "pvpowerout"        : {"value" :194, "length" : 4, "type" : "num", "divide" : 10},               
            "op_va"             : {"value" :204, "length" : 4, "type" : "num", "divide" : 10},                
            "acchr_watt"        : {"value" :210, "length" : 4, "type" : "num", "divide" : 10},                
            "acchr_VA"          : {"value" :218, "length" : 4, "type" : "num", "divide" : 10},                
            "bat_Volt"          : {"value" :226, "length" : 2, "type" : "num", "divide" : 100},                
            "batterySoc"        : {"value" :230, "length" : 2, "type" : "num", "divide" : 1},                
            "bus_volt"          : {"value" :234, "length" : 2, "type" : "num", "divide" : 10},                
            "grid_volt"         : {"value" :238, "length" : 2, "type" : "num", "divide" : 10},                
            "line_freq"         : {"value" :242, "length" : 2, "type" : "num", "divide" : 100},                
            "outputvolt"        : {"value" :246, "length" : 2, "type" : "num", "divide" : 10},      
            "pvgridvoltage"     : {"value" :246, "length" : 2, "type" : "num", "divide" : 10},                          
            "outputfreq"        : {"value" :250, "length" : 2, "type" : "num", "divide" : 100},                
            "invtemp"           : {"value" :258, "length" : 2, "type" : "num", "divide" : 10},                  
            "dcdctemp"          : {"value" :262, "length" : 2, "type" : "num", "divide" : 10},
            "loadpercent"       : {"value" :266, "length" : 2, "type" : "num", "divide" : 10},                
            "buck1_ntc"         : {"value" :286, "length" : 2, "type" : "num", "divide" : 10},                
            "buck2_ntc"         : {"value" :290, "length" : 2, "type" : "num", "divide" : 10},                
            "OP_Curr"           : {"value" :294, "length" : 2, "type" : "num", "divide" : 10},                
            "Inv_Curr"          : {"value" :298, "length" : 2, "type" : "num", "divide" : 10},               
            "AC_InWatt"         : {"value" :302, "length" : 4, "type" : "num", "divide" : 10},                
            "AC_InVA"           : {"value" :310, "length" : 4, "type" : "num", "divide" : 10},                
            "faultBit"          : {"value" :318, "length" : 2, "type" : "num", "divide" : 1},                
            "warningBit"        : {"value" :322, "length" : 2, "type" : "num", "divide" : 1},                
            "faultValue"        : {"value" :326, "length" : 2, "type" : "num", "divide" : 1},                
            "warningValue"      : {"value" :330, "length" : 2, "type" : "num", "divide" : 1},                
            "constantPowerOK"   : {"value" :346, "length" : 2, "type" : "num", "divide" : 1},                
            "epvtoday"          : {"value" :358, "length" : 4, "type" : "num", "divide" : 10}, 
            "pvenergytoday"     : {"value" :358, "length" : 4, "type" : "num", "divide" : 10}, 
            "epvtotal"          : {"value" :366, "length" : 4, "type" : "num", "divide" : 10},                
            "eacCharToday"      : {"value" :390, "length" : 4, "type" : "num", "divide" : 10},    
            "eacCharTotal"      : {"value" :398, "length" : 4, "type" : "num", "divide" : 10},  
            "ebatDischarToday"  : {"value" :406, "length" : 4, "type" : "num", "divide" : 10},  
            "ebatDischarTotal"  : {"value" :414, "length" : 4, "type" : "num", "divide" : 10},  
            "eacDischarToday"   : {"value" :422, "length" : 4, "type" : "num", "divide" : 10},  
            "eacDischarTotal"   : {"value" :430, "length" : 4, "type" : "num", "divide" : 10},  
            "ACCharCurr"        : {"value" :438, "length" : 2, "type" : "num", "divide" : 10},  
            "ACDischarWatt"     : {"value" :442, "length" : 4, "type" : "num", "divide" : 10},  
            "ACDischarVA"       : {"value" :450, "length" : 4, "type" : "num", "divide" : 10},  
            "BatDischarWatt"    : {"value" :458, "length" : 4, "type" : "num", "divide" : 10},  
            "BatDischarVA"      : {"value" :466, "length" : 4, "type" : "num", "divide" : 10},  
            "BatWatt"           : {"value" :474, "length" : 4, "type" : "numx", "divide" : 10}                                                 
        }}

        self.recorddict9 = {"T060120": {
            "decrypt"           : {"value" :"True"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "divide" : 10},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text", "divide" : 10},
            "date"              : {"value" :136, "divide" : 10}, 
            "voltage_l1"        : {"value" :160, "length" : 4, "type" : "num", "divide" : 10},  
            "voltage_l2"        : {"value" :168, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},  
            "voltage_l3"        : {"value" :176, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},  
            "Current_l1"        : {"value" :184, "length" : 4, "type" : "num", "divide" : 10},
            "Current_l2"        : {"value" :192, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "Current_l3"        : {"value" :200, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},            
            "act_power_l1"      : {"value" :208, "length" : 4, "type" : "numx", "divide" : 10},        
            "act_power_l2"      : {"value" :216, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},        
            "act_power_l3"      : {"value" :224, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},        
            "app_power_l1"      : {"value" :232, "length" : 4, "type" : "numx", "divide" : 10},        
            "app_power_l2"      : {"value" :240, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},        
            "app_power_l3"      : {"value" :248, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},        
            "react_power_l1"    : {"value" :256, "length" : 4, "type" : "numx","divide" : 10},        
            "react_power_l2"    : {"value" :264, "length" : 4, "type" : "numx","divide" : 10,"incl" : "no"},        
            "react_power_l3"    : {"value" :272, "length" : 4, "type" : "numx","divide" : 10,"incl" : "no"},        
            "powerfactor_l1"    : {"value" :280, "length" : 4, "type" : "numx", "divide" : 1000},                      
            "powerfactor_l2"    : {"value" :288, "length" : 4, "type" : "numx", "divide" : 1000,"incl" : "no"},                      
            "powerfactor_l3"    : {"value" :296, "length" : 4, "type" : "numx", "divide" : 1000,"incl" : "no"},                      
            "pos_rev_act_power" : {"value" :304, "length" : 4, "type" : "numx", "divide" : 10}, 
            "pos_act_power"     : {"value" :304, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"}, 
            "rev_act_power"     : {"value" :304, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},
            "app_power"         : {"value" :312, "length" : 4, "type" : "numx", "divide" : 10}, 
            "react_power"       : {"value" :320, "length" : 4, "type" : "numx", "divide" : 10}, 
            "powerfactor"       : {"value" :328, "length" : 4, "type" : "numx", "divide" : 1000},   
            "frequency"         : {"value" :336, "length" : 4, "type" : "num", "divide" : 10},   
            "L1-2_voltage"      : {"value" :344, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"}, 
            "L2-3_voltage"      : {"value" :352, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},   
            "L3-1_voltage"      : {"value" :360, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},   
            "pos_act_energy"    : {"value" :368, "length" : 4, "type" : "numx", "divide" : 10},  
            "rev_act_energy"    : {"value" :376, "length" : 4, "type" : "numx", "divide" : 10},   
            "pos_act_energy_kvar" : {"value" :384, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},    
            "rev_act_energy_kvar" : {"value" :392, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},   
            "app_energy_kvar"   : {"value" :400, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},   
            "act_energy_kwh"    : {"value" :408, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},   
            "react_energy_kvar" : {"value" :416, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"}   
        }}

        self.recorddict.update(self.recorddict1)
        self.recorddict.update(self.recorddict2)
        self.recorddict.update(self.recorddict3)
        self.recorddict.update(self.recorddict4)
        self.recorddict.update(self.recorddict5)       
        self.recorddict.update(self.recorddict6)       
        self.recorddict.update(self.recorddict7)  
        self.recorddict.update(self.recorddict8) 
        self.recorddict.update(self.recorddict9)  

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

