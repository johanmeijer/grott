import sys, os

# Required to import grottconf from the root
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


import pytest
from grottconf import Conf
from grott_ha import make_payload, mapping


@pytest.fixture
def conf():
    conf = Conf("2.7.7")
    conf.layout = "T06NNNNSPF"
    return conf


key = "pvpowerout"
serial = "NCO7410"


def test_generate_payload(conf):
    "Test that an auto generated payload for MQTT configuration"

    payload = make_payload(conf, serial, key, key)
    print(payload)
    # The default divider for pvpowerout is 10
    assert payload["value_template"] == "{{ value_json.pvpowerout | float / 10 }}"
    assert payload["name"] == "NCO7410 PV Output (Actual)"
    assert payload["unique_id"] == "grott_NCO7410_pvpowerout"
    assert payload["state_class"] == "measurement"
    assert payload["device_class"] == "power"
    assert payload["unit_of_measurement"] == "W"


def test_auto_generate_divider(conf):
    "Test that an auto generated value_template contain the divider"

    payload = make_payload(conf, serial, "TEST DEVICE", key)
    # The default divider for pvpowerout is 10
    assert payload["value_template"] == "{{ value_json.pvpowerout | float / 10 }}"

    payload = make_payload(conf, serial, "TEST DEVICE", "BatWatt")
    # The  divider for the numx is also 10
    assert payload["value_template"] == "{{ value_json.BatWatt | float / 10 }}"


def test_manual_divider(conf):
    "Test that's the manual value template is not overwritten"
    # Alter the configuration
    value_template = "{{value_json.pvpowerout | float / 10000}}"
    mapping[key]["value_template"] = value_template
    payload = make_payload(conf, serial, "TEST DEVICE", key)
    # Remove the alteration
    del mapping[key]["value_template"]

    assert payload["value_template"] == value_template


def test_unknow_mapping(conf):
    "Test that an unknow mapping still has the good divider"
    conf.recorddict[conf.layout].update(
        {
            "test": {"value": 290, "length": 4, "type": "num", "divide": 51},
            "test_not_num": {"value": 290, "length": 4, "type": "text", "divide": 51},
        }
    )

    # No mapping should use the raw divider
    payload = make_payload(conf, serial, "TEST DEVICE", "test")
    assert payload["value_template"] == "{{ value_json.test | float / 51 }}"

    # Type not text should return the raw value
    payload = make_payload(conf, serial, "TEST DEVICE", "test_not_num")
    assert payload["value_template"] == "{{ value_json.test_not_num }}"


def test_default_mapping(conf):
    "Test a mapping without type, should use the divider, because default is num"

    # test date {"value" :76, "length" : 10, "type" : "text"},
    payload = make_payload(conf, serial, "TEST DEVICE", "date")

    assert payload["value_template"] == "{{ value_json.date | float / 10 }}"


def test_name_generation(conf):
    "Test the output of the name generation"

    # test date {"value" :76, "length" : 10, "type" : "text"},
    payload = make_payload(conf, serial, "TEST DEVICE", key)

    assert payload["name"] == "NCO7410 PV Output (Actual)"


def test_name_generation_non_mapped(conf):
    "Test the output of the name generation"

    # test date {"value" :76, "length" : 10, "type" : "text"},
    payload = make_payload(conf, serial, "test", "test")

    assert payload["name"] == "NCO7410 test"
