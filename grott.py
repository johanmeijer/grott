#Grott Growatt monitor based on TCPIP sniffing or proxy (new 2.0) 
#             
#       Monitor needs to run on a (linux) system that is abble to see TCPIP that is sent from inverter to Growatt Server
#       
#       In the TCPIP sniffer mode this can be achieved by rerouting the growatt WIFI data via a Linux server with port forwarding
#
#       For more information how to see aditional documentation on github 
#
#       Monitor can run in forground and as a standard service!
#
#       For version history see: version_history.txt

# Updated: 2023-01-20

verrel = "2.7.8"

import sys

from grottconf import Conf
from grottproxy import Proxy
from grottsniffer import Sniff

#proces config file
conf = Conf(verrel)

#print configuration
if conf.verbose: conf.print()

#To test config only remove # below
#sys.exit(1)

if conf.mode == 'proxy':
        proxy = Proxy(conf)
        try:
            proxy.main(conf)
        except KeyboardInterrupt:
            print("Ctrl C - Stopping server")
            try: 
                proxy.on_close(conf)
            except:     
                print("\t - no ports to close")
            sys.exit(1)

if conf.mode == 'sniff':
        sniff = Sniff(conf)
        try: 
            sniff.main(conf)
        except KeyboardInterrupt:
            print("Ctrl C - Stopping server")
            sys.exit(1)

else:
    print("- Grott undefined mode")