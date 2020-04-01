# Grott
Growatt inverter monitor

The growatt inverter with shine wifi adapter sends log data to the growatt (website) at the internet. At this website you can see detailed information on how the inverter is performing. 

I was looking for a way the intercept this information and use it for my home domotica environment. 

Searching at the internet I find some site where people managed to intercept the data and send this information to pvoutput website. 
See: 

https://github.com/sciurius/Growatt-WiFi-Tools 

http://123zonne-energie.ning.com/profiles/blogs/growatt-wifi-module-via-raspberry-pi-automatische-upload-naar

Inspired by this solutions, I decided that I want a more generic solution. So I use the ideas and created an own solution based on routing the data (IP forwarding) via a Raspberry Pi and capture the growatt log data with a python ip packet sniffer (based on: https://github.com/buckyroberts/Python-Packet-Sniffer ) that sends a JSON message to a MQTT broker (eg MOSQUITTO). 

With node red it is possible to connect to use the MQTT data and create dashboard or sent it to other receivers like pvoutput or Domoticz. 

The program is written in python and can be started from the command line or linux services. Because the program is using sockets to capature the data, it is necessary to run it with SUDO rights. 

Version 1.0.4: enables configuration file and commandline based parameter specification

Version 1.0.6: fix error with parameter processing from .ini file (compat = True / valueoffset = xx) 

Version 1.0.7: fix error with unscrambled growatt record (shinelan support) and add option for mqtt user/password authentication

Copy grott.service in /etc/systemd/system directory for running grott as a deamon (see wiki how to use services)
Be aware the assumption is that grott.py and grott.ini are installed in /home/pi/growatt. grott.service need to be modified if other directory is used. 

The Grott monitor is tested with a Growatt 1500-s inverter with a ShineWIFI-S wifi device

***************************************
Since 23 March 2020 the Growatt record layout seems to be changed. For my configuration it is needed to change .ini file with:

compat = True

valueoffset = 26

Be aware to use a actual version of  grott.py (1.0.6 or above) for correct parameter processing
***************************************
