# Integration with Home Assistant

Home Assistant supports a modular configuration.
If you create a folder called "sensors" under your configuration folder (commonly ".homeassistant"), you can place one of these yaml files in there.
Your own configuration can be placed in a separate file as well.

```yaml
sensor: !include_dir_merge_list sensors/
```

## Energy Dashboard

Add your solar panels via Setting > Dashboards > Energy, "Add Solar Production", `sensor.growatt_generated_energy_total`
