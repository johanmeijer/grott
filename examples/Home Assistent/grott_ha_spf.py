# coding=utf-8
# author Etienne G.

import json
from datetime import datetime, timezone

from paho.mqtt.publish import single, multiple

from grottconf import Conf

__version__ = "0.0.8"

"""A pluging for grott
This plugin allow to have autodiscovery of the device in HA

Should be able to support multiples inverters

Version 0.0.8
  - Changed mapping to be compatible with SPF inverter, in this case specifically, SPFXX00ES.
  - Updated sensor names to fall in line with HA guidelines.
  
Config:
    - ha_mqtt_host (required): The host of the MQTT broker user by HA (often the IP of HA)
    - ha_mqtt_port (required): The port (the default is oftent 1883)
    - ha_mqtt_user (optional): The user use to connect to the broker (you can use your user)
    - ha_mqtt_password (optional): The password to connect to the mqtt broket (you can use your password)
    - ha_mqtt_retain (optional): Set the retain flag for the data message (default: False)

Return codes:
    - 0: Everything is OK
    - 1: Missing MQTT extvar configuration
    - 2: Error while publishing the measure value message
    - 3: MQTT connection error
    - 4: Error while creating last_push status key
    - 5: Refused to push a buffered message (prevent invalid stats, not en error)
    - 6: Error while configuring HA MQTT sensor devices
    - 7: Can't configure device for HA MQTT
"""


config_topic = "homeassistant/{sensor_type}/grott/{device}_{attribut}/config"
state_topic = "homeassistant/grott/{device}/state"


mapping = {
    "datalogserial": {
        "name": "Datalogger serial",
    },
    "pvserial": {"name": "Serial"},
    "ppv1": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "PV1 Watt",
        "unit_of_measurement": "W",
        "value_template": "{{value_json.ppv1| float / 10 }}",
    },
    "vpv1": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "PV1 Voltage",
        "unit_of_measurement": "V",
        "value_template": "{{value_json.vpv1| float / 10 }}",
    },
    "buck1curr": {
        "state_class": "measurement",
        "device_class": "current",
        "name": "PV1 Current",
        "unit_of_measurement": "A",
        "value_template": "{{value_json.buck1curr| float / 10 }}",
    },
    "ppv2": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "PV2 Watt",
        "unit_of_measurement": "W",
        "value_template": "{{value_json.ppv2| float / 10 }}",
    },
    "vpv2": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "PV2 Voltage",
        "unit_of_measurement": "V",
        "value_template": "{{value_json.vpv2| float / 10 }}",
    },
    "buck2curr": {
        "state_class": "measurement",
        "device_class": "current",
        "name": "PV2 Current",
        "unit_of_measurement": "A",
        "value_template": "{{value_json.buck2curr| float / 10 }}",
    },
    "OP_Curr": {
        "state_class": "measurement",
        "device_class": "current",
        "name": "Output Current",
        "unit_of_measurement": "A",
        "value_template": "{{value_json.OP_Curr| float / 10 }}",
    },
    "AC_InWatt": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "AC Input kiloWatt (Actual)",
        "unit_of_measurement": "W",
        "value_template": "{{value_json.AC_InWatt| float / 10 }}",
    },
    "op_watt": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "Output kiloWatt (Actual)",
        "unit_of_measurement": "W",
        "value_template": "{{value_json.op_watt| float / 10 }}",
    },
    "op_va": {
        "state_class": "measurement",
        "device_class": "apparent_power",
        "name": "Output VA (Actual)",
        "unit_of_measurement": "VA",
        "value_template": "{{value_json.op_va| float / 10 }}",
    },
    "line_freq": {
        "state_class": "measurement",
        "device_class": "frequency",
        "name": "Grid frequency",
        "unit_of_measurement": "Hz",
        "value_template": "{{value_json.line_freq| float / 100 }}",
        "icon": "mdi:waveform",
    },
    "outputfreq": {
        "state_class": "measurement",
        "device_class": "frequency",
        "name": "Output frequency",
        "unit_of_measurement": "Hz",
        "value_template": "{{value_json.outputfreq| float / 100 }}",
        "icon": "mdi:waveform",
    },
    "outputvolt": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "Grid voltage",
        "unit_of_measurement": "V",
        "value_template": "{{value_json.outputvolt| float / 10 }}",
    },
    "loadpercent": {
        "state_class": "measurement",
        "name": "Inverter Load",
        "unit_of_measurement": "%",
        "value_template": "{{value_json.loadpercent| float / 10 }}",
    },
    # Grid config
    "grid_volt": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "Grid voltage",
        "unit_of_measurement": "V",
        "value_template": "{{value_json.grid_volt| float / 10 }}",
    },
    "acchr_watt": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "AC Charger Watts",
        "unit_of_measurement": "W",
        "value_template": "{{value_json.acchr_watt| float / 10 }}",
    },
    "ACDischarWatt": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "AC Discharge Watts",
        "unit_of_measurement": "W",
        "value_template": "{{value_json.ACDischarWatt| float / 10 }}",
    },
    "acchr_VA": {
        "state_class": "measurement",
        "device_class": "apparent_power",
        "name": "AC Charger VA",
        "unit_of_measurement": "VA",
        "value_template": "{{value_json.acchr_VA| float / 10 }}",
    },
    "ACDischarVA": {
        "state_class": "measurement",
        "device_class": "apparent_power",
        "name": "AC Discharge VA",
        "unit_of_measurement": "VA",
        "value_template": "{{value_json.ACDischarVA| float / 10 }}",
    },
    "AC_InVA": {
        "state_class": "measurement",
        "device_class": "apparent_power",
        "name": "AC Input VA",
        "unit_of_measurement": "VA",
        "value_template": "{{value_json.ACDischarVA| float / 10 }}",
    },
    "bus_volt": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "Bus voltage",
        "unit_of_measurement": "V",
        "value_template": "{{value_json.bus_volt| float / 10 }}",
    },
    "Inv_Curr": {
        "state_class": "measurement",
        "device_class": "current",
        "name": "Grid current",
        "unit_of_measurement": "A",
        "value_template": "{{value_json.Inv_Curr| float / 10 }}",
    },
    "ACCharCurr": {
        "state_class": "measurement",
        "device_class": "current",
        "name": "AC charger current",
        "unit_of_measurement": "A",
        "value_template": "{{value_json.ACCharCurr| float / 10 }}",
    },
    # End grid
    "epv1tod": {
        "state_class": "total",
        "device_class": "energy",
        "name": "PV1 Generated energy (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.epv1tod| float / 10 }}",
        "icon": "mdi:solar-power",
    },
    "epv2tod": {
        "state_class": "total",
        "device_class": "energy",
        "name": "PV2 Generated energy (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.epv2tod| float / 10 }}",
        "icon": "mdi:solar-power",
    },
    "pvstatus": {
        "name": "Status",
        "icon": "mdi:power-settings",
        "value_template": "{{value_json.pvstatus| int }}",
    },
    
    "invtemp": {
        "state_class": "measurement",
        "device_class": "temperature",
        "name": "Inverter temperature",
        "unit_of_measurement": "°C",
        "value_template": "{{value_json.invtemp| float / 10 }}",
    },
    "dcdctemp": {
        "state_class": "measurement",
        "device_class": "temperature",
        "name": "DC to DC temperature",
        "unit_of_measurement": "°C",
        "value_template": "{{value_json.dcdctemp| float / 10 }}",
    },
    
    "epv1today": {
        "device_class": "energy",
        "name": "Solar production (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.epv1today| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "epv1total": {
        "device_class": "energy",
        "name": "Solar production (Total)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.epv1total| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "epv2today": {
        "device_class": "energy",
        "name": "Solar PV2 production (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.epv2today| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "epv2total": {
        "device_class": "energy",
        "name": "Solar PV2 production (Total)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.epv2total| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "grott_last_push": {
        "device_class": "timestamp",
        "name": "Grott last data push",
        "value_template": "{{value_json.grott_last_push}}",
    },
    "grott_last_measure": {
        "device_class": "timestamp",
        "name": "Last measure",
    },
    "eacDischarToday": {
        "device_class": "energy",
        "name": "Discharge from AC (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.eacDischarToday| float / 10 }}",
        "icon": "mdi:battery-arrow-up",
        "state_class": "total",
    },
    "eacDischarTotal": {
        "device_class": "energy",
        "name": "Discharge from AC (Total)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.eacDischarTotal| float / 10 }}",
        "icon": "mdi:battery-arrow-up",
        "state_class": "total_increasing",
    },
    # batteries
    "eacCharToday": {
        "device_class": "energy",
        "name": "Battery charge from AC (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.eacCharToday| float / 10 }}",
        "icon": "mdi:battery-arrow-up",
        "state_class": "total",
    },
    "eacCharTotal": {
        "device_class": "energy",
        "name": "Battery charge from AC (Total)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.eacCharTotal| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "bat_Volt": {
        "state_class": "measurement",
        "device_class": "voltage",
        "value_template": "{{value_json.bat_Volt| float / 100 }}",
        "name": "Battery voltage",
        "unit_of_measurement": "V",
    },
    "batterySoc": {
        "name": "Battery charge",
        "device_class": "battery",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "icon": "mdi:battery-charging-60",
    },
    "BatDischarWatt": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "Battery Discharge Watts",
        "unit_of_measurement": "W",
        "value_template": "{{value_json.BatDischarWatt| float / 10 }}",
    },
    "BatWatt": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "Battery Energy",
        "unit_of_measurement": "W",
        "value_template": "{{value_json.BatWatt| float / 10 * -1 }}",
    },
    "BatDischarVA": {
        "state_class": "measurement",
        "device_class": "apparent_power",
        "name": "Battery Discharge VA",
        "unit_of_measurement": "VA",
        "value_template": "{{value_json.BatDischarVA| float / 10 }}",
    },
    "ebatDischarToday": {
        "name": "Battery discharge (Today)",
        "device_class": "energy",
        "state_class": "total",
        "value_template": "{{value_json.ebatDischarToday| float / 10 }}",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-down",
    },
    "ebatDischarTotal": {
        "name": "Battery discharge (Total)",
        "device_class": "energy",
        "state_class": "total_increasing",
        "value_template": "{{value_json.ebatDischarTotal| float / 10 }}",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-down",
    },
    
}

MQTT_HOST_CONF_KEY = "ha_mqtt_host"
MQTT_PORT_CONF_KEY = "ha_mqtt_port"
MQTT_USERNAME_CONF_KEY = "ha_mqtt_user"
MQTT_PASSWORD_CONF_KEY = "ha_mqtt_password"
MQTT_RETAIN_CONF_KEY = "ha_mqtt_retain"


def make_payload(conf: Conf, device: str, name: str, key: str, unit: str = None):
    # Default configuration payload
    payload = {
        "name": "{name}",
        "unique_id": f"grott_{device}_{key}",  # Generate a unique device ID
        "state_topic": f"homeassistant/grott/{device}/state",
        "device": {
            "identifiers": [device],  # Group under a device
            "name": device,
            "manufacturer": "Growatt",
        },
    }

    # If there's a custom mapping add the new values
    if key in mapping:
        payload.update(mapping[key])

    # Generate the name of the key, with all the param available
    payload["name"] = payload["name"].format(device=device, name=name, key=key)
    # HA automatically group the sensor if the device name is prepended

    # Reuse the existing divide value if available and not existing
    # and apply it to the HA config
    layout = conf.recorddict[conf.layout]
    if "value_template" not in payload and key in layout:
        # From grottdata:207, default type is num, also process numx
        if layout[key].get("type", "num") in ("num", "numx"):
            divider = layout[key].get("divide", "1")
            payload[
                "value_template"
            ] = "{{{{ value_json.{key} | float / {divide} }}}}".format(
                key=key,
                divide=divider,
            )

    if "value_template" not in payload:
        payload["value_template"] = f"{{{{ value_json.{key} }}}}"

    return payload


class MqttStateHandler:
    __pv_config = {}
    client_name = "Grott - HA"

    @classmethod
    def is_configured(cls, serial: str):
        return cls.__pv_config.get(serial, False)

    @classmethod
    def set_configured(cls, serial: str):
        cls.__pv_config[serial] = True


def process_conf(conf: Conf):
    required_params = [
        MQTT_HOST_CONF_KEY,
        MQTT_PORT_CONF_KEY,
    ]
    if not all([param in conf.extvar for param in required_params]):
        print("Missing configuration for ha_mqtt")
        raise AttributeError

    if MQTT_USERNAME_CONF_KEY in conf.extvar:
        auth = {
            "username": conf.extvar[MQTT_USERNAME_CONF_KEY],
            "password": conf.extvar[MQTT_PASSWORD_CONF_KEY],
        }
    else:
        auth = None

    # Need to convert the port if passed as a string
    port = conf.extvar[MQTT_PORT_CONF_KEY]
    if isinstance(port, str):
        port = int(port)
    return {
        "client_id": MqttStateHandler.client_name,
        "auth": auth,
        "hostname": conf.extvar[MQTT_HOST_CONF_KEY],
        "port": port,
    }


def publish_single(conf: Conf, topic, payload, retain=False):
    conf = process_conf(conf)
    return single(topic, payload=payload, retain=retain, **conf)


def publish_multiple(conf: Conf, msgs):
    conf = process_conf(conf)
    return multiple(msgs, **conf)


def grottext(conf: Conf, data: str, jsonmsg: str):
    """Allow to push to HA MQTT bus, with auto discovery"""

    required_params = [
        MQTT_HOST_CONF_KEY,
        MQTT_PORT_CONF_KEY,
    ]
    if not all([param in conf.extvar for param in required_params]):
        print("Missing configuration for ha_mqtt")
        return 1

    # Need to decode the json string
    jsonmsg = json.loads(jsonmsg)

    if jsonmsg.get("buffered") == "yes":
        # Skip buffered message, HA don't support them
        if conf.verbose:
            print("\t - Grott HA - skipped buffered")
        return 5

    device_serial = jsonmsg["device"]
    values = jsonmsg["values"]

    # Send the last push in UTC with TZ
    dt = datetime.now(timezone.utc)
    # Add a new value to the existing values
    values["grott_last_push"] = dt.isoformat()

    # Layout can be undefined
    if not MqttStateHandler.is_configured(device_serial) and getattr(
        conf, "layout", None
    ):
        configs_payloads = []
        print(
            f"\tGrott HA {__version__} - creating {device_serial} config in HA, {len(values.keys())} to push"
        )
        for key in values.keys():
            # Generate a configuration payload
            payload = make_payload(conf, device_serial, key, key)
            if not payload:
                print(f"\t[Grott HA] {__version__} skipped key: {key}")
                continue

            try:
                topic = config_topic.format(
                    sensor_type="sensor",
                    device=device_serial,
                    attribut=key,
                )
                configs_payloads.append(
                    {
                        "topic": topic,
                        "payload": json.dumps(payload),
                        "retain": True,
                        "qos": 1,
                    }
                )
            except Exception as e:
                print(
                    f"\t - [grott HA] {__version__} Exception while creating new sensor {key}: {e}"
                )
                return 6

        # Create a virtual last_push key to allow tracking when there was the last data transmission

        try:
            key = "grott_last_push"
            payload = make_payload(conf, device_serial, key, key)
            topic = config_topic.format(
                sensor_type="sensor",
                device=device_serial,
                attribut=key,
            )
            configs_payloads.append(
                {
                    "topic": topic,
                    "payload": json.dumps(payload),
                    "retain": True,
                    "qos": 1,
                }
            )
        except Exception as e:
            print(
                f"\t - [grott HA] {__version__} Exception while creating new sensor last push: {e}"
            )
            return 4
        print(f"\tPushing {len(configs_payloads)} configurations payload to HA")
        publish_multiple(conf, configs_payloads)
        print(f"\tConfigurations pushed")
        # Now it's configured, no need to come back
        MqttStateHandler.set_configured(device_serial)

    if not MqttStateHandler.is_configured(device_serial):
        print(f"\t[Grott HA] {__version__} Can't configure device: {device_serial}")
        return 7

    # Push the values to the topic
    retain = conf.extvar.get(MQTT_RETAIN_CONF_KEY, False)
    try:
        publish_single(
            conf,
            state_topic.format(device=device_serial),
            json.dumps(values),
            retain=retain,
        )
    except Exception as e:
        print("[HA ext] - Exception while publishing - {}".format(e))
        # Reset connection state in case of problem
        return 2
    return 0


def test_generate_payload():
    "Test that an auto generated payload for MQTT configuration"

    class TestConf:
        recorddict = {
            "test": {
                "pvpowerout": {"value": 122, "length": 4, "type": "num", "divide": 10}
            }
        }
        layout = "test"

    payload = make_payload(TestConf(), "NCO7410", "pvpowerout", "pvpowerout")
    print(payload)
    # The default divider for pvpowerout is 10
    assert payload["value_template"] == "{{ value_json.pvpowerout | float / 10 }}"
    assert payload["name"] == "NCO7410 PV Output (Actual)"
    assert payload["unique_id"] == "grott_NCO7410_pvpowerout"
    assert payload["state_class"] == "measurement"
    assert payload["device_class"] == "power"
    assert payload["unit_of_measurement"] == "W"


def test_generate_payload_without_divider():
    "Test that an auto generated payload for MQTT configuration"

    class TestConf:
        recorddict = {
            "test": {
                "pvpowerout": {
                    "value": 122,
                    "length": 4,
                    "type": "num",
                }
            }
        }
        layout = "test"

    payload = make_payload(TestConf(), "NCO7410", "pvpowerout", "pvpowerout")
    print(payload)
    # The default divider for pvpowerout is 10
    assert payload["value_template"] == "{{ value_json.pvpowerout | float / 1 }}"
    assert payload["name"] == "NCO7410 PV Output (Actual)"
    assert payload["unique_id"] == "grott_NCO7410_pvpowerout"
    assert payload["state_class"] == "measurement"
    assert payload["device_class"] == "power"
    assert payload["unit_of_measurement"] == "W"
