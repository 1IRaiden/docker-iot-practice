"""
mqtt_bridge.py — замена telegraf для приёма MQTT и записи в InfluxDB.
Используется вместо telegraf из-за несовместимости telegraf 1.25/1.30
с eclipse-mosquitto 1.6 на Debian 13.
"""
import paho.mqtt.client as mqtt
from influxdb import InfluxDBClient
import time
import os

MQTT_HOST   = os.environ.get("MQTT_HOST",   "192.168.3.10")
MQTT_PORT   = int(os.environ.get("MQTT_PORT", "1883"))
INFLUX_HOST = os.environ.get("INFLUX_HOST", "influxdb")
INFLUX_PORT = int(os.environ.get("INFLUX_PORT", "8086"))
INFLUX_DB   = os.environ.get("INFLUX_DB",   "sensors")

influx = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT, database=INFLUX_DB)


def on_connect(client, userdata, flags, rc):
    print(f"[bridge] Connected to MQTT {MQTT_HOST}:{MQTT_PORT} rc={rc}", flush=True)
    client.subscribe("sensors/#")
    print("[bridge] Subscribed to sensors/#", flush=True)


def on_message(client, userdata, msg):
    try:
        topic  = msg.topic
        value  = float(msg.payload.decode())
        parts  = topic.split("/")
        sensor_type = parts[1] if len(parts) > 1 else "unknown"
        sensor_name = parts[2] if len(parts) > 2 else "unknown"

        point = [{
            "measurement": "mqtt_consumer",
            "tags": {
                "sensor": sensor_name,
                "topic":  topic
            },
            "fields": {
                "value": value
            }
        }]
        influx.write_points(point)
        print(f"[bridge] {topic} = {value}", flush=True)
    except Exception as e:
        print(f"[bridge] Error: {e}", flush=True)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

while True:
    try:
        print(f"[bridge] Connecting to {MQTT_HOST}:{MQTT_PORT}...", flush=True)
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except Exception as e:
        print(f"[bridge] Connection failed: {e}. Retry in 5s...", flush=True)
        time.sleep(5)
