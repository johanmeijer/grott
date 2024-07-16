# coding=utf-8
# author Etienne G.

import json
from datetime import datetime, timezone

from paho.mqtt.publish import single, multiple

from grottconf import Conf

__version__ = "0.0.7-rc2"

"""A pluging for grott
This plugin allow to have autodiscovery of the device in HA

Should be able to support multiples inverters

Config:
    - ha_mqtt_host (required): The host of the MQTT broker user by HA (often the IP of HA)
    - ha_mqtt_port (required): The port (the default is oftent 1883)
    - ha_mqtt_user (optional): The user use to connect to the broker (you can use your user)
    - ha_mqtt_password (optional): The password to connect to the mqtt broket (you can use your password)

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
    "pv1watt": {
        "name": "PV1 Watt",
        "state_class": "measurement",
        "device_class": "power",
        "unit_of_measurement": "W",
    },
    "pv1voltage": {
        "name": "PV1 Voltage",
        "state_class": "measurement",
        "device_class": "voltage",
        "unit_of_measurement": "V",
    },
    "pv1current": {
        "name": "PV1 Current",
        "state_class": "measurement",
        "device_class": "current",
        "unit_of_measurement": "A",
    },
    "pv2watt": {
        "name": "PV2 Watt",
        "state_class": "measurement",
        "device_class": "power",
        "unit_of_measurement": "W",
    },
    "pv2voltage": {
        "name": "PV2 Voltage",
        "state_class": "measurement",
        "device_class": "voltage",
        "unit_of_measurement": "V",
    },
    "pv2current": {
        "name": "PV2 Current",
        "state_class": "measurement",
        "device_class": "current",
        "unit_of_measurement": "A",
    },
    "pvpowerin": {
        "name": "PV Input (Actual)",
        "state_class": "measurement",
        "device_class": "power",
        "unit_of_measurement": "W",
    },
    "pvpowerout": {
        "name": "PV Output (Actual)",
        "state_class": "measurement",
        "device_class": "power",
        "unit_of_measurement": "W",
    },
    "pvfrequentie": {
        "name": "Grid frequency",
        "state_class": "measurement",
        "device_class": "frequency",
        "unit_of_measurement": "Hz",
        "icon": "mdi:waveform",
    },
    # Grid config
    "pvgridvoltage": {
        "name": "Phase 1 voltage",
        "state_class": "measurement",
        "device_class": "voltage",
        "unit_of_measurement": "V",
    },
    "pvgridvoltage2": {
        "name": "Phase 2 voltage",
        "state_class": "measurement",
        "device_class": "voltage",
        "unit_of_measurement": "V",
    },
    "pvgridvoltage3": {
        "name": "Phase 3 voltage",
        "state_class": "measurement",
        "device_class": "voltage",
        "unit_of_measurement": "V",
    },
    "pvgridcurrent": {
        "name": "Phase 1 current",
        "state_class": "measurement",
        "device_class": "current",
        "unit_of_measurement": "A",
    },
    "pvgridcurrent2": {
        "state_class": "measurement",
        "device_class": "current",
        "name": "Phase 2 current",
        "unit_of_measurement": "A",
    },
    "pvgridcurrent3": {
        "name": "Phase 3 current",
        "state_class": "measurement",
        "device_class": "current",
        "unit_of_measurement": "A",
    },
    "pvgridpower": {
        "name": "Phase 1 power",
        "state_class": "measurement",
        "device_class": "power",
        "unit_of_measurement": "W",
    },
    "pvgridpower2": {
        "name": "Phase 2 power",
        "state_class": "measurement",
        "device_class": "power",
        "unit_of_measurement": "W",
    },
    "pvgridpower3": {
        "name": "Phase 3 power",
        "state_class": "measurement",
        "device_class": "power",
        "unit_of_measurement": "W",
    },
    # End grid
    "pvenergytoday": {
        "name": "Generated energy (Today)",
        "state_class": "total",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
    },
    "epvtoday": {
        "name": "PV Energy today (Today)",
        "state_class": "total",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
    },
    "epv1today": {
        "name": "Solar PV1 production",
        "state_class": "total",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
    },
    "epv2today": {
        "name": "Solar PV2 production",
        "state_class": "total",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
    },
    "pvenergytotal": {
        "state_class": "total_increasing",
        "device_class": "energy",
        "name": "Generated energy (Total)",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
    },
    "epvtotal": {
        "name": "Generated PV energy (Total)",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "epv1total": {
        "name": "Solar PV1 production (Total)",
        "state_class": "total",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
    },
    "epv2total": {
        "name": "Solar PV2 production (Total)",
        "state_class": "total",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
    },
    # For SPH compatiblity
    "epvTotal": {
        "name": "Generated PV energy (Total)",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "pactogridr": {
        "name": "Energy export (Today)",
        "device_class": "energy",
        "state_class": "measurement",
        "unit_of_measurement": "Wh",
        "state_class": "total",
        "icon": "mdi:solar-power",
    },
    "pactogridtot": {
        "name": "Energy export (Total)",
        "device_class": "energy",
        "state_class": "measurement",
        "unit_of_measurement": "Wh",
        "state_class": "total_increasing",
        "icon": "mdi:solar-power",
    },
    "pvstatus": {
        "name": "State",
        # "value_template": "{% if value_json.pvstatus == 0 %}Standby{% elif value_json.pvstatus == 1 %}Normal{% elif value_json.pvstatus == 2 %}Fault{% else %}Unknown{% endif %}",
        "icon": "mdi:power-settings",
    },
    "totworktime": {
        "name": "Working time",
        "device_class": "duration",
        "unit_of_measurement": "hours",
        "value_template": "{{ value_json.totworktime| float / 7200 | round(2) }}",
    },
    "pvtemperature": {
        "name": "Inverter temperature",
        "state_class": "measurement",
        "device_class": "temperature",
        "unit_of_measurement": "°C",
    },
    "pvipmtemperature": {
        "name": "IPM temperature",
        "device_class": "temperature",
        "unit_of_measurement": "°C",
        "state_class": "measurement",
    },
    "pvboottemperature": {
        "name": "Inverter boost temperature",
        "device_class": "temperature",
        "unit_of_measurement": "°C",
        "state_class": "measurement",
    },
    "pvboosttemp": {
        "name": "Inverter boost temperature",
        "device_class": "temperature",
        "unit_of_measurement": "°C",
        "state_class": "measurement",
    },
    "etogrid_tod": {
        "name": "Energy to grid (Today)",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:transmission-tower-import",
        "state_class": "total",
    },
    "etogrid_tot": {
        "name": "Energy to grid (Total)",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:transmission-tower-import",
        "state_class": "total_increasing",
    },
    "etouser_tod": {
        "name": "Import from grid (Today)",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "etouser_tot": {
        "name": "Import from grid (Total)",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:transmission-tower-export",
        "state_class": "total_increasing",
    },
    "pactouserr": {
        "name": "Import from grid (Actual)",
        "device_class": "energy",
        "device_class": "power",
        "unit_of_measurement": "W",
        "icon": "mdi:transmission-tower-export",
    },
    # Register 1015 # TODO: investiagate
    # "pactousertot": {
    #     "name": "Power consumption total",
    #     "device_class": "power",
    #     "unit_of_measurement": "kW",
    #     "icon": "mdi:transmission-tower-export",
    # },
    "elocalload_tod": {
        "name": "Load consumption (Today)",
        "device_class": "energy",
        "unit_of_measurement": "Wh",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "elocalload_tot": {
        "name": "Load consumption (Total)",
        "device_class": "energy",
        "unit_of_measurement": "Wh",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "plocaloadr": {
        "name": "Local load consumption",
        "device_class": "power",
        "unit_of_measurement": "W",
        "icon": "mdi:transmission-tower-export",
    },
    "grott_last_push": {
        "name": "Grott last data push",
        "device_class": "timestamp",
        "value_template": "{{value_json.grott_last_push}}",
    },
    "grott_last_measure": {
        "name": "Last measure",
        "device_class": "timestamp",
    },
    # batteries
    "eacharge_today": {
        "name": "Battery charge from AC (Today)",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-up",
        "state_class": "total",
    },
    "eacharge_total": {
        "name": "Battery charge from AC (Today)",
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "vbat": {
        "name": "Battery voltage",
        "state_class": "measurement",
        "device_class": "voltage",
        "unit_of_measurement": "V",
    },
    "SOC": {
        "name": "Battery charge",
        "device_class": "battery",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "icon": "mdi:battery-charging-60",
    },
    # taken from register 1048 of RTU manual v1.20
    "batterytype": {
        "name": "Batteries type",
        "value_template": "{% if value_json.batterytype == 0 %}Lithium{% elif value_json.batterytype == '1' %}Lead-acid{% elif value_json.batterytype == '2' %}Other{% else %}Unknown{% endif %}",
        "icon": "mdi:power-settings",
    },
    "p1charge1": {
        "name": "Battery charge",
        "device_class": "power",
        "unit_of_measurement": "kW",
        "state_class": "measurement",
        "icon": "mdi:battery-arrow-up",
    },
    "eharge1_tod": {
        "name": "Battery charge (Today)",
        "device_class": "energy",
        "state_class": "total",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-up",
    },
    "eharge1_tot": {
        "name": "Battery charge (Total)",
        "device_class": "energy",
        "state_class": "total_increasing",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-up",
    },
    "edischarge1_tod": {
        "name": "Battery discharge (Today)",
        "device_class": "energy",
        "state_class": "total",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-down",
    },
    "edischarge1_tot": {
        "name": "Battery discharge (Total)",
        "device_class": "energy",
        "state_class": "total_increasing",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-down",
    },
    "battemp": {
        "name": "Battery temperature",
        "device_class": "temperature",
        "unit_of_measurement": "°C",
        "icon": "mdi:thermometer",
    },
    "spbusvolt": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "BP bus voltage",
        "unit_of_measurement": "V",
    },
    "systemfaultword1": {
        "name": "System fault register 1",
    },
    "systemfaultword2": {
        "name": "System fault register 2",
    },
    "systemfaultword3": {
        "name": "System fault register 3",
    },
    "systemfaultword4": {
        "name": "System fault register 4",
    },
    "systemfaultword5": {
        "name": "System fault register 5",
    },
    "systemfaultword6": {
        "name": "System fault register 6",
    },
    "systemfaultword7": {
        "name": "System fault register 7",
    },
    "vpv1": {
        "name": "PV1 Voltage",
        "state_class": "measurement",
        "device_class": "voltage",
        "unit_of_measurement": "V",
    },
    "vpv2": {
        "name": "PV2 Voltage",
        "state_class": "measurement",
        "device_class": "voltage",
        "unit_of_measurement": "V",
    },
    "ppv1": {
        "name": "PV1 charge power",
        "device_class": "power",
        "unit_of_measurement": "W",
        "state_class": "measurement",
    },
    "ppv2": {
        "name": "PV1 charge power",
        "device_class": "power",
        "unit_of_measurement": "W",
        "state_class": "measurement",
    },
    "buck1curr": {
        "name": "Buck1 current",
        "device_class": "current",
        "unit_of_measurement": "A",
        "state_class": "measurement",
    },
    "buck2curr": {
        "name": "Buck2 current",
        "device_class": "current",
        "unit_of_measurement": "A",
        "state_class": "measurement",
    },
    "op_watt": {
        "name": "Output active power",
        "device_class": "power",
        "unit_of_measurement": "W",
        "state_class": "measurement",
    },
    "op_va": {
        "name": "Output apparent power",
        "device_class": "apparent_power",
        "unit_of_measurement": "VA",
        "state_class": "measurement",
    },
}


def make_payload(conf: Conf, device: str, name: str, key: str, unit: str = None):
    # Default configuration payload
    payload = {
        "name": "{name}",
        "unique_id": f"grott_{device}_{key}",  # Generate a unique device ID
        "state_topic": f"homeassistant/grott/{device}/state",
        "device": {
            "identifiers": [device],  # Group under a device
            "name": device,
            "manufacturer": "GroWatt",
        },
    }

    # If there's a custom mapping add the new values
    if key in mapping:
        payload.update(mapping[key])

    # Reuse the existing divide value if available and not existing
    # and apply it to the HA config
    layout = conf.recorddict[conf.layout]
    if "value_template" not in payload and key in layout:
        # From grottdata:207, default type is num, also process numx
        if layout[key].get("type", "num") in ("num", "numx") and layout[key].get(
            "divide", "1"
        ):
            payload[
                "value_template"
            ] = "{{{{ value_json.{key} | float / {divide} }}}}".format(
                key=key,
                divide=layout[key].get("divide"),
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
        "ha_mqtt_host",
        "ha_mqtt_port",
    ]
    if not all([param in conf.extvar for param in required_params]):
        print("Missing configuration for ha_mqtt")
        raise AttributeError

    if "ha_mqtt_user" in conf.extvar:
        auth = {
            "username": conf.extvar["ha_mqtt_user"],
            "password": conf.extvar["ha_mqtt_password"],
        }
    else:
        auth = None

    # Need to convert the port if passed as a string
    port = conf.extvar["ha_mqtt_port"]
    if isinstance(port, str):
        port = int(port)
    return {
        "client_id": MqttStateHandler.client_name,
        "auth": auth,
        "hostname": conf.extvar["ha_mqtt_host"],
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
        "ha_mqtt_host",
        "ha_mqtt_port",
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
        print(f"\tGrott HA {__version__} - creating {device_serial} config in HA")
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
                }
            )
        except Exception as e:
            print(
                f"\t - [grott HA] {__version__} Exception while creating new sensor last push: {e}"
            )
            return 4
        publish_multiple(conf, configs_payloads)
        # Now it's configured, no need to come back
        MqttStateHandler.set_configured(device_serial)

    if not MqttStateHandler.is_configured(device_serial):
        print(f"\t[Grott HA] {__version__} Can't configure device: {device_serial}")
        return 7

    # Push the vales to the topics
    try:
        publish_single(
            conf, state_topic.format(device=device_serial), json.dumps(values)
        )
    except Exception as e:
        print("[HA ext] - Exception while publishing - {}".format(e))
        # Reset connection state in case of problem
        return 2
    return 0
