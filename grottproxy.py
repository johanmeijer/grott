"""Grott Growatt monitor :  Proxy """
# Updated: 2024-10-27
# Version 3.0.0
import logging
import socket
import select
import time
import sys
from grottdata import procdata, decrypt, format_multi_line
vrmproxy = "3.0.0_241019"

## to resolve errno 32: broken pipe issue (only linux)
if sys.platform != 'win32' :
    from signal import signal, SIGPIPE, SIG_DFL

#set logging definities
logger = logging.getLogger(__name__)

# Changing the buffer_size and delay, you can improve the speed and bandwidth.
# But when buffer get to high or delay go too down, you can broke things
buffer_size = 4096
#buffer_size = 65535
delay = 0.0002

def calc_crc(data):
    """"calculate CR16, Modbus."""
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for i in range(8):
            if (crc & 1) != 0:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc

def validate_record(xdata):
    """ validata data record on length and CRC (for "05" and "06" records)"""
    logger.debug("Data record validation started")
    data = bytes.fromhex(xdata)
    ldata = len(data)
    len_orgpayload = int.from_bytes(data[4:6],"big")
    header = "".join("{:02x}".format(n) for n in data[0:8])
    protocol = header[6:8]
    returnmsg = "ok"
    crc = 0

    if protocol in ("05","06"):
        lcrc = 4
        crc = int.from_bytes(data[ldata-2:ldata],"big")
    else:
        lcrc = 0

    len_realpayload = (ldata*2 - 12 -lcrc) / 2

    if protocol != "02" :

        try:
            crc_calc = calc_crc(data[0:ldata-2])
        except:
            crc_calc = crc = 0

    if len_realpayload == len_orgpayload :
        returncc = 0
        if protocol != "02" and crc != crc_calc:
            returnmsg = "data record crc error"
            returncc = 8
    else :
        returnmsg = "data record length error"
        returncc = 8

    return(returncc,returnmsg)


class Forward:
    """"DEFINE FORWARD CONNECTION"""
    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        """start forward connection"""
        try:
            self.forward.connect((host, port))
            return self.forward
        except Exception as e:
            logger.critical("Proxy forward error : %s", e)
            return False

class Proxy:
    """Proxy main class"""
    input_list = []
    channel = {}

    def __init__(self, conf):
        #set loglevel
        logger.setLevel(conf.loglevel.upper())
        conf.vrmproxy = vrmproxy
        logger.info("Grott proxy mode started, version: %s",conf.vrmproxy)

        ## to resolve errno 32: broken pipe issue (Linux only)
        if sys.platform != 'win32':
            signal(SIGPIPE, SIG_DFL)
        #
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #set default grottip address
        if conf.grottip == "default" :
            conf.grottip = '0.0.0.0'
        self.server.bind((conf.grottip, conf.grottport))
        #socket.gethostbyname(socket.gethostname())
        try:
            hostname = socket.gethostname()
            logger.info("\t - Hostname : %s", hostname)
            testip = socket.gethostbyname(hostname)
            logger.info("\t - IP : {0}, port : {1}".format(testip,conf.grottport))
        except Exception as e:
            logger.warning("IP and port information not available: %s",e)

        self.server.listen(200)
        self.forward_to = (conf.growattip, conf.growattport)

    def main(self,conf):
        """proxy main routine"""
        self.input_list.append(self.server)
        while 1:
            time.sleep(delay)
            ss = select.select
            inputready, outputready, exceptready = ss(self.input_list, [], [])
            for self.s in inputready:
                if self.s == self.server:
                    self.on_accept()
                    break
                try:
                    #read buffer until empty!
                    msgbuffer = b''
                    while True:
                        part = self.s.recv(buffer_size)
                        msgbuffer += part
                        if len(part) < buffer_size:
                        # either 0 or end of data
                            break
                    #self.data, self.addr = self.s.recvfrom(buffer_size)
                except Exception as e:
                    logger.warning("Connection error: %s",e)
                    logger.debug("Socket info:\n\t %s",self.s)
                    self.on_close()
                    break
                if len(msgbuffer) == 0:
                    self.on_close()
                    break
                else:
                    #split buffer if contain multiple records
                    self.header = "".join("{:02x}".format(n) for n in msgbuffer[0:8])
                    self.protocol = self.header[6:8]
                    self.datalength = int(self.header[8:12],16)
                    #reclength = int.from_bytes(msgbuffer[4:6],"big")
                    buflength = len(msgbuffer)
                    #total reclength is datarec + buffer (+ crc)
                    if self.protocol in ("05","06"):
                        reclength = self.datalength + 8
                    else :
                        reclength = self.datalength + 6
                    while reclength <= buflength:
                        logger.debugv("Received buffer:\n{0} \n".format(format_multi_line("\t",msgbuffer,120)))
                        self.data = msgbuffer[0:reclength]
                        self.on_recv(conf)
                        if buflength > reclength :
                            logger.debug("handle_readble_socket, Multiple records in buffer, process next message in buffer")
                            msgbuffer = msgbuffer[reclength:buflength]
                            self.header = "".join("{:02x}".format(n) for n in msgbuffer[0:8])
                            self.protocol =self.header[6:8]
                            self.datalength = int(self.header[8:12],16)
                            if self.protocol in ("05","06"):
                                reclength = self.datalength + 8
                            else :
                                reclength = self.datalength + 6
                            buflength = len(msgbuffer)
                        else: break

    def on_accept(self):
        """accept new connection"""
        forward = Forward().start(self.forward_to[0], self.forward_to[1])
        clientsock, clientaddr = self.server.accept()
        if forward:
            logger.info("Client connection from: %s", clientaddr)
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
        else:
            logger.warning("Can't establish connection with remote server")
            logger.warning("Closing connection with client side: %s", clientaddr)
            clientsock.close()

    def on_close(self):
        """close connection"""
        logger.info("Close connection requested for: %s",self.s)
        #try / except to resolve errno 107: Transport endpoint is not connected
        try:
            logger.info("{0} disconnected".format(self.s.getpeername()))
        except:
            logger.info("Peer already disconnected")

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
        """process received data"""
        data = self.data
        logger.debug("Growatt packet received:")
        logger.debug(" - %s",self.channel[self.s])
        #
        #test if record is not corrupted
        vdata = "".join("{:02x}".format(n) for n in data)
        validatecc = validate_record(vdata)
        if validatecc[0] != 0 :
            logger.warning("Invalid data record received: %s, processing stopped for this record",validatecc[1])
            logger.debugv("Original data:\n{0} \n".format(format_multi_line("\t",self.data,120)))
            #Create response if needed?
            return
        # FILTER!!!!!!!! Detect if configure data is sent!
        if conf.blockcmd :
            #standard everything is blocked!
            logger.debug("Command block checking started")
            blockflag = True
            #partly block configure Shine commands
            if self.header[14:16] == "18" :
                if conf.blockcmd :
                    if self.protocol == "05" or self.protocol == "06" :
                        confdata = decrypt(data)
                    else :  confdata = data
                    #
                    #get conf command (location depends on record type), maybe later more flexibility is needed
                    if self.protocol == "06" :
                        confcmd = confdata[76:80]
                    else:
                        confcmd = confdata[36:40]
                    #
                    if self.header[14:16] == "18" :
                        #do not block if configure time command of configure IP (if noipf flag set)
                        logger.debug("Datalogger Configure command detected")
                        if confcmd == "001f" or (confcmd == "0011" and conf.noipf) :
                            blockflag = False
                            if confcmd == "001f":
                                confcmd = "Time"
                            if confcmd == "0011":
                                confcmd = "Change IP"
                            logger.info("Datalogger configure command not blocked : %s ", confcmd)
                    else :
                        #All configure inverter commands will be blocked
                        logger.debug("Inverter Configure command detected")
            #allow records:
            if self.header[12:16] in conf.recwl :
                blockflag = False
                logger.debug("Record not blocked, while in exception list: %s ", self.header[12:16])

            if blockflag :
                logger.info("Record blocked: %s", self.header[12:16])
                if self.protocol == "05" or self.protocol == "06" :
                    blockeddata = decrypt(data)
                else :  blockeddata = data
                logger.debugv("\n{0} \n".format(format_multi_line("\t", blockeddata, 120)))
                return

        # send data to destination
        self.channel[self.s].send(data)
        if len(data) > conf.minrecl :
            #process received data
            procdata(conf,data)
        else:
            logger.debug("Data less then minimum record length, data not processed")
