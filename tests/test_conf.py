import pytest
from grottconf import Conf

class TestGrottConf:

    def test_default_postprocess_flags(self):
        conf = Conf("2.7.8")
        assert conf.mqttapplydividers == False
        assert conf.ifapplydividers == False

    @pytest.mark.parametrize('cfg_file, expected', [
        ('tests/testdata/conf_applydividers_test_true.ini', True), 
        ('tests/testdata/conf_applydividers_test_false.ini', False)])
    def test_cfgfile_overidden_postprocess_flag(self, cfg_file, expected):
        conf = Conf("2.7.8", cmdargs=['-c', cfg_file])
        assert conf.mqttapplydividers == expected
        assert conf.ifapplydividers == expected

