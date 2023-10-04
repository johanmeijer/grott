import datetime
import os
import json
import requests

def grottext(conf, data, jsonmsg) :
    """
    Grot extension to update the corresponding domoticz energy counters with the latest data
    extvar configuration:
    "domoticz_ip": ip adres of domoticz
    "domoticz_port": port number domoticz
    "serial_id": idx number in domoticz for the corresponding energy counter
    example in grott.ini (2 inverters used, one or more is possible):
        [extension]
        # grott extension parameters definitions
        extension = True
        extname = grottdomo
        extvar = {"domoticz_ip": "127.0.0.1","domoticz_port": "8080",  "TCG2A4XXXX": "2084", "TCG2A4XXXX": "2085"}

    Updated: 2023-10-04
    Version 1.0.0
    """

    resultcode = 0

    if conf.verbose :

        print("\t - " + "Grott extension module entered ")
        ###
        ### uncomment this print statements if you want to see the information that is availble.
        ###

        print(jsonmsg)
        # print(data)
        # print(dir(conf))
        # print(conf.extvar)
    jsonobj = json.loads(jsonmsg)

    values = {
        "device":jsonobj["device"],
        "time":jsonobj["time"],
    }

    for key in jsonobj["values"]:
        # test if there is an divide factor is specifed
        try:
           keydivide =  conf.recorddict[conf.layout][key]["divide"]
        except:
           keydivide = 1
 
        if type(jsonobj["values"][key]) != type(str()) and keydivide != 1:
            values[key] = jsonobj["values"][key]/keydivide
            if key == "totworktime":
                # round totworktime a bit so it doesn't take 18 characters
                values[key] = round(values[key], 2)
        else:
            values[key] = jsonobj["values"][key]
 

    deviceId = jsonobj["device"]
    if conf.verbose :
        print("\nDeviceId = " + deviceId)
        print(values)

    try:
        meter_idx = conf.extvar[deviceId]
    except:
        print ("Meter idx for "+deviceId + " not found, add it to grott.ini in plugin data with the meter id in domoticz")

    domoticz_ip = conf.extvar["domoticz_ip"] 
    domoticz_port = conf.extvar["domoticz_port"]
    power = values["pvgridpower"]
    total = values["pvenergytotal"] * 1000
    new_meter_value =  str(power) + ";" + str(total) 

    domoticz_url = f"http://{domoticz_ip}:{domoticz_port}/json.htm?type=command&param=udevice&idx={meter_idx}&nvalue=0&svalue={new_meter_value}"

    response = requests.get(domoticz_url)
    if conf.verbose :
        if response.status_code == 200:
            print("Meter bijgewerkt met succes! " + domoticz_url)
        else:
            print(f"Fout bijwerken van de meter - Statuscode: {response.status_code}")


    return resultcode
