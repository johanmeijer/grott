# coding=utf-8
# author Etienne G.

import json
from datetime import datetime, timezone

from paho.mqtt.client import Client

from grottconf import Conf

"""A pluging for grott
This plugin allow to have autodiscovery of the device in HA

Should be able to support multiples inverters

Config:
    - ha_mqtt_host (required): The host of the MQTT broker user by HA (often the IP of HA)
    - ha_mqtt_port (required): The port (the default is oftent 1883)
    - ha_mqtt_user (optional): The user use to connect to the broker (you can use your user)
    - ha_mqtt_password (optional): The password to connect to the mqtt broket (you can use your password)
"""


config_topic = "homeassistant/{sensor_type}/grott/{device}_{attribut}/config"
state_topic = "homeassistant/grott/{device}_{attribut}/state"


mapping = {
    "datalogserial": {
        "name": "{device} - Serial",
    },
    "pvserial": {"name": "{device} - Serial"},
    "vbat": {
        "device_class": "voltage",
        "name": "{device} - Batteries voltage",
        "unit": "V",
        "value_template": "{{value| float / 10 }}",
    },
    "pv1watt": {
        "device_class": "power",
        "name": "{device} - PV1 Watt",
        "unit": "w",
        "value_template": "{{value| float / 10 }}",
    },
    "pv1voltage": {
        "device_class": "voltage",
        "name": "{device} - PV1 Voltage",
        "unit": "V",
        "value_template": "{{value| float / 10 }}",
    },
    "pv1current": {
        "device_class": "current",
        "name": "{device} - PV1 Current",
        "unit": "A",
        "value_template": "{{value| float / 10 }}",
    },
    "pv2watt": {
        "device_class": "power",
        "name": "{device} - PV2 Watt",
        "unit": "w",
        "value_template": "{{value| float / 10 }}",
    },
    "pv2voltage": {
        "device_class": "voltage",
        "name": "{device} - PV2 Voltage",
        "unit": "V",
        "value_template": "{{value| float / 10 }}",
    },
    "pv2current": {
        "device_class": "current",
        "name": "{device} - PV2 Current",
        "unit": "A",
        "value_template": "{{value| float / 10 }}",
    },
    "pvpowerin": {
        "device_class": "power",
        "name": "{device} - Input kiloWatt (Actual)",
        "unit": "kW",
        "value_template": "{{value| float / 10000 }}",
    },
    "pvpowerout": {
        "device_class": "power",
        "name": "{device} - Output kiloWatt (Actual)",
        "unit": "kW",
        "value_template": "{{value| float / 10000 }}",
    },
    "pvfrequentie": {
        "name": "{device} - Grid frequency",
        "unit": "Hz",
        "value_template": "{{value| float / 100 }}",
        "icon": "mdi:waveform",
    },
    # Grid config
    "pvgridvoltage": {
        "device_class": "voltage",
        "name": "{device} - Phase 1 voltage",
        "unit": "V",
        "value_template": "{{value| float / 10 }}",
    },
    "pvgridvoltage2": {
        "device_class": "voltage",
        "name": "{device} - Phase 2 voltage",
        "unit": "V",
        "value_template": "{{value| float / 10 }}",
    },
    "pvgridvoltage3": {
        "device_class": "voltage",
        "name": "{device} - Phase 3 voltage",
        "unit": "V",
        "value_template": "{{value| float / 10 }}",
    },
    "pvgridcurrent": {
        "device_class": "current",
        "name": "{device} - Phase 1 current",
        "unit": "A",
        "value_template": "{{value| float / 10 }}",
    },
    "pvgridcurrent2": {
        "device_class": "current",
        "name": "{device} - Phase 2 current",
        "unit": "A",
        "value_template": "{{value| float / 10 }}",
    },
    "pvgridcurrent3": {
        "device_class": "current",
        "name": "{device} - Phase 3 current",
        "unit": "A",
        "value_template": "{{value| float / 10 }}",
    },
    "pvgridpower": {
        "device_class": "power",
        "name": "{device} - Phase 1 power",
        "unit": "kW",
        "value_template": "{{value| float / 10000 }}",
    },
    "pvgridpower2": {
        "device_class": "power",
        "name": "{device} - Phase 2 power",
        "unit": "kW",
        "value_template": "{{value| float / 10000 }}",
    },
    "pvgridpower3": {
        "device_class": "power",
        "name": "{device} - Phase 3 power",
        "unit": "kW",
        "value_template": "{{value| float / 10000 }}",
    },
    # End grid
    "pvenergytoday": {
        "device_class": "energy",
        "name": "{device} - Generated energy (Today)",
        "unit": "kWh",
        "value_template": "{{value| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "pvenergytotal": {
        "device_class": "energy",
        "name": "{device} - Generated energy (Total)",
        "unit": "kWh",
        "value_template": "{{value| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "pvstatus": {
        "name": "{device} - State",
        "value_template": "{% if value == '0' %}Waiting{% elif value == '1' %}Normal{% elif value == '2' %}Fault{% else %}Unknown{% endif %}",
        "icon": "mdi:power-settings",
    },
    "totworktime": {
        "device_class": "duration",
        "name": "{device} - Working time",
        "unit": "hours",
        "value_template": "{{ value| float / 7200 }}",
    },
    "pvtemperature": {
        "device_class": "temperature",
        "name": "{device} - Inverter temperature",
        "unit": "°C",
        "value_template": "{{value| float / 10 }}",
    },
    "pvipmtemperature": {
        "device_class": "temperature",
        "unit": "°C",
        "value_template": "{{value| float / 10 }}",
    },  # TODO, find name: "name": "{device} - Inverter temperature",
    "pvboottemperature": {
        "device_class": "temperature",
        "name": "{device} - Inverter boost temperature",
        "unit": "°C",
        "value_template": "{{value| float / 10 }}",
    },
    "etogrid_tod": {
        "device_class": "energy",
        "name": "{device} - Energy to grid (Today)",
        "unit": "kWh",
        "value_template": "{{value| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "etogrid_tot": {
        "device_class": "energy",
        "name": "{device} - Energy to grid (Total)",
        "unit": "kWh",
        "value_template": "{{value| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "etouser_tod": {
        "device_class": "energy",
        "name": "{device} - Energy to user (Today)",
        "unit": "kWh",
        "value_template": "{{value| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "etouser_tot": {
        "device_class": "energy",
        "name": "{device} - Energy to user (Total)",
        "unit": "kWh",
        "value_template": "{{value| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "grott_last_push": {
        "device_class": "timestamp",
        "name": "{device} - Grott last data push",
    },
}


def make_payload(
    conf: Conf, device: str, device_class: str, name: str, key: str, unit: str = None
):
    payload = {
        "name": "{device} - {name}",
        "unique_id": f"grott_{device}_{key}",  # Generate a unique device ID
        "state_topic": f"homeassistant/grott/{device}_{name}/state",
        "device": {
            "identifiers": [device],  # Group under a device
            "name": device,
            "manufacturer": "GrowWatt",
        },
    }

    # If there's a custom mapping add the new values
    if key in mapping:
        payload.update(mapping[key])

    # Generate the name of the key, with all the param available
    payload["name"] = payload["name"].format(
        device=device, device_class=device_class, name=name, key=key
    )

    # Reuse the existing divide value if available and not existing
    # and apply it to the HA config
    layout = conf.recorddict[conf.layout]
    if key in layout:
        if layout[key].get("type", "") == "num" and layout[key].get("divide"):
            if "value_template" not in payload:
                payload["value_template"] = "{{value| float / %s }}" % (
                    layout[key].get("divide"),
                )
    return payload


class MqttStateHandler:
    # Hold the persistent connection
    __mqtt_conn = None
    __pv_config = {}

    @classmethod
    def get_conn(cls, conf):
        # Prevent making a lot of connections, reuse the existing one
        if cls.__mqtt_conn:
            return cls.__mqtt_conn

        cls.__mqtt_conn = Client()
        if "ha_mqtt_user" in conf.extvar:
            cls.__mqtt_conn.username_pw_set(
                conf.extvar["ha_mqtt_user"], conf.extvar["ha_mqtt_password"]
            )

        # Need to convert the port if passed as a string
        port = conf.extvar["ha_mqtt_port"]
        if isinstance(port, str):
            port = int(port)

        cls.__mqtt_conn.connect(conf.extvar["ha_mqtt_host"], port)
        return cls.__mqtt_conn

    @classmethod
    def is_configured(cls, serial: str):
        return cls.__pv_config.get(serial, False)

    @classmethod
    def set_configured(cls, serial: str):
        cls.__pv_config[serial] = True

    @classmethod
    def reset(cls):
        cls.__mqtt_conn = None
        cls.__pv_config = {}


def grottext(conf: Conf, data: str, jsonmsg: dict):
    """Allow to push to HA MQTT bus, with auto discovery"""

    required_params = [
        "ha_mqtt_host",
        "ha_mqtt_port",
    ]
    if not all([param in conf.extvar for param in required_params]):
        print("Missing configuration for ha_mqtt")
        return 1

    conn = MqttStateHandler.get_conn(conf)

    # Need to decode the json string
    jsonmsg = json.loads(jsonmsg)

    device_serial = jsonmsg["device"]
    values = jsonmsg["values"]

    if not MqttStateHandler.is_configured(device_serial):
        print(f"\tGrott HA - creating {device_serial} config in HA")
        for key in values.keys():
            # Generate a configuration payload
            payload = make_payload(conf, device_serial, "", key, key)

            try:
                conn.publish(
                    config_topic.format(
                        sensor_type="sensor",
                        device=device_serial,
                        attribut=key,
                    ),
                    json.dumps(payload),
                )
            except:
                # Reset connection state in case of problem
                MqttStateHandler.reset()
                return 1

        # Create a virtual last_push key to allow tracking when there was the last data transmission
        key = "grott_last_push"
        payload = make_payload(conf, device_serial, "", key, key)
        try:
            conn.publish(
                config_topic.format(
                    sensor_type="sensor",
                    device=device_serial,
                    attribut=key,
                ),
                json.dumps(payload),
            )
        except:
            # Reset connection state in case of problem
            MqttStateHandler.reset()
            return 1

        # Now it's configured, no need to come back
        MqttStateHandler.set_configured(device_serial)

    # Push the vales to the topics
    try:
        for key, value in values.items():
            conn.publish(state_topic.format(device=device_serial, attribut=key), value)
        # Send the last push in UTC with TZ
        dt = datetime.now(timezone.utc)
        conn.publish(
            state_topic.format(device=device_serial, attribut="grott_last_push"),
            dt.isoformat(),
        )
    except:
        # Reset connection state in case of problem
        MqttStateHandler.reset()
        return 2
    return 0
