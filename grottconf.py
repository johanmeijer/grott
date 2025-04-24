"""Grottconf setting the configuration environment (class Conf)"""
# grottconf  process command parameter and settings file
# Updated: 2024-12-08
import configparser, sys, argparse, os, json, io
import ipaddress
from os import walk
from grottdata import format_multi_line, str2bool
import logging
#set logging definities
#logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
vrmconf = "3.1.0_20250406"

class Conf :
    """define/proces grott configuration settings"""
    def __init__(self, vrm):
        """"Init Configuration"""
        logger.info("Config Processing Started")
        #Set parm's
        #prio: 1.Command line parms, 2.env. variables, 3.config file 4.program default
        #process command settings that set processing values (verbose, trace, output, config, nomqtt)
        # Set default for the command line parms
        self.verrel = vrm
        self.vrmconf = vrmconf
        self.vrmproxy = "nky"
        self.vrmsniff = "nky"
        self.vrmdata = "nky"
        self.vrmserver = "nky"
        self.verbose= False
        self.loglevel = "INFO"
        self.cfgfile = "grott.ini"
        self.parserinit()
        #Set default config:
        self.defaultconf()
        #Process config file
        self.procconf()
        #Process environmental variable
        self.procenv()
        #Process variables to override/correct  config and environmental settings
        self.confpost()
        self.resetdebuglevel()
        #print configuration
        self.print()
        #test print only info
        #self.print(["Info","Hardcoded"])

        #process not if in standalone mode
        if self.mode not in ["serversa"]:
            #prepare MQTT security
            if not self.mqttauth: self.pubauth = None
            else: self.pubauth = dict(username=self.mqttuser, password=self.mqttpsw)

            #define recordlayouts
            self.set_reclayouts()

            #define record whitlist (if blocking / filtering enabled
            self.set_recwl()

            #prepare influxDB
            if self.influx :
                returncc=self.procinflux()
                if returncc[0] == 0 : logger.info(returncc[1])
                elif returncc[0] > 4 :
                    logger.critical(returncc[1])
                    raise SystemExit()
                else :
                    self.influx = False
                    logger.warning("%s, Grott procesing will continue without InfluxDB", returncc[1])
                    #logger.warning(returncc[1] + ", Grott procesing will continue without InfluxDB")

    def defaultconf(self) :
        """set config defaults"""
        #define parameters dictionary :
        #format self.parm[parm] = {"type" : parmtype,"value": parmvalue, "environ" : environ_var/none, "show" : show,noshow]
        #use addparm(self,type,parm,value,environ=None,show=True) :
        self.parm = dict()
        #define parmtype / secyions in parmlib be aware hardcoded will be ignorded from parmlib
        self.parmtype = ["Info","Hardcoded","Generic","Growatt","Server","MQTT","PVOutput","influx","extension"]
        ###Set fixed variables (not changable with .ini or environmental variables)
        self.addparm("Info","verrel",self.verrel)
        self.addparm("Info","verrelconf",vrmconf)
        self.addparm("Info","verreldata",self.vrmdata)
        self.addparm("Info","verrelproxy",self.vrmproxy)
        self.addparm("Info","verrelsniff",self.vrmsniff)
        self.addparm("Info","verrelserver",self.vrmserver)
        #set changeable variables (in .ini or environmentals:
        #recordtypes for inverter data processing
        self.addparm("Hardcoded","datarec",["04","50"])
        #recordtypes for inverter data processing
        self.addparm("Hardcoded","smartmeterrec",["1b","20","1e"])
        #!depricated! minimal datarecord length that can be processed (no ack record!)
        self.addparm("Hardcoded","mindatarec",12)
         #3.0.0. invertid not changable anymore, only there for compatability
        self.addparm("Hardcoded","inverterid","automatic")
        #set standard sysout, can only be overwritten at startup
        self.addparm("Hardcoded","outfile","sys.stdout")
        ###Set default variables
        #3.0.0 not recommended use loglevel!
        self.addparm("Generic","verbose",self.verbose,"gverbose")
        #Standard python logging level: DEBUG,INFO,WARNING,ERROR,CRITICAL added DEBUGV (debug verbose+)
        self.addparm("Generic","loglevel",self.loglevel,"gloglevel")
        #config file can only be set via startup parameter
        self.addparm("Generic","cfgfile",self.cfgfile)
        #specify lower minrecl (e.g. minrecl = 1) to log / debug all records. minrecl = 100 will supress most of commincation records except data related records
        self.addparm("Generic","minrecl",100,"gminrecl")
        #specify invertype:  default (use standard tl-s type of inverters, automatic (>3.0.0, lets grott automatically detect),spf, sph, mod etc use specific invertypes)
        self.addparm("Generic","invtype","auto","ginvtype")
        #define invertype setting for multiple servers {"invertid" : "invtype", "invertid1" : "invtype1", }
        self.addparm("Generic","invtypemap","{}","ginvtypemap")
        #Include all defined keys from layout (also incl = no)
        self.addparm("Generic","includeall","False","gincludeall")
        #Block growatt inverter and Shine configure commands
        self.addparm("Generic","blockcmd","False","gblockcmd")
        #Allow IP change if needed (not recommend setting, only use this for short time)
        self.addparm("Generic","noipf",False,"gnoipf")
        #time used =  auto: use record time or if not valid server time, alternative server: use always server time 3.0.0 renamed conf.gtime to conf.time gtime set for compat reasons.
        self.addparm("Generic","gtime","auto","gtime")
        self.addparm("Generic","time","auto","gtime")
        # enable / disable sending historical data from buffer
        self.addparm("Generic","sendbuf",True,"gsendbuf")
        #set defaultmode
        self.addparm("Generic","mode","proxy","gmode")
        #set default grott port
        self.addparm("Generic","grottport",5279,"grottport")
        #set default grott ip
        self.addparm("Generic","grottip","default","ggrottip")
        #set timezone (at this moment only used for influxdb)
        self.addparm("Generic","tmzone","local","gtmzone")
        ### Growatt settings
        # self.growattip = "server.growatt.com"
        # For China:                     server-cn.growatt.com
        # For US:                        server-us.growatt.com
        # For Australia and New Zealand: server-au.growatt.com
        self.addparm("Growatt","growattip","server.growatt.com", "ggrowattip")
        self.addparm("Growatt","growattport",5279,"ggrowattport")
        ### Grottserver settings
        self.addparm("Server","serverip","0.0.0.0","gserverip")
        self.addparm("Server","serverport",5781,"gserverport")
        # pass data to growatt
        self.addparm("Server","serverpassthrough",False,"gserverpassthrough")
        #httpserver
        self.addparm("Server","httpport",5782,"ghttpport")
        #Time to sleep waiting on API response
        self.addparm("Server","apirespwait",0.5,"gapirespwait")
        #Totaal time in seconds to wait on Inverter Response
        self.addparm("Server","inverterrespwait",10,"ginverterrespwait")
        #Totaal time in seconds to wait on Datalogger Response
        self.addparm("Server","dataloggerrespwait",5,"gdataloggerrespwait")
        #Totaal time in seconds to wait before a inactive session will be closed
        self.addparm("Server","ConnectionTimeout",200,"gConnectionTimeout")

        #MQTT Basic settings
        ##self.nomqtt = False
        self.addparm("MQTT","nomqtt",False,"gnomqtt")
        ##self.mqttip = "localhost"
        self.addparm("MQTT","mqttip","localhost","gmqttip")
        ##self.mqttport = 1883
        self.addparm("MQTT","mqttport",1883,"gmqttport")
        ##self.mqtttopic= "energy/growatt"
        self.addparm("MQTT","mqtttopic","energy/growatt","gmqtttopic")
        ##self.mqttretain = False
        self.addparm("MQTT","mqttretain",False,"gmqttretain")
        #MQTT Security Settings
        ##self.mqttauth = False
        self.addparm("MQTT","mqttauth",False,"mqttauth")
        ##self.mqttuser = "grott"
        self.addparm("MQTT","mqttuser","grott","gmqttuser")
        ##self.mqttpsw = "growatt2020"
        self.addparm("MQTT","mqttpsw","growatt2020","gmqttpsw","noshow")
        #MQTT Advanced Settings
        ##self.mqttmtopic = "False"
        self.addparm("MQTT","mqttmtopic",False,"gmqttmtopic")
        ##self.mqttmtopicname= "energy/meter"
        self.addparm("MQTT","mqttmtopicname","energy/meter","gmqttmtopicname")
        #self.mqttinverterintopic = False
        self.addparm("MQTT","mqttinverterintopic",False,"gmqttinverterintopic")

        #pvoutput default
        self.pvoutput = False
        self.pvinverters = 1
        self.pvurl = "https://pvoutput.org/service/r2/addstatus.jsp"
        self.pvapikey = "yourapikey"
        self.pvsystemid = {}
        self.pvinverterid = {}
        self.pvsystemid[1] = "systemid1"
        self.pvinverterid[1] = "inverter1"
        self.pvdisv1 = False
        self.pvtemp = False
        self.pvuplimit = 5

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
        #self.extension = False
        self.addparm("extension","extension",False,"gextension")
        #self.extname = "grottext"
        self.addparm("extension","extname","grottext","gextname")
        #self.extvar = {"ip": "localhost", "port":8000}
        self.addparm("extension","extvar",'{"none": "none"}',"gextvar")


    def resetdebuglevel(self):
        #Reset loggerlevel if changed during parm processing
        #verbose == True if loglevel == "debug" (For compat reason, till all messages are displayed via logger)
        #if self.loglevel.upper() == "DEBUG" : self.verbose = True
        if self.loglevel.upper() in ("DEBUG","DEBUGV") : self.changeparm("verbose",True)
        elif self.verbose == True : self.changeparm("loglevel","DEBUG")
        logger.setLevel(self.loglevel.upper())

    def addparm(self,type,parm,value,environ=None,show="show") :
        #nieuw parameter format conf.parm[parm] = {"type" : parmtype,"value": parmvalue, "environ" : environ_var/none, "show" : True/False}]
        self.parm[parm] = {"type" : type,"value": value, "environ" : environ, "show" : show}
        logger.debug("config parameter added: {0} = {1}".format(parm,self.parm[parm]))
        #set conf.parm
        setattr(self, parm, value)

    def changeparm(self,parm,value) :
        #set new parameter value
        self.parm[parm]["value"] = value
        logger.debug("config parameter changed: {0} = {1}".format(parm,self.parm[parm]))
        #change conf.parm
        setattr(self, parm, value)

    def print(self,list="all"):
        """Print configuration settins"""
        logger.info("Grottsettings:\n")
        #logger.info("_Generic:")
        if list == "all" :
            printlist = self.parmtype
            if self.mode in ["proxy","sniffer"]:
                printlist.remove("Server")
            if self.mode in ["serversa"] :
                for item in ("MQTT","PVOutput","influx","extension"):
                    try:
                        printlist.remove(item)
                    except Exception as e:
                        logger.debug("item already deleted: %s",item)
        else:
            printlist = list

        #for parmtype in self.parmtype:
        for parmtype in printlist:
            logger.info(f"_{parmtype}:")
            # parmname = "self."key
            # exec(f"{[parmvalue]} = {parmname}")
            for key in self.parm :
                if self.parm[key]["environ"] == None : self.parm[key]["environ"] =""
                #if self.parm[key]["type"] == parmtype and self.parm[key]["show"]:
                if self.parm[key]["type"] == parmtype :
                    #get real value
                    value = getattr(self,key)
                    if self.parm[key]["show"] == "show" :
                        logger.info(("\t{0:<20}{1}{2:<21}{3}".format(key,"",self.parm[key]["environ"],value)))
                    else:
                        logger.info(("\t{0:<20}{1}{2:<21}{3}".format(key,"",self.parm[key]["environ"],"**secret**")))
        # print("oud")
        #logger.info("\t\tVersion:{0:>20}{1:<30}".format("",self.verrel))
        #logger.info("\t\tVersion:{0:>20}{1:<30}".format("",self.parm["generic"]["verrel"]))
        # print(self.verbose)
        # logger.info("\t\tverbose:{0:>20}{1:<30}".format("",["False","True"][self.verbose]))
        # logger.info("\t\tloglevel:\t\t%s",self.loglevel)
        #logger.info("\t\ttrace:  \t\t%s",self.trace)
        # logger.info("\t\tconfigfile:\t\t%s",self.cfgfile)
        # logger.info("\t\tminrecl:\t\t%s",self.minrecl)
        #logger.info("\tdecrypt:\t\t%s",self.decrypt)
        #logger.info("\tcompat:\t\t%s",self.compat)
        # logger.info("\t\tinvtype:\t\t%s",self.invtype)
        # logger.info("\t\tinvtypemap:\t\t%s",self.invtypemap)
        # logger.info("\t\tinclude_all:\t\t%s",self.includeall)
        # logger.info("\t\tblockcmd:\t\t%s",self.blockcmd)
        # logger.info("\t\tnoipf:   \t\t%s",self.noipf)
        # logger.info("\t\ttime:    \t\t%s",self.gtime)
        # logger.info("\t\tsendbuf:\t\t%s",self.sendbuf)
        # logger.info("\t\ttimezone:\t\t%s",self.tmzone)
        #logger.info("\tvalueoffset:\t\t%s",self.valueoffset)
        #logger.info("\toffset:\t\t%s",self.offset)
        # logger.info("\t\tinverterid:\t\t%s",self.inverterid)
        # logger.info("\t\tmode:    \t\t%s",self.mode)
        # logger.info("\t\tgrottip: \t\t%s",self.grottip)
        # logger.info("\t\tgrottport\t\t%s",self.grottport)
        #logger.info("\tSN\t\t%s",self.SN)
        #growatt
        #if (self.mode in ("server","serversa")) and (self.serverpassthrough) :
        # logger.info("_Growattserver:")
        # logger.info("\t\tgrowattip:\t\t%s",self.growattip)
        # logger.info("\t\tgrowattport:\t\t%s",self.growattport)
        #grottserver
        # if self.mode in ("server","serversa"):
        #     logger.info("_Grottserver:")
        #     #logger.info("\t\tconfserver:\t\t%s",self.confserver)
        #     logger.info("\t\tserverpassthrough:\t%s",self.serverpassthrough)
        #     logger.info("\t\tserverip:\t\t%s",self.serverip)
        #     logger.info("\t\tserverport:\t\t%s",self.serverport)
        #     logger.info("\t\thttpport:\t\t%s",self.httpport)
        #     logger.info("\t\tserverrespwait\t\t%s",self.serverrespwait)
        #     logger.info("\t\tserverirespwait:\t%s",self.serverirespwait)
        #     logger.info("\t\tserverlrespwait:\t%s",self.serverlrespwait)
        #Mqtt
        # if not self.nomqtt :
        #     logger.info("_MQTT:")
        #     logger.info("\t\tnomqtt:   \t\t%s",self.nomqtt)
        #     logger.info("\t\tmqttip:   \t\t%s",self.mqttip)
        #     logger.info("\t\tmqttport:\t\t%s",self.mqttport)
        #     logger.info("\t\tmqtttopic:\t\t%s",self.mqtttopic)
        #     logger.info("\t\tmqttmtopic:\t\t%s",self.mqttmtopic)
        #     logger.info("\t\tmqttmtopicname:\t\t%s",self.mqttmtopicname)
        #     logger.info("\t\tmqttinverterintopic:\t\t%s",self.mqttinverterintopic)
        #     logger.info("\t\tmqtttretain:\t\t%s",self.mqttretain)
        #     logger.info("\t\tmqtttauth:\t\t%s",self.mqttauth)
        #     logger.info("\t\tmqttuser:\t\t%s",self.mqttuser)
        #     logger.info("\t\tmqttpsw:\t\t%s","**secret**")                                                 #scrambleoutputiftested!
        #pvoutput
        if self.pvoutput :
            logger.info("_PVOutput:")
            logger.info("\t\tpvoutput:\t\t%s",self.pvoutput)
            logger.info("\t\tpvdisv1:\t\t%s",self.pvdisv1)
            logger.info("\t\tpvtemp:   \t\t%s",self.pvtemp)
            logger.info("\t\tpvurl:    \t\t%s",self.pvurl)
            logger.info("\t\tpvapikey:\t\t%s",self.pvapikey)
            logger.info("\t\tpvinverters:\t\t%s",self.pvinverters)
            if self.pvinverters==1:
                logger.info("\t\tpvsystemid:\t\t%s",self.pvsystemid[1])
            else:
                logger.info("\t\tpvsystemid:\t\t%s",self.pvsystemid)
                logger.info("\t\tpvinvertid:\t\t%s",self.pvinverterid)
        #Influx
        if self.influx :
            logger.info("_Influxdb:")
            logger.info("\t\tinflux: \t\t%s",self.influx)
            logger.info("\t\tinflux2:\t\t%s",self.influx2)
            logger.info("\t\tdatabase:\t\t%s",self.ifdbname)
            logger.info("\t\tip:      \t\t%s",self.ifip)
            logger.info("\t\tport:    \t\t%s",self.ifport)
            logger.info("\t\tuser:    \t\t%s",self.ifuser)
            logger.info("\t\tpassword:\t\t%s","**secret**")
            #logger.info("\tpassword:\t\t%s",self.ifpsw)
            logger.info("\t\torganization:\t\t%s",self.iforg)
            logger.info("\t\tbucket:  \t\t%s",self.ifbucket)
            logger.info("\t\ttoken:   \t\t%s","**secret**")
            #logger.info("\ttoken:\t\t%s",self.iftoken)
        #extension
        # if self.extension :
        #     logger.info("_Extension:")
        #     logger.info("\t\textension:\t\t%s",self.extension)
        #     logger.info("\t\textname:\t\t%s",self.extname)
        #     logger.info("\t\textvar:  \t\t%s",self.extvar)
        #     #add empty row
        #     logger.info("")

    def parserinit(self):
        """Process commandline parameters"""
        parser = argparse.ArgumentParser(prog='grott')
        parser.add_argument('-v','--verbose',help="set verbose",action='store_true')
        parser.add_argument('--version', action='version', version=self.verrel)
        parser.add_argument('-l','--log',help="set log level",metavar="[loglevel]")
        parser.add_argument('-c',help="set config file if not specified config file is grott.ini",metavar="[config file]")
        parser.add_argument('-o',help="set output file, if not specified output is stdout",metavar="[output file]")
        #get args
        args, unknown = parser.parse_known_args()
        #process args
        if (args.c != None) : self.cfgfile=args.c
        #if (args.o != None) : sys.stdout = open(args.o, 'wb',0) changed to support unbuffered output in windows !!!
        if (args.o != None) : sys.stdout = io.TextIOWrapper(open(args.o, 'wb', 0), write_through=True)
        if (args.log != None) :
            self.loglevel=args.log.upper()
            if self.loglevel.upper() in ("DEBUG","DEBUGV") : self.verbose = True
        elif (args.verbose != None) :
            self.verbose = args.verbose
            print(args.verbose)
            if self.verbose : self.loglevel = "DEBUG"
        logger.setLevel(self.loglevel.upper())
        #show args
        logger.info("Grott Command line parameters processed:")
        logger.info("\t- verbose:   \t\t%s", self.verbose)
        logger.info("\t- loglevel:   \t\t%s", self.loglevel)
        logger.info("\t- config file:\t\t%s", self.cfgfile)
        logger.info("\t- output file:\t\t%s", sys.stdout)

    def confpost(self):
        """Post processing after all parameters settings are read"""
        #set default grottip address
        if self.grottip == "default" :
            self.changeparm("grottip",'0.0.0.0')
        #set the grott ip/poort as the grottserver IP/poort while the server will be the entry point.
        #httplisterner will also use the same ip address.
        if self.mode == "server":
            self.changeparm("serverip",self.grottip)
            self.changeparm("serverport",self.grottport)
        # correct settings if changed by parameter processing
        # might better be moved to the processing sections?

        logger.info("Correct parameter settings if needed")

        #290 if hasattr(self, "amode"):
        #290     self.mode = self.amode
        #290 if hasattr(self, "ablockcmd") and self.ablockcmd == True:
        #290     self.blockcmd = self.ablockcmd
        #290 if hasattr(self, "anoipf") and self.anoipf == True:
        #290     self.noipf = self.anoipf
        #290 if hasattr(self, "ainverterid"):
        #290     self.inverterid = self.ainverterid
        #290 if hasattr(self, "anomqtt") and self.anomqtt:
        #290     self.nomqtt = self.anomqtt
        #290 if hasattr(self, "apvoutput") and self.apvoutput:
        #290     self.pvoutput = self.apvoutput
        #Correct Bool if changed to string during parsing process
        # if self.verbose == True or self.verbose == "True" : self.verbose = True
        # else : self.verbose = False
        self.verbose = str2bool(self.verbose)
        #290 self.trace = str2bool(self.trace)
        #290 self.decrypt = str2bool(self.decrypt)
        #290 self.compat = str2bool(self.compat)
        self.includeall = str2bool(self.includeall)
        self.blockcmd = str2bool(self.blockcmd)
        self.noipf = str2bool(self.noipf)
        self.sendbuf = str2bool(self.sendbuf)
        #
        self.serverpassthrough = str2bool(self.serverpassthrough)
        #
        self.nomqtt = str2bool(self.nomqtt)
        self.mqttmtopic = str2bool(self.mqttmtopic)
        self.mqttauth = str2bool(self.mqttauth)
        self.mqttretain = str2bool(self.mqttretain)
        #
        self.pvoutput = str2bool(self.pvoutput)
        self.pvdisv1 = str2bool(self.pvdisv1)
        self.pvtemp = str2bool(self.pvtemp)
        #
        self.influx = str2bool(self.influx)
        self.influx2 = str2bool(self.influx2)
        self.extension = str2bool(self.extension)
        #Prepare invert settings
        self.SN = "".join(['{:02x}'.format(ord(x)) for x in self.inverterid])
        #3.0.0 self.offset = 6
        #set offset for older inverter types or after record change by Growatt
        #3.0.0 if self.compat: self.offset = int(self.valueoffset)
        #grott in standalone server mode no additional processing
        if self.mode == "serversa" :
            self.nomqtt = True
            self.pvoutput = False
            self.influxdb = False
            self.influxdb2 = False
    def procconf(self):
        logger.info("Grott process configuration file")
        config = configparser.ConfigParser()
        config.read(self.cfgfile)
        if config.has_option("Generic","minrecl"): self.minrecl = config.getint("Generic","minrecl")
        if config.has_option("Generic","verbose"): self.verbose = config.getboolean("Generic","verbose")
        if config.has_option("Generic","loglevel"): self.loglevel = config.get("Generic","loglevel")
        if config.has_option("Generic","decrypt"): self.decrypt = config.getboolean("Generic","decrypt")
        if config.has_option("Generic","compat"): self.compat = config.getboolean("Generic","compat")
        if config.has_option("Generic","includeall"): self.includeall = config.getboolean("Generic","includeall")
        if config.has_option("Generic","invtype"): self.invtype = config.get("Generic","invtype")
        if config.has_option("Generic","invtypemap"): self.invtypemap = eval(config.get("Generic","invtypemap"))
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
        #
        if config.has_option("Growatt","ip"): self.growattip = config.get("Growatt","ip")
        if config.has_option("Growatt","port"): self.growattport = config.getint("Growatt","port")
        #Server
        if config.has_option("Server","serverpassthrough"): self.serverpassthrough = config.getboolean("Server","serverpassthrough")
        if config.has_option("Server","serverip"): self.serverip = config.get("Server","serverip")
        if config.has_option("Server","serverport"): self.serverport = config.getint("Server","serverport")
        if config.has_option("Server","httpport"): self.httpport = config.getint("Server","httpport")
        if config.has_option("Server","apirespwait"): self.apirespwait = config.getfloat("Server","apirespwait")
        if config.has_option("Server","inverterrespwait"): self.inverterrespwait = config.getint("Server","inverterrespwait")
        if config.has_option("Server","dataloggerrespwait"): self.dataloggerrespwait = config.getint("Server","dataloggerrespwait")
        if config.has_option("Server","ConnectionTimeout"): self.ConnectionTimeout = config.getint("Server","ConnectionTimeout")
        #mqtt
        if config.has_option("MQTT","nomqtt"): self.nomqtt = config.get("MQTT","nomqtt")
        if config.has_option("MQTT","ip"): self.mqttip = config.get("MQTT","ip")
        if config.has_option("MQTT","port"): self.mqttport = config.getint("MQTT","port")
        if config.has_option("MQTT","topic"): self.mqtttopic = config.get("MQTT","topic")
        if config.has_option("MQTT","mtopic"): self.mqttmtopic = config.get("MQTT","mtopic")
        if config.has_option("MQTT","mtopicname"): self.mqttmtopicname = config.get("MQTT","mtopicname")
        if config.has_option("MQTT","inverterintopic"): self.mqttinverterintopic = config.getboolean("MQTT","inverterintopic")
        if config.has_option("MQTT","retain"): self.mqttretain = config.getboolean("MQTT","retain")
        if config.has_option("MQTT","auth"): self.mqttauth = config.getboolean("MQTT","auth")
        if config.has_option("MQTT","user"): self.mqttuser = config.get("MQTT","user")
        if config.has_option("MQTT","password"): self.mqttpsw = config.get("MQTT","password")
        if config.has_option("PVOutput","pvoutput"): self.pvoutput = config.get("PVOutput","pvoutput")
        if config.has_option("PVOutput","pvtemp"): self.pvtemp = config.get("PVOutput","pvtemp")
        if config.has_option("PVOutput","pvdisv1"): self.pvdisv1 = config.get("PVOutput","pvdisv1")
        if config.has_option("PVOutput","pvinverters"): self.pvinverters = config.getint("PVOutput","pvinverters")
        if config.has_option("PVOutput","apikey"): self.pvapikey = config.get("PVOutput","apikey")
        if config.has_option("PVOutput", "pvuplimit"): self.pvuplimit = config.getint("PVOutput", "pvuplimit")
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

    def getenv(self, envvar):
        envval = os.getenv(envvar)

        if self.verbose: print(f"\n\tPulled '{envvar}={envval}' from the environment")
        return envval

    def procenv(self):
        logger.info("Grott process environmental variables")
        if os.getenv('gmode') in ("sniff", "proxy", "server", "serversa") :  self.mode = self.getenv('gmode')
        if os.getenv('gverbose') != None :  self.verbose = self.getenv('gverbose')
        if os.getenv('gminrecl') != None :
            if 0 <= int(os.getenv('gminrecl')) <= 255  :     self.minrecl = self.getenv('gminrecl')
        if os.getenv('gdecrypt') != None : self.decrypt = self.getenv('gdecrypt')
        if os.getenv('gcompat') != None :  self.compat = self.getenv('gcompat')
        if os.getenv('gincludeall') != None :  self.includeall = self.getenv('gincludeall')
        if os.getenv('ginvtype') != None :  self.invtype = self.getenv('ginvtype')
        if os.getenv('ginvtypemap') != None :  self.invtypemap = eval(self.getenv('ginvtypemap'))
        if os.getenv('gblockcmd') != None : self.blockcmd = self.getenv('gblockcmd')
        if os.getenv('gnoipf') != None : self.noipf = self.getenv('gnoipf')
        if os.getenv('gtime') in ("auto", "server") : self.gtime = self.getenv('gtime')
        if os.getenv('gtimezone') != None : self.tmzone = self.getenv('gtimezone')
        if os.getenv('gsendbuf') != None : self.sendbuf = self.getenv('gsendbuf')
        if os.getenv('ginverterid') != None :  self.inverterid = self.getenv('ginverterid')
        if os.getenv('ggrottip') != None :
            try:
                ipaddress.ip_address(os.getenv('ggrottip'))
                self.grottip = self.getenv('ggrottip')
            except:
                if self.verbose : print("\nGrott IP address env invalid")
        if os.getenv('ggrottport') != None :
            if 0 <= int(os.getenv('ggrottport')) <= 65535  :  self.grottport = self.getenv('ggrottport')
        if os.getenv('gvalueoffset') != None :
            if 0 <= int(os.getenv('gvalueoffset')) <= 255  :  self.valueoffset = self.getenv('gvalueoffset')
        if os.getenv('ggrowattip') != None :
            try:
                ipaddress.ip_address(os.getenv('ggrowattip'))
                self.growattip = self.getenv('ggrowattip')
            except:
                if self.verbose : print("\nGrott Growatt server IP address env invalid")
        if os.getenv('ggrowattport') != None :
            if 0 <= int(os.getenv('ggrowattport')) <= 65535  :  self.growattport = int(self.getenv('ggrowattport'))
            else :
                if self.verbose : print("\nGrott Growatt server Port address env invalid")
        #handle Serever environmentals
        if os.getenv('ConnectionTimeout') != None :  self.nomqtt = self.getenv('ConnectionTimeout')
        #handle mqtt environmentals
        if os.getenv('gnomqtt') != None :  self.nomqtt = self.getenv('gnomqtt')
        if os.getenv('gmqttip') != None :
            try:
                ipaddress.ip_address(os.getenv('gmqttip'))
                self.mqttip = self.getenv('gmqttip')
            except:
                if self.verbose : print("\nGrott MQTT server IP address env invalid")
        if os.getenv('gmqttport') != None :
            if 0 <= int(os.getenv('gmqttport')) <= 65535  :  self.mqttport = int(self.getenv('gmqttport'))
            else :
                if self.verbose : print("\nGrott MQTT server Port address env invalid")

        if os.getenv('gmqtttopic') != None :  self.mqtttopic = self.getenv('gmqtttopic')
        if os.getenv('gmqttinverterintopic') != None : self.mqttinverterintopic = self.getenv('gmqttinverterintopic')
        if os.getenv('gmqttmtopic') != None :  self.mqttmtopic = self.getenv('gmqttmtopic')
        if os.getenv('gmqttmtopicname') != None :  self.mqttmtopicname = self.getenv('gmqttmtopicname')
        if os.getenv('gmqttretain') != None :  self.mqttretain = self.getenv('gmqttretain')
        if os.getenv('gmqttauth') != None :  self.mqttauth = self.getenv('gmqttauth')
        if os.getenv('gmqttuser') != None :  self.mqttuser = self.getenv('gmqttuser')
        if os.getenv('gmqttpassword') != None : self.mqttpsw = self.getenv('gmqttpassword')
        #Handle PVOutput variables
        if os.getenv('gpvoutput') != None :  self.pvoutput = self.getenv('gpvoutput')
        if os.getenv('gpvtemp') != None :  self.pvtemp = self.getenv('gpvtemp')
        if os.getenv('gpvdisv1') != None :  self.pvdisv1 = self.getenv('gpvdisv1')
        if os.getenv('gpvapikey') != None :  self.pvapikey = self.getenv('gpvapikey')
        if os.getenv('gpvinverters') != None :  self.pvinverters = int(self.getenv('gpvinverters'))
        for x in range(self.pvinverters+1) :
                if os.getenv('gpvsystemid'+str(x)) != None :  self.pvsystemid[x] = self.getenv('gpvsystemid'+ str(x))
                if os.getenv('gpvinverterid'+str(x)) != None :  self.pvinverterid[x] = self.getenv('gpvinverterid'+ str(x))
        if self.pvinverters == 1 :
            if os.getenv('gpvsystemid') != None :  self.pvsystemid[1] = self.getenv('gpvsystemid')
        if os.getenv('pvuplimit') != None :  self.pvuplimit = int(self.getenv('pvuplimit'))
        #Handle Influx
        if os.getenv('ginflux') != None :  self.influx = self.getenv('ginflux')
        if os.getenv('ginflux2') != None :  self.influx2 = self.getenv('ginflux2')
        if os.getenv('gifdbname') != None :  self.ifdbname = self.getenv('gifdbname')
        if os.getenv('gifip') != None :
            try:
                ipaddress.ip_address(os.getenv('gifip'))
                self.ifip = self.getenv('gifip')
            except:
                if self.verbose : print("\nGrott InfluxDB server IP address env invalid")
        if os.getenv('gifport') != None :
            if 0 <= int(os.getenv('gifport')) <= 65535  :  self.ifport = int(self.getenv('gifport'))
            else :
                if self.verbose : print("\nGrott InfluxDB server Port address env invalid")
        if os.getenv('gifuser') != None :  self.ifuser = self.getenv('gifuser')
        if os.getenv('gifpassword') != None :  self.ifpsw = self.getenv('gifpassword')
        if os.getenv('giforg') != None :  self.iforg = self.getenv('giforg')
        if os.getenv('gifbucket') != None :  self.ifbucket = self.getenv('gifbucket')
        if os.getenv('giftoken') != None :  self.iftoken = self.getenv('giftoken')
        #Handle Extension
        if os.getenv('gextension') != None :  self.extension = self.getenv('gextension')
        if os.getenv('gextname') != None :  self.extname = self.getenv('gextname')
        if os.getenv('gextvar') != None :  self.extvar = eval(self.getenv('gextvar'))

    def procinflux(self):
        #Influx db initialisation
        if self.ifip == "localhost" : self.ifip = '0.0.0.0'
        if self.influx2 == False:
            logger.info("Grott InfluxDB V1 initiating started")
            try:
                from influxdb import InfluxDBClient
            except:
                return(4,"Grott Influxdb Library not installed in Python")

            self.influxclient = InfluxDBClient(host=self.ifip, port=self.ifport, timeout=3, username=self.ifuser, password=self.ifpsw)

            try:
                databases = [db['name'] for db in self.influxclient.get_list_database()]
            except Exception as e:
                return(4,"Grott can not connect to InfluxDB")

            if self.ifdbname not in databases:
                logger.info("Grott %s database not yet defined, will be created",self.ifdbname)
                try:
                    self.influxclient.create_database(self.ifdbname)
                except Exception as e:
                    return(4,"influxDB error: {0} - {1}".format(e.code,e.content))

            self.influxclient.switch_database(self.ifdbname)
            return(0,"InfluxDB V1 initiation completed for: "+self.ifdbname)

        else:
            #influxDB V2 initiatlisation
            logger.info("Grott InfluxDB V2 initiating started")
            try:
                from influxdb_client import InfluxDBClient
                from influxdb_client.client.write_api import SYNCHRONOUS
            except:
                return(4,"Grott Influxdb-client Library not installed in Python")

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
                    #print("\t - " + "influxDB bucket ", self.ifbucket, "not defined")
                    #self.influx = False
                    #raise SystemExit("Grott Influxdb initialisation error")
                    return(4,"influxDB bucket {0}, not defined".format(self.ifbucket))

                orgfound = False
                for org in organizations:
                    if org.name == self.iforg:
                        orgfound = True
                        break
                if not orgfound:
                    return(4,"influxDB organization : {0} not defined or no authorised".format(self.iforg))

            except Exception as e:
                #if self.verbose :  print("\t - " + "Grott error: can not contact InfluxDB",e.message)
                #self.influx = False                       # no influx processing any more till restart (and errors repared)
                #raise SystemExit("Grott Influxdb initialisation error")
                return(4,"Grott error: can not contact InfluxDB: {0} - {1}".format(e.status,e.message))

            return(0,"InfluxDB V2 initiation completed for - {0}: {1}".format(self.iforg,self.ifdbname))



    def set_recwl(self):
        #define record that will not be blocked or inspected if blockcmd is specified
        self.recwl = {"0103",                                    #announce record
                         "0104",                                    #data record
                         "0116",                                    #ping
                         "0105",                                    #identify/display inverter config
                         "0119",                                    #identify/display datalogger config
                         "0120",                                    #Smart Monitor Record
                         "0150",                                    #Archived record
                         "5003",                                    #announce record
                         "5004",                                    #data record
                         "5016",                                    #ping
                         "5005",                                    #identify/display inverter config
                         "5019",                                    #identify/display datalogger config
                         "501b",                                    #SDM630 with Raillog
                         "5050",                                    #Archived record
                         "5103",                                    #announce record
                         "5104",                                    #data record
                         "5116",                                    #ping
                         "5105",                                    #identify/display inverter config
                         "5119",                                    #identify/display datalogger config
                         "5129",                                    #announce record
                         "5150",                                    #Archived record
                         "5103",                                    #announce record
                         "5104",                                    #data record
                         "5216",                                    #ping
                         "5105",                                    #identify/display inverter config
                         "5219",                                    #identify/display datalogger config
                         "5229",                                    #announce record
                         "5250"                                     #Archived record

        }

        try:
            with open('recwl.txt') as f:
                self.recwl = f.read().splitlines()
            logger.info("Grott read external record whitelist: 'recwl.txt'")
        except:
            logger.info("Grott external record whitelist 'recwl.txt' not found")
        logger.debug("\t- Grott records whitelisted : \n {0}".format(format_multi_line("\t", str(self.recwl))))

    def set_reclayouts(self):
        #define record layout to be used based on byte 4,6,7 of the header T+byte4+byte6+byte7
        self.recorddict = {}

        self.recorddict1 = {"T02NNNN": {
            "decrypt"           : {"value" :"False"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "incl" : "yes"},
            "pvserial"          : {"value" :36, "length" : 10, "type" : "text"},
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
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "incl" : "yes"},
            "pvserial"          : {"value" :36, "length" : 10, "type" : "text"},
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
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "incl" : "yes"},
            "pvserial"          : {"value" :36, "length" : 10, "type" : "text"},
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
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text","incl" : "yes"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text"},
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
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text","incl" : "yes"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text"},
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
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text","incl" : "yes"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text"},
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
            "SOC"                : {"value" :722, "length" : 2, "type" : "num", "divide" : 1},
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
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "divide" : 10,"incl" : "yes"},
            "pvserial"          : {"value" :36, "length" : 10, "type" : "text"},
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
            "epv1tod"           : {"value" :270, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "epv1tot"           : {"value" :278, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "epvToday"          : {"value" :278, "length" : 4, "type" : "num", "divide" : 10},
            "pvenergytoday"     : {"value" :278, "length" : 4, "type" : "num", "divide" : 10},
            "epv2tod"           : {"value" :286, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "epvTotal"          : {"value" :286, "length" : 4, "type" : "num", "divide" : 10},
            "pvenergytotal"     : {"value" :286, "length" : 4, "type" : "num", "divide" : 10},
            "epv2tot"           : {"value" :294, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
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
            "BatWatt"           : {"value" :394, "length" : 4, "type" : "numx", "divide" : 10},
            "invfanspeed"       : {"value" :414, "length" : 2, "type" : "num", "divide" : 1}
        } }

        self.recorddict8 = {"T06NNNNSPF": {
            "decrypt"           : {"value" :"True"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text","incl" : "yes"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text"},
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
            "BatWatt"           : {"value" :474, "length" : 4, "type" : "numx", "divide" : 10},
            "invfanspeed"       : {"value" :494, "length" : 2, "type" : "num", "divide" : 1}
        }}

        self.recorddict9 = {"T06NNNNXTL3": {
            "decrypt"           : {"value" :"True"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "incl" : "yes"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text"},
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
            "pv3voltage"        : {"value" :202, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},
            "pv3current"        : {"value" :206, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},
            "pv3watt"           : {"value" :210, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
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
            "Vac_RS"            : {"value" :358, "length" : 2, "type" : "num", "divide" : 10},
            "Vac_ST"            : {"value" :362, "length" : 2, "type" : "num", "divide" : 10},
            "Vac_TR"            : {"value" :366, "length" : 2, "type" : "num", "divide" : 10},
            "pvenergytoday"     : {"value" :370, "length" : 4, "type" : "num", "divide" : 10},
            "pvenergytotal"     : {"value" :378, "length" : 4, "type" : "num", "divide" : 10},
            "totworktime"       : {"value" :386, "length" : 4, "type" : "num", "divide" : 7200},
            "epv1today"         : {"value" :394, "length" : 4, "type" : "num", "divide" : 10},
            "epv1total"         : {"value" :402, "length" : 4, "type" : "num", "divide" : 10},
            "epv2today"         : {"value" :410, "length" : 4, "type" : "num", "divide" : 10},
            "epv2total"         : {"value" :418, "length" : 4, "type" : "num", "divide" : 10},
            "epvtotal"          : {"value" :522, "length" : 4, "type" : "num", "divide" : 10},
            "pvtemperature"     : {"value" :530, "length" : 2, "type" : "num", "divide" : 10},
            "pvipmtemperature"  : {"value" :534, "length" : 2, "type" : "num", "divide" : 10},
            "pvboottemperature" : {"value" :538, "length" : 2, "type" : "num", "divide" : 10},
            "temp4"             : {"value" :542, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},
            "uwBatVolt_DSP"     : {"value" :546, "length" : 2, "type" : "num", "divide" : 10},
            "pbusvolt"          : {"value" :550, "length" : 2, "type" : "num", "divide" : 1},
            "nbusvolt"          : {"value" :554, "length" : 2, "type" : "num", "divide" : 1}
        }}

        self.recorddict10 = {"T06NN20": {
            "decrypt"           : {"value" :"True"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text","incl" : "yes"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text"},
            "date"              : {"value" :136, "divide" : 10},
            "voltage_l1"        : {"value" :160, "length" : 4, "type" : "num", "divide" : 10},
            "voltage_l2"        : {"value" :168, "length" : 4, "type" : "num", "divide" : 10,"incl" : "yes"},
            "voltage_l3"        : {"value" :176, "length" : 4, "type" : "num", "divide" : 10,"incl" : "yes"},
            "Current_l1"        : {"value" :184, "length" : 4, "type" : "num", "divide" : 10},
            "Current_l2"        : {"value" :192, "length" : 4, "type" : "num", "divide" : 10,"incl" : "yes"},
            "Current_l3"        : {"value" :200, "length" : 4, "type" : "num", "divide" : 10,"incl" : "yes"},
            "act_power_l1"      : {"value" :208, "length" : 4, "type" : "numx", "divide" : 10},
            "act_power_l2"      : {"value" :216, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "yes"},
            "act_power_l3"      : {"value" :224, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "yes"},
            "app_power_l1"      : {"value" :232, "length" : 4, "type" : "numx", "divide" : 10},
            "app_power_l2"      : {"value" :240, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "yes"},
            "app_power_l3"      : {"value" :248, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "yes"},
            "react_power_l1"    : {"value" :256, "length" : 4, "type" : "numx","divide" : 10},
            "react_power_l2"    : {"value" :264, "length" : 4, "type" : "numx","divide" : 10,"incl" : "yes"},
            "react_power_l3"    : {"value" :272, "length" : 4, "type" : "numx","divide" : 10,"incl" : "yes"},
            "powerfactor_l1"    : {"value" :280, "length" : 4, "type" : "numx", "divide" : 1},
            "powerfactor_l2"    : {"value" :288, "length" : 4, "type" : "numx", "divide" : 1,"incl" : "yes"},
            "powerfactor_l3"    : {"value" :296, "length" : 4, "type" : "numx", "divide" : 1,"incl" : "yes"},
            "pos_rev_act_power" : {"value" :304, "length" : 4, "type" : "numx", "divide" : 10},
            "pos_act_power"     : {"value" :304, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "yes"},
            "rev_act_power"     : {"value" :304, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "yes"},
            "app_power"         : {"value" :312, "length" : 4, "type" : "numx", "divide" : 10},
            "react_power"       : {"value" :320, "length" : 4, "type" : "numx", "divide" : 10},
            "powerfactor"       : {"value" :328, "length" : 4, "type" : "numx", "divide" : 1},
            "frequency"         : {"value" :336, "length" : 4, "type" : "num", "divide" : 10},
            "L1-2_voltage"      : {"value" :344, "length" : 4, "type" : "num", "divide" : 10,"incl" : "yes"},
            "L2-3_voltage"      : {"value" :352, "length" : 4, "type" : "num", "divide" : 10,"incl" : "yes"},
            "L3-1_voltage"      : {"value" :360, "length" : 4, "type" : "num", "divide" : 10,"incl" : "yes"},
            "pos_act_energy"    : {"value" :368, "length" : 4, "type" : "numx", "divide" : 10},
            "rev_act_energy"    : {"value" :376, "length" : 4, "type" : "numx", "divide" : 10},
            "pos_act_energy_kvar" : {"value" :384, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},
            "rev_act_energy_kvar" : {"value" :392, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},
            "app_energy_kvar"   : {"value" :400, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},
            "act_energy_kwh"    : {"value" :408, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"},
            "react_energy_kvar" : {"value" :416, "length" : 4, "type" : "numx", "divide" : 10,"incl" : "no"}
        }}

        self.recorddict11 = {"T06NN1b": {
            "decrypt"           	: {"value" :"True"},
            #"rectype"		    	: {"value": "log","type" : "text","incl" : "no"},
            "datalogserial"         : {"value" :16, "length" : 10, "type" : "text","incl" : "yes"},
            "device"                : {"value": "SDM630","type" : "def","incl" : "no"},
            #"pvserial"          	: {"value" :36, "length" : 10, "type" : "text"},
            #"recortype1"        	: {"value" :70, "length" : 2, "type" : "num","incl" : "no"},
            #"recortype2"        	: {"value" :74, "length" : 2, "type" : "num","incl" : "no"},
            "logstart"            	: {"value" :96,"type" : "def","incl" : "no"},
            "active_energy"     	: {"pos" :1, "type" : "log"},
            "reactive_energy"    	: {"pos" :2, "type" : "log"},
            "activePowerL1"     	: {"pos" :3, "type" : "log"},
            "activePowerL2"     	: {"pos" :4, "type" : "log"},
            "activePowerL3"     	: {"pos" :5, "type" : "log"},
            "reactivePowerL1"   	: {"pos" :6, "type" : "log"},
            "reactivePowerL2"   	: {"pos" :7, "type" : "log"},
            "reactivePowerL3"   	: {"pos" :8, "type" : "log"},
            "apperentPowerL1"   	: {"pos" :9, "type" : "log"},
            "apperentPowerL2"     	: {"pos" :10, "type" : "log"},
            "apperentPowerL3"     	: {"pos" :11, "type" : "log"},
            "powerFactorL1"     	: {"pos" :12, "type" : "log"},
            "powerFactorL2"     	: {"pos" :13, "type" : "log"},
            "powerFactorL3"    		: {"pos" :14, "type" : "log"},
            "voltageL1"           	: {"pos" :15, "type" : "log"},
            "voltageL2"            	: {"pos" :16, "type" : "log"},
            "voltageL3"            	: {"pos" :17, "type" : "log"},
            "currentL1"            	: {"pos" :18, "type" : "log"},
            "currentL2"            	: {"pos" :19, "type" : "log"},
            "currentL3"            	: {"pos" :20, "type" : "log"},
            "power"             	: {"pos" :21, "type" : "log"},
            "active_power"         	: {"pos" :21, "type" : "logpos"},
            "reverse_active_power" 	: {"pos" :21, "type" : "logneg"},
            "apparent_power"       	: {"pos" :22, "type" : "log"},
            "reactive_power"       	: {"pos" :23, "type" : "log"},
            "power_factor"         	: {"pos" :24, "type" : "log"},
            "frequency"            	: {"pos" :25, "type" : "log"},
            "posiActivePower"      	: {"pos" :26, "type" : "log"},
            "reverActivePower"     	: {"pos" :27, "type" : "log"},
            "posiReactivePower"    	: {"pos" :28, "type" : "log"},
            "reverReactivePower"   	: {"pos" :29, "type" : "log"},
            "apparentEnergy"       	: {"pos" :30, "type" : "log"},
            "totalActiveEnergyL1"	: {"pos" :31, "type" : "log"},
            "totalActiveEnergyL2"  	: {"pos" :32, "type" : "log"},
            "totalActiveEnergyL3"  	: {"pos" :33, "type" : "log"},
            "totalRectiveEnergyL1" 	: {"pos" :34, "type" : "log"},
            "totalRectiveEnergyL2" 	: {"pos" :35, "type" : "log"},
            "totalRectiveEnergyL3" 	: {"pos" :36, "type" : "log"},
            "total_energy"     		: {"pos" :37, "type" : "log"},
            "l1Voltage2"     		: {"pos" :38, "type" : "log"},
            "l2Voltage3"     		: {"pos" :39, "type" : "log"},
            "l3Voltage1"     		: {"pos" :40, "type" : "log"},
            "pos41"    				: {"pos" :41, "type" : "log","incl" : "no"},
            "pos42"     			: {"pos" :42, "type" : "log","incl" : "no"},
            "pos43"     			: {"pos" :43, "type" : "log","incl" : "no"},
            "pos44"     			: {"pos" :44, "type" : "log","incl" : "no"},
            "pos45"     			: {"pos" :45, "type" : "log","incl" : "no"},
            "pos46"     			: {"pos" :46, "type" : "log","incl" : "no"},
            "pos47"     			: {"pos" :47, "type" : "log","incl" : "no"},
            "pos48"     			: {"pos" :48, "type" : "log","incl" : "no"},
            "pos49"     			: {"pos" :49, "type" : "log","incl" : "no"},
            "pos50"     			: {"pos" :50, "type" : "log","incl" : "no"},
            "pos51"     			: {"pos" :51, "type" : "log","incl" : "no"},
            "pos52"     			: {"pos" :52, "type" : "log","incl" : "no"},
            "pos53"     			: {"pos" :53, "type" : "log","incl" : "no"},
            "pos54"     			: {"pos" :54, "type" : "log","incl" : "no"},
            "pos55"     			: {"pos" :55, "type" : "log","incl" : "no"},
            "pos56"     			: {"pos" :56, "type" : "log","incl" : "no"},
            "pos57"     			: {"pos" :57, "type" : "log","incl" : "no"},
            "pos58"     			: {"pos" :58, "type" : "log","incl" : "no"},
            "pos59"					: {"pos" :59, "type" : "log","incl" : "no"},
            "pos60" 			    : {"pos" :60, "type" : "log","incl" : "no"},
            "pos61"     			: {"pos" :61, "type" : "log","incl" : "no"},
            "pos62"     			: {"pos" :62, "type" : "log","incl" : "no"},
            "pos63"     			: {"pos" :63, "type" : "log","incl" : "no"},
            "pos64"     			: {"pos" :64, "type" : "log","incl" : "no"},
            "pos65"     			: {"pos" :65, "type" : "log","incl" : "no"},
            "pos66"     			: {"pos" :66, "type" : "log","incl" : "no"}
        }}

        self.recorddict12 = {"T05NNNNXSPH": {
            "decrypt"           : {"value" :"True"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text","incl" : "yes"},
            "pvserial"          : {"value" :36, "length" : 10, "type" : "text"},
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
            "pvpowerout"        : {"value" :218, "length" : 4, "type" : "numx", "divide" : 10},
            "pvfrequentie"      : {"value" :226, "length" : 2, "type" : "num", "divide" : 100},
            "pvgridvoltage"     : {"value" :230, "length" : 2, "type" : "num", "divide" : 10},
            "pvgridcurrent"     : {"value" :234, "length" : 2, "type" : "num", "divide" : 10},
            "pvgridpower"       : {"value" :238, "length" : 4, "type" : "num", "divide" : 10},
            "pvgridvoltage2"    : {"value" :246, "length" : 2, "type" : "num", "divide" : 10},
            "pvgridcurrent2"    : {"value" :250, "length" : 2, "type" : "num", "divide" : 10},
            "pvgridpower2"      : {"value" :254, "length" : 4, "type" : "num", "divide" : 10},
            "pvgridvoltage3"    : {"value" :262, "length" : 2, "type" : "num", "divide" : 10},
            "pvgridcurrent3"    : {"value" :266, "length" : 2, "type" : "num", "divide" : 10},
            "pvgridpower3"      : {"value" :270, "length" : 4, "type" : "num", "divide" : 10},
            "totworktime"       : {"value" :306, "length" : 4, "type" : "num", "divide" : 7200},
            "eactoday"          : {"value" :290, "length" : 4, "type" : "num", "divide" : 10},
            "pvenergytoday"     : {"value" :290, "length" : 4, "type" : "num", "divide" : 10},
            "eactotal"          : {"value" :298, "length" : 4, "type" : "num", "divide" : 10},
            "epvtotal"          : {"value" :442, "length" : 4, "type" : "num", "divide" : 10},
            "epv1today"         : {"value" :314, "length" : 4, "type" : "num", "divide" : 10},
            "epv1total"         : {"value" :322, "length" : 4, "type" : "num", "divide" : 10},
            "epv2today"         : {"value" :330, "length" : 4, "type" : "num", "divide" : 10},
            "epv2total"         : {"value" :338, "length" : 4, "type" : "num", "divide" : 10},
            "pvtemperature"     : {"value" :450, "length" : 2, "type" : "num", "divide" : 10},
            "pvipmtemperature"  : {"value" :454, "length" : 2, "type" : "num", "divide" : 10},
            "pvboosttemp"       : {"value" :458, "length" : 2, "type" : "num", "divide" : 10},
            "bat_dsp"           : {"value" :466, "length" : 2, "type" : "num", "divide" : 10},
            "pbusvolt"          : {"value" :470, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},
            "#nbusvolt"          : {"value" :474, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},
            "#ipf"               : {"value" :478, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},
            "#realoppercent"     : {"value" :482, "length" : 2, "type" : "num", "divide" : 100,"incl" : "no"},
            "#opfullwatt"        : {"value" :486, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "#deratingmode"      : {"value" :494, "length" : 2, "type" : "num", "divide" : 1,"incl" : "no"},
            "eacharge_today"     : {"value" :526, "length" : 4, "type" : "num", "divide" : 10},
            "eacharge_total"     : {"value" :534, "length" : 4, "type" : "num", "divide" : 10},
            "batterytype"        : {"value" :554, "length" : 2, "type" : "num", "divide" : 1},
            "uwsysworkmode"      : {"value" :586, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword0"   : {"value" :590, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword1"   : {"value" :594, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword2"   : {"value" :588, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword3"   : {"value" :602, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword4"   : {"value" :606, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword5"   : {"value" :610, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword6"   : {"value" :614, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword7"   : {"value" :618, "length" : 2, "type" : "num", "divide" : 1},
            "pdischarge1"        : {"value" :622, "length" : 4, "type" : "num", "divide" : 10},
            "p1charge1"          : {"value" :630, "length" : 4, "type" : "num", "divide" : 10},
            "vbat"               : {"value" :738, "length" : 2, "type" : "num", "divide" : 10},
            "SOC"                : {"value" :742, "length" : 2, "type" : "num", "divide" : 1},
            "pactouserr"         : {"value" :746, "length" : 4, "type" : "num", "divide" : 10},
            "#pactousers"        : {"value" :654, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "#pactousert"        : {"value" :662, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "pactousertot"       : {"value" :670, "length" : 4, "type" : "num", "divide" : 10},
            "pactogridr"         : {"value" :678, "length" : 4, "type" : "num", "divide" : 10},
            "#pactogrids"        : {"value" :686, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "#pactogridt"        : {"value" :694, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "pactogridtot"       : {"value" :702, "length" : 4, "type" : "num", "divide" : 10},
            "plocaloadr"         : {"value" :710, "length" : 4, "type" : "num", "divide" : 10},
            "#plocaloads"        : {"value" :718, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "#plocaloadt"        : {"value" :726, "length" : 4, "type" : "num", "divide" : 10,"incl" : "no"},
            "plocaloadtot"       : {"value" :734, "length" : 4, "type" : "num", "divide" : 10},
            "#ipm"               : {"value" :742, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},
            "#battemp"           : {"value" :746, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},
            "spdspstatus"        : {"value" :750, "length" : 2, "type" : "num", "divide" : 10},
            "spbusvolt"          : {"value" :754, "length" : 2, "type" : "num", "divide" : 10},
            "etouser_tod"        : {"value" :762, "length" : 4, "type" : "num", "divide" : 10},
            "etouser_tot"        : {"value" :770, "length" : 4, "type" : "num", "divide" : 10},
            "etogrid_tod"        : {"value" :778, "length" : 4, "type" : "num", "divide" : 10},
            "etogrid_tot"      : {"value" :786, "length" : 4, "type" : "num", "divide" : 10},
            "edischarge1_tod"  : {"value" :794, "length" : 4, "type" : "num", "divide" : 10},
            "edischarge1_tot"  : {"value" :802, "length" : 4, "type" : "num", "divide" : 10},
            "eharge1_tod"      : {"value" :810, "length" : 4, "type" : "num", "divide" : 10},
            "eharge1_tot"      : {"value" :818, "length" : 4, "type" : "num", "divide" : 10},
            "elocalload_tod"  : {"value" :826, "length" : 4, "type" : "num", "divide" : 10},
            "elocalload_tot"  : {"value" :834, "length" : 4, "type" : "num", "divide" : 10}
        } }

        self.recorddict13 = {"T06NNNNXSPA": {
            "decrypt"           : {"value" :"True"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text","incl" : "yes"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text"},
            "date"              : {"value" :136, "divide" : 10},
            "group1start"         : {"value" :150, "length" : 2, "type" : "num","incl" : "no"},
            "group1end"           : {"value" :154, "length" : 2, "type" : "num","incl" : "no"},
            "pvstatus"           : {"value" :158, "length" : 2, "type" : "num"},
            "uwsysworkmode"      : {"value" :158, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword0"   : {"value" :162, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword1"   : {"value" :166, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword2"   : {"value" :170, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword3"   : {"value" :174, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword4"   : {"value" :178, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword5"   : {"value" :182, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword6"   : {"value" :186, "length" : 2, "type" : "num", "divide" : 1},
            "systemfaultword7"   : {"value" :190, "length" : 2, "type" : "num", "divide" : 1},
            "pdischarge1"        : {"value" :194, "length" : 4, "type" : "num", "divide" : 10},
            "pcharge1"           : {"value" :202, "length" : 4, "type" : "num", "divide" : 10},
            "vbat"               : {"value" :210, "length" : 2, "type" : "num", "divide" : 10},
            "SOC"                : {"value" :214, "length" : 2, "type" : "num", "divide" : 1},
            "pactouserr"         : {"value" :218, "length" : 4, "type" : "num", "divide" : 10},
            "pactousers"         : {"value" :226, "length" : 4, "type" : "num", "divide" : 10},
            "pactousert"         : {"value" :234, "length" : 4, "type" : "num", "divide" : 10},
            "pactousertot"       : {"value" :242, "length" : 4, "type" : "num", "divide" : 10},
            "pactogridr"         : {"value" :250, "length" : 4, "type" : "num", "divide" : 10},
            "pactogrids "        : {"value" :258, "length" : 4, "type" : "num", "divide" : 10},
            "pactogrid t"        : {"value" :266, "length" : 4, "type" : "num", "divide" : 10},
            "pactogridtot"       : {"value" :274, "length" : 4, "type" : "num", "divide" : 10},
            "plocaloadr"         : {"value" :282, "length" : 4, "type" : "num", "divide" : 10},
            "plocaloads"        : {"value" :290, "length" : 4, "type" : "num", "divide" : 10},
            "plocaloadt"        : {"value" :298, "length" : 4, "type" : "num", "divide" : 10},
            "plocaloadtot"       : {"value" :306, "length" : 4, "type" : "num", "divide" : 10},
            "ipm"                : {"value" :314, "length" : 2, "type" : "num", "divide" : 10},
            "battemp "           : {"value" :318, "length" : 2, "type" : "num", "divide" : 10},
            "spdspstatus"        : {"value" :322, "length" : 2, "type" : "num", "divide" : 10},
            "spbusvolt"          : {"value" :328, "length" : 2, "type" : "num", "divide" : 10},
            "etouser_tod"        : {"value" :334, "length" : 4, "type" : "num", "divide" : 10},
            "etouser_tot"        : {"value" :342, "length" : 4, "type" : "num", "divide" : 10},
            "etogrid_tod"        : {"value" :350, "length" : 4, "type" : "num", "divide" : 10},
            "etogrid_tot"        : {"value" :358, "length" : 4, "type" : "num", "divide" : 10},
            "edischarge1_tod"    : {"value" :366, "length" : 4, "type" : "num", "divide" : 10},
            "edischarge1_tot"    : {"value" :374, "length" : 4, "type" : "num", "divide" : 10},
            "eharge1_tod"        : {"value" :382, "length" : 4, "type" : "num", "divide" : 10},
            "eharge1_tot"        : {"value" :390, "length" : 4, "type" : "num", "divide" : 10},
            "elocalload_tod"     : {"value" :398, "length" : 4, "type" : "num", "divide" : 10},
            "elocalload_tot"     : {"value" :406, "length" : 4, "type" : "num", "divide" : 10},
            "dwexportlimitap"    : {"value" :414, "length" : 4, "type" : "num", "divide" : 10},
            "epsfac"             : {"value" :426, "length" : 2, "type" : "num", "divide" : 100},
            "epsvac1"            : {"value" :430, "length" : 2, "type" : "num", "divide" : 10},
            "epsiac1"            : {"value" :434, "length" : 2, "type" : "num", "divide" : 10},
            "epspac1"            : {"value" :438, "length" : 4, "type" : "num", "divide" : 10},
            "epsvac2"            : {"value" :446, "length" : 2, "type" : "num", "divide" : 10},
            "epsiac2"            : {"value" :450, "length" : 2, "type" : "num", "divide" : 10},
            "epspac2"            : {"value" :454, "length" : 4, "type" : "num", "divide" : 10},
            "epsvac3"            : {"value" :462, "length" : 2, "type" : "num", "divide" : 10},
            "epsiac3"            : {"value" :466, "length" : 2, "type" : "num", "divide" : 10},
            "epspac3"            : {"value" :470, "length" : 4, "type" : "num", "divide" : 10},
            "loadpercent"        : {"value" :478, "length" : 2, "type" : "num", "divide" : 1},
            "pf"                 : {"value" :482, "length" : 2, "type" : "num", "divide" : 10},
            "bmsstatusold"       : {"value" :486, "length" : 2, "type" : "num", "divide" : 1},
            "bmsstatus"          : {"value" :490, "length" : 2, "type" : "num", "divide" : 1},
            "bmserrorold"        : {"value" :494, "length" : 2, "type" : "num", "divide" : 1},
            "bmserror"           : {"value" :498, "length" : 2, "type" : "num", "divide" : 1},
            "bmssoc"             : {"value" :502, "length" : 2, "type" : "num", "divide" : 1},
            "bmsbatteryvolt"     : {"value" :506, "length" : 2, "type" : "num", "divide" : 100},
            "bmsbatterycurr"     : {"value" :510, "length" : 2, "type" : "num", "divide" : 100},
            "bmsbatterytemp"     : {"value" :514, "length" : 2, "type" : "num", "divide" : 100},
            "bmsmaxcurr"         : {"value" :518, "length" : 2, "type" : "num", "divide" : 100},
            "bmsgaugerm"         : {"value" :522, "length" : 2, "type" : "num", "divide" : 1},
            "bmsgaugefcc"        : {"value" :526, "length" : 2, "type" : "num", "divide" : 1},
            "bmsfw"              : {"value" :530, "length" : 2, "type" : "num", "divide" : 1},
            "bmsdeltavolt"       : {"value" :534, "length" : 2, "type" : "num", "divide" : 1},
            "bmscyclecnt"        : {"value" :538, "length" : 2, "type" : "num", "divide" : 1},
            "bmssoh"             : {"value" :542, "length" : 2, "type" : "num", "divide" : 1},
            "bmsconstantvolt"    : {"value" :546, "length" : 2, "type" : "num", "divide" : 100},
            "bmswarninfoold"     : {"value" :550, "length" : 2, "type" : "num", "divide" : 1},
            "bmswarninfo"        : {"value" :554, "length" : 2, "type" : "num", "divide" : 1},
            "bmsgaugeiccurr"     : {"value" :558, "length" : 2, "type" : "num", "divide" : 1},
            "bmsmcuversion"      : {"value" :562, "length" : 2, "type" : "num", "divide" : 100},
            "bmsgaugeversion"    : {"value" :566, "length" : 2, "type" : "num", "divide" : 1},
            "bmswgaugefrversionl": {"value" :570, "length" : 2, "type" : "num", "divide" : 1},
            "bmswgaugefrversionh": {"value" :574, "length" : 2, "type" : "num", "divide" : 1},
            "bmsbmsinfo"         : {"value" :578, "length" : 2, "type" : "num", "divide" : 1},
            "bmspackinfo"        : {"value" :582, "length" : 2, "type" : "num", "divide" : 1},
            "bmsusingcap"        : {"value" :586, "length" : 2, "type" : "num", "divide" : 1},
            "bmscell1volt"       : {"value" :590, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell2volt"       : {"value" :594, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell3volt"       : {"value" :598, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell4volt"       : {"value" :602, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell5volt"       : {"value" :606, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell6volt"       : {"value" :610, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell7volt"       : {"value" :614, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell8volt"       : {"value" :618, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell9volt"       : {"value" :622, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell10volt"      : {"value" :626, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell11volt"      : {"value" :630, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell12volt"      : {"value" :634, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell13volt"      : {"value" :638, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell14volt"      : {"value" :642, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell15volt"      : {"value" :646, "length" : 2, "type" : "num", "divide" : 100},
            "bmscell16volt"      : {"value" :650, "length" : 2, "type" : "num", "divide" : 100},
            "acchargeenergytodayh": {"value" :654, "length" : 2, "type" : "num", "divide" : 10,"incl" : "no"},                 #deze is een beetjevreemd omdat de high en Low over groepem heen gedefinieerd zijn en uit elkaar liggen
            "group2start"        : {"value" :658, "length" : 2, "type" : "num","incl" : "no"},
            "group2end"          : {"value" :662, "length" : 2, "type" : "num","incl" : "no"},
            "acchargeenergytoday": {"value" :666, "length" : 2, "type" : "num", "divide" : 1},                                 # vooralsnog ervan uitgegaan dat low alleen genoeg is!
            "acchargeenergytotal": {"value" :670, "length" : 4, "type" : "num", "divide" : 1},
            "acchargepower"      : {"value" :678,"length" : 4, "type" : "num", "divide" : 1},
            "70%_invpoweradjust" : {"value" :686,"length" : 2, "type" : "num", "divide" : 1},
            "extraacpowertogrid" : {"value" :690, "length" : 4, "type" : "num", "divide" : 1},
            "eextratoday"        : {"value" :698, "length" : 4, "type" : "num", "divide" : 10},
            "eextratotal"        : {"value" :704, "length" : 4, "type" : "num", "divide" : 10},
            "esystemtoday"       : {"value" :712, "length" : 4, "type" : "num", "divide" : 10},
            "esystemtotal"       : {"value" :720, "length" : 4, "type" : "num", "divide" : 10},
            "group3start"        : {"value" :1166, "length" : 2, "type" : "num","incl" : "no"},
            "group3end"          : {"value" :1170, "length" : 2, "type" : "num","incl" : "no"},
            "inverterstatus"     : {"value" :1174, "length" : 2, "type" : "num", "divide" : 1},
            "pacs"               : {"value" :1314, "length" : 4, "type" : "numx", "divide" : 10},
            "fac"                : {"value" :1322, "length" : 2, "type" : "num", "divide" : 100},
            "vac1"               : {"value" :1326, "length" : 2, "type" : "num", "divide" : 10},
            "iac1"               : {"value" :1330, "length" : 2, "type" : "num", "divide" : 10},
            "pac1"               : {"value" :1334, "length" : 4, "type" : "num", "divide" : 10},
            "eactoday"           : {"value" :1386, "length" : 4, "type" : "num", "divide" : 10},
            "eactot"             : {"value" :1394, "length" : 4, "type" : "num", "divide" : 10},
            "timetotal"          : {"value" :1402, "length" : 4, "type" : "num", "divide" : 7200},
            "Temp1"              : {"value" :1546, "length" : 2, "type" : "num", "divide" : 10},
            "Temp2"              : {"value" :1550, "length" : 2, "type" : "num", "divide" : 10},
            "Temp3"              : {"value" :1554, "length" : 2, "type" : "num", "divide" : 10},
            "Temp4"              : {"value" :1558, "length" : 2, "type" : "num", "divide" : 10},
            "uwbatvoltdsp"       : {"value" :1562, "length" : 2, "type" : "num", "divide" : 10},
            "pbusvoltage"        : {"value" :1566, "length" : 2, "type" : "num", "divide" : 10},
            "nbusvoltage"        : {"value" :1570, "length" : 2, "type" : "num", "divide" : 10},
            "remotectrlen"       : {"value" :1574, "length" : 2, "type" : "num", "divide" : 1},
            "remotectrlpower"    : {"value" :1578, "length" : 2, "type" : "num", "divide" : 1},
            "extraacpowertogrid" : {"value" :1582, "length" : 4, "type" : "num", "divide" : 10},
            "eextratoday"        : {"value" :1590, "length" : 4, "type" : "num", "divide" : 10},
            "eextratotal"        : {"value" :1598, "length" : 4, "type" : "num", "divide" : 10},
            "esystemtoday"       : {"value" :1606, "length" : 4, "type" : "num", "divide" : 10},
            "esystemtotal"       : {"value" :1614, "length" : 4, "type" : "num", "divide" : 10},
            "eacchargetoday"     : {"value" :1622, "length" : 4, "type" : "num", "divide" : 10},
            "eacchargetotal"     : {"value" :1630, "length" : 4, "type" : "num", "divide" : 10},
            "acchargepower"      : {"value" :1638, "length" : 4, "type" : "num", "divide" : 10},
            "priority"           : {"value" :1646, "length" : 2, "type" : "num", "divide" : 1},
            "batterytype"        : {"value" :1650, "length" : 2, "type" : "num", "divide" : 1},
            "autoproofreadcmd"   : {"value" :1654, "length" : 2, "type" : "num", "divide" : 1}
        } }

        self.recorddict14 = {"T06NNNNXMIN": {
            "decrypt"           : {"value" :"true"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text", "divide" : 10},
            "date"              : {"value" :136, "divide" : 10},
            "group1start"       : {"value" :150, "length" : 2, "type" : "num","incl" : "no"},
            "group1end"         : {"value" :154, "length" : 2, "type" : "num","incl" : "no"},
            "pvstatus"          : {"value" : 158,"length" : 2,"type" : "num","divide" : 1},
            "pvpowerin"         : {"value" : 162,"length" : 4,"type" : "num","divide" : 10},
            "pv1voltage"        : {"value" : 170,"length" : 2,"type" : "num","divide" : 10},
            "pv1current"        : {"value" : 174,"length" : 2,"type" : "num","divide" : 10},
            "pv1watt"           : {"value" : 178,"length" : 4,"type" : "num","divide" : 10},
            "pv2voltage"        : {"value" : 186,"length" : 2,"type" : "num","divide" : 10},
            "pv2current"        : {"value" : 190,"length" : 2,"type" : "num","divide" : 10},
            "pv2watt"           : {"value" : 194,"length" : 4,"type" : "num","divide" : 10},
            "pv3voltage"        : {"value" : 202,"length" : 2,"type" : "num","divide" : 10},
            "pv3current"        : {"value" : 206,"length" : 2,"type" : "num","divide" : 10},
            "pv3watt"           : {"value" : 210,"length" : 4,"type" : "num","divide" : 10},
            "pv4voltage"        : {"value" : 218,"length" : 2,"type" : "num","divide" : 10},
            "pv4current"        : {"value" : 222,"length" : 2,"type" : "num","divide" : 10},
            "pv4watt"           : {"value" : 226,"length" : 4,"type" : "num","divide" : 10},
            "pvpowerout"        : {"value" : 250,"length" : 4,"type" : "num","divide" : 10},
            "pvfrequentie"      : {"value" : 258,"length" : 2,"type" : "num","divide" : 100},
            "pvgridvoltage"     : {"value" : 262,"length" : 2,"type" : "num","divide" : 10},
            "pvgridcurrent"     : {"value" : 266,"length" : 2,"type" : "num","divide" : 10},
            "pvgridpower"       : {"value" : 270,"length" : 4,"type" : "num","divide" : 10},
            "pvgridvoltage2"    : {"value" : 278,"length" : 2,"type" : "num","divide" : 10},
            "pvgridcurrent2"    : {"value" : 282,"length" : 2,"type" : "num","divide" : 10},
            "pvgridpower2"      : {"value" : 286,"length" : 4,"type" : "num","divide" : 10},
            "pvgridvoltage3"    : {"value" : 294,"length" : 2,"type" : "num","divide" : 10},
            "pvgridcurrent3"    : {"value" : 298,"length" : 2,"type" : "num","divide" : 10},
            "pvgridpower3"      : {"value" : 302,"length" : 4,"type" : "num","divide" : 10},
            "vacrs"            : {"value" : 310,"length" : 2,"type" : "num","divide" : 10},
            "vacst"            : {"value" : 314,"length" : 2,"type" : "num","divide" : 10},
            "vactr"            : {"value" : 318,"length" : 2,"type" : "num","divide" : 10},
            "ptousertotal"      : {"value" : 322,"length" : 4,"type" : "num","divide" : 10},
            "ptogridtotal"      : {"value" : 330,"length" : 4,"type" : "num","divide" : 10},
            "ptoloadtotal"      : {"value" : 338,"length" : 4,"type" : "num","divide" : 10},
            "totworktime"       : {"value" : 346,"length" : 4,"type" : "num","divide" : 7200},
            "pvenergytoday"     : {"value" : 354,"length" : 4,"type" : "num","divide" : 10},
            "pvenergytotal"     : {"value" : 362,"length" : 4,"type" : "num","divide" : 10},
            "epvtotal"          : {"value" : 370,"length" : 4,"type" : "num","divide" : 10},
            "epv1today"         : {"value" : 378,"length" : 4,"type" : "num","divide" : 10},
            "epv1total"         : {"value" : 386,"length" : 4,"type" : "num","divide" : 10},
            "epv2today"         : {"value" : 394,"length" : 4,"type" : "num","divide" : 10},
            "epv2total"         : {"value" : 402,"length" : 4,"type" : "num","divide" : 10},
            "epv3today"         : {"value" : 410,"length" : 4,"type" : "num","divide" : 10},
            "epv3total"         : {"value" : 418,"length" : 4,"type" : "num","divide" : 10},
            "etousertoday"      : {"value" : 426,"length" : 4,"type" : "num","divide" : 10},
            "etousertotal"      : {"value" : 434,"length" : 4,"type" : "num","divide" : 10},
            "etogridtoday"      : {"value" : 442,"length" : 4,"type" : "num","divide" : 10},
            "etogridtotal"      : {"value" : 450,"length" : 4,"type" : "num","divide" : 10},
            "eloadtoday"        : {"value" : 458,"length" : 4,"type" : "num","divide" : 10},
            "eloadtotal"        : {"value" : 466,"length" : 4,"type" : "num","divide" : 10},
            "deratingmode"      : {"value" : 502,"length" : 2,"type" : "num","divide" : 1},
            "iso"               : {"value" : 506,"length" : 2,"type" : "num","divide" : 1},
            "dcir"              : {"value" : 510,"length" : 2,"type" : "num","divide" : 10},
            "dcis"              : {"value" : 514,"length" : 2,"type" : "num","divide" : 10},
            "dcit"              : {"value" : 518,"length" : 2,"type" : "num","divide" : 10},
            "gfci"              : {"value" : 522,"length" : 4,"type" : "num","divide" : 1},
            "pvtemperature"     : {"value" : 530,"length" : 2,"type" : "num","divide" : 10},
            "pvipmtemperature"  : {"value" : 534,"length" : 2,"type" : "num","divide" : 10},
            "temp3"             : {"value" : 538,"length" : 2,"type" : "num","divide" : 10},
            "temp4"             : {"value" : 542,"length" : 2,"type" : "num","divide" : 10},
            "temp5"             : {"value" : 546,"length" : 2,"type" : "num","divide" : 10},
            "pbusvoltage"       : {"value" : 550,"length" : 2,"type" : "num","divide" : 10},
            "nbusvoltage"       : {"value" : 554,"length" : 2,"type" : "num","divide" : 10},
            "ipf"               : {"value" : 558,"length" : 2,"type" : "num","divide" : 1},
            "realoppercent"     : {"value" : 562,"length" : 2,"type" : "num","divide" : 1},
            "opfullwatt"        : {"value" : 566,"length" : 4,"type" : "num","divide" : 10},
            "standbyflag"       : {"value" : 574,"length" : 2,"type" : "num","divide" : 1},
            "faultcode"         : {"value" : 578,"length" : 2,"type" : "num","divide" : 1},
            "warningcode"       : {"value" : 582,"length" : 2,"type" : "num","divide" : 1},
            "systemfaultword0"  : {"value" : 586,"length" : 2,"type" : "num","divide" : 1},
            "systemfaultword1"  : {"value" : 590,"length" : 2,"type" : "num","divide" : 1},
            "systemfaultword2"  : {"value" : 594,"length" : 2,"type" : "num","divide" : 1},
            "systemfaultword3"  : {"value" : 598,"length" : 2,"type" : "num","divide" : 1},
            "systemfaultword4"  : {"value" : 602,"length" : 2,"type" : "num","divide" : 1},
            "systemfaultword5"  : {"value" : 606,"length" : 2,"type" : "num","divide" : 1},
            "systemfaultword6"  : {"value" : 610,"length" : 2,"type" : "num","divide" : 1},
            "systemfaultword7"  : {"value" : 614,"length" : 2,"type" : "num","divide" : 1},
            "invstartdelaytime" : {"value" : 618,"length" : 2,"type" : "num","divide" : 1},
            "bdconoffstate"     : {"value" : 630,"length" : 2,"type" : "num","divide" : 1},
            "drycontactstate"   : {"value" : 634,"length" : 2,"type" : "num","divide" : 1},
            "group2start"       : {"value" :658, "length" : 2, "type" : "num","incl" : "no"},
            "group2end"         : {"value" :662, "length" : 2, "type" : "num","incl" : "no"},
            "edischrtoday"      : {"value" : 666,"length" : 4,"type" : "num","divide" : 10},
            "edischrtotal"      : {"value" : 674,"length" : 4,"type" : "num","divide" : 10},
            "echrtoday"         : {"value" : 682,"length" : 4,"type" : "num","divide" : 10},
            "echrtotal"         : {"value" : 690,"length" : 4,"type" : "num","divide" : 10},
            "eacchrtoday"       : {"value" : 698,"length" : 4,"type" : "num","divide" : 10},
            "eacchrtotal"       : {"value" : 706,"length" : 4,"type" : "num","divide" : 10},
            "priority"          : {"value" : 742,"length" : 2,"type" : "num","divide" : 1},
            "epsfac"            : {"value" : 746,"length" : 2,"type" : "num","divide" : 100},
            "epsvac1"           : {"value" : 750,"length" : 2,"type" : "num","divide" : 10},
            "epsiac1"           : {"value" : 754,"length" : 2,"type" : "num","divide" : 10},
            "epspac1"           : {"value" : 758,"length" : 4,"type" : "num","divide" : 10},
            "epsvac2"           : {"value" : 766,"length" : 2,"type" : "num","divide" : 10},
            "epsiac2"           : {"value" : 770,"length" : 2,"type" : "num","divide" : 10},
            "epspac2"           : {"value" : 774,"length" : 4,"type" : "num","divide" : 10},
            "epsvac3"           : {"value" : 782,"length" : 2,"type" : "num","divide" : 10},
            "epsiac3"           : {"value" : 786,"length" : 2,"type" : "num","divide" : 10},
            "epspac3"           : {"value" : 790,"length" : 4,"type" : "num","divide" : 10},
            "epspac"            : {"value" : 798,"length" : 4,"type" : "num","divide" : 10},
            "loadpercent"       : {"value" : 806,"length" : 2,"type" : "num","divide" : 10},
            "pf"                : {"value" : 810,"length" : 2,"type" : "num","divide" : 10},
            "dcv"               : {"value" : 814,"length" : 2,"type" : "num","divide" : 1},
            "bdc1_sysstatemode" : {"value" : 830,"length" : 2,"type" : "num","divide" : 1},
            "bdc1_faultcode"    : {"value" : 834,"length" : 2,"type" : "num","divide" : 1},
            "bdc1_warncode"     : {"value" : 838,"length" : 2,"type" : "num","divide" : 1},
            "bdc1_vbat"         : {"value" : 842,"length" : 2,"type" : "num","divide" : 100},
            "bdc1_ibat"         : {"value" : 846,"length" : 2,"type" : "num","divide" : 10},
            "bdc1_soc"          : {"value" : 850,"length" : 2,"type" : "num","divide" : 1},
            "bdc1_vbus1"        : {"value" : 854,"length" : 2,"type" : "num","divide" : 10},
            "bdc1_vbus2"        : {"value" : 858,"length" : 2,"type" : "num","divide" : 10},
            "bdc1_ibb"          : {"value" : 862,"length" : 2,"type" : "num","divide" : 10},
            "bdc1_illc"         : {"value" : 866,"length" : 2,"type" : "num","divide" : 10},
            "bdc1_tempa"        : {"value" : 870,"length" : 2,"type" : "num","divide" : 10},
            "bdc1_tempb"        : {"value" : 874,"length" : 2,"type" : "num","divide" : 10},
            "bdc1_pdischr"      : {"value" : 878,"length" : 4,"type" : "num","divide" : 10},
            "bdc1_pchr"         : {"value" : 886,"length" : 4,"type" : "num","divide" : 10},
            "bdc1_edischrtotal" : {"value" : 894,"length" : 4,"type" : "num","divide" : 10},
            "bdc1_echrtotal"    : {"value" : 902,"length" : 4,"type" : "num","divide" : 10},
            "bdc1_flag"          : {"value" : 914,"length" : 2,"type" : "num","divide" : 1},
            "bdc2_sysstatemode" : {"value" : 922,"length" : 2,"type" : "num","divide" : 1},
            "bdc2_faultcode"    : {"value" : 926,"length" : 2,"type" : "num","divide" : 1},
            "bdc2_warncode"     : {"value" : 930,"length" : 2,"type" : "num","divide" : 1},
            "bdc2_vbat"         : {"value" : 934,"length" : 2,"type" : "num","divide" : 100},
            "bdc2_ibat"         : {"value" : 938,"length" : 2,"type" : "num","divide" : 10},
            "bdc2_soc"          : {"value" : 942,"length" : 2,"type" : "num","divide" : 1},
            "bdc2_vbus1"        : {"value" : 946,"length" : 2,"type" : "num","divide" : 10},
            "bdc2_vbus2"        : {"value" : 950,"length" : 2,"type" : "num","divide" : 10},
            "bdc2_ibb"          : {"value" : 954,"length" : 2,"type" : "num","divide" : 10},
            "bdc2_illc"         : {"value" : 958,"length" : 2,"type" : "num","divide" : 10},
            "bdc2_tempa"        : {"value" : 962,"length" : 2,"type" : "num","divide" : 10},
            "bdc2_tempb"        : {"value" : 966,"length" : 2,"type" : "num","divide" : 10},
            "bdc2_pdischr"      : {"value" : 970,"length" : 4,"type" : "num","divide" : 10},
            "bdc2_pchr"         : {"value" : 978,"length" : 4,"type" : "num","divide" : 10},
            "bdc2_edischrtotal" : {"value" : 986,"length" : 4,"type" : "num","divide" : 10},
            "bdc2_echrtotal"    : {"value" : 994,"length" : 4,"type" : "num","divide" : 10},
            "bdc2_flag"          : {"value" : 1006,"length" : 4,"type" : "num","divide" : 1},
            "bms_status"         : {"value" : 1014,"length" : 2,"type" : "num","divide" : 1},
            "bms_error"          : {"value" : 1018,"length" : 2,"type" : "num","divide" : 1},
            "bms_warninfo"       : {"value" : 1022,"length" : 2,"type" : "num","divide" : 1},
            "bms_soc"            : {"value" : 1026,"length" : 2,"type" : "num","divide" : 1},
            "bms_batteryvolt"    : {"value" : 1030,"length" : 2,"type" : "num","divide" : 100},
            "bms_batterycurr"    : {"value" : 1034,"length" : 2,"type" : "numx","divide" : 100},
            "bms_batterytemp"    : {"value" : 1038,"length" : 2,"type" : "num","divide" : 10},
            "bms_maxcurr"        : {"value" : 1042,"length" : 2,"type" : "num","divide" : 100},
            "bms_deltavolt"      : {"value" : 1046,"length" : 2,"type" : "num","divide" : 100},
            "bms_cyclecnt"       : {"value" : 1050,"length" : 2,"type" : "num","divide" : 1},
            "bms_soh"            : {"value" : 1054,"length" : 2,"type" : "num","divide" : 1},
            "bms_constantvolt"   : {"value" : 1058,"length" : 2,"type" : "num","divide" : 100},
            "bms_bms_info"        : {"value" : 1062,"length" : 2,"type" : "num","divide" : 1},
            "bms_packinfo"       : {"value" : 1066,"length" : 2,"type" : "num","divide" : 1},
            "bms_usingcap"       : {"value" : 1070,"length" : 2,"type" : "num","divide" : 1},
            "bms_fw"             : {"value" : 1074,"length" : 2,"type" : "num","divide" : 1},
            "bms_mcuversion"     : {"value" : 1078,"length" : 2,"type" : "num","divide" : 1},
            "bms_commtype"       : {"value" : 1082,"length" : 2,"type" : "num","divide" : 1}
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
        self.recorddict.update(self.recorddict12)                   #T05NNNNXSPH
        self.recorddict.update(self.recorddict13)                   #T06NNNNXSPA
        self.recorddict.update(self.recorddict14)

                # Layout definitions for automatic record detection
        self.alodict = {}

        #Define Layout for auto Layout generation
        # default base protocol 00,02
        self.ALO02 = { "ALO02" : {
            "decrypt"           : {"value" : "False"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "incl" : "yes"},
            "pvserial"          : {"value" :36, "length" : 10, "type" : "text"},
            "date"              : {"value" :56, "divide" : 10},
            "datastart"       : {"value"   :70, "length" : 2, "type" : "num","incl" : "no"},
            } }

        # base protocol 05
        self.ALO05 = { "ALO05" : {
            "decrypt"           : {"value" : "True"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "incl" : "yes"},
            "pvserial"          : {"value" :36, "length" : 10, "type" : "text"},
            "date"              : {"value" :56, "divide" : 10},
            "datastart"       : {"value"   :70, "length" : 2, "type" : "num","incl" : "no"},
            } }

        # base protocol 06

        self.ALO06    = { "ALO06" :  {
            "decrypt"           : {"value" :"True"},
            "datalogserial"     : {"value" :16, "length" : 10, "type" : "text", "incl" : "yes"},
            "pvserial"          : {"value" :76, "length" : 10, "type" : "text", "divide" : 10},
            "date"              : {"value" :136, "divide" : 10},
            "datastart"         : {"value" :150, "length" : 2, "type" : "num","incl" : "no"},
            } }

        self.ALO_0_44V1 = {"ALO_0_44V1": {
            "pvstatus"          : {"value" :78, "length" : 2, "type" : "numx","register" : 0},
            "pvstatus2"          : {"value" :80, "length" : 2, "type" : "numx","register" : 0},
            "pvpowerin"         : {"value" :82, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1},
            "pv1voltage"        : {"value" :90, "length" : 2, "type" : "numx", "divide" : 10, "register" : 3},
            "pv1current"        : {"value" :94, "length" : 2, "type" : "numx", "divide" : 10, "register" : 4},
            "pv1watt"           : {"value" :98, "length" : 4, "type" : "numx", "divide" : 10, "register" : 5},
            "pv2voltage"        : {"value" :106, "length" : 2, "type" : "numx", "divide" : 10, "register" : 7},
            "pv2current"        : {"value" :110, "length" : 2, "type" : "numx", "divide" : 10, "register" : 8},
            "pv2watt"           : {"value" :114, "length" : 4, "type" : "numx", "divide" : 10, "register" : 9},
            "pvpowerout"        : {"value" :122, "length" : 4, "type" : "numx", "divide" : 10, "register" : 11},
            "pvfrequentie"      : {"value" :130, "length" : 2, "type" : "numx", "divide" : 100, "register" : 13},
            "pvgridvoltage"     : {"value" :134, "length" : 2, "type" : "numx", "divide" : 10, "register" : 14},
            "pvgridcurrent"     : {"value" :138, "length" : 2, "type" : "numx", "divide" : 10, "register" : 15},
            "pvgridpower"       : {"value" :142, "length" : 4, "type" : "numx", "divide" : 10, "register" : 16},
            "pvgridvoltage2"    : {"value" :150, "length" : 2, "type" : "numx", "divide" : 10, "register" : 18},
            "pvgridcurrent2"    : {"value" :154, "length" : 2, "type" : "numx", "divide" : 10, "register" : 19},
            "pvgridpower2"      : {"value" :158, "length" : 4, "type" : "numx", "divide" : 10, "register" : 20},
            "pvgridvoltage3"    : {"value" :166, "length" : 2, "type" : "numx", "divide" : 10, "register" : 22},
            "pvgridcurrent3"    : {"value" :170, "length" : 2, "type" : "numx", "divide" : 10, "register" : 23},
            "pvgridpower3"      : {"value" :174, "length" : 4, "type" : "numx", "divide" : 10, "register" : 24},
            "pvenergytoday"     : {"value" :182, "length" : 4, "type" : "numx", "divide" : 10, "register" : 26},
            "pvenergytotal"     : {"value" :190, "length" : 4, "type" : "numx", "divide" : 10, "register" : 28},
            "totworktime"       : {"value" :198, "length" : 4, "type" : "numx", "divide" : 7200, "register" : 30},
            "pvtemperature"     : {"value" :206, "length" : 2, "type" : "numx", "divide" : 10, "register" : 32},
            "isof"              : {"value" :210, "length" : 2, "type" : "numx", "divide" : 1, "register" : 33,"incl" : "no"},
            "gfcif"             : {"value" :214, "length" : 2, "type" : "numx", "divide" : 1, "register" : 34,"incl" : "no"},
            "dcif"              : {"value" :218, "length" : 2, "type" : "numx", "divide" : 1, "register" : 35,"incl" : "no"},
            "vpvfault"          : {"value" :222, "length" : 2, "type" : "numx", "divide" : 1, "register" : 36,"incl" : "no"},
            "vacfault"          : {"value" :226, "length" : 2, "type" : "numx", "divide" : 1, "register" : 37,"incl" : "no"},
            "facfault"          : {"value" :230, "length" : 2, "type" : "numx", "divide" : 1, "register" : 38,"incl" : "no"},
            "tmpfault"          : {"value" :234, "length" : 2, "type" : "numx", "divide" : 1, "register" : 39,"incl" : "no"},
            "faultcode"         : {"value" :238, "length" : 2, "type" : "numx", "divide" : 1, "register" : 40,"incl" : "no"},
            "pvipmtemperature"  : {"value" :242, "length" : 2, "type" : "numx", "divide" : 10, "register" : 41},
            "pbusvolt"          : {"value" :246, "length" : 2, "type" : "numx", "divide" : 10, "register" : 42,"incl" : "no"},
            "nbusvolt"          : {"value" :250, "length" : 2, "type" : "numx", "divide" : 10, "register" : 43,"incl" : "no"},
            "checkstep"         : {"value" :254, "length" : 2, "type" : "numx", "divide" : 10, "register" : 44,"incl" : "no"},
            } }


        self.ALO_45_89V1 = {"ALO_45_89V1": {
            "IPF"               : {"value" :318, "length" : 2, "type" : "numx", "divide" : 1, "register" : 45,"incl" : "no"},
            "ResetCHK"          : {"value" :318, "length" : 2, "type" : "numx", "divide" : 1, "register" : 46,"incl" : "no"},
            "DeratingMode"      : {"value" :318, "length" : 2, "type" : "numx", "divide" : 1, "register" : 47,"incl" : "no"},
            "epv1today"         : {"value" :278, "length" : 4, "type" : "numx", "divide" : 10, "register" : 48},
            "epv1total"         : {"value" :286, "length" : 4, "type" : "numx", "divide" : 10, "register" : 50},
            "epv2today"         : {"value" :294, "length" : 4, "type" : "numx", "divide" : 10, "register" : 52},
            "epv2total"         : {"value" :302, "length" : 4, "type" : "numx", "divide" : 10, "register" : 54},
            "epvtotal"          : {"value" :310, "length" : 4, "type" : "numx", "divide" : 10, "register" : 56},
            "rac"               : {"value" :318, "length" : 4, "type" : "numx", "divide" : 10, "register" : 58,"incl" : "no"},
            "eractoday"         : {"value" :326, "length" : 4, "type" : "numx", "divide" : 10, "register" : 60,"incl" : "no"},
            "eractotal"         : {"value" :334, "length" : 4, "type" : "numx", "divide" : 10, "register" : 62,"incl" : "no"}
            } }

#Layout voor protocol v2

        self.ALO_0_124 = {"ALO_0_124": {
            "pvstatus"          : {"value" :78, "length" : 2, "type" : "numx", "divide" : 10,"register" : 0,},
            "pvpowerin"         : {"value" :82, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1},
            "pv1voltage"        : {"value" :90, "length" : 2, "type" : "numx", "divide" : 10, "register" : 3},
            "pv1current"        : {"value" :94, "length" : 2, "type" : "numx", "divide" : 10, "register" : 4},
            "pv1watt"           : {"value" :98, "length" : 4, "type" : "numx", "divide" : 10, "register" : 5},
            "pv2voltage"        : {"value" :106, "length" : 2, "type" : "numx", "divide" : 10, "register" : 7},
            "pv2current"        : {"value" :110, "length" : 2, "type" : "numx", "divide" : 10, "register" : 8},
            "pv2watt"           : {"value" :114, "length" : 4, "type" : "numx", "divide" : 10, "register" : 9},
            "pv3voltage"        : {"value" :122, "length" : 2, "type" : "numx", "divide" : 10, "register" : 11, "incl" : "no"},
            "pv3current"        : {"value" :126, "length" : 2, "type" : "numx", "divide" : 10, "register" : 12, "incl" : "no"},
            "pv3watt"           : {"value" :130, "length" : 4, "type" : "numx", "divide" : 10, "register" : 13, "incl" : "no"},
            "pv4voltage"        : {"value" :106, "length" : 2, "type" : "numx", "divide" : 10, "register" : 15, "incl" : "no"},
            "pv4current"        : {"value" :110, "length" : 2, "type" : "numx", "divide" : 10, "register" : 16, "incl" : "no"},
            "pv4watt"           : {"value" :114, "length" : 4, "type" : "numx", "divide" : 10, "register" : 17, "incl" : "no"},
            "pvpowerout"        : {"value" :218, "length" : 4, "type" : "numx", "divide" : 10, "register" : 35},
            "pvfrequentie"      : {"value" :226, "length" : 2, "type" : "numx", "divide" : 100, "register" : 37},
            "pvgridvoltage"     : {"value" :230, "length" : 2, "type" : "numx", "divide" : 10, "register" : 38},
            "pvgridcurrent"     : {"value" :234, "length" : 2, "type" : "numx", "divide" : 10, "register" : 39},
            "pvgridpower"       : {"value" :238, "length" : 4, "type" : "numx", "divide" : 10, "register" : 40},
            "pvgridvoltage2"    : {"value" :246, "length" : 2, "type" : "numx", "divide" : 10, "register" : 42},
            "pvgridcurrent2"    : {"value" :250, "length" : 2, "type" : "numx", "divide" : 10, "register" : 43},
            "pvgridpower2"      : {"value" :254, "length" : 4, "type" : "numx", "divide" : 10, "register" : 44},
            "pvgridvoltage3"    : {"value" :262, "length" : 2, "type" : "numx", "divide" : 10, "register" : 46},
            "pvgridcurrent3"    : {"value" :266, "length" : 2, "type" : "numx", "divide" : 10, "register" : 47},
            "pvgridpower3"      : {"value" :270, "length" : 4, "type" : "numx", "divide" : 10, "register" : 48},
            "vacrs"             : {"value" :000, "length" : 2, "type" : "numx", "divide" : 10, "register" : 50},
            "vacst"             : {"value" :000, "length" : 2, "type" : "numx", "divide" : 10, "register" : 51},
            "vactr"             : {"value" :000, "length" : 2, "type" : "numx", "divide" : 10, "register" : 52},
            "eactoday"          : {"value" :290, "length" : 4, "type" : "numx", "divide" : 10, "register" : 53},
            "pvenergytoday"     : {"value" :290, "length" : 4, "type" : "numx", "divide" : 10, "register" : 53},
            "eactotal"          : {"value" :298, "length" : 4, "type" : "numx", "divide" : 10, "register" : 55},
            "pvenergytotal"     : {"value" :298, "length" : 4, "type" : "numx", "divide" : 10, "register" : 55},
            "totworktime"       : {"value" :306, "length" : 4, "type" : "numx", "divide" : 7200, "register" : 57},
            "epv1today"         : {"value" :314, "length" : 4, "type" : "numx", "divide" : 10, "register" : 59},
            "epv1total"         : {"value" :322, "length" : 4, "type" : "numx", "divide" : 10, "register" : 61},
            "epv2today"         : {"value" :330, "length" : 4, "type" : "numx", "divide" : 10, "register" : 63},
            "epv2total"         : {"value" :338, "length" : 4, "type" : "numx", "divide" : 10, "register" : 65},
            "epvtotal"          : {"value" :442, "length" : 4, "type" : "numx", "divide" : 10, "register" : 91},
            "pvtemperature"     : {"value" :450, "length" : 2, "type" : "numx", "divide" : 10, "register" : 93},
            "pvipmtemperature"  : {"value" :454, "length" : 2, "type" : "numx", "divide" : 10, "register" : 94},
            "pvboosttemp"       : {"value" :458, "length" : 2, "type" : "numx", "divide" : 10, "register" : 95},
            "temp4"            : {"value" :462, "length" : 2, "type" : "numx", "divide" : 10, "register" : 96, "incl" : "no"},
            "bat_dsp"           : {"value" :466, "length" : 2, "type" : "numx", "divide" : 10, "register" : 97},
            "pbusvolt"          : {"value" :470, "length" : 2, "type" : "numx", "divide" : 10, "register" : 98, "incl" : "no"},
            "nbusvolt"          : {"value" :474, "length" : 2, "type" : "numx", "divide" : 10, "register" : 99, "incl" : "no"},
            "ipf"               : {"value" :478, "length" : 2, "type" : "numx", "divide" : 10, "register" : 100, "incl" : "no"},
            "realoppercent"     : {"value" :482, "length" : 2, "type" : "numx", "divide" : 100, "register" : 101, "incl" : "no"},
            "opfullwatt"        : {"value" :486, "length" : 4, "type" : "numx", "divide" : 10, "register" : 102, "incl" : "no"},
            "deratingmode"      : {"value" :494, "length" : 2, "type" : "numx", "divide" : 1, "register" : 104, "incl" : "no"},
            "eacharge_today"     : {"value" :526, "length" : 4, "type" : "numx", "divide" : 10, "register" : 111},
            "eacharge_total"     : {"value" :534, "length" : 4, "type" : "numx", "divide" : 10, "register" : 113},
            "priority"           : {"value" :550, "length" : 2, "type" : "numx", "divide" : 1, "register" : 118},
            "batterytype"        : {"value" :554, "length" : 2, "type" : "numx", "divide" : 1, "register" : 119},

        }}

        self.ALO_1000_1124 = {"ALO_1000_1124": {
            "pvstatus"           : {"value" :78, "length" : 2, "type" : "numx","register" : 1000},
            "systemfaultword0"   : {"value" :162, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1001, "incl" : "no"},
            "systemfaultword1"   : {"value" :166, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1002, "incl" : "no"},
            "systemfaultword2"   : {"value" :170, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1003, "incl" : "no"},
            "systemfaultword3"   : {"value" :174, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1004, "incl" : "no"},
            "systemfaultword4"   : {"value" :178, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1005, "incl" : "no"},
            "systemfaultword5"   : {"value" :182, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1006, "incl" : "no"},
            "systemfaultword6"   : {"value" :186, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1007, "incl" : "no"},
            "systemfaultword7"   : {"value" :190, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1008, "incl" : "no"},
            "pdischarge1"        : {"value" :194, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1009},
            "pcharge1"           : {"value" :202, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1011},
            "vbat"               : {"value" :210, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1013},
            "soc"                : {"value" :214, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1014},
            "pactouserr"         : {"value" :218, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1015},
            "pactousers"         : {"value" :226, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1017},
            "pactousert"         : {"value" :234, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1019},
            "pactousertot"       : {"value" :242, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1021},
            "pactogridr"         : {"value" :250, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1023},
            "pactogrids "        : {"value" :258, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1025},
            "pactogridt"         : {"value" :266, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1027},
            "pactogridtot"       : {"value" :274, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1029},
            "plocaloadr"         : {"value" :282, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1031},
            "plocaloads"         : {"value" :290, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1033},
            "plocaloadt"         : {"value" :298, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1035},
            "plocaloadtot"       : {"value" :306, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1037},
            "ipmtmp"             : {"value" :314, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1039},
            "battemp "           : {"value" :318, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1040},
            "spdspstatus"        : {"value" :322, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1041},
            "spbusvolt"          : {"value" :328, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1042},
            "etousertod"         : {"value" :334, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1044},
            "etousertot"         : {"value" :342, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1046},
            "etogridtod"         : {"value" :350, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1048},
            "etogridtot"         : {"value" :358, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1050},
            "edischarge1tod"     : {"value" :366, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1052},
            "edischarge1tot"     : {"value" :374, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1054},
            "eharge1tod"         : {"value" :382, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1056},
            "eharge1tot"         : {"value" :390, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1058},
            "elocalloadtod"      : {"value" :398, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1060},
            "elocalloadtot"      : {"value" :406, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1062},
            "dwexportlimitap"    : {"value" :414, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1064},
            "epsfac"             : {"value" :426, "length" : 2, "type" : "numx", "divide" : 100, "register" : 1067},
            "epsvac1"            : {"value" :430, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1068},
            "epsiac1"            : {"value" :434, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1069},
            "epspac1"            : {"value" :438, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1070},
            "epsvac2"            : {"value" :446, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1072},
            "epsiac2"            : {"value" :450, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1073},
            "epspac2"            : {"value" :454, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1074},
            "epsvac3"            : {"value" :462, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1076},
            "epsiac3"            : {"value" :466, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1077},
            "epspac3"            : {"value" :470, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1078},
            "loadpercent"        : {"value" :478, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1080},
            "pf"                 : {"value" :482, "length" : 2, "type" : "numx", "divide" : 10, "register" : 1081},
            "bmsstatusold"       : {"value" :486, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1082},
            "bmsstatus"          : {"value" :490, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1083},
            "bmserrorold"        : {"value" :494, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1084},
            "bmserror"           : {"value" :498, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1085},
            "bmssoc"             : {"value" :502, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1086},
            "bmsbatteryvolt"     : {"value" :506, "length" : 2, "type" : "numx", "divide" : 100,  "register" : 1087},
            "bmsbatterycurr"     : {"value" :510, "length" : 2, "type" : "numx", "divide" : 100,  "register" : 1088},
            "bmsbatterytemp"     : {"value" :514, "length" : 2, "type" : "numx", "divide" : 100,  "register" : 1089},
            "bmsmaxcurr"         : {"value" :518, "length" : 2, "type" : "numx", "divide" : 100,  "register" : 1090},
            "bmsgaugerm"         : {"value" :522, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1091},
            "bmsgaugefcc"        : {"value" :526, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1092},
            "bmsfw"              : {"value" :530, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1093},
            "bmsdeltavolt"       : {"value" :534, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1094},
            "bmscyclecnt"        : {"value" :538, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1095},
            "bmssoh"             : {"value" :542, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1096},
            "bmsconstantvolt"    : {"value" :546, "length" : 2, "type" : "numx", "divide" : 100, "register" : 1097},
            "bmswarninfoold"     : {"value" :550, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1098},
            "bmswarninfo"        : {"value" :554, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1099},
            "bmsgaugeiccurr"     : {"value" :558, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1100},
            "bmsmcuversion"      : {"value" :562, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1101},
            "bmsgaugeversion"    : {"value" :566, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1102},
            "bmswgaugefrversionl": {"value" :570, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1103},
            "bmswgaugefrversionh": {"value" :574, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1104},
            "bmsbmsinfo"         : {"value" :578, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1105},
            "bmspackinfo"        : {"value" :582, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1106},
            "bmsusingcap"        : {"value" :586, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1107},
            "uwMaxCellVolt"      : {"value" :590, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1108},
            "uwMinCellVolt"      : {"value" :594, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1109},
            "bModuleNum"         : {"value" :598, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1110},
            "BatNum"             : {"value" :602, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1112},
            "uwMaxVoltCellNo"    : {"value" :606, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1113},
            "uwMinVoltCellNo"    : {"value" :610, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1114},
            "uwMaxTemprCell_10T" : {"value" :614, "length" : 2, "type" : "numx", "divide" : 10,  "register" : 1115},
            "uwMaxTemprCellNo"   : {"value" :618, "length" : 2, "type" : "numx", "divide" : 10,  "register" : 1116},
            "uwMinTemprCelLNo"   : {"value" :622, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1117},
            "ProtectpackID"      : {"value" :626, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1118},
            "MaxSOC"             : {"value" :630, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1119},
            "MinSOC"             : {"value" :634, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1120},
            "BMS_Error2"         : {"value" :638, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1121},
            "BMS_Error3"         : {"value" :642, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1122},
            "BMS_WarnInfo2"      : {"value" :646, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1123},
            "ACChargeEnergyTodH" : {"value" :650, "length" : 2, "type" : "numx", "divide" : 1,  "register" : 1124}     #deze is een beetjevreemd omdat de high en Low over groeprn heen gedefinieerd zijn en uit elkaar liggen
         }}

        self.ALO_1125_1249 = {"ALO_1125_1249": {
            "acchargeenergytoday": {"value" :666, "length" : 2, "type" : "numx", "divide" : 1, "register" : 1125},                                 # vooralsnog ervan uitgegaan dat low alleen genoeg is!
            "acchargeenergytotal": {"value" :670, "length" : 4, "type" : "numx", "divide" : 1, "register" : 1126},
            "acchargepower"      : {"value" :678,"length" : 4, "type" : "numx", "divide" : 1, "register" : 1128},
            "70%_invpoweradjust" : {"value" :686,"length" : 2, "type" : "numx", "divide" : 1, "register" : 1130},
            "extraacpowertogrid" : {"value" :690, "length" : 4, "type" : "numx", "divide" : 1, "register" : 1131},
            "eextratoday"        : {"value" :698, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1133},
            "eextratotal"        : {"value" :704, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1135},
            "esystemtoday"       : {"value" :712, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1137},
            "esystemtotal"       : {"value" :720, "length" : 4, "type" : "numx", "divide" : 10, "register" : 1139}
        }}

        self.ALO_2000_2124 = {"ALO_2000_2124": {
            "pvstatus"           : {"value" :1174, "length" : 2, "type" : "numx", "divide" : 1, "register" : 2000},
            "pac"                : {"value" :1314, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2035},
            "fac"                : {"value" :1322, "length" : 2, "type" : "numx", "divide" : 100,  "register" : 2037},
            "vac1"               : {"value" :1326, "length" : 2, "type" : "numx", "divide" : 10, "register" : 2038},
            "iac1"               : {"value" :1330, "length" : 2, "type" : "numx", "divide" : 10, "register" : 2039},
            "pac1"               : {"value" :1334, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2040},
            "eactoday"           : {"value" :1386, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2053},
            "eactot"             : {"value" :1394, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2055},
            "timetotal"          : {"value" :1402, "length" : 4, "type" : "numx", "divide" : 7200, "register" : 2057},
            "pvtemperature"       : {"value" :1546, "length" : 2, "type" : "numx", "divide" : 10, "register" : 2093},
            "pvimptemperature"   : {"value" :1550, "length" : 2, "type" : "numx", "divide" : 10, "register" : 2094},
            "boostemp"           : {"value" :1554, "length" : 2, "type" : "numx", "divide" : 10, "register" : 2095},
            "Temp4"              : {"value" :1558, "length" : 2, "type" : "numx", "divide" : 10, "register" : 2096},
            "uwbatvoltdsp"       : {"value" :1562, "length" : 2, "type" : "numx", "divide" : 10, "register" : 2097},
            "pbusvoltage"        : {"value" :1566, "length" : 2, "type" : "numx", "divide" : 10, "register" : 2098},
            "nbusvoltage"        : {"value" :1570, "length" : 2, "type" : "numx", "divide" : 10, "register" : 2099},
            "remotectrlen"       : {"value" :1574, "length" : 2, "type" : "numx", "divide" : 1, "register" : 2100},
            "remotectrlpower"    : {"value" :1578, "length" : 2, "type" : "numx", "divide" : 1, "register" : 2101},
            "extraacpowertogrid" : {"value" :1582, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2102},
            "eextratoday"        : {"value" :1590, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2104},
            "eextratotal"        : {"value" :1598, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2106},
            "esystemtoday"       : {"value" :1606, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2108},
            "esystemtotal"       : {"value" :1614, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2110},
            "eacchargetoday"     : {"value" :1622, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2112},
            "eacchargetotal"     : {"value" :1630, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2114},
            "acchargepower"      : {"value" :1638, "length" : 4, "type" : "numx", "divide" : 10, "register" : 2116},
            "priority"           : {"value" :1646, "length" : 2, "type" : "numx", "divide" : 1, "register" : 2118},
            "batterytype"        : {"value" :1650, "length" : 2, "type" : "numx", "divide" : 1, "register" : 2119},
            "autoproofreadcmd"   : {"value" :1654, "length" : 2, "type" : "numx", "divide" : 1, "register" : 2120},
        }}

        self.ALO_3000_3124 = {"ALO_3000_3124": {
            "pvstatus"          : {"value" : 158,"length" : 2,"type" : "num","divide" : 1,"register" : 3000},
            "pvpowerin"         : {"value" : 162,"length": 4,"type" : "numx","divide" : 10,"register" : 3001},
            "pv1voltage"        :{"value" : 170,"length": 2,"type" : "numx","divide" : 10,"register" : 3003},
            "pv1current"        : {"value" : 174,"length": 2,"type" : "numx","divide" : 10,"register" : 3004},
            "pv1watt"           : {"value" : 178,"length": 4,"type" : "numx","divide" : 10,"register" : 3005},
            "pv2voltage"        : {"value" : 186,"length": 2,"type" : "numx","divide" : 10,"register" : 3007},
            "pv2current"        : {"value" : 190,"length": 2,"type" : "numx","divide" : 10,"register" : 3008},
            "pv2watt"           : {"value" : 194,"length": 4,"type" : "numx","divide" : 10,"register" : 3009},
            "pv3voltage"        : {"value" : 202,"length": 2,"type" : "numx","divide" : 10,"register" : 3011},
            "pv3current"        : {"value" : 206,"length": 2,"type" : "numx","divide" : 10,"register" : 3012},
            "pv3watt"           : {"value" : 210,"length": 4,"type" : "numx","divide" : 10,"register" : 3013},
            "pv4voltage"        : {"value" : 218,"length": 2,"type" : "numx","divide" : 10,"register" : 3015},
            "pv4current"        : {"value" : 222,"length": 2,"type" : "numx","divide" : 10,"register" : 3016},
            "pv4watt"           : {"value" : 226,"length": 4,"type" : "numx","divide" : 10,"register" : 3017},
            "qac"               : {"value" : 242,"length": 4,"type" : "numx","divide" : 10,"register" : 3021},
            "pac"               : {"value" : 250,"length": 4,"type" : "numx","divide" : 10,"register" : 3023},
            "pvpowerout"        : {"value" : 250,"length": 4,"type" : "numx","divide" : 10,"register" : 3023},
            "pvfrequency"       : {"value" : 258,"length": 2,"type" : "numx","divide" : 100,"register" : 3025},
            "pvgridvoltage"     : {"value" : 262,"length": 2,"type" : "numx","divide" : 10,"register" : 3026},
            "pvgridcurrent"     : {"value" : 266,"length": 2,"type" : "numx","divide" : 10,"register" : 3027},
            "pvgridpower"       : {"value" : 270,"length": 4,"type" : "numx","divide" : 10,"register" : 3028},
            "pvgridvoltage2"    : {"value" : 278,"length": 2,"type" : "numx","divide" : 10,"register" : 3030},
            "pvgridcurrent2"    : {"value" : 282,"length": 2,"type" : "numx","divide" : 10,"register" : 3031},
            "pvgridpower2"      : {"value" : 286,"length": 4,"type" : "numx","divide" : 10,"register" : 3032},
            "pvgridvoltage3"    : {"value" : 294,"length": 2,"type" : "numx","divide" : 10,"register" : 3034},
            "pvgridcurrent3"    : {"value" : 298,"length": 2,"type" : "numx","divide" : 10,"register" : 3035},
            "pvgridpower3"      : {"value" : 302,"length": 4,"type" : "numx","divide" : 10,"register" : 3036},
            "vacrs"             : {"value" : 310,"length": 2,"type" : "numx","divide" : 10,"register" : 3038},
            "vacst"             : {"value" : 314,"length": 2,"type" : "numx","divide" : 10,"register" : 3039},
            "vactr"             : {"value" : 318,"length": 2,"type" : "numx","divide" : 10,"register" : 3040},
            "ptousertotal"      : {"value" : 322,"length": 4,"type" : "numx","divide" : 10,"register" : 3041},
            "ptogridtotal"      : {"value" : 330,"length": 4,"type" : "numx","divide" : 10,"register" : 3043},
            "ptoloadtotal"      : {"value" : 338,"length": 4,"type" : "numx","divide" : 10,"register" : 3045},
            "totworktime"       : {"value" : 346,"length": 4,"type" : "numx","divide" : 7200,"register" : 3047},
            "eactoday"          : {"value" : 354,"length": 4,"type" : "numx","divide" : 10,"register" : 3049},
            "pvenergytoday"     : {"value" : 354,"length": 4,"type" : "numx","divide" : 10,"register" : 3049},
            "eactotal"          : {"value" : 362,"length": 4,"type" : "numx","divide" : 10,"register" : 3051},
            "pvenergytotal"     : {"value" : 362,"length": 4,"type" : "numx","divide" : 10,"register" : 3051},
            "epvtotal"          : {"value" : 370,"length": 4,"type" : "numx","divide" : 10,"register" : 3053},
            "epv1today"         : {"value" : 378,"length": 4,"type" : "numx","divide" : 10,"register" : 3055},
            "epv1total"         : {"value" : 386,"length": 4,"type" : "numx","divide" : 10,"register" : 3057},
            "epv2today"         : {"value" : 394,"length": 4,"type" : "numx","divide" : 10,"register" : 3059},
            "epv2total"         : {"value" : 402,"length": 4,"type" : "numx","divide" : 10,"register" : 3061},
            "epv3today"         : {"value" : 410,"length": 4,"type" : "numx","divide" : 10,"register" : 3063},
            "epv3total"         : {"value" : 418,"length": 4,"type" : "numx","divide" : 10,"register" : 3065},
            "etousertoday"      : {"value" : 426,"length": 4,"type" : "numx","divide" : 10,"register" : 3067},
            "etousertotal"      : {"value" : 434,"length": 4,"type" : "numx","divide" : 10,"register" : 3069},
            "etogridtoday"      : {"value" : 442,"length": 4,"type" : "numx","divide" : 10,"register" : 3071},
            "etogridtotal"      : {"value" : 450,"length": 4,"type" : "numx","divide" : 10,"register" : 3073},
            "eloadtoday"        : {"value" : 458,"length": 4,"type" : "numx","divide" : 10,"register" : 3075},
            "eloadtotal"        : {"value" : 466,"length": 4,"type" : "numx","divide" : 10,"register" : 3077},
            "epv4today"         : {"value" : 474,"length": 4,"type" : "numx","divide" : 10,"register" : 3079},
            "epv4total"         : {"value" : 482,"length": 4,"type" : "numx","divide" : 10,"register" : 3081},
            "epvtoday"          : {"value" : 490,"length": 4,"type" : "numx","divide" : 10,"register" : 3083},
            "reserved3085"      : {"value" : 498,"length": 2,"type" : "numx","divide" : 1,"register" : 3085, "incl" : "no"},
            "deratingmode"      : {"value" : 502,"length": 2,"type" : "numx","divide" : 1,"register" : 3086},
            "iso"               : {"value" : 506,"length": 2,"type" : "numx","divide" : 1,"register" : 3087},
            "dcir"              : {"value" : 510,"length": 2,"type" : "numx","divide" : 10,"register" : 3088},
            "dcis"              : {"value" : 514,"length": 2,"type" : "numx","divide" : 10,"register" : 3089},
            "dcit"              : {"value" : 518,"length": 2,"type" : "numx","divide" : 10,"register" : 3090},
            "gfci"              : {"value" : 522,"length": 2,"type" : "numx","divide" : 1,"register" : 3091},
            "busvoltage"        : {"value" : 526,"length": 2,"type" : "numx","divide" : 10,"register" : 3092},
            "pvtemperature"     : {"value" : 530,"length": 2,"type" : "numx","divide" : 10,"register" : 3093},
            "pvimptemperature"  : {"value" : 534,"length": 2,"type" : "numx","divide" : 10,"register" : 3094},
            "boosttemperature"  : {"value" : 538,"length": 2,"type" : "numx","divide" : 10,"register" : 3095},
            "temp4"             : {"value" : 542,"length": 2,"type" : "numx","divide" : 10,"register" : 3096},
            "comboardtemperature": {"value" : 546,"length": 2,"type" : "numx","divide" : 10,"register" : 3097},
            "pbusvoltage"       : {"value" : 550,"length": 2,"type" : "numx","divide" : 10,"register" : 3098},
            "nbusvoltage"       : {"value" : 554,"length": 2,"type" : "numx","divide" : 10,"register" : 3099},
            "ipf"               : {"value" : 558,"length": 2,"type" : "numx","divide" : 1,"register" : 3100},
            "realoppercent"     : {"value" : 562,"length": 2,"type" : "numx","divide" : 1,"register" : 3101},
            "opfullwatt"        : {"value" : 566,"length": 4,"type" : "numx","divide" : 10,"register" : 3102},
            "standbyflag"       : {"value" : 574,"length": 2,"type" : "numx","divide" : 1,"register" : 3104},
            "faultmaincode"     : {"value" : 578,"length": 2,"type" : "numx","divide" : 1,"register" : 3105},
            "warnmaincode"      : {"value" : 582,"length": 2,"type" : "numx","divide" : 1,"register" : 3106},
            "faultsubcode"      : {"value" : 586,"length": 2,"type" : "numx","divide" : 1,"register" : 3107},
            "warnsubcode"       : {"value" : 590,"length": 2,"type" : "numx","divide" : 1,"register" : 3108},
            "reserved3109"      : {"value" : 594,"length": 2,"type" : "numx","divide" : 1,"register" : 3109, "incl" : "no"},
            "reserved3110"      : {"value" : 598,"length": 2,"type" : "numx","divide" : 1,"register" : 3110, "incl" : "no"},
            "uwpresentfftvaxxxlue[channela]": {"value" : 602,"length": 2,"type" : "numx","divide" : 1,"register" : 3111},
            "bafcistatus"       : {"value" : 606,"length": 2,"type" : "numx","divide" : 1,"register" : 3112},
            "uwstrength[channela]": {"value" : 610,"length": 2,"type" : "numx","divide" : 1,"register" : 3113},
            "uwselfcheckvalue[channela]": {"value" : 614,"length": 2,"type" : "numx","divide" : 1,"register" : 3114},
            "invstartdelaytime" : {"value" : 618,"length": 2,"type" : "numx","divide" : 1,"register" : 3115},
            "reserved3116"      : {"value" : 622,"length": 2,"type" : "numx","divide" : 1,"register" : 3116, "incl" : "no"},
            "reserved3117"      : {"value" : 626,"length": 2,"type" : "numx","divide" : 1,"register" : 3117, "incl" : "no"},
            "bdconoffstate"     : {"value" : 630,"length": 2,"type" : "numx","divide" : 1,"register" : 3118},
            "drycontactstate"   : {"value" : 634,"length": 2,"type" : "numx","divide" : 1,"register" : 3119},
            "reserved3120"      : {"value" : 638,"length": 2,"type" : "numx","divide" : 1,"register" : 3120, "incl" : "no"},
            "pself"             : {"value" : 642,"length": 4,"type" : "numx","divide" : 10,"register" : 3121},
            "esystoday"         : {"value" : 650,"length": 4,"type" : "numx","divide" : 10,"register" : 3123}
        }}

        self.ALO_3125_3249 = {"ALO_3125_3249": {
            "edischrtoday"      : {"value" : 666,"length": 4,"type" : "numx","divide" : 10,"register" : 3125},
            "edischrtotal"      : {"value" : 674,"length": 4,"type" : "numx","divide" : 10,"register" : 3127},
            "echrtoday"         : {"value" : 682,"length": 4,"type" : "numx","divide" : 10,"register" : 3129},
            "echrtotal"         : {"value" : 690,"length": 4,"type" : "numx","divide" : 10,"register" : 3131},
            "eacchrtoday"       : {"value" : 698,"length": 4,"type" : "numx","divide" : 10,"register" : 3133},
            "eacchrtotal"       : {"value" : 706,"length": 4,"type" : "numx","divide" : 10,"register" : 3135},
            "esystotal"         : {"value" : 714,"length": 4,"type" : "numx","divide" : 1,"register" : 3137},
            "eselftoday"        : {"value" : 722,"length": 4,"type" : "numx","divide" : 10,"register" : 3139},
            "eselftotal"        : {"value" : 730,"length": 4,"type" : "numx","divide" : 10,"register" : 3141},
            "reserved3143"      : {"value" : 738,"length": 2,"type" : "numx","divide" : 1,"register" : 3143},
            "priority"          : {"value" : 742,"length": 2,"type" : "numx","divide" : 1,"register" : 3144},
            "epsfac"            : {"value" : 746,"length": 2,"type" : "numx","divide" : 100,"register" : 3145},
            "epsvac1"           : {"value" : 750,"length": 2,"type" : "numx","divide" : 10,"register" : 3146},
            "epsiac1"           : {"value" : 754,"length": 2,"type" : "numx","divide" : 10,"register" : 3147},
            "epspac1"           : {"value" : 742,"length": 4,"type" : "numx","divide" : 10,"register" : 3144},
            "epsvac2"           : {"value" : 766,"length": 2,"type" : "numx","divide" : 10,"register" : 3150},
            "epsiac2"           : {"value" : 770,"length": 2,"type" : "numx","divide" : 10,"register" : 3151},
            "epspac2"           : {"value" : 774,"length": 4,"type" : "numx","divide" : 10,"register" : 3152},
            "epsvac3"           : {"value" : 782,"length": 2,"type" : "numx","divide" : 10,"register" : 3154},
            "epsiac3"           : {"value" : 786,"length": 2,"type" : "numx","divide" : 10,"register" : 3155},
            "epspac3"           : {"value" : 790,"length": 4,"type" : "numx","divide" : 10,"register" : 3156},
            "epspac"            : {"value" : 798,"length": 4,"type" : "numx","divide" : 10,"register" : 3158},
            "loadpercent"       : {"value" : 806,"length": 2,"type" : "numx","divide" : 10,"register" : 3160},
            "pf"                : {"value" : 810,"length": 2,"type" : "numx","divide" : 10,"register" : 3161},
            "dcv"               : {"value" : 814,"length": 2,"type" : "numx","divide" : 1,"register" : 3162},
            "reserved3163"      : {"value" : 818,"length": 2,"type" : "numx","divide" : 1,"register" : 3163, "incl" : "no"},
            "newbdcflag"        : {"value" : 822,"length": 2,"type" : "numx","divide" : 1,"register" : 3164},
            "bdcderatingmode"   : {"value" : 826,"length": 2,"type" : "numx","divide" : 1,"register" : 3165},
            "sysstatemode"      : {"value" : 830,"length": 2,"type" : "numx","divide" : 1,"register" : 3166},
            "faultcode"         : {"value" : 834,"length": 2,"type" : "numx","divide" : 1,"register" : 3167},
            "warncode"          : {"value" : 838,"length": 2,"type" : "numx","divide" : 1,"register" : 3168},
            "vbat"              : {"value" : 842,"length": 2,"type" : "numx","divide" : 100,"register" : 3169},
            "ibat"              : {"value" : 846,"length": 2,"type" : "numx","divide" : 10,"register" : 3170},
            "soc"               : {"value" : 850,"length": 2,"type" : "numx","divide" : 1,"register" : 3171},
            "vbus1"             : {"value" : 854,"length": 2,"type" : "numx","divide" : 10,"register" : 3172},
            "vbus2"             : {"value" : 858,"length": 2,"type" : "numx","divide" : 10,"register" : 3173},
            "ibb"               : {"value" : 862,"length": 2,"type" : "numx","divide" : 10,"register" : 3174},
            "illc"              : {"value" : 866,"length": 2,"type" : "numx","divide" : 10,"register" : 3175},
            "tempa"             : {"value" : 870,"length": 2,"type" : "numx","divide" : 10,"register" : 3176},
            "tempb"             : {"value" : 874,"length": 2,"type" : "numx","divide" : 10,"register" : 3177},
            "pdischr"           : {"value" : 878,"length": 4,"type" : "numx","divide" : 10,"register" : 3178},
            "pchr"              : {"value" : 886,"length": 4,"type" : "numx","divide" : 10,"register" : 3180},
            "pchrxxxl"          : {"value" : 890,"length": 2,"type" : "numx","divide" : 1,"register" : 3181},
            "edischrtotalstor"  : {"value" : 894,"length": 4,"type" : "numx","divide" : 10,"register" : 3182},
            "echrtotalstor"     : {"value" : 902,"length": 4,"type" : "numx","divide" : 10,"register" : 3184},
            "reserved3186"      : {"value" : 910,"length": 2,"type" : "numx","divide" : 1,"register" : 3186, "incl" : "no"},
            "bdc1flag"          : {"value" : 914,"length": 2,"type" : "numx","divide" : 1,"register" : 3187},
            "vbus2low"          : {"value" : 918,"length": 2,"type" : "numx","divide" : 10,"register" : 3188},
            "bmsmaxvoltcellno"  : {"value" : 922,"length": 2,"type" : "numx","divide" : 1,"register" : 3189},
            "bmsminvoltcellno"  : {"value" : 926,"length": 2,"type" : "numx","divide" : 1,"register" : 3190},
            "bmsbatteryavgtemp" : {"value" : 930,"length": 2,"type" : "numx","divide" : 1,"register" : 3191},
            "bmsmaxcelltemp"    : {"value" : 934,"length": 2,"type" : "numx","divide" : 10,"register" : 3192},
            "bmsbatteryavgtemp2": {"value" : 938,"length": 2,"type" : "numx","divide" : 10,"register" : 3193},
            "bmsmaxcelltemp2"   : {"value" : 942,"length": 2,"type" : "numx","divide" : 1,"register" : 3194},
            "bmsbatteryavgtemp3": {"value" : 946,"length": 2,"type" : "numx","divide" : 1,"register" : 3195},
            "bmsmaxsoc"         : {"value" : 950,"length": 2,"type" : "numx","divide" : 1,"register" : 3196},
            "bmsminsoc"         : {"value" : 954,"length": 2,"type" : "numx","divide" : 1,"register" : 3197},
            "parallelbatterynum": {"value" : 958,"length": 2,"type" : "numx","divide" : 1,"register" : 3198},
            "bmsderatereason"   : {"value" : 962,"length": 2,"type" : "numx","divide" : 1,"register" : 3199},
            "bmsgaugefcc(ah)"   : {"value" : 966,"length": 2,"type" : "numx","divide" : 1,"register" : 3200},
            "bmsgaugerm(ah)"    : {"value" : 970,"length": 2,"type" : "numx","divide" : 1,"register" : 3201},
            "bmserror"          : {"value" : 974,"length": 2,"type" : "numx","divide" : 1,"register" : 3202},
            "bmswarn"           : {"value" : 978,"length": 2,"type" : "numx","divide" : 1,"register" : 3203},
            "bmsfault"          : {"value" : 982,"length": 2,"type" : "numx","divide" : 1,"register" : 3204},
            "bmsfault2"         : {"value" : 986,"length": 2,"type" : "numx","divide" : 1,"register" : 3205},
            "reserved3206"      : {"value" : 990,"length": 2,"type" : "numx","divide" : 1,"register" : 3206, "incl" : "no"},
            "reserved3207"      : {"value" : 994,"length": 2,"type" : "numx","divide" : 1,"register" : 3207, "incl" : "no"},
            "reserved3208"      : {"value" : 998,"length": 2,"type" : "numx","divide" : 1,"register" : 3208, "incl" : "no"},
            "reserved3209"      : {"value" : 1002,"length": 2,"type" : "numx","divide" : 1,"register" : 3209, "incl" : "no"},
            "batisostatus"      : {"value" : 1006,"length": 2,"type" : "numx","divide" : 1,"register" : 3210},
            "battneedchargerequestflag": {"value" : 1010,"length": 2,"type" : "numx","divide" : 1,"register" : 3211},
            "bmsstatus"         : {"value" : 1014,"length": 2,"type" : "numx","divide" : 1,"register" : 3212},
            "bmserror2"         : {"value" : 1018,"length": 2,"type" : "numx","divide" : 1,"register" : 3213},
            "bmswarn2"          : {"value" : 1022,"length": 2,"type" : "numx","divide" : 1,"register" : 3214},
            "bmssoc"            : {"value" : 1026,"length": 2,"type" : "numx","divide" : 1,"register" : 3215},
            "bmsbatteryvolt"    : {"value" : 1030,"length": 2,"type" : "numx","divide" : 100,"register" : 3216},
            "bmsbatterycurr"    : {"value" : 1034,"length": 2,"type" : "numx","divide" : 100,"register" : 3217},
            "bmsbatterytemp"    : {"value" : 1038,"length": 2,"type" : "numx","divide" : 10,"register" : 3218},
            "bmsmaxcurr"        : {"value" : 1042,"length": 2,"type" : "numx","divide" : 100,"register" : 3219},
            "bmsmaxdischrcurr"  : {"value" : 1046,"length": 2,"type" : "numx","divide" : 100,"register" : 3220},
            "bmscyclecnt"       : {"value" : 1050,"length": 2,"type" : "numx","divide" : 1,"register" : 3221},
            "bmssoh"            : {"value" : 1054,"length": 2,"type" : "numx","divide" : 1,"register" : 3222},
            "bmschargevoltlimit": {"value" : 1058,"length": 2,"type" : "numx","divide" : 100,"register" : 3223},
            "bmsdischargevoltlimit": {"value" : 1062,"length": 2,"type" : "numx","divide" : 1,"register" : 3224},
            "bmswarn3"          : {"value" : 1066,"length": 2,"type" : "numx","divide" : 1,"register" : 3225},
            "bmserror3"         : {"value" : 1070,"length": 2,"type" : "numx","divide" : 1,"register" : 3226},
            "reserved3227"      : {"value" : 1074,"length": 2,"type" : "numx","divide" : 1,"register" : 3227, "incl" : "no"},
            "reserved3228"      : {"value" : 1078,"length": 2,"type" : "numx","divide" : 1,"register" : 3228, "incl" : "no"},
            "reserved3229"      : {"value" : 1082,"length": 2,"type" : "numx","divide" : 1,"register" : 3229, "incl" : "no"},
            "bmssinglevoltmax"  : {"value" : 1086,"length": 2,"type" : "numx","divide" : 1,"register" : 3230},
            "bmssinglevoltmin"  : {"value" : 1090,"length": 2,"type" : "numx","divide" : 1,"register" : 3231},
            "batloadvolt"       : {"value" : 1094,"length": 2,"type" : "numx","divide" : 100,"register" : 3232},
            "reserved3233"      : {"value" : 1098,"length": 2,"type" : "numx","divide" : 1,"register" : 3233, "incl" : "no"},
            "debugdata1"        : {"value" : 1102,"length": 2,"type" : "numx","divide" : 1,"register" : 3234, "incl" : "no"},
            "debugdata2"        : {"value" : 1106,"length": 2,"type" : "numx","divide" : 1,"register" : 3235, "incl" : "no"},
            "debugdata3"        : {"value" : 1110,"length": 2,"type" : "numx","divide" : 1,"register" : 3236, "incl" : "no"},
            "debugdata4"        : {"value" : 1114,"length": 2,"type" : "numx","divide" : 1,"register" : 3237, "incl" : "no"},
            "debugdata5"        : {"value" : 1118,"length": 2,"type" : "numx","divide" : 1,"register" : 3238, "incl" : "no"},
            "debugdata6"        : {"value" : 1122,"length": 2,"type" : "numx","divide" : 1,"register" : 3239, "incl" : "no"},
            "debugdata7"        : {"value" : 1126,"length": 2,"type" : "numx","divide" : 1,"register" : 3240, "incl" : "no"},
            "debugdata8"        : {"value" : 1130,"length": 2,"type" : "numx","divide" : 1,"register" : 3241, "incl" : "no"},
            "debugdata9"        : {"value" : 1134,"length": 2,"type" : "numx","divide" : 1,"register" : 3242, "incl" : "no"},
            "debugdata10"       : {"value" : 1138,"length": 2,"type" : "numx","divide" : 1,"register" : 3243, "incl" : "no"},
            "debugdata11"       : {"value" : 1142,"length": 2,"type" : "numx","divide" : 1,"register" : 3244, "incl" : "no"},
            "debugdata12"       : {"value" : 1146,"length": 2,"type" : "numx","divide" : 1,"register" : 3245, "incl" : "no"},
            "debugdata13"       : {"value" : 1150,"length": 2,"type" : "numx","divide" : 1,"register" : 3246, "incl" : "no"},
            "debugdata14"       : {"value" : 1154,"length": 2,"type" : "numx","divide" : 1,"register" : 3247, "incl" : "no"},
            "debugdata15"       : {"value" : 1158,"length": 2,"type" : "numx","divide" : 1,"register" : 3248, "incl" : "no"},
            "debugdata16"       : {"value" : 1162,"length": 2,"type" : "numx","divide" : 1,"register" : 3249, "incl" : "no"}
        }}

        self.ALO_3250_3280 = {"ALO_3250_3280": {
            "pex1": {"value" : 1170,"length": 4,"type" : "numx","divide" : 10,"register" : 3250},
            "pex2": {"value" : 1178,"length": 4,"type" : "numx","divide" : 10,"register" : 3252},
            "eex1today": {"value" : 1186,"length": 4,"type" : "numx","divide" : 10,"register" : 3254},
            "eex2today": {"value" : 1194,"length": 4,"type" : "numx","divide" : 10,"register" : 3256},
            "eex1total": {"value" : 1202,"length": 4,"type" : "numx","divide" : 10,"register" : 3258},
            "eex2total": {"value" : 1210,"length": 4,"type" : "numx","divide" : 10,"register" : 3260},
            "uwbatno": {"value" : 1218,"length": 2,"type" : "numx","divide" : 1,"register" : 3262},
            "batserialnum1": {"value" : 1222,"length": 2,"type" : "numx","divide" : 1,"register" : 3263},
            "batserialnum2": {"value" : 1226,"length": 2,"type" : "numx","divide" : 1,"register" : 3264},
            "batserialnum3": {"value" : 1230,"length": 2,"type" : "numx","divide" : 1,"register" : 3265},
            "batserialnum4": {"value" : 1234,"length": 2,"type" : "numx","divide" : 1,"register" : 3266},
            "batserialnum5": {"value" : 1238,"length": 2,"type" : "numx","divide" : 1,"register" : 3267},
            "batserialnum6": {"value" : 1242,"length": 2,"type" : "numx","divide" : 1,"register" : 3268},
            "batserialnum7": {"value" : 1246,"length": 2,"type" : "numx","divide" : 1,"register" : 3269},
            "batserialnum8": {"value" : 1250,"length": 2,"type" : "numx","divide" : 1,"register" : 3270},
            "reserved3271": {"value" : 1254,"length": 2,"type" : "numx","divide" : 1,"register" : 3271},
            "reserved3272": {"value" : 1258,"length": 2,"type" : "numx","divide" : 1,"register" : 3272},
            "reserved3273": {"value" : 1262,"length": 2,"type" : "numx","divide" : 1,"register" : 3273},
            "reserved3274": {"value" : 1266,"length": 2,"type" : "numx","divide" : 1,"register" : 3274},
            "reserved3275": {"value" : 1270,"length": 2,"type" : "numx","divide" : 1,"register" : 3275},
            "reserved3276": {"value" : 1274,"length": 2,"type" : "numx","divide" : 1,"register" : 3276},
            "reserved3277": {"value" : 1278,"length": 2,"type" : "numx","divide" : 1,"register" : 3277},
            "reserved3278": {"value" : 1282,"length": 2,"type" : "numx","divide" : 1,"register" : 3278},
            "reserved3279": {"value" : 1286,"length": 2,"type" : "numx","divide" : 1,"register" : 3279},
            "bclrtodaydataflag": {"value" : 1290,"length": 2,"type" : "numx","divide" : 1,"register" : 3280},
        }}

        self.alodict.update(self.ALO02)
        self.alodict.update(self.ALO05)
        self.alodict.update(self.ALO06)
        self.alodict.update(self.ALO_0_44V1)
        self.alodict.update(self.ALO_45_89V1)
        self.alodict.update(self.ALO_0_124)
        self.alodict.update(self.ALO_1000_1124)
        self.alodict.update(self.ALO_1125_1249)
        self.alodict.update(self.ALO_2000_2124)
        self.alodict.update(self.ALO_3000_3124)
        self.alodict.update(self.ALO_3125_3249)
        self.alodict.update(self.ALO_3250_3280)

        f = []
        logger.info("Grott process external json layout files")
        for (dirpath, dirnames, filenames) in walk('.'):
            f.extend(filenames)
            break
        for x in f:
            if ((x[0] == 't' or x[0] == 'T') and x.find('.json') > 0):
                logger.info("\t%s", x)
                with open(x) as json_file:
                    dicttemp = json.load(json_file)
                    self.recorddict.update(dicttemp)


        #290 if self.verbose: print("\nGrott layout records loaded")
        if self.verbose: print
        logger.info("Grott layout records loaded")

        for key in self.recorddict :
            #logger.info("\t{0}".format(key,format_multi_line("\t", str(self.recorddict[key]),120)))
            logger.info("\t{0}".format(key))
            logger.debugv("\n{0}\n".format(format_multi_line("\t", str(self.recorddict[key]),120)))

        for key in self.alodict :
            print(logger.level)
            logger.info("\t{0}".format(key))
            logger.debugv("\n{0}\n".format(format_multi_line("\t", str(self.alodict[key]),120)))
