################################################################
Do not use this script. Writing to a register to much can damage the eeprom!!!!!!!
Use for inspiration only
################################################################

{"""Grottman manage inverter"""
import configparser, sys, argparse, os, json, io
import ipaddress
from os import walk
import logging
from paho.mqtt import client as mqtt_client
#from paho.mqtt import publish as publish
import json, requests,time
#set logging definities
#logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
vrmman = "3.1.0_20250504"
#MQTT definition
mqtt_ip = "192.168.0.206"
mqtt_port = 1883
mqtt_topic = "energy/grottman"
p1_topic = "ledomo/domo_p1meter/electricity/"
gw_topic = "energy/growatt"
mqtt_clientid = "grottman"
#grott defintion
grottapi_ip = "192.168.0.206"
grottapi_port = 5782
#Inverter definition
inverter_id = "KLM0CLL0G5"
inv_powerrate = 3600
pchar_reg = 3047
pdchar_reg = 3036
#Max charge step
pchar_maxstep = 5
#where to start with ico mode switch
pchar_basevalue = 10
#Max dcharge step
pdchar_maxstep = 5
#where to start with ico mode switch
pdchar_basevalue = 8
logger.info("grottman started: %s",vrmman)

class grottman:
    def __init__(self):
        logger.info("grottman started: %s",vrmman)
        #init api request
        self.apijson = {}
        self.apijson["inverter"] = inverter_id
        self.apijson["command"] = "register"
        self.apiurl = f"http://{grottapi_ip}:{grottapi_port}/inverter"
        self.newpchar = 0
        self.newpdchar = 0
        self.initpriority = True
        self.oldpriority = 99

    def connect_mqtt(self) :
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("Connected to MQTT Broker!")
            else:
                logger.info("Failed to connect, return code %d\n", rc)

        try:
            mqttc = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
        except:
            mqttc = mqtt_client.Client(mqtt_clientid)
        # client.username_pw_set(username, password)
        mqttc.on_connect = on_connect
        mqttc.connect(mqtt_ip, mqtt_port)
        return mqttc

    def getinvreg(self,register):
        apiurl = f"http://{grottapi_ip}:{grottapi_port}/inverter"
        apijson = {}
        apijson["inverter"] = inverter_id
        apijson["command"] = "register"
        apijson["register"] = register
        getreturn = 0
        while getreturn !=200 :
              r = requests.get(apiurl, params=apijson)
              getreturn = r.status_code
              if getreturn != 200 :
                logger.debug("Http error reading inverter register: %s, retry",register)

        value = r.json()["value"]
        return value

        # try:
        #     r = requests.get(apiurl, params=apijson)
        #     value = r.json()["value"]
        #     if r.status_code != 200 :
        #         logger.debug("Http error reading inverter register: %s",register)
        # except Exception as e:
        #     logger.debug("error reading inverter register: {0},{1}".format(register,e))
        return value

    def putinvreg(self,register,value):
        apiurl = f"http://{grottapi_ip}:{grottapi_port}/inverter"
        apijson = {}
        apijson["inverter"] = inverter_id
        apijson["command"] = "register"
        apijson["register"] = register
        apijson["value"] = value
        try:
            r = requests.put(apiurl, params=apijson)
            if r.status_code != 200 :
                logger.debug("Http error writingg inverter register: %s",register)
        except Exception as e:
            logger.debug("error writing inverter register: {0},{1}".format(register,e))
        return r.status_code

    def mqttpublish(self,client,mqttmsg):
        try:
            client.publish(mqtt_topic, mqttmsg)
            logger.debug('MQTT message message sent')
        except TimeoutError:
            logger.debug('MQTT connection time out error')
        except ConnectionRefusedError:
            logger.debug('MQTT connection refused by target')
        except BaseException as error:
            logger.debug('MQTT send failed:', str(error))

    def subscribe(self,client: mqtt_client):

        def on_message(client, userdata, msg):
            logger.debug("Received {0} from {1}".format (msg.payload.decode(),msg.topic))
            #print(self.apiurl)
            try:
                self.pchar
                self.pdchar
            except:
                    logger.info("Read current pcharge/pdcharge values")
                    try:
                        self.pchar = self.getinvreg(pchar_reg)
                        self.pdchar = self.getinvreg(pdchar_reg)
                        logger.info("Start value pchar: {0}. pdchar: {1}".format(self.pchar,self.pdchar))
                    except Exception as e:
                        resultcode = e
                        logger.debug("Get pchar/pdchar response: %s, will try again next cycle",resultcode)
                        return
            if msg.topic == p1_topic :
                p1_message = json.loads(msg.payload.decode())
                actualpower = p1_message["data"]["EactR"] - p1_message["data"]["EactD"]
                logger.debug("actual power: {0}, EactR: {1}, EactD: {2}".format(actualpower, p1_message["data"]["EactR"], p1_message["data"]["EactD"]))
                logger.debug("pchar: {0}, pdchar: {1}".format(self.pchar,self.pdchar))
                # if al info is there start processing
                try:
                    self.pchar
                    self.pdchar
                    self.soc
                    self.priority

                except Exception as e:
                    logger.info("Not all values initialised, will wait for next cycle: %s",e)
                    return
                logger.debug("Start calaculating inverter settings")
                if self.priority == 1 :
                    logger.debug("Mode: Battery First")
                    if self.priority != self.oldpriority:
                        logger.debug("Mode Switched from {0}, to {1}".format(self.oldpriority,self.priority))
                        # priority change reset pdchar values to base value:
                        putreturn = 0
                        while putreturn != 200 :
                            self.pchar = pchar_basevalue
                            putreturn = self.putinvreg(pchar_reg,self.pchar)
                        self.oldpriority = self.priority
                        logger.debug("Mode switched to Grid First, pchar set to base value: %s",self.pchar)

                    if self.soc != 100:
                        logger.debug("calculate and set charge percentage")
                        self.newpchar = int(round(self.pchar - actualpower/(inv_powerrate/100)))
                        #Limit steps
                        if self.newpchar > self.pchar+pchar_maxstep : self.newpchar = self.pchar+pchar_maxstep
                        if self.newpchar < self.pchar-pchar_maxstep : self.newpchar = self.pchar-pchar_maxstep
                        #limit charge power to 1980
                        if self.newpchar > 55 : self.newpchar = 55
                        if self.newpchar < 0 : self.newpchar = 0

                        logger.debug("current pchar: {0}, calculated pchar: {1}, actualpower: {2}".format(self.pchar,self.newpchar,actualpower))

                        if self.newpchar != self.pchar:
                            try:
                                    putreturn = self.putinvreg(pchar_reg,self.newpchar)
                                    #print("putreturn",putreturn)
                                    if putreturn == 200:
                                        mqttjson = {}
                                        mqttjson["actualpower"] = actualpower
                                        mqttjson["pchar"] = self.pchar
                                        mqttjson["newpchar"] = self.newpchar
                                        mqttjson["pdchar"] = self.pdchar
                                        mqttjson["newpdchar"] = self.newpdchar
                                        mqttmsg = json.dumps(mqttjson)
                                        try:
                                            mqttp = self.mqttpublish(client,mqttmsg)
                                        except Exception as e:
                                            logger.debug("mqttp failed, return : {0}. error: {1}".format(mqttp,e))

                                        self.pchar = self.newpchar
                                        logger.debug("Put pchar change succesfull new value:  %s",self.pchar)
                                    else:
                                        logger.debug("Put pchar error %s, value not changed", putreturn)
                            except Exception as e:
                                    logger.debug("put pchar/pdchar response: %s, will try again next cycle",e)
                        else:
                            logger.debug("No pchar change needed")
                    else:
                        logger.debug("Battery fully charged, do nothing")
                        return

                if self.priority == 2    :
                    logger.debug("Mode: Grid First")
                    if self.priority != self.oldpriority:
                        logger.debug("Mode Switched from {0}, to {1}".format(self.oldpriority,self.priority))
                        # priority change reset pdchar values to base value:
                        putreturn = 0
                        while putreturn != 200 :
                            self.pdchar = pchar_basevalue
                            putreturn = self.putinvreg(pdchar_reg,self.pchar)
                        self.oldpriority = self.priority
                        logger.debug("Mode switched to Grid First, pchar set to base value: %s",self.pchar)

                    if self.soc > 10:
                       logger.debug("calculate and set decharge percentage")
                       self.newpdchar = int(round(self.pdchar + actualpower/(inv_powerrate/100)))
                       #Limit steps
                       if self.newpdchar > self.pdchar+pdchar_maxstep : self.newpchar = self.pdchar+pdchar_maxstep
                       if self.newpdchar < self.pdchar-pdchar_maxstep : self.newpchar = self.pdchar-pdchar_maxstep
                       # limit discharge power to 50*36 (1800)
                       if self.newpdchar > 50 : self.newpdchar = 50
                       if self.newpdchar < 0 : self.newpdchar = 0

                       logger.debug("current pdchar: {0}, calculated pdchar: {1}, actualpower: {2}".format(self.pdchar,self.newpdchar,actualpower))
                       if self.newpdchar != self.pdchar:
                            try:
                                    putreturn = self.putinvreg(pdchar_reg,self.newpdchar)
                                    #print("putreturn",putreturn)
                                    if putreturn == 200:

                                        mqttjson = {}
                                        mqttjson["actualpower"] = actualpower
                                        mqttjson["pchar"] = self.pchar
                                        mqttjson["newpchar"] = self.newpchar
                                        mqttjson["pdchar"] = self.pdchar
                                        mqttjson["newpdchar"] = self.newpdchar
                                        mqttmsg = json.dumps(mqttjson)

                                        try:
                                            mqttp = self.mqttpublish(client,mqttmsg)
                                        except Exception as e:
                                            logger.debug("mqttp failed, return : {0}. error: {1}".format(mqttp,e))

                                        self.pdchar = self.newpdchar
                                        logger.debug("Put pdchar change succesfull new value:  %s",self.pdchar)

                                    else:
                                        logger.debug("Put pdchar error %s, value not changed", putreturn)
                            except Exception as e:
                                    logger.debug("put pchar/pdchar response: %s, will try again next cycle",e)
                       else:
                            logger.debug("No pdchar change needed")
                    else:
                       logger.debug("Battery below 10%, stop decharging")
                return

            if msg.topic == gw_topic :
                logger.debug("Growatt message receive: %s",gw_topic)
                gw_message = json.loads(msg.payload.decode())
                self.soc = gw_message["values"]["soc"]
                self.priority = gw_message["values"]["priority"]
                #print("gw_message:", gw_message)
                #print("soc",self.soc)
                #print("priority",self.priority)

        def on_publish(client, userdata, mid):
            logger.debug("on_publish, mid {}".format(mid))

        client.subscribe(p1_topic)
        client.subscribe(gw_topic)
        client.on_message = on_message
        #client.on_publish = on_publish

    def run(self):
        client = self.connect_mqtt()
        self.subscribe(client)
        client.loop_forever()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    runman = grottman()
    runman.run()

}
