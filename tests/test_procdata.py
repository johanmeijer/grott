import pytest
from unittest.mock import patch, Mock
import json

from grottconf import Conf
import grottdata

class TestProcData:


    # Record layout used :  T06NNNNSPF
    #
    # Apr 10 16:36:39 europa grott[145191]:          - Grott values retrieved:
    # Apr 10 16:36:39 europa grott[145191]:                  -  datalogserial        :  DDD0CAB191
    # Apr 10 16:36:39 europa grott[145191]:                  -  pvserial             :  GYH2BLL080
    # Apr 10 16:36:39 europa grott[145191]:                  -  pvstatus             :  2
    # Apr 10 16:36:39 europa grott[145191]:                  -  vpv1                 :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  vpv2                 :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  ppv1                 :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  ppv2                 :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  buck1curr            :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  buck2curr            :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  op_watt              :  48.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  pvpowerout           :  48.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  op_va                :  32000.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  acchr_watt           :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  acchr_VA             :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  bat_Volt             :  53.1
    # Apr 10 16:36:39 europa grott[145191]:                  -  batterySoc           :  100
    # Apr 10 16:36:39 europa grott[145191]:                  -  bus_volt             :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  grid_volt            :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  line_freq            :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  outputvolt           :  208.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  pvgridvoltage        :  208.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  outputfreq           :  50.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  invtemp              :  25.6
    # Apr 10 16:36:39 europa grott[145191]:                  -  dcdctemp             :  25.9
    # Apr 10 16:36:39 europa grott[145191]:                  -  loadpercent          :  2.7
    # Apr 10 16:36:39 europa grott[145191]:                  -  buck1_ntc            :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  buck2_ntc            :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  OP_Curr              :  0.4
    # Apr 10 16:36:39 europa grott[145191]:                  -  Inv_Curr             :  0.4
    # Apr 10 16:36:39 europa grott[145191]:                  -  AC_InWatt            :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  AC_InVA              :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  faultBit             :  0
    # Apr 10 16:36:39 europa grott[145191]:                  -  warningBit           :  0
    # Apr 10 16:36:39 europa grott[145191]:                  -  faultValue           :  0
    # Apr 10 16:36:39 europa grott[145191]:                  -  warningValue         :  0
    # Apr 10 16:36:39 europa grott[145191]:                  -  constantPowerOK      :  0
    # Apr 10 16:36:39 europa grott[145191]:                  -  epvtoday             :  3.3
    # Apr 10 16:36:39 europa grott[145191]:                  -  pvenergytoday        :  3.3
    # Apr 10 16:36:39 europa grott[145191]:                  -  epvtotal             :  2434.5
    # Apr 10 16:36:39 europa grott[145191]:                  -  eacCharToday         :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  eacCharTotal         :  68.9
    # Apr 10 16:36:39 europa grott[145191]:                  -  ebatDischarToday     :  1.1
    # Apr 10 16:36:39 europa grott[145191]:                  -  ebatDischarTotal     :  1799.2
    # Apr 10 16:36:39 europa grott[145191]:                  -  eacDischarToday      :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  eacDischarTotal      :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  ACCharCurr           :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  ACDischarWatt        :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  ACDischarVA          :  0.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  BatDischarWatt       :  42.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  BatDischarVA         :  42.0
    # Apr 10 16:36:39 europa grott[145191]:                  -  BatWatt              :  59.0
    #
    # Apr 10 16:36:39 europa grott[145191]:          - MQTT jsonmsg:
    # Apr 10 16:36:39 europa grott[145191]:                          {"device": "GYH2BLL080", "time": "2023-04-10T12:20:31", "buffered": "no",
    # Apr 10 16:36:39 europa grott[145191]:                          "values": {"datalogserial": "DDD0CAB191", "pvserial": "GYH2BLL080",
    # Apr 10 16:36:39 europa grott[145191]:                          "pvstatus": 2, "vpv1": 0, "vpv2": 0, "ppv1": 0, "ppv2": 0, "buck1curr": 0,
    # Apr 10 16:36:39 europa grott[145191]:                          "buck2curr": 0, "op_watt": 480, "pvpowerout": 480, "op_va": 320000,
    # Apr 10 16:36:39 europa grott[145191]:                          "acchr_watt": 0, "acchr_VA": 0, "bat_Volt": 5310, "batterySoc": 100,
    # Apr 10 16:36:39 europa grott[145191]:                          "bus_volt": 0, "grid_volt": 0, "line_freq": 0, "outputvolt": 2080,
    # Apr 10 16:36:39 europa grott[145191]:                          "pvgridvoltage": 2080, "outputfreq": 5000, "invtemp": 256, "dcdctemp": 259,
    # Apr 10 16:36:39 europa grott[145191]:                          "loadpercent": 27, "buck1_ntc": 0, "buck2_ntc": 0, "OP_Curr": 4, "Inv_Curr":
    # Apr 10 16:36:39 europa grott[145191]:                          4, "AC_InWatt": 0, "AC_InVA": 0, "faultBit": 0, "warningBit": 0,
    # Apr 10 16:36:39 europa grott[145191]:                          "faultValue": 0, "warningValue": 0, "constantPowerOK": 0, "epvtoday": 33,
    # Apr 10 16:36:39 europa grott[145191]:                          "pvenergytoday": 33, "epvtotal": 24345, "eacCharToday": 0, "eacCharTotal":
    # Apr 10 16:36:39 europa grott[145191]:                          689, "ebatDischarToday": 11, "ebatDischarTotal": 17992, "eacDischarToday":
    # Apr 10 16:36:39 europa grott[145191]:                          0, "eacDischarTotal": 0, "ACCharCurr": 0, "ACDischarWatt": 0, "ACDischarVA":
    # Apr 10 16:36:39 europa grott[145191]:                          0, "BatDischarWatt": 420, "BatDischarVA": 420, "BatWatt": 590}}
    #
    # Apr 10 16:36:39 europa grott[145191]:          - Grott influxdb jsonmsg:
    # Apr 10 16:36:39 europa grott[145191]:                          [{'measurement': 'GYH2BLL080', 'time': '2023-04-10T12:20:31', 'fields':
    # Apr 10 16:36:39 europa grott[145191]:                          {'datalogserial': 'DDD0CAB191', 'pvserial': 'GYH2BLL080', 'pvstatus': 2,
    # Apr 10 16:36:39 europa grott[145191]:                          'vpv1': 0, 'vpv2': 0, 'ppv1': 0, 'ppv2': 0, 'buck1curr': 0, 'buck2curr': 0,
    # Apr 10 16:36:39 europa grott[145191]:                          'op_watt': 480, 'pvpowerout': 480, 'op_va': 320000, 'acchr_watt': 0,
    # Apr 10 16:36:39 europa grott[145191]:                          'acchr_VA': 0, 'bat_Volt': 5310, 'batterySoc': 100, 'bus_volt': 0,
    # Apr 10 16:36:39 europa grott[145191]:                          'grid_volt': 0, 'line_freq': 0, 'outputvolt': 2080, 'pvgridvoltage': 2080,
    # Apr 10 16:36:39 europa grott[145191]:                          'outputfreq': 5000, 'invtemp': 256, 'dcdctemp': 259, 'loadpercent': 27,
    # Apr 10 16:36:39 europa grott[145191]:                          'buck1_ntc': 0, 'buck2_ntc': 0, 'OP_Curr': 4, 'Inv_Curr': 4, 'AC_InWatt': 0,
    # Apr 10 16:36:39 europa grott[145191]:                          'AC_InVA': 0, 'faultBit': 0, 'warningBit': 0, 'faultValue': 0,
    # Apr 10 16:36:39 europa grott[145191]:                          'warningValue': 0, 'constantPowerOK': 0, 'epvtoday': 33, 'pvenergytoday':
    # Apr 10 16:36:39 europa grott[145191]:                          33, 'epvtotal': 24345, 'eacCharToday': 0, 'eacCharTotal': 689,
    # Apr 10 16:36:39 europa grott[145191]:                          'ebatDischarToday': 11, 'ebatDischarTotal': 17992, 'eacDischarToday': 0,
    # Apr 10 16:36:39 europa grott[145191]:                          'eacDischarTotal': 0, 'ACCharCurr': 0, 'ACDischarWatt': 0, 'ACDischarVA': 0,
    # Apr 10 16:36:39 europa grott[145191]:                          'BatDischarWatt': 420, 'BatDischarVA': 420, 'BatWatt': 590}}]

    valid_data =  b'\x00\xa1\x00\x06\x01\x5f\x01\x04\x03\x36\x2b\x47\x22\x35\x36\x76\x4b\x5e\x77'\
    b'\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72'\
    b'\x28\x2e\x29\x46\x36\x0b\x3e\x5f\x4f\x51\x74\x74\x47\x72\x6f\x77\x61\x74\x74'\
    b'\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x76\x70\x7e\x4b\x66\x70\x74\x61'\
    b'\x74\x74\x6b\x72\x6d\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f'\
    b'\x77\x61\x74\x74\x46\x92\x6f\x77\x65\x96\x74\x47\x72\x6f\x77\x61\x74\x74\x53'\
    b'\xcc\x6f\x13\x61\x74\x74\x47\x72\x6f\x7f\x41\x67\xfc\x47\x72\x6e\x77\x60\x77'\
    b'\x74\x5c\x66\xd1\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x43\x72\x6b\x77'\
    b'\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x3a\x51\x47\x5f'\
    b'\x6f\x2e\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x55\x47\x72\x30\x6e\x61\x74\x74'\
    b'\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x63\xc5\x74\x47\x72\x64\x77\x61'\
    b'\x32\x3c\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f'\
    b'\x77\x61\x74\x75\xe3\x72\x6f\x76\xc5\x74\x74\x45\x3c\x6f\x77\x61\x74\x74\x47'\
    b'\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x7c\x61\x74\x32\x0f\x72\x6f\x77\x3b\x74'\
    b'\xf2\xb8\x8f\x6f\x76\x9e\xbf\x74\x47\x72\x6e\x77\x61\x74\x74\x47\x72\x6f\x77'\
    b'\x61\x74\x2b\x5e\x72\x4e\x10\xba\x13\xaf\x20\xa9\x08\xac\x06\xaf\x74\x47\x72'\
    b'\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74'\
    b'\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61'\
    b'\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x4b\x2f'

    # ------------ This data has absurd ppv2 value  and should not be processed
    # Jul 07 02:57:43 europa grott[1222736]:          - Grott automatic protocol detection
    # Jul 07 02:57:43 europa grott[1222736]:          - Grott data record length 359
    # Jul 07 02:57:43 europa grott[1222736]:          - layout   :  T060104SPF
    # Jul 07 02:57:43 europa grott[1222736]:          - no matching record layout found, try generic
    # Jul 07 02:57:43 europa grott[1222736]:          - Record layout used :  T06NNNNSPF
    # Jul 07 02:57:43 europa grott[1222736]:          - Growatt data decrypted V2
    # Jul 07 02:57:43 europa grott[1222736]:          - Grott Growatt data decrypted
    # Jul 07 02:57:43 europa grott[1222736]:          - Growatt plain data:
    # Jul 07 02:57:43 europa grott[1222736]:                  00a90006015f01044444443043414231393100000000000000000000000000000000000000004
    # Jul 07 02:57:43 europa grott[1222736]:                  7594832424c4c303830000000000000000000000000000000000000000017070617073a030000
    # Jul 07 02:57:43 europa grott[1222736]:                  002c00000000000000000000ea600000ea6000000000000000000000000000000000000000000
    # Jul 07 02:57:43 europa grott[1222736]:                  00000000000000000000000000000000000000000000000000000000000000000010000000c08
    # Jul 07 02:57:43 europa grott[1222736]:                  8c088c000000000000000000000000002d00590000000000000000002d0000741c00000000000
    # Jul 07 02:57:43 europa grott[1222736]:                  0000000000000000002b10000000a000054370000000000000000000000000000000000000000
    # Jul 07 02:57:43 europa grott[1222736]:                  0eb000000eb000000f460000000000000000000000000000000a000054370000005a008600000
    # Jul 07 02:57:43 europa grott[1222736]:                  001fe7d0000000300000000000000010000741c002df7dbf7dbf7dbf7dbf7db00000000000000
    # Jul 07 02:57:43 europa grott[1222736]:                  00000000000000000000000000000000000000000000000000000000000000000000000000000
    # Jul 07 02:57:43 europa grott[1222736]:                  000000000000000000000e802
    # Jul 07 02:57:43 europa grott[1222736]:          - Growatt new layout processing
    # Jul 07 02:57:43 europa grott[1222736]:                  - decrypt       :  True
    # Jul 07 02:57:43 europa grott[1222736]:                  - offset        :  6
    # Jul 07 02:57:43 europa grott[1222736]:                  - record layout :  T06NNNNSPF
    # Jul 07 02:57:43 europa grott[1222736]:          - Grott server date/time used
    # Jul 07 02:57:43 europa grott[1222736]:          - Grott values retrieved:
    # Jul 07 02:57:43 europa grott[1222736]:                  -  datalogserial        :  DDD0CAB191
    # Jul 07 02:57:43 europa grott[1222736]:                  -  pvserial             :  GYH2BLL080
    # Jul 07 02:57:43 europa grott[1222736]:                  -  pvstatus             :  0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  vpv1                 :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  vpv2                 :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  ppv1                 :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  ppv2                 :  393216000.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  buck1curr            :  6000.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  buck2curr            :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  op_watt              :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  pvpowerout           :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  op_va                :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  acchr_watt           :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  acchr_VA             :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  bat_Volt             :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  batterySoc           :  0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  bus_volt             :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  grid_volt            :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  line_freq            :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  outputvolt           :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  pvgridvoltage        :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  outputfreq           :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  invtemp              :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  dcdctemp             :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  loadpercent          :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  buck1_ntc            :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  buck2_ntc            :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  OP_Curr              :  0.1
    # Jul 07 02:57:43 europa grott[1222736]:                  -  Inv_Curr             :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  AC_InWatt            :  78862.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  AC_InVA              :  14339276.8
    # Jul 07 02:57:43 europa grott[1222736]:                  -  faultBit             :  0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  warningBit           :  0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  faultValue           :  0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  warningValue         :  0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  constantPowerOK      :  0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  epvtoday             :  4.5
    # Jul 07 02:57:43 europa grott[1222736]:                  -  pvenergytoday        :  4.5
    # Jul 07 02:57:43 europa grott[1222736]:                  -  epvtotal             :  2972.4
    # Jul 07 02:57:43 europa grott[1222736]:                  -  eacCharToday         :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  eacCharTotal         :  68.9
    # Jul 07 02:57:43 europa grott[1222736]:                  -  ebatDischarToday     :  1.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  ebatDischarTotal     :  2155.9
    # Jul 07 02:57:43 europa grott[1222736]:                  -  eacDischarToday      :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  eacDischarTotal      :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  ACCharCurr           :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  ACDischarWatt        :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  ACDischarVA          :  0.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  BatDischarWatt       :  376.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  BatDischarVA         :  376.0
    # Jul 07 02:57:43 europa grott[1222736]:                  -  BatWatt              :  391.0  
    invalid_data_1 = b'\x00\xa9\x00\x06\x01\x5f\x01\x04\x03\x36\x2b\x47\x22\x35\x36\x76\x4b\x5e\x77'\
    b'\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72'\
    b'\x28\x2e\x29\x46\x36\x0b\x3e\x5f\x4f\x51\x74\x74\x47\x72\x6f\x77\x61\x74\x74'\
    b'\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x76\x73\x72\x50\x75\x55\x74\x61'\
    b'\x74\x74\x6b\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x8b\x14\x74\x47\x98\x0f'\
    b'\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47'\
    b'\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74'\
    b'\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x46\x72\x6f\x77'\
    b'\x6d\x7c\xf8\x4f\xfe\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x5f'\
    b'\x6f\x2e\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x59\x47\x72\x1b\x6b\x61\x74\x74'\
    b'\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x63\xc5\x74\x47\x72\x65\x77\x61'\
    b'\x20\x43\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f'\
    b'\x77\x61\x74\x7a\xf7\x72\x6f\x79\xd1\x74\x74\x48\x34\x6f\x77\x61\x74\x74\x47'\
    B'\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x7d\x61\x74\x20\x70\x72\x6f\x77\x3b\x74'\
    b'\xf2\x47\x72\x6f\x76\x9f\x09\x74\x47\x72\x6c\x77\x61\x74\x74\x47\x72\x6f\x76'\
    b'\x61\x74\x00\x5b\x72\x42\x80\xba\x83\xaf\xb0\xa9\x98\xac\x96\xaf\x74\x47\x72'\
    b'\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74'\
    b'\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61'\
    b'\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x9c\x45'


    # ---------- this data has absurd epvtoday value and should not be processed
    # Jul 06 22:40:59 europa grott[1222736]:          - Grott automatic protocol detection
    # Jul 06 22:40:59 europa grott[1222736]:          - Grott data record length 359
    # Jul 06 22:40:59 europa grott[1222736]:          - layout   :  T060104SPF
    # Jul 06 22:40:59 europa grott[1222736]:          - no matching record layout found, try generic
    # Jul 06 22:40:59 europa grott[1222736]:          - Record layout used :  T06NNNNSPF
    # Jul 06 22:40:59 europa grott[1222736]:          - Growatt data decrypted V2
    # Jul 06 22:40:59 europa grott[1222736]:          - Grott Growatt data decrypted
    # Jul 06 22:40:59 europa grott[1222736]:          - Growatt plain data:
    # Jul 06 22:40:59 europa grott[1222736]:                  00760006015f01044444443043414231393100000000000000000000000000000000000000004
    # Jul 06 22:40:59 europa grott[1222736]:                  7594832424c4c303830000000000000000000000000000000000000000017070617073a030000
    # Jul 06 22:40:59 europa grott[1222736]:                  002c00000000000000000000ea600000ea6000000000000000000000000000000000000000000
    # Jul 06 22:40:59 europa grott[1222736]:                  00000000000000000000000000000000000000000000000000000000000000000010000000c07
    # Jul 06 22:40:59 europa grott[1222736]:                  44074400000af000000af000660000002d0059000003160000053c000000000000000014fa006
    # Jul 06 22:40:59 europa grott[1222736]:                  400000000000008201388000001610183001f14f0000000000000000000000004000400000000
    # Jul 06 22:40:59 europa grott[1222736]:                  0000000000000000000000004e2500000000000000000006000073f500000000005a008600660
    # Jul 06 22:40:59 europa grott[1222736]:                  00101e600000003000000000000022e000073f50006f7dbf7dbf7dbf7dbf7db00000000000000
    # Jul 06 22:40:59 europa grott[1222736]:                  00000000000000000000000000000000000000000000000000000000000000000000000000000
    # Jul 06 22:40:59 europa grott[1222736]:                  000000000000000000000792a
    # Jul 06 22:40:59 europa grott[1222736]:          - Growatt new layout processing
    # Jul 06 22:40:59 europa grott[1222736]:                  - decrypt       :  True
    # Jul 06 22:40:59 europa grott[1222736]:                  - offset        :  6
    # Jul 06 22:40:59 europa grott[1222736]:                  - record layout :  T06NNNNSPF
    # Jul 06 22:40:59 europa grott[1222736]:          - Grott server date/time used
    # Jul 06 22:40:59 europa grott[1222736]:          - Grott values retrieved:
    # Jul 06 22:40:59 europa grott[1222736]:                  -  datalogserial        :  DDD0CAB191
    # Jul 06 22:40:59 europa grott[1222736]:                  -  pvserial             :  GYH2BLL080
    # Jul 06 22:40:59 europa grott[1222736]:                  -  pvstatus             :  0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  vpv1                 :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  vpv2                 :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  ppv1                 :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  ppv2                 :  393216000.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  buck1curr            :  6000.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  buck2curr            :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  op_watt              :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  pvpowerout           :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  op_va                :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  acchr_watt           :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  acchr_VA             :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  bat_Volt             :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  batterySoc           :  0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  bus_volt             :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  grid_volt            :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  line_freq            :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  outputvolt           :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  pvgridvoltage        :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  outputfreq           :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  invtemp              :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  dcdctemp             :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  loadpercent          :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  buck1_ntc            :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  buck2_ntc            :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  OP_Curr              :  0.1
    # Jul 06 22:40:59 europa grott[1222736]:                  -  Inv_Curr             :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  AC_InWatt            :  78829.2
    # Jul 06 22:40:59 europa grott[1222736]:                  -  AC_InVA              :  12189696.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  faultBit             :  2800
    # Jul 06 22:40:59 europa grott[1222736]:                  -  warningBit           :  0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  faultValue           :  2800
    # Jul 06 22:40:59 europa grott[1222736]:                  -  warningValue         :  102
    # Jul 06 22:40:59 europa grott[1222736]:                  -  constantPowerOK      :  0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  epvtoday             :  8781824.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  pvenergytoday        :  8781824.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  epvtotal             :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  eacCharToday         :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  eacCharTotal         :  13631988.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  ebatDischarToday     :  35.3
    # Jul 06 22:40:59 europa grott[1222736]:                  -  ebatDischarTotal     :  2536246.3
    # Jul 06 22:40:59 europa grott[1222736]:                  -  eacDischarToday      :  35127296.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  eacDischarTotal      :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  ACCharCurr           :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  ACDischarWatt        :  0.4
    # Jul 06 22:40:59 europa grott[1222736]:                  -  ACDischarVA          :  26214.4
    # Jul 06 22:40:59 europa grott[1222736]:                  -  BatDischarWatt       :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  BatDischarVA         :  0.0
    # Jul 06 22:40:59 europa grott[1222736]:                  -  BatWatt              :  0.0
    invalid_data_2 = b'\x00\x77\x00\x06\x01\x5f\x01\x04\x03\x36\x2b\x47\x22\x35\x36\x76\x4b\x5e\x77'\
    b'\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72'\
    b'\x28\x2e\x29\x46\x36\x0b\x3e\x5f\x4f\x51\x74\x74\x47\x72\x6f\x77\x61\x74\x74'\
    b' \x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x76\x73\x72\x50\x75\x55\x74\x61'\
    b'\x74\x74\x6b\x72\x63\x70\x12\x73\x07\x47\x72\x66\x67\x61\x74\x7d\x57\x72\x39'\
    b'\x77\x61\x74\x74\x44\x52\x6f\x77\x64\x32\x74\x47\x72\x6f\x77\x61\x74\x74\x53'\
    b'\x88\x6f\x13\x61\x74\x74\x47\x72\x6f\x7f\x41\x67\xfc\x47\x72\x6e\x21\x60\xf9'\
    b'\x74\x58\x66\x9f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x43\x72\x6b\x77'\
    b'\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x3a\x51\x47\x5f'\
    b'\x6f\x2e\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x73\x47\x72\x1c\x81\x61\x74\x74'\
    b'\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x63\xc5\x74\x47\x72\x6a\x77\x61'\
    b'\x20\x46\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f'\
    b'\x77\x61\x74\x76\x97\x72\x6f\x75\xb1\x8b\x8b\xb6\xa0\x6f\x77\x61\x74\x74\x47'\
    b'\x72\x6f\x77\x22\x74\x74\x47\x72\x6f\x72\x61\x74\x20\x75\x72\x6f\x77\x3b\x74'\
    b'\xf2\x47\x26\x6f\x76\x60\xf0\x74\x47\x72\x6c\x77\x61\x74\x74\x47\x72\x6e\xbc'\
    b'\x61\x74\x07\xb1\x72\x68\x80\xba\x83\xaf\xb0\xa9\x98\xac\x96\xaf\x74\x47\x72'\
    b'\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74'\
    b'\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61'\
    b'\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x35\xd3'

    @pytest.mark.parametrize('cfg_file, expected', [
    ('tests/testdata/grott_applydividers_test_mqtt_true.ini', 59), 
    ('tests/testdata/grott_applydividers_test_mqtt_false.ini', 590)])
    @patch('grottdata.publish.single')
    def test_mqtt_applydividers(self, mock_publish_single, cfg_file, expected):
        conf = Conf("2.7.8", cmdargs=['-c', cfg_file])
        grottdata.procdata(conf,self.valid_data)
        assert mock_publish_single.called == True
        json_payload = json.loads(mock_publish_single.call_args.kwargs['payload'])
        assert json_payload['device'] == 'GYH2BLL080'
        assert json_payload['values']['pvserial'] == 'GYH2BLL080'
        assert json_payload['values']['BatWatt'] == expected


    @pytest.mark.parametrize('cfg_file, expected', [
    ('tests/testdata/grott_applydividers_test_influxdb_false.ini', 590), 
    ('tests/testdata/grott_applydividers_test_influxdb_true.ini', 59)])
    def test_influxdb_applydividers(self, cfg_file, expected):
        conf = Conf("2.7.8", cmdargs=['-c', cfg_file])
        
        # we need to set influx and influx2 to True, otherwise the ifwrite_api.write() call will not be made
        # but we have to set it after conf is initialized, to skip the actual influxdb connection opening
        conf.influx = True
        conf.influx2 = True

        ifwrite_mock = Mock()
        conf.ifwrite_api = ifwrite_mock

        grottdata.procdata(conf,self.valid_data)
        assert ifwrite_mock.write.called == True
        payload = ifwrite_mock.write.call_args.args[2]
        assert payload[0]['measurement'] == 'GYH2BLL080'
        assert payload[0]['fields']['pvserial'] == 'GYH2BLL080'
        assert payload[0]['fields']['BatWatt'] == expected


    @patch('grottdata.publish.single')
    def test_discard_invalid_data_1(self, mock_publish_single):
        conf = Conf("2.7.8", cmdargs=['-c', 'tests/testdata/grott_applydividers_test_mqtt_true.ini'])
        grottdata.procdata(conf,self.invalid_data_1)
        assert mock_publish_single.called == False

    @patch('grottdata.publish.single')
    def test_discard_invalid_data_2(self, mock_publish_single):
        conf = Conf("2.7.8", cmdargs=['-c', 'tests/testdata/grott_applydividers_test_mqtt_true.ini'])
        grottdata.procdata(conf,self.invalid_data_2)
        assert mock_publish_single.called == False