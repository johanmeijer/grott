# coding=utf-8
# author Etienne G.

import json
from datetime import datetime, timezone

from paho.mqtt.client import Client

from grottconf import Conf

__version__ = "0.0.3"

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
state_topic = "homeassistant/grott/{device}/state"


mapping = {
    "datalogserial": {
        "name": "{device} Datalogger serial",
    },
    "pvserial": {"name": "{device} Serial"},
    "pv1watt": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "{device} PV1 Watt",
        "unit_of_measurement": "w",
        "value_template": "{{value_json.pv1watt| float / 10 }}",
    },
    "pv1voltage": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "{device} PV1 Voltage",
        "unit_of_measurement": "V",
        "value_template": "{{value_json.pv1voltage| float / 10 }}",
    },
    "pv1current": {
        "state_class": "measurement",
        "device_class": "current",
        "name": "{device} PV1 Current",
        "unit_of_measurement": "A",
        "value_template": "{{value_json.pv1current| float / 10 }}",
    },
    "pv2watt": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "{device} PV2 Watt",
        "unit_of_measurement": "w",
        "value_template": "{{value_json.pv2watt| float / 10 }}",
    },
    "pv2voltage": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "{device} PV2 Voltage",
        "unit_of_measurement": "V",
        "value_template": "{{value_json.pv2voltage| float / 10 }}",
    },
    "pv2current": {
        "state_class": "measurement",
        "device_class": "current",
        "name": "{device} PV2 Current",
        "unit_of_measurement": "A",
        "value_template": "{{value_json.pv2current| float / 10 }}",
    },
    "pvpowerin": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "{device} Input kiloWatt (Actual)",
        "unit_of_measurement": "kW",
        "value_template": "{{value_json.pvpowerin| float / 10000 }}",
    },
    "pvpowerout": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "{device} Output kiloWatt (Actual)",
        "unit_of_measurement": "kW",
        "value_template": "{{value_json.pvpowerout| float / 10000 }}",
    },
    "pvfrequentie": {
        "state_class": "measurement",
        "device_class": "frequency",
        "name": "{device} Grid frequency",
        "unit_of_measurement": "Hz",
        "value_template": "{{value_json.pvfrequentie| float / 100 }}",
        "icon": "mdi:waveform",
    },
    # Grid config
    "pvgridvoltage": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "{device} Phase 1 voltage",
        "unit_of_measurement": "V",
        "value_template": "{{value_json.pvgridvoltage| float / 10 }}",
    },
    "pvgridvoltage2": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "{device} Phase 2 voltage",
        "unit_of_measurement": "V",
        "value_template": "{{value_json.pvgridvoltage2| float / 10 }}",
    },
    "pvgridvoltage3": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "{device} Phase 3 voltage",
        "unit_of_measurement": "V",
        "value_template": "{{value_json.pvgridvoltage3| float / 10 }}",
    },
    "pvgridcurrent": {
        "state_class": "measurement",
        "device_class": "current",
        "name": "{device} Phase 1 current",
        "unit_of_measurement": "A",
        "value_template": "{{value_json.pvgridcurrent| float / 10 }}",
    },
    "pvgridcurrent2": {
        "state_class": "measurement",
        "device_class": "current",
        "name": "{device} Phase 2 current",
        "unit_of_measurement": "A",
        "value_template": "{{value_json.pvgridcurrent2| float / 10 }}",
    },
    "pvgridcurrent3": {
        "state_class": "measurement",
        "device_class": "current",
        "name": "{device} Phase 3 current",
        "unit_of_measurement": "A",
        "value_template": "{{value_json.pvgridcurrent3| float / 10 }}",
    },
    "pvgridpower": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "{device} Phase 1 power",
        "unit_of_measurement": "kW",
        "value_template": "{{value_json.pvgridpower| float / 10000 }}",
    },
    "pvgridpower2": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "{device} Phase 2 power",
        "unit_of_measurement": "kW",
        "value_template": "{{value_json.pvgridpower2| float / 10000 }}",
    },
    "pvgridpower3": {
        "state_class": "measurement",
        "device_class": "power",
        "name": "{device} Phase 3 power",
        "unit_of_measurement": "kW",
        "value_template": "{{value_json.pvgridpower3| float / 10000 }}",
    },
    # End grid
    "pvenergytoday": {
        "state_class": "total",
        "device_class": "energy",
        "name": "{device} Generated energy (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.pvenergytoday| float / 10 }}",
        "icon": "mdi:solar-power",
    },
    "pvenergytotal": {
        "state_class": "total_increasing",
        "device_class": "energy",
        "name": "{device} Generated energy (Total)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.pvenergytotal| float / 10 }}",
        "icon": "mdi:solar-power",
    },
    "epvtotal": {
        "device_class": "energy",
        "name": "{device} Generated PV energy (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.epvToday| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "pactogridr": {
        "state_class": "measurement",
        "device_class": "energy",
        "name": "{device} Energy export (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.pactogridr| float / 10 }}",
        "icon": "mdi:solar-power",
    },
    "pactogridtot": {
        "device_class": "energy",
        "name": "{device} Energy export (Total)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.pactogridtot| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "pvstatus": {
        "name": "{device} State",
        "value_template": "{% if value_json.pvstatus == 0 %}Standby{% elif value_json.pvstatus == 1 %}Normal{% elif value_json.pvstatus == 2 %}Fault{% else %}Unknown{% endif %}",
        "icon": "mdi:power-settings",
    },
    "totworktime": {
        "device_class": "duration",
        "name": "{device} Working time",
        "unit_of_measurement": "hours",
        "value_template": "{{ value_json.totworktime| float / 7200 | round(2) }}",
    },
    "pvtemperature": {
        "state_class": "measurement",
        "device_class": "temperature",
        "name": "{device} Inverter temperature",
        "unit_of_measurement": "°C",
        "value_template": "{{value_json.pvtemperature| float / 10 }}",
    },
    "pvipmtemperature": {
        "device_class": "temperature",
        "unit_of_measurement": "°C",
        "value_template": "{{value_json.pvipmtemperature| float / 10 }}",
        "state_class": "measurement",
    },  # TODO, find name: "name": "{device} Inverter temperature",
    "pvboottemperature": {
        "device_class": "temperature",
        "name": "{device} Inverter boost temperature",
        "unit_of_measurement": "°C",
        "value_template": "{{value_json.pvboottemperature| float / 10 }}",
        "state_class": "measurement",
    },
    "pvboosttemp": {
        "device_class": "temperature",
        "name": "{device} Inverter boost temperature",
        "unit_of_measurement": "°C",
        "value_template": "{{value_json.pvboosttemp| float / 10 }}",
        "state_class": "measurement",
    },
    "etogrid_tod": {
        "device_class": "energy",
        "name": "{device} Energy to grid (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.etogrid_tod| float / 10 }}",
        "icon": "mdi:transmission-tower-import",
        "state_class": "total",
    },
    "etogrid_tot": {
        "device_class": "energy",
        "name": "{device} Energy to grid (Total)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.etogrid_tot| float / 10 }}",
        "icon": "mdi:transmission-tower-import",
        "state_class": "total_increasing",
    },
    "etouser_tod": {
        "device_class": "energy",
        "name": "{device} Import from grid (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.etouser_tod| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "etouser_tot": {
        "device_class": "energy",
        "name": "{device} Import from grid (Total)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.etouser_tot| float / 10 }}",
        "icon": "mdi:transmission-tower-export",
        "state_class": "total_increasing",
    },
    "pactouserr": {
        "name": "{device} Import from grid current",
        "device_class": "power",
        "unit_of_measurement": "kW",
        "value_template": "{{value_json.pactouserr| float / 10 }}",
        "icon": "mdi:transmission-tower-export",
    },
    # Register 1015 # TODO: investiagate
    # "pactousertot": {
    #     "name": "{device} Power consumption total",
    #     "device_class": "power",
    #     "unit_of_measurement": "kW",
    #     "icon": "mdi:transmission-tower-export",
    # },
    "elocalload_tod": {
        "device_class": "energy",
        "name": "{device} Load consumption (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.elocalload_tod| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "elocalload_tot": {
        "device_class": "energy",
        "name": "{device} Load consumption (Total)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.elocalload_tot| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "plocaloadr": {
        "name": "{device} Local load consumption",
        "device_class": "power",
        "unit_of_measurement": "kW",
        "value_template": "{{value_json.plocaloadr| float / 10 }}",
        "icon": "mdi:transmission-tower-export",
    },
    "epv1today": {
        "device_class": "energy",
        "name": "{device} Solar production (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.epv1today| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "epv1total": {
        "device_class": "energy",
        "name": "{device} Solar production (Total)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.epv1total| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "epv2today": {
        "device_class": "energy",
        "name": "{device} Solar PV2 production (Today)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.epv2today| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total",
    },
    "epv2total": {
        "device_class": "energy",
        "name": "{device} Solar PV2 production (Total)",
        "unit_of_measurement": "kWh",
        "value_template": "{{value_json.epv2total| float / 10 }}",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "grott_last_push": {
        "device_class": "timestamp",
        "name": "{device} Grott last data push",
        "value_template": "{{value_json.grott_last_push}}",
    },
    "grott_last_measure": {
        "device_class": "timestamp",
        "name": "{device} Last measure",
    },
    # batteries
    "eacharge_today": {
        "device_class": "energy",
        "name": "{device} Battery charge from AC (Today)",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-up",
        "state_class": "total",
    },
    "eacharge_total": {
        "device_class": "energy",
        "name": "{device} Battery charge from AC (Today)",
        "unit_of_measurement": "kWh",
        "icon": "mdi:solar-power",
        "state_class": "total_increasing",
    },
    "vbat": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "{device} Battery voltage",
        "unit_of_measurement": "V",
    },
    "SOC": {
        "name": "{device} Battery charge",
        "device_class": "battery",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "icon": "mdi:battery-charging-60",
    },
    # taken from register 1048 of RTU manual v1.20
    "batterytype": {
        "name": "{device} Batteries type",
        "value_template": "{% if value_json.batterytype == 0 %}Lithium{% elif value_json.batterytype == '1' %}Lead-acid{% elif value_json.batterytype == '2' %}Other{% else %}Unknown{% endif %}",
        "icon": "mdi:power-settings",
    },
    "p1charge1": {
        "name": "{device} Battery charge",
        "device_class": "power",
        "unit_of_measurement": "kW",
        "icon": "mdi:battery-arrow-up",
    },
    "eharge1_tod": {
        "name": "{device} Battery charge (Today)",
        "device_class": "energy",
        "state_class": "total",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-up",
    },
    "eharge1_tot": {
        "name": "{device} Battery charge (Total)",
        "device_class": "energy",
        "state_class": "total_increasing",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-up",
    },
    "edischarge1_tod": {
        "name": "{device} Battery discharge (Today)",
        "device_class": "energy",
        "state_class": "total",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-down",
    },
    "edischarge1_tot": {
        "name": "{device} Battery discharge (Total)",
        "device_class": "energy",
        "state_class": "total_increasing",
        "unit_of_measurement": "kWh",
        "icon": "mdi:battery-arrow-down",
    },
    "battemp": {
        "name": "{device} Battery temperature",
        "device_class": "temperature",
        "unit_of_measurement": "°C",
        "icon": "mdi:thermometer",
    },
    "spbusvolt": {
        "state_class": "measurement",
        "device_class": "voltage",
        "name": "{device} BP bus voltage",
        "unit_of_measurement": "V",
    },
    "systemfaultword3": {
        "name": "{device} System faultregister",
        "value_template": """
            {% if value_json.systemfaultword3 == 0%}
                OK
            {% else %}
                {% if value_json.systemfaultword3|int|bitwise_and(1) > 0 %}
                    Battery reverse
                {% endif %}
                {% if value_json.systemfaultword3|int|bitwise_and(2) > 0 %}
                    BMS Battery Open
                {% endif %}
                {% if value_json.systemfaultword3|int|bitwise_and(4) > 0 %}
                    Battery Voltage Low
                {% endif %}
            {% endif %}
        """,
    },
}


def make_payload(
    conf: Conf, device: str, device_class: str, name: str, key: str, unit: str = None
):
    payload = {
        "name": "{device} {name}",
        "unique_id": f"grott_{device}_{key}",  # Generate a unique device ID
        "state_topic": f"homeassistant/grott/{device}/state",
        "device": {
            "identifiers": [device],  # Group under a device
            "name": device,
            "manufacturer": "GrowWatt",
        },
        "value_template": f"{{{{ value_json.{key} }}}}",
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
                payload[
                    "value_template"
                ] = "{{{{value_json.{key} | float / {divide} }}}}".format(
                    key=key,
                    divide=layout[key].get("divide"),
                )
    return payload


class MqttStateHandler:
    # Hold the persistent connection
    __mqtt_conn: Client = None
    __pv_config = {}

    @classmethod
    def get_conn(cls, conf):
        # Prevent making a lot of connections, reuse the existing one
        if cls.__mqtt_conn:
            return cls.__mqtt_conn

        cls.__mqtt_conn = Client("grott - ha")
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
        try:
            # Try to close cleanly
            if cls.__mqtt_conn:
                cls.__mqtt_conn.disconnect()
        except Exception as e:
            print(f"\t - Error while closing HA conneciton: {e}")
            pass
        cls.__mqtt_conn = None


def grottext(conf: Conf, data: str, jsonmsg: str):
    """Allow to push to HA MQTT bus, with auto discovery"""

    required_params = [
        "ha_mqtt_host",
        "ha_mqtt_port",
    ]
    if not all([param in conf.extvar for param in required_params]):
        print("Missing configuration for ha_mqtt")
        return 1

    try:
        conn = MqttStateHandler.get_conn(conf)
    except Exception as e:
        MqttStateHandler.reset()
        print("[HA Extension] Error while connecting to HA: {}".format(e))
        return 3

    # Need to decode the json string
    jsonmsg = json.loads(jsonmsg)

    if jsonmsg.get("buffered") == "yes":
        # Skip buffered message, HA don't support them
        if conf.verbose:
            print("\t - Grott HA - skipped buffered")
        return 1

    device_serial = jsonmsg["device"]
    values = jsonmsg["values"]

    # Send the last push in UTC with TZ
    dt = datetime.now(timezone.utc)
    # Add a new value to the existing values
    values["grott_last_push"] = dt.isoformat()

    if not MqttStateHandler.is_configured(device_serial):
        print(f"\tGrott HA {__version__} - creating {device_serial} config in HA")
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
                    retain=True,
                )
            except:
                # Reset connection state in case of problem
                MqttStateHandler.reset()
                return 1

        # Create a virtual last_push key to allow tracking when there was the last data transmission

        try:
            key = "grott_last_push"
            payload = make_payload(conf, device_serial, "", key, key)
            conn.publish(
                config_topic.format(
                    sensor_type="sensor",
                    device=device_serial,
                    attribut=key,
                ),
                json.dumps(payload),
                retain=True,
            )
        except:
            # Reset connection state in case of problem
            MqttStateHandler.reset()
            return 4

        # Now it's configured, no need to come back
        MqttStateHandler.set_configured(device_serial)

    # Push the vales to the topics
    try:
        conn.publish(
            state_topic.format(device=device_serial), json.dumps(values)
        )
    except Exception as e:
        print("[HA ext] - Exception while publishing - {}".format(e))
        # Reset connection state in case of problem
        MqttStateHandler.reset()
        return 2
    return 0
