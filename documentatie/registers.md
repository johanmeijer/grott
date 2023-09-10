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

### Current Devices 
Available registers per device type: 

- TL-X/TL-XH/TL-XH US（MIN Type): register range：0-124, 3000-3124, 3125-3249(TL-XHUS)
- TL3-X(MAX、MID、MAC Type): register range：0-124, 125-249；
- MAX 1500V、MAX-X LV: register range：0-124, 125-249；
- MOD TL3-XH: register range：0-124, 3000-3124
- Storage(MIX Type)：register range：0-124, 1000-1124
- Storage(SPA Type)：register range：0-124, 1000-1124
- Storage(SPH Type)：register range：0-124, 1000-1124

#### Register 0 - 124
| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------| 
| 15 | LCD-Language | LCD-Language |W|0-5||| 0: Italian;<br />1: English;<br />2: German;<br />3: Spanish;<br />4: French;<br />5: Chinese;<br />6：Polish<br />7：Portugues<br />8：Hungary|    
#### Register 125 - 249
| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------| 
#### Register 3000 - 3124
| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------| 
#### Register 3125 - 3249 
| Reg  | Name              | Description      | Write | Value   |Unit |Initial| Note                                                               |
| ---- | ----------------- | ---------------- |-------|---------|-----|-------| -------------------------------------------------------------------| 



