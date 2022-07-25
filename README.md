# dht22-mqtt for Home Assistant

This is a fork of [rsaikali/dht22-mqtt](https://github.com/rsaikali/dht22-mqtt) for usage with [Home Assistant](https://www.home-assistant.io)
and a TLS enabled MQTT broker.

`dht22-mqtt` is a Python script to get temperature and humidity measures published to a MQTT (message queue) broker.
Temperature and humidity are retrieved through a DHT22 sensor (connected to RaspberryPi GPIO in my case).

Measurements are retrieved using the given GPIO pin, and published into MQTT broker given the topic, host and port you have configured.

## Fork Differences
* Most things adapted from [R4scal/mhz19-mqtt-daemon](https://github.com/R4scal/mhz19-mqtt-daemon)
* Read parameters from config file, not from environment variables
* MQTT with TLS support
* Home Assistant style topics
* Home Assistant style service discovery
* Allow running for one-time reading (by setting Daemon enabled to false)
* Some cleanup
* For now: no explicit docker setup (but should work pretty much the same as before)

## Hardware needed

This project needs a DHT22 temperature and humidity sensor connected to a RaspberryPi.
Many examples are available on Google on how to plug the sensor to RaspberryPi GPIO pins.

<p align="center">
    <img src="https://img3.bgxcdn.com/thumb/large/2014/xiemeijuan/07/SKU146979/SKU146979a.jpg" width="200" height="200">
    <img src="https://www.elektor.fr/media/catalog/product/cache/2b4bee73c90e4689bbc4ca8391937af9/r/a/raspberry-pi-4-4gb.jpg" width="200" height="200">
</p>

Please note that I'll use the GPIO pin 4 in the following chapters.

## How to use it?

`dht22-mqtt` can be used as a standalone Python script or as a Docker container.

### Use as a standalone script

Install Linux requirements on RaspberryPi:

```sh
apt-get update
apt-get install --no-install-recommends -y libgpiod2
```

Git clone the project:

```sh
git clone https://github.com/Murgeye/dht22-mqtt.git
cd dht22-mqtt
```

Install Python requirements:

```sh
pip3 install -r requirements.txt
```

Copy the config.ini.dist to config.ini:
```
cp config.ini.dist config.ini
```

Edit the config according to your needs. Settings should be documented in the `config.ini.dist`.

If you do not set user and password environment variables, auth is not used. 

Launch application:

```sh
python ./dht22_mqtt.py
```

You should see output printed:
```sh
(...)
2022-07-25 12:04:34,128 [DHT22-MQTT] INFO     MQTT connection established
2022-07-25 12:04:35,128 [DHT22-MQTT] INFO     Initializing DHT-22, PIN 4
2022-07-25 12:04:35,133 [DHT22-MQTT] INFO     Announcing DHT-22 to MQTT broker for auto-discovery ...
2022-07-25 12:04:35,134 [DHT22-MQTT] INFO     Retrieving data from DHT-22 sensor...
2022-07-25 12:04:35,397 [DHT22-MQTT] INFO     publishing: {"temperature": 27.6, "humidity": 64.3} --> homeassistant/sensor/state
2022-07-25 12:04:35,900 [DHT22-MQTT] INFO     Sleeping (120 seconds) ...
(...)
```

## Running as systemd service

To keep this script running in the background and on startup, use the supplied `dht22_sensor.service` file.

1. Change the service file by setting WorkingDirectory to the directory you cloned this repository to.
2. Change the path to the python file in ExecStart.
3. Run:
```sh
# Symlink the service file
sudo ln -s $PWD/dht22_sensor.service /etc/systemd/system/dht22_sensor.service 
# Reload service files
sudo systemctl daemon-reload
# Start the service
sudo systemctl start dht22_sensor.service
# Enable startup
sudo systemctl enable dht22_sensor.service
```
4. Check status with
```
sudo systemctl status dht22_sensor.service
```
