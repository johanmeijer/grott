#Grott Growatt monitor :  Proxy 
#       
# Updated: 2020-05-22

import socket
import select
import time
import sys
import struct
import textwrap
from itertools import cycle # to support "cycling" the iterator
import time, json, datetime, codecs

from grottdata import procdata

#import mqtt                       
import paho.mqtt.publish as publish

# Changing the buffer_size and delay, you can improve the speed and bandwidth.
# But when buffer get to high or delay go too down, you can broke things
#buffer_size = 4096
buffer_size = 65535
delay = 0.0001

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
    input_list = []
    channel = {}

    def __init__(self, conf):
        if conf.verbose: 
            print("")
            print("\nGrott proxy mode started\n")
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((conf.grottip, conf.grottport))
        self.server.listen(200)
        self.forward_to = (conf.growattip, conf.growattport)
        
    def main(self,conf):
        self.input_list.append(self.server)
        while 1:
            time.sleep(delay)
            ss = select.select
            inputready, outputready, exceptready = ss(self.input_list, [], [])
            for self.s in inputready:
                if self.s == self.server:
                    self.on_accept(conf)
                    break
                self.data, self.addr = self.s.recvfrom(buffer_size)
                if len(self.data) == 0:
                    self.on_close(conf)
                    break
                else:
                    self.on_recv(conf)

    def on_accept(self,conf):
        forward = Forward().start(self.forward_to[0], self.forward_to[1])
        clientsock, clientaddr = self.server.accept()
        if forward:
            if conf.verbose: print("\t -", clientaddr, "has connected")
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
        else:
            if conf.verbose: 
                print("\t - Can't establish connection with remote server."),
                print("\t - Closing connection with client side", clientaddr)
            clientsock.close()

    def on_close(self,conf):
        if conf.verbose: print("\t -", self.s.getpeername(), "has disconnected")
        #remove objects from input_list
        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        # close the connection with client
        self.channel[out].close()  # equivalent to do self.s.close()
        # close the connection with remote server
        self.channel[self.s].close()
        # delete both objects from channel dict
        del self.channel[out]
        del self.channel[self.s]

    def on_recv(self,conf):
        data = self.data      
        print("")
        print("\t - " + "Growatt packet received:") 
        print("\t\t ", self.channel[self.s])
        # send data to destination
        self.channel[self.s].send(data)
        if len(data) > conf.minrecl :
            #process received data
            procdata(conf,data)    
        else:     
            if conf.verbose: print("\t - " + 'Data less then minimum record length, data not processed') 
                