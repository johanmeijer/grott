import datetime
import os
import json

def open_makedirs(filename, *args, **kwargs):
    """ Open file, creating the parent directories if neccesary. """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    return open(filename, *args, **kwargs)

def grottext(conf, data, jsonmsg) :
    """
    Grot extension to log data to CSV file
    One CSV file per day is saved.
    extvar configuration:
    "outpath": path where to save CSV files, default: "/home/pi/grottlog"
    "csvheader": comma separated string with fields to store, defaults to all available fields
    Updated: 2022-01-05
    Version 2.6.1
    """

    resultcode = 0

    if conf.verbose :

        print("\t - " + "Grott extension module entered ")
        ###
        ### uncomment this print statements if you want to see the information that is availble.
        ###

        # print(jsonmsg)
        # print(data)
        # print(dir(conf))
        # print(conf.extvar)

    jsonobj = json.loads(jsonmsg)

    try:
        outpath = conf.extvar["outpath"]
    except:
        outpath = "/home/pi/grottlog"
    try:
        csvheader = conf.extvar["csvheader"]
    except:
        csvheader = "device,time," + ",".join(jsonobj["values"].keys())
    csventries = [s.strip() for s in csvheader.split(',')]

    now = datetime.datetime.now()
    csvfile = os.path.join(outpath, '{0.year}-minute/{0.year}{0.month:02}{0.day:02}.csv'.format(now))

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

    csvline = ','.join(str(values[k]) for k in csventries) + '\n'

    if conf.verbose :
        print("csvfile: ", csvfile)
        print("csvheader: ", csvheader)
        print("csvline: ", csvline)

    with open_makedirs(csvfile, 'a') as f:
        if os.path.getsize(csvfile) == 0:
            f.write(csvheader + '\n')
        f.write(csvline)

    return resultcode
