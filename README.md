# Grott
Growatt inverter monitor

!!!! new in version 2.x : proxy mode. This mode does not require IP forwarding !!!  

The growatt inverter with Shine wifi adapter sends log data to the growatt website at the internet. At this website you can see detailed information on how the inverter is performing. 

I was looking for a way to intercept this information and use it within my home domotica environment. 

Searching at the internet I find some sites where people managed to intercept the data and send this information to the pvoutput website. 
See: 

https://github.com/sciurius/Growatt-WiFi-Tools 

http://123zonne-energie.ning.com/profiles/blogs/growatt-wifi-module-via-raspberry-pi-automatische-upload-naar
(link not available anymore)

Inspired by this solutions, I decided that I want a more generic solution. So I used the ideas and created an own solution based on routing the data via a Raspberry Pi (or any other Linux device) and process the Growatt log data with a python program that sends a JSON message with status information to a MQTT broker (eg MOSQUITTO). 

MQTT can be used to distribute the data to the applications who need it (eg node red, home assistant, domoticz).  

I use node red  to consume the MQTT data, create dashboards and sent it to other receivers like PVoutput or Domoticz. Node red can also enable the use of other tooling like influxDB/Grafana to capature and analyse the data. 

Grott (version 2+) has to modes: sniff and proxy. 

In sniff mode (default and compatable with older Grott versions) IP sniffering technology is used (based on: https://github.com/buckyroberts/Python-Packet-Sniffer). In this mode the data needs to be "re-routed" using linux IP forwarding on the device Grott is running. In this mode Grott "sees" every IP package and when a Growatt TCP packages passes it will be processed and a MQTT will be sent if inverter status information is detected. 

With the new proxy mode Grott is listening on a IP port (default 5279), processes the data (sent MQTT message) and routes the original packet to the growatt website. 

The new mode functionality can be enabled by: 

- mode = proxy in the conf.ini file 
- m proxy parameter during startup

Pro / Cons: 

    sniff mode
    + Data will also be routed to the growatt server if Grott is not active
    - All TCP packages (also not growatt) need to be processed by Grott. 
      This is more resource (processor) intesive and can have a negative impact on the device performance.
    - Configure IP forwarding can be complex if a lot of other network routing is configured (e.g. by Docker). 
    - Sudo rights necessary to allow network sniffering
    
    proxy mode: 
    + Simple configuration 
    + Only Growatt IP records are being analysed and processed by Grott 
    + Less resource intensive 
    + No sudo rights needed
    - If Grott is not running no data will be sent to the Growatt server

The program is written in python and can be started from the command line or linux services. In sniff mode it is necessary to run Grott with SUDO rights. 

Copy grott.service in /etc/systemd/system directory for running grott as a deamon (see wiki how to use services)

Be aware the assumption is that Grott is installed in /home/pi/growatt. grott.service Needs to be modified if an other directory is used. 

The following modules are needed the use Grott:
- grott.py
- grott.ini
- grottconf.py
- grottdata.py
- grottproxy.py
- grottsniffer.py

The Grott monitor is tested on Raspian (RPI) and Ubuntu, with
+ 1500-S (ShineWiFi)
+ 3000-S  (Shinelan)
+ 2500-MTL-S (ShineWiFi)
+ 4200-MTL-S (Shinelan)

Version History: see Version_history.txt file. 
