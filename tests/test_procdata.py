import pytest
from unittest.mock import patch
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

    @pytest.mark.parametrize('cfg_file, expected', [
    ('tests/testdata/grott_postprocess_test_mqtt_true.ini', 59), 
    ('tests/testdata/grott_postprocess_test_mqtt_false.ini', 590)])
    @patch('grottdata.publish.single')
    def test_procdata(self, mock_publish_single, cfg_file, expected):
        conf = Conf("2.7.8", cmdargs=['-c', cfg_file])
        grottdata.procdata(conf,self.valid_data)
        assert mock_publish_single.called == True
        json_payload = json.loads(mock_publish_single.call_args.kwargs['payload'])
        assert json_payload['device'] == 'GYH2BLL080'
        assert json_payload['values']['BatWatt'] == expected


    
    
