# Testing

This is a simple test system for running `grott` without being connected
to the solar system.

First start grott with test settings:
```shell
python grott.py -v -c test/grott-test.ini
```

Then run the data generator:
```shell
python test/grottdatagenerator.py
```