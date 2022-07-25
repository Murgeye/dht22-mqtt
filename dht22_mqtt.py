#!/usr/bin/env python3
"""
Python3 script for getting values from a DHT22 Sensor on a Raspberry PI and
publishing these values to an MQTT broker.

Forked from: https://github.com/rsaikali/dht22-mqtt
"""
import logging
import os
import time
import argparse
import sys
from configparser import ConfigParser
import socket
import ssl
import json
from time import sleep

import adafruit_dht
import paho.mqtt.client as mqtt

DEFAULT_BASE_TOPIC = 'homeassistant'
DEFAULT_SENSOR_NAME = '{}_dht22'.format(socket.gethostname()).replace("-", "_")

PROJECT_NAME = 'DHT-22 Raspberry MQTT Client/Daemon'
PROJECT_URL = 'https://github.com/Murgeye/dht22-mqtt'

logging.basicConfig(level=logging.DEBUG,
        format='%(asctime)s [%(name)s] %(levelname)-8s %(message)s')
logger = logging.getLogger("DHT22-MQTT")

def get_config():
    """
    Get and parse config file.
    """
    # Argparse
    parser = argparse.ArgumentParser(description=PROJECT_NAME,
            epilog='For further details see: ' + PROJECT_URL)
    parser.add_argument('--config_dir',
            help='set directory where config.ini is located',
            default=sys.path[0])
    parse_args = parser.parse_args()

    # Load configuration file
    config_dir = parse_args.config_dir

    config = ConfigParser(delimiters=('=', ))
    config.optionxform = str
    config.read([os.path.join(config_dir, 'config.ini')])
    return config

def on_connect(_client, _userdata, _flags, return_code):
    """
    Callback function for mqtt client. Called after connection was established/failed.
    """
    if return_code == 0:
        logger.info('MQTT connection established')
    else:
        logger.error('Connection error with result code %d - %s', return_code,
            mqtt.connack_string(return_code))
        #kill main thread
        sys.exit(1)

def connect_to_mqtt(config):
    """
    Connect to the MQTT broker using parameters from config.
    """
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    hostname = config["MQTT"].get('HOSTNAME', 'localhost')
    port = config["MQTT"].getint('PORT', 1883)
    username = config["MQTT"].get('USERNAME', None)
    password = config["MQTT"].get('PASSWORD', None)

    if config['MQTT'].getboolean('TLS', False):
        # According to the docs, setting PROTOCOL_SSLv23 "Selects the highest protocol version
        # that both the client and server support. Despite the name, this option can select
        # “TLS” protocols as well as “SSL”" - so this seems like a resonable default
        mqtt_client.tls_set(
            ca_certs=config['MQTT'].get('TLS_CA_CERT', None),
            keyfile=config['MQTT'].get('TLS_KEYFILE', None),
            certfile=config['MQTT'].get('TLS_CERTFILE', None),
            tls_version=ssl.PROTOCOL_SSLv23
        )
    if not(username is None and password is None):
        mqtt_client.username_pw_set(username, password)
    try:
        mqtt_client.connect(hostname,
                            port=port,
                            keepalive=config['MQTT'].getint('KEEPALIVE', 60))
    # pylint: disable=bare-except
    except:
        logger.info('MQTT connection error.\
                Please check your settings in the configuration file "config.ini"',
                error=True, sd_notify=True)
        sys.exit(1)
    else:
        mqtt_client.loop_start()
        sleep(1.0) # some slack to establish the connection
    return mqtt_client

def service_announcement(mqtt_client, sensor_name=DEFAULT_SENSOR_NAME,
        base_topic=DEFAULT_BASE_TOPIC):
    """
    Publish service announcement for Home Assistant to MQTT.
    """
    # Discovery Announcement
    logger.info('Announcing DHT-22 to MQTT broker for auto-discovery ...')
    topic_path = '{}/sensor/{}'.format(base_topic, sensor_name)
    base_payload = {
        "state_topic": "{}/state".format(topic_path).lower()
    }
    # Temperature
    payload = dict(base_payload.items())
    payload['unit_of_measurement'] = '°C'
    payload['value_template'] = "{{ value_json.temperature }}"
    payload['name'] = "{} Temperature".format(sensor_name)
    payload['device_class'] = 'temperature'
    mqtt_client.publish('{}/{}_temperature/config'.format(topic_path, sensor_name).lower(),
            json.dumps(payload), 1, True)
    # Humidity
    payload = dict(base_payload.items())
    payload['unit_of_measurement'] = '%'
    payload['value_template'] = "{{ value_json.humidity }}"
    payload['name'] = "{} Humidity".format(sensor_name)
    mqtt_client.publish('{}/{}_humidity/config'.format(topic_path, sensor_name).lower(),
            json.dumps(payload), 1, True)

def sensor_loop(mqtt_client, dht22_sensor, config,
        sensor_name=DEFAULT_SENSOR_NAME, base_topic=DEFAULT_BASE_TOPIC):
    """
    Actual work loop. If the daemon is enabled, the following loop is performed:
    1. Get DHT22 values
    2. Publish values to MQTT
    3. Sleep for configured period
    If the daemon is not enabled, this loop is only performed once.
    """
    daemon_enabled = config['Daemon'].getboolean('ENABLED', True)
    sleep_period = config['Daemon'].getint('PERIOD', 120)
    max_errors = config["General"].getint('MAX_ERRORS', 5)
    error_count = 0
    while error_count < max_errors:
        logger.info('Retrieving data from DHT-22 sensor...')
        try:
            # Read from sensor
            temperature = dht22_sensor.temperature
            humidity = dht22_sensor.humidity
        except RuntimeError:
            logger.exception("Error reading DHT22 values:")
            # Let's try again after some delay ...
            time.sleep(10)
            continue
        data = {"temperature": temperature, "humidity": humidity}
        try:
            mqtt_client.publish('{}/sensor/{}/state'.format(base_topic, sensor_name).lower(),
                    json.dumps(data))
            logger.info('Publishing: %s --> %s/sensor/%s/state',
                    json.dumps(data), base_topic.lower(), sensor_name.lower())
            sleep(0.5) # some slack for the publish roundtrip and callback function
        # pylint: disable=bare-except
        except:
            logger.exception("An error occured publishing values to MQTT:")

        if daemon_enabled:
            error_count = 0
            logger.info('Sleeping (%d seconds) ...', sleep_period)
            sleep(sleep_period)
        else:
            logger.info('Execution finished in non-daemon-mode')
            break

def main():
    """
    Main function.
    """
    config = get_config()
    base_topic = config['MQTT'].get('BASE_TOPIC', DEFAULT_BASE_TOPIC).lower()
    sensor_name = config['MQTT'].get('SENSOR_NAME', DEFAULT_SENSOR_NAME).lower()
    dht22_pin = config["DHT22"].getint('PIN', 4)

    mqtt_client = connect_to_mqtt(config)

    logger.info("Initializing DHT-22, PIN %d", dht22_pin)

    # Initializes DHT22 on given GPIO pin
    dht22_sensor = adafruit_dht.DHT22(dht22_pin)
    service_announcement(mqtt_client, sensor_name=sensor_name, base_topic=base_topic)
    sensor_loop(mqtt_client, dht22_sensor, config, sensor_name, base_topic=base_topic)
    logger.info("Execution ended!")

if __name__ == "__main__":
    main()
