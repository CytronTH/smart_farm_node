# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import busio
import json
import wifi
import ssl
import socketpool
from adafruit_bme280 import basic as adafruit_bme280
from adafruit_minimqtt.adafruit_minimqtt import MQTT

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

mqtt_topic = "tele/air_data"

count1 = 0
count2 = 0
count3 = 0
count4 = 0

i2c = busio.I2C(board.GP5, board.GP4)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
bme280.sea_level_pressure = 1013.25

def send_sensor_data(data):
    mqtt_client = MQTT(broker=mqtt_broker, port=mqtt_port, username=mqtt_username, password=mqtt_password)
    mqtt_client.connect()
    mqtt_client.publish(mqtt_topic, json.dumps(data))
    mqtt_client.disconnect()

# Connect to Wi-Fi
def connect_to_wifi():
    global count1
    print("Connecting to %s" % secrets["ssid"])
    while not wifi.radio.connected:
        try:
            wifi.radio.connect(secrets["ssid"], secrets["password"])
            print("Connected to WiFi")
        except Exception as e:
            count1 = count1 + 1
            print("could not connect to %s, retrying %d: ",secrets["ssid"], count1, e)

def reconnect_to_wifi():
    global count2
    print("Try to re-connecting to WiFi")
    while not wifi.radio.connected:
        try:
            wifi.radio.connect(secrets["ssid"], secrets["password"])
            print("WiFi connection is return. Try to re-connect to MQTT Broker")
            mqtt_client.reconnect()
        except Exception as e:
            count2 = count2 + 1
            print("could not connect to WiFi, retrying %d: ",count2, e)

# Reconnect to Wi-Fi if the connection is lost
def check_wifi_connection():
    if wifi.radio.connected == False:
        print("Wi-Fi connection lost. Reconnecting...")
        reconnect_to_wifi()
    else:
        return

def start_mqtt_connection():
    global count3
    print("Start MQTT Broker connection")
    print("Attempting to connect to %s" % mqtt_client.broker)
    while not mqtt_client.is_connected():
        try:
            mqtt_client.connect()
            print("Connected to MQTT Broker!")
        except Exception as e:
            count3 = count3 + 1
            print("could not connect to MQTT Broker, retrying %d: ",count3, e)

def check_mqtt_connection():
    global count4
    print("Checking MQTT Broker connection")
#    while mqtt_client.is_connected() == False:
    try:
        mqtt_client.reconnect()
        print("Reconnected to MQTT Broker!")
    except Exception as e:
        count4 += 1
        print("BrokenPipeError occurred. Reconnecting to MQTT Broker... ({0})".format(count4))

def connect(mqtt_client, userdata, flags, rc):
    print("Flags: {0}\n RC: {1}".format(flags, rc))
    
def publish(mqtt_client, userdata, topic, pid):
    # This method is called when the mqtt_client publishes data to a feed.
    print("Published to {0} with PID {1}".format(topic, pid))

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Set up a MiniMQTT Client
mqtt_client = MQTT(
    broker=secrets["broker"],
    port=secrets["port"],
    username=secrets["user"],
    password=secrets["pass"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Connect callback handlers to mqtt_client
mqtt_client.on_connect = connect
mqtt_client.on_publish = publish

connect_to_wifi()
start_mqtt_connection()

while True:
    try:
        check_wifi_connection()
        # Recheck Wi-Fi and MQTT connections before sending new data
        bme280_data = {
            "Temperature": bme280.temperature,
            "Humidity": bme280.relative_humidity,
            "Pressure": bme280.pressure,
            "Altitude": bme280.altitude
        }

        print("BME280 Sensor Readings:")
        for key, value in bme280_data.items():
            print(f"{key} : {value}")
        print("\n------------------------------------------------")

        complete_data = json.dumps(bme280_data)

        # Send the combined data via MQTT
        mqtt_client.publish(mqtt_topic, complete_data)

        time.sleep(5)
    except Exception as e:
        print("MQTT Exception: {0}".format(e))
        print("Reconnecting to MQTT Broker...")
        time.sleep(2)
        print(mqtt_client.is_connected())
        check_mqtt_connection()