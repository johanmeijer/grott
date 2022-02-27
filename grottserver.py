# grottserver.py emulates the server.growatt.com website and is initial developed  for debugging and testing grott. 
# Updated: 2022-02-27
# Version: 
verrel = "0.0.2"    

import socketserver
#import json
import textwrap
#import crcmod
import libscrc
# https://pypi.org/project/libscrc/ 

# Declare Variables (to be moved to config file later)

HOST = "0.0.0.0" 
PORT = 5782

# Formats multi-line data
def format_multi_line(prefix, string, size=80):
    size -= len(prefix)
    if isinstance(string, bytes):
        string = ''.join(r'\x{:02x}'.format(byte) for byte in string)
        if size % 2:
            size -= 1
    return '\n'.join([prefix + line for line in textwrap.wrap(string, size)])

#encrypt / decrypt data. 
def decrypt(decdata) :   

    ndecdata = len(decdata)

    # Create mask and convert to hexadecimal
    mask = "Growatt"
    hex_mask = ['{:02x}'.format(ord(x)) for x in mask]    
    nmask = len(hex_mask)

    #start decrypt routine 
    unscrambled = list(decdata[0:8])                                            #take unscramble header
    
    for i,j in zip(range(0,ndecdata-8),cycle(range(0,nmask))): 
        unscrambled = unscrambled + [decdata[i+8] ^ int(hex_mask[j],16)]
    
    result_string = "".join("{:02x}".format(n) for n in unscrambled)
    
    print("\t - " + "Growatt data decrypted V2")   
    return result_string 

class MyTCPHandler(socketserver.BaseRequestHandler):
    payload = "none"    
    payload_dict = {}
    def handle(self):
        while 1:
            # self.request is the TCP socket connected to the client
            self.data = self.request.recv(1024).strip()
            if not self.data:
                    break
            ndata = len(self.data)
            
            #Display data
            print("Grottserver: Data received from : " + format(self.client_address[0]) + ":" + format(self.client_address[1]) )
            print("\t - " + "Grottserver - original Data:") 
            print(format_multi_line("\t\t ", self.data))    
 
            #Create header 
            header = "".join("{:02x}".format(n) for n in self.data[0:8])
            print("\t - " + "Grottserver - Header: ")          
            print(format_multi_line("\t\t ", header))

            #Prepare response

            if header[0:6] == "474554" : 
                #if get do some http processing (future use).  
                print("Grottserver - get received:") 
                httpresponse = "HTTP 200 OK"
                #self.request.sendall(httpresponse)   
            
            elif header[14:16] in ("16") :
                #if ping send data as reply 
                response = self.data
                print("Grottserver: ping received") 
                print("\t - " + "Grottserver - response: ")          
                print(format_multi_line("\t\t ", response))
                self.request.sendall(response)

            elif header[14:16] in ("03", "04", "50", "29", "1b", "20" ) :  
                #if datarecord send ack.  
                print("Grottserver: " + header[12:16] + " data record received") 
                #create ack response
                headerackx = bytes.fromhex(header[0:8] + '0003' + header[12:16] + '47')      
                
                # Create CRC 16 Modbus
                crc16 = libscrc.modbus(headerackx)   

                # create and send response                
                response = headerackx + crc16.to_bytes(2,"big")
                print("\t - " + "Grottserver - response: ")          
                print(format_multi_line("\t\t ", response))
                self.request.sendall(response)   

            elif header[14:16] in ("19") :  
                print("Grottserver: " + header[12:16] + " record received, no response needed") 

            else : 
                print("Grottserver: unknown record received:") 


if __name__ == "__main__":
    #HOST, PORT = "0.0.0.0", 5782
    print("Grottserver - Version: " + verrel)
    print("Grottserver - Started to listen at:", HOST, ":" , PORT)  
    
    #v.0.0.2 improve restartability 
    socketserver.TCPServer.allow_reuse_address = True 
    with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()