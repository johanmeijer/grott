#
# grottconf  process command parameter and settings file
# Updated: 2020-05-22

import configparser, sys, argparse

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
        self.valueoffset = 6 
        self.inverterid = "ABC1234567" 
        self.mode = "sniff"
        self.grottport = "5279"
        self.grottip = "0.0.0.0"                                                                    #connect to server IP adress     
        self.outfile ="sys.stdout"

        #Growatt server default 
        self.growattip = "47.91.67.66"
        self.growattport = 5279

        #MQTT default
        self.mqttip = "localhost"
        self.mqttport = 1883
        self.mqtttopic= "energy/growatt"
        self.nomqtt = False                                                                          #not in ini file, can only be changed via start parms
        self.mqttauth = True
        self.mqttuser = "grott"
        self.mqttpsw = "growatt2020"

        print("Grott Growatt logging monitor : " + self.verrel)    

        #proces configuration file
        config = configparser.ConfigParser()
        config.read(self.cfgfile)
        if config.has_option("Generic","minrecl"): self.minrecl = config.getint("Generic","minrecl")
        if config.has_option("Generic","decrypt"): self.decrypt = config.getboolean("Generic","decrypt")
        if config.has_option("Generic","compat"): self.compat = config.getboolean("Generic","compat")
        if config.has_option("Generic","inverterid"): self.inverterid = config.get("Generic","inverterid")
        if config.has_option("Generic","mode"): self.mode = config.get("Generic","mode")
        if config.has_option("Generic","port"): self.grottport = config.getint("Generic","port")
        if config.has_option("Generic","valueoffset"): self.valueoffset = config.get("Generic","valueoffset")
        #if config.has_option("Growatt","ip"): self.growattip = config.get("Growatt","ip")          #not used server address is automatically picked if bind to 0.0.0.0
        if config.has_option("Growatt","port"): self.growattport = config.getint("Growatt","port")
        if config.has_option("MQTT","ip"): self.mqttip = config.get("MQTT","ip")
        if config.has_option("MQTT","port"): self.mqttport = config.getint("MQTT","port")
        if config.has_option("MQTT","topic"): self.mqtttopic = config.get("MQTT","topic")
        if config.has_option("MQTT","auth"): self.mqttauth = config.getboolean("MQTT","auth")
        if config.has_option("MQTT","user"): self.mqttuser = config.get("MQTT","user")
        if config.has_option("MQTT","password"): self.mqttpsw = config.get("MQTT","password")

        #Prepare invert settings
        self.SN = "".join(['{:02x}'.format(ord(x)) for x in self.inverterid])
        self.offset = 6 
        if self.compat: self.offset = int(self.valueoffset)                                       #set offset for older inverter types or after record change by Growatt
        
        #prepare MQTT security
        if not self.mqttauth: self.pubauth = None
        else: self.pubauth = dict(username=self.mqttuser, password=self.mqttpsw)

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
        print("\tvalueoffset: \t",self.valueoffset)
        print("\toffset:      \t",self.offset)
        print("\tinverterid:  \t",self.inverterid)
        print("\tmode:        \t",self.mode)
        #print("\tgrottip      \t",self.grottip)
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

    def parser(self): 
        #Proces commandline paramete rs
        parser = argparse.ArgumentParser(prog='grott')
        parser.add_argument('-v','--verbose',help="set verbose",action='store_true')
        parser.add_argument('--version', action='version', version=self.verrel)
        parser.add_argument('-c',help="set config file if not specified config file is grott.ini",metavar="[config file]")
        parser.add_argument('-o',help="set output file, if not specified output is stdout",metavar="[output file]")
        parser.add_argument('-m',help="set mode (sniff or proxy), if not specified mode is sniff",metavar="[mode]")
        parser.add_argument('-nm','--nomqtt',help="disable mqtt send",action='store_true')
        parser.add_argument('-t','--trace',help="enable trace, use in addition to verbose option (only available in sniff mode)",action='store_true')

        #parser.print_help()
        args = parser.parse_args()
        self.verbose = args.verbose
        self.nomqtt = args.nomqtt
        self.trace = args.trace
        if (args.c != None) : self.cfgfile=args.c
        if (args.o != None) : sys.stdout = open(args.o, 'w')
        if (args.m == "proxy") : 
            self.mode = "proxy"
        else :
            self.mode = "sniff"                                         # default

        if self.verbose : 
            print("\nGrott Command line parameters processed:")
            print("\tverbose:     \t", self.verbose)    
            print("\tconfig file: \t", self.cfgfile)
            print("\toutput file: \t", sys.stdout)
            print("\tnomqtt:      \t", self.nomqtt)
            print("\ttrace:       \t", self.trace)
