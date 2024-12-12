# Register and datalogger documentation 
This document documents the known datalogger and inverter registers settings. These register can be used to control these devices. 
Be aware most of this register behaviour is retrieved from incomplet documentation and / or reversed protocol engenering / emperical research. 
Use it with care and be aware it might damage your devices. Changing the register setting, eg with the grottserver api, is at your own risk.

## datalogger
| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------| 
|4|Interval|update interval|W||Ascii|| e.g 5 or 1 or 0.5|
|31|datetime|current date-time|W||Ascii||e.g 2022-05-17 21:01:50|
|17| growatt_ip|Growatt server ip addres|W||Ascii||set for redirection to Grott e.g. 192.168.0.206|
|18| growatt_port|Growatt server Port|W||Num||set for redirection to Grott e.g. 5279|

## inverter

### Traditional devices (-S/MTL-S)
Available registers per device type:

- -S register range：0-44, 45-89

#### Register 0 - 44

| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------| 
| 15 | LCD-Language | LCD-Language |W|0-5||| 0: Italian;<br />1: English;<br />2: German;<br />3: Spanish;<br />4: French;<br />5: Chinese;<br />6：Polish<br />7：Portugues<br />8：Hungary|    

#### Register 45 - 89

| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------| 
| 45 | Year | 	Inverter time: 4 digit year |W|yyyy|||When writing, the offset from 2000|    
| 46 | Month | 	Inverter time: month |W|1-12||||    
| 47 | Day | 	Inverter time: day |W|1-31||||
| 48 | Hour | 	Inverter time: hour |W|0-23||||
| 49 | Minute | 	Inverter time: minute |W|0-59||||
| 50 | Second | 	Inverter time: second |W|0-59||||


### Current Devices 
Available registers per device type: 

TL-X/TL-XH/TL-XH US (MIN Type): <br/>
03 register range: 0-124, 3000-3124, 3125-3249 (TL-XHUS) <br/>
04 register range: 3000-3124, 3125-3249, 3250-3374 (TL-XH) <br/>

TL3-X (MAX - MID - MAC Type): <br/>
03 register range: 0-124, 125-249 <br/>
04 register range: 0-124, 125-249 <br/>

MAX 1500V - MAX-X LV: <br/>
03 register range: 0-124, 125-249 <br/>
04 register range: 0-124, 125-249, 875-999 <br/>

MOD TL3-XH: <br/>
03 register range: 0-124, 3000-3124 <br/>
04 register range: 3000-3124, 3125-3249 <br/>

Storage (MIX Type): <br/>
03 register range: 0-124, 1000-1124 <br/>
04 register range: 0-124, 1000-1124 <br/>

Storage (SPA Type): <br/>
03 register range: 0-124, 1000-1124 <br/>
04 register range: 1000-1124, 2000-2124, 1125-1249 <br/>

Storage (SPH Type): <br/>
03 register range: 0-124, 1000-1124 <br/>
04 register range: 0-124, 1000-1124, 1125-1249 <br/>

Search for: Growatt-Inverter-Modbus-RTU-Protocol-II-V1-24-English.pdf for protocol version 1.24 for most of these registers below

#### Register 0 - 124
| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------| 
| 15 | LCD-Language | LCD-Language |W|0-5||| 0: Italian;<br />1: English;<br />2: German;<br />3: Spanish;<br />4: French;<br />5: Chinese;<br />6：Polish<br />7：Portugues<br />8：Hungary|    
#### Register 125 - 249
| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------| 
#### Register 1000 - 1249 (Storage Power)
| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------|
| 1000 | Float charge current limit | When charge current battery need is lower than this value, enter nto float charge |W||0.1A|600| CC current|
| 1044 | Priority | ForceChrEn / ForceDischrEn Load first / Bat first / Grid first | | 0:Load (default)  <br/> 1:Battery  <br/>  2:Grid|| 0 | Force Charge En/dis Force Discharge En/dis|
| 1060 | BuckUpsFunEn | Ups function enable or disable | | Enable: 1 Disable: 0 ||||
| 1061 | BuckUPSVoltSet | UPS output voltage | | 0:230 1:208 2:240 || 230v ||
| 1062 | UPSFreqSet | UPS output frequency |W|0:50Hz 1:60Hz || 50Hz ||
| 1070 | GridFirstDischargePowerRate | Discharge Power Rate when Grid First | W | 0-100 | 1% ||| Discharge Power Rate when Grid First |
| 1071 | GridFirstStopSOC | Stop Discharge soc when Grid First | W | 0-100 | 1% || Stop Discharge soc when Grid First |
| 1080 | Grid First Start Time 1 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 |||  
| 1081 | Grid First Stop Time 1 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1082 | Grid First Stop Switch 1 | Enable: 1 Disable: 0 | W | 0 or 1 ||| Grid First enable 1 |
| 1083 | Grid First Start Time 2 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1084 | Grid First Stop Time 2 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1085 | Grid First Stop Switch 2 | Enable: 1 Disable: 0 ForceDischarge <br/> Switch&LCD_SET_FORCE_TRUE_2)==LCD_SET_FORCE_TRUE_2 | W | 0 or 1 |  | | Grid First enable 2 <br/> ForceDischarge; LCD_SET_FORCE_TRUE_2 |
| 1086 | Grid First Start Time 3 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1087 | Grid First Stop Time 3 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1088 | Grid First Stop Switch 3 | Enable: 1 Disable: 0 | W | 0 or 1 ||| Grid First enable 3 |
| 1090 | Bat FirstPower Rate | Charge Power Rate when Bat First | W | 0-100 | 1% || Charge Power Rate when Bat First |
| 1091 | wBat First stop SOC | Stop Charge soc when Bat First | W | 0-100 | 1% || Stop Charge soc when Bat First | 
| 1092 | AC charge Switch | When Bat First Enable: 1 Disable: 0 | W | 0 or 1 ||| AC charge enable |
| 1100 | Bat First Start Time 1 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1101 | Bat First Stop Time 1 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1102 | Bat First on/off Switch 1 | Enable: 1 Disable: 0 | W | 0 or 1 ||| Battery First Enable 1 |
| 1103 | Bat First Start Time 2 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1104 | Bat First Stop Time 2 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1105 | Bat First on/off Switch 2 | Enable: 1 Disable: 0 | W | 0 or 1 ||| Battery First Enable 2 |
| 1106 | Bat First Start Time 3 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1107 | Bat First Stop Time 3 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1108 | Bat First on/off Switch 3 | Enable: 1 Disable: 0 | W | 0 or 1 ||| Battery First Enable 3 |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------|
| 1109 |  | Load First Discharge Stopped Soc | R | 0-100 ||| This is not offical, I worked this out so may not be final <br/> See discussion here: https://github.com/johanmeijer/grott/issues/405|
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------|
| 1110 | Load First Start Time 1 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1111 | Load First Stop Time 1 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1112 | Load First on/off Switch 1 | Enable: 1 Disable: 0 | W | 0 or 1 ||| Load First Enable 1 | 
| 1113 | Load First Start Time 2 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1114 | Load First Stop Time 2 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1115 | Load First on/off Switch 2 | Enable: 1 Disable: 0 | W | 0 or 1 ||| Load First Enable 2 | 
| 1116 | Load First Start Time 3 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1117 | Load First Stop Time 3 | High eight bit: hour Low eight bit: minute | W | 0-23 0-59 ||| 
| 1118 | Load First on/off Switch 3 | Enable: 1 Disable: 0 | W | 0 or 1 ||| Load First Enable 3 | 
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------|
#### Register 3000 - 3124
| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------| 
#### Register 3125 - 3249 
| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------| 


