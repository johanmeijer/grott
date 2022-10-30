#Grott Growatt monitor :  Proxy 
#       
# Updated: 2020-10-04
# Version 2.2.1d

import socket
import select
import time
import sys
import struct
import textwrap
from itertools import cycle # to support "cycling" the iterator
import time, json, datetime, codecs
from typing import Dict
## to resolve errno 32: broken pipe issue (only linux)
if sys.platform != 'win32' :
   from signal import signal, SIGPIPE, SIG_DFL

from grottdata import procdata, decrypt

#import mqtt                       
import paho.mqtt.publish as publish

# Changing the buffer_size and delay, you can improve the speed and bandwidth.
# But when buffer get to high or delay go too down, you can broke things
buffer_size = 4096
#buffer_size = 65535


class ProxyPair:

    """ 
    Client/Datalogger <-> Growatt server communication channels
    Unique per client connection
    """
    def __init__(self, logger_sock: socket.socket, growatt_sock: socket.socket):
        self.client = logger_sock
        self.server = growatt_sock


class Forward:
    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            return self.forward
        except Exception as e:
            print(e)
            return False  

class Proxy:

    def __init__(self, conf):
        print("\nGrott proxy mode started")
        ## to resolve errno 32: broken pipe issue (Linux only)
        if sys.platform != 'win32':
            signal(SIGPIPE, SIG_DFL) 
        ## 
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #set default grottip address
        if conf.grottip == "default" : conf.grottip = '0.0.0.0'
        self.server.bind((conf.grottip, conf.grottport))
        #socket.gethostbyname(socket.gethostname())
        try: 
            hostname = (socket.gethostname())    
            print("Hostname :", hostname)
            print("IP : ", socket.gethostbyname(hostname), ", port : ", conf.grottport, "\n")
        except:  
            print("IP and port information not available") 

        self.server.listen(200)
        self.forward_to = (conf.growattip, conf.growattport)
        self.__clients: Dict[int, ProxyPair] = {}  # file descriptor <-> socket pair pointers at runtime
        """ Dataloggers added as clients """
        self.__forwarders: Dict[int, ProxyPair] = {}  # file descriptor <-> socket pair pointers at runtime
        """ Proxy connections to server.growatt added as forwarders """
        self.poller = select.poll()
        self.conf = conf  # conf moved in the class as it's provided on initialization. No need to be passed in every method
        
    def main(self):
        self.poller.register(self.server.fileno(), select.POLLIN)

        while True:
            events = self.poller.poll(1000)  # Once per second or on event 
            for f_no, ev_mask in events:

                """ Proxy Logic """
                if f_no == self.server.fileno():
                    """ Register a new connection and poll for data """
                    self.on_accept()
                    continue
                elif self.__clients.get(f_no):
                    """ Read from client/datalogger socket"""
                    data, flags = self.__clients[f_no].client.recvfrom(buffer_size)
                    if len(data) == 0 and self.conf.verbose:
                        print('Connection closed from client/datalogger')
                elif self.__forwarders.get(f_no):
                    """ Read from server.growatt 
                        Block command logic can be hooked directly here
                    """
                    data, flags = self.__forwarders[f_no].server.recvfrom(buffer_size)
                    if len(data) == 0 and self.conf.verbose:
                        print('Connection closed from server.growatt')
   
                if len(data) == 0:
                    self.on_close(f_no)
                    continue
                else:
                    self.on_recv(f_no, data)

    def on_accept(self):
        forward = Forward().start(self.forward_to[0], self.forward_to[1])
        clientsock, clientaddr = self.server.accept()
        pair = ProxyPair(clientsock, forward)
        if forward:
            if self.conf.verbose: print("\t -", clientaddr, "has connected")

            self.__clients.update({pair.client.fileno(): pair})
            self.__forwarders.update({pair.server.fileno(): pair})
            self.poller.register(pair.client.fileno(), select.POLLIN)
            self.poller.register(pair.server.fileno(), select.POLLIN)
        else:
            if self.conf.verbose: 
                print("\t - Can't establish connection with remote server."),
                print("\t - Closing connection with client side", clientaddr)
            clientsock.close()

    def on_close(self, f_no: int):
        if self.__clients.get(f_no):
            unreg = self.__clients.pop(f_no)
            peer = unreg.client
        else:
            unreg = self.__forwarders.pop(f_no)
            peer = unreg.server
        if self.conf.verbose: 
            #try / except to resolve errno 107: Transport endpoint is not connected 
            try: 
                print("\t -", peer.getpeername(), "has disconnected")
            except:  
                print("\t -", "peer has disconnected")
        self.poller.unregister(unreg.client.fileno())
        self.poller.unregister(unreg.server.fileno())
        try:
            peer.send(b'')  # Send empty packet to the peer and close both connections.
        except:
            pass
        unreg.client.close()
        unreg.server.close()

    def on_recv(self, f_no: int, sock_data: bytes):
        data = sock_data
        conf = self.conf

        if self.__forwarders.get(f_no):
            channel = self.__forwarders[f_no].client
        else:
            channel = self.__clients[f_no].server

        print("")
        print("\t - " + "Growatt packet received:") 
        print("\t\t ", channel)
        # FILTER!!!!!!!! Detect if configure data is sent!
        header = "".join("{:02x}".format(n) for n in data[0:8])
        if conf.blockcmd : 
            #standard everything is blocked!
            blockflag = True 
            #partly block configure Shine commands                   
            if header[14:16] == "18" :         
                if conf.blockcmd : 
                    if header[6:8] == "05" or header[6:8] == "06" : confdata = decrypt(data) 
                    else :  confdata = data

                    #get conf command (location depends on record type), maybe later more flexibility is needed
                    if header[6:8] == "06" : confcmd = confdata[76:80]
                    else: confcmd = confdata[36:40]
                    
                    if header[14:16] == "18" : 
                        #do not block if configure time command of configure IP (if noipf flag set)
                        if conf.verbose : print("\t - Grott: Shine Configure command detected")                                                    
                        if confcmd == "001f" or (confcmd == "0011" and conf.noipf) : 
                            blockflag = False
                            if confcmd == "001f": confcmd = "Time"
                            if confcmd == "0011": confcmd = "Change IP"
                            if conf.verbose : print("\t - Grott: Configure command not blocked : ", confcmd)    
                    else : 
                        #All configure inverter commands will be blocked
                        if conf.verbose : print("\t - Grott: Inverter Configure command detected")
            
            #allow records: 
            if header[12:16] in conf.recwl : blockflag = False     

            if blockflag : 
                print("\t - Grott: Record blocked: ", header[12:16])
                return

        # send data to destination
        """ Forward to the other end of the pair (selected at the entryoint)
        and process the data if meets the requirements
        """
        channel.send(data)
        if len(data) > conf.minrecl :
            #process received data
            procdata(conf,data)    
        else:     
            if conf.verbose: print("\t - " + 'Data less then minimum record length, data not processed') 
                