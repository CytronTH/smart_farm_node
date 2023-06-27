import time
import board
import busio
from adafruit_as7341 import AS7341
import adafruit_ltr390
import json
import wifi
import ssl
import socketpool
import microcontroller
from adafruit_minimqtt.adafruit_minimqtt import MQTT

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

mqtt_topic = "tele/light_node"

i2c1 = busio.I2C(board.GP27, board.GP26)  # uses board.SCL and board.SDA
i2c2 = busio.I2C(board.GP5, board.GP4)

count1 = 0
count2 = 0
count3 = 0
count4 = 0

sensor = AS7341(i2c1)
ltr = adafruit_ltr390.LTR390(i2c2)

def bar_graph(read_value):
    scaled = int(read_value / 1000)
    return "[%5d] " % read_value + (scaled * "*")

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
        as7341_data = {
            "415nm/Violet": sensor.channel_415nm,
            "445nm/Indigo": sensor.channel_445nm,
            "480nm/Blue": sensor.channel_480nm,
            "15nm/Cyan": sensor.channel_515nm,
            "555nm/Green": sensor.channel_555nm,
            "590nm/Yellow": sensor.channel_590nm,
            "630nm/Orange": sensor.channel_630nm,
            "680nm/Red": sensor.channel_680nm,
            "Clear": sensor.channel_clear,
            "Near-IR (NIR)": sensor.channel_nir
        }

        ltr390_data = {
            "UV": ltr.uvs,
            "Ambient_Light": ltr.light,
            "UVI": ltr.uvi,
            "Lux": ltr.lux
        }

        print("AS7341 Sensor Readings:")
        for key, value in as7341_data.items():
            print(f"{key} : {value}")
        print("\n------------------------------------------------")

        print("LTR390 Sensor Readings:")
        for key, value in ltr390_data.items():
            print(f"{key}: {value}")
        print("\n================================================")

        # Create a combined dictionary
        combined_data = {
            "AS7341": as7341_data,
            "LTR390": ltr390_data
        }
        complete_data = json.dumps(combined_data)

        # Send the combined data via MQTT
        mqtt_client.publish(mqtt_topic, complete_data)

        time.sleep(10)
    except Exception as e:
        print("MQTT Exception: {0}".format(e))
        print("Reconnecting to MQTT Broker...")
        time.sleep(2)
        print(mqtt_client.is_connected())
        check_mqtt_connection()


