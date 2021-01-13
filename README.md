# Grott
## The Growatt inverter monitor 

## Short description: 
The growatt inverter sends log data to the growatt website at the internet. At this website (or with the mobile app) you can see detailed information on how the inverter is performing. 

Grott is monitoring and process this data (containing information about performance and status of the inverter) and send this to: 

* MQTT
* PVOutput.org
* InfluxDB (V1 and V2) 
* Using the extension function you can add your own processing and output functionality, 
 
MQTT can be used to distribute the data to the applications who need it (eg NodeRed, Home Assistant, OpenHab and Domoticz). Descriptions and examples are available in the Wiki 

The program is written in python and runs under Linux, Windows and is available in a docker container on Docker Hub (see: https://github.com/johanmeijer/grott/wiki/Docker-support).  

Grott can be started from the command line or as a (linux or Windows ) service. 

Please see the wiki for more information and installation details. There is also a short first time installation description available. 

# Version History 
## New in Version 2.4.0  
Introduce possibility to add extensions for additional (personalized) processing. 
<br> 
see: https://github.com/johanmeijer/grott/wiki/Extensions

## New in Version 2.3.1  
Direct output to inlfuxdb (v1 and v2)   
<br> 
see: https://github.com/johanmeijer/grott/wiki/InfluxDB-Support
## New in Version 2.2.6  
Mulitiple inverter (multiple system id's) support in PVOutput.org 
<br> 
see: https://github.com/johanmeijer/grott/wiki/PVOutput.org-support 

#### Be aware: Wiith this release the default grott.ini moved to examples directory 
This file is deleted from the grott default directory to simply github installation (not overwrite your settings). 
It is advised to copy this file into the Grott default directory (and customise it) during first time installation 

## New in Version 2.2.1  
#### Automatic protocol detection and processing
Limited .ini configuration needed (inverterid, encryption, offset and record layout is automaticially detected)
#### Direct output to PVOutput.org (no mqtt processing needed). 
Specify pvoutput = True and apikey and systemid in .ini file to enable it. 
#### Docker support 
2 docker containers are created ledidobe/grottrpi (specific old RPI with ARM32) and ledidobe/grott (generic one, tested on synology NAS and Ubuntu). See https://hub.docker.com/search?q=ledidobe&type=image. 
See issue 4 and 15 on how to use it (wiki will be updated soon)
#### Command Blocking / Filtering
with blockcmd = True specified in .ini (configure/reboot) commands from outside to the inverter are blocked. This protects the inverter from beeing controlled from the outside while data exchange with server.growatt.com for reporting is still active.  
#### Use date/time from data record
If date/time is available in the data (inserted by the inverter) this will be used. In this way buffered records will be sent with the original  creation time (in the past). 
If date/time is not available in the data record the server time will be used (as it was originally). 
In the mqtt message the  key buffered is added (yes/no) which indicates that the message is from the buffer (past) or actual. 

## Version 2: Introduction of 2 modes support: sniff and proxy. 

In sniff mode (default and compatable with older Grott versions) IP sniffering technology is used (based on: https://github.com/buckyroberts/Python-Packet-Sniffer). In this mode the data needs to be "re-routed" using linux IP forwarding on the device Grott is running. In this mode Grott "sees" every IP package and when a Growatt TCP packages passes it will be processed and a MQTT will be sent if inverter status information is detected. 

With the proxy mode Grott is listening on a IP port (default 5279), processes the data (sent MQTT message) and routes the original packet to the growatt website. 

The proxy mode functionality can be enabled by: 

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
    + Blocking / Filtering of commands from the outside is possible
    - If Grott is not running no data will be sent to the Growatt server

The adivse is to use the proxy mode. This mode is strategic and will be used for enhanced features like automatic protocol detection and command blocking filtering.  
<br>
Sniff mode is not supported under Windows
<br>
In sniff mode it is necessary to run Grott with SUDO rights. 

*** 

## Grott as a Service 
Copy grott.service in /etc/systemd/system directory for running grott as a deamon (see wiki how to use services for bot Linux as Windows)

Be aware the assumption is that Grott is installed in /home/pi/growatt. grott.service Needs to be modified if an other directory is used. 

## Minimal installation 
The following modules are needed the use Grott:
- grott.py
- grott.ini (available in examples direcory) 
- grottconf.py
- grottdata.py
- grottproxy.py
- grottsniffer.py


### The Grott monitor is tested on Raspian (Raspberry PI),Ubuntu and windows 10 (proxy only), with
+ 1500-S (ShineWiFi)
+ 3000-S  (Shinelan)
+ 2500-MTL-S (ShineWiFi)
+ 4200-MTL-S (Shinelan)
+ 5000TL-X   (ShineWifi-X)
+ 3600TL-XE (ShineLink-X)
+ 3600TL-XE (ShineLan)

## The Docker images are tested RPI(arm32), Ubuntu and Synology NAS

#### More Version History: see Version_history.txt file. 
#### Grott is a "hobby" project you can use it as it is (with the potential errors and imperfections). Remarks and requests for improvement are welcome. 
