# Integration with Home Assistant

## MQTT integration
Home Assistant supports a modular configuration.
If you create a folder called "sensors" under your configuration folder (commonly ".homeassistant"), you can place one of these yaml files in there.
Your own configuration can be placed in a separate file as well.

```yaml
sensor: !include_dir_merge_list sensors/
```

### Energy Dashboard

Add your solar panels via Setting > Dashboards > Energy, "Add Solar Production", `sensor.growatt_generated_energy_total`

## HA extension

To use this extension, copy the file `grott_ha.py` to the root of the project.

Edit your `grott.ini` file and add:

```ini
[extension] 
# grott extension parameters definitions
extension = True
extname = grott_ha
extvar = {"ha_mqtt_host": "HA_MQTT_SERVER", "ha_mqtt_port": "HA_MQTT_PORT", "ha_mqtt_user": "HA_MQTT_USER", "ha_mqtt_password": "HA_MQTT_PASSWORD"}
```

Replace the values by the values for your configuration (you can use your user/password to authenticate wit the MQTT Server)

Run Grott, the new device should appear shortly.