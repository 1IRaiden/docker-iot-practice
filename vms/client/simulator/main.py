import paho.mqtt.client as paho
import time
import json
from os import environ

from entity.sensor import Temperature, Pressure, Current, Humidity

broker    = environ.get("SIM_HOST",         "localhost")
port      = int(environ.get("SIM_PORT",     "1883"))
name      = environ.get("SIM_NAME",         "sensor1")
period    = int(environ.get("SIM_PERIOD",   "5"))
type_sim  = environ.get("SIM_TYPE",         "temperature")
topic_fmt = environ.get("SIM_TOPIC_FORMAT", "value")

sensors = {
    "temperature": Temperature,
    "pressure":    Pressure,
    "current":     Current,
    "humidity":    Humidity,
}


def on_publish(client, userdata, result):
    print(f"[{name}] published", flush=True)


sensor = sensors[type_sim](name=name)
client = paho.Client(sensor.name)
client.on_publish = on_publish
client.connect(broker, port)

print(f"[{name}] type={type_sim} period={period}s format={topic_fmt}", flush=True)

while True:
    sensor.generate_new_value()

    if topic_fmt == "json":
        topic   = f"sensors/{sensor.type}"
        payload = json.dumps({"name": sensor.name, "value": sensor.value})
    else:
        topic   = f"sensors/{sensor.type}/{sensor.name}"
        payload = sensor.get_data()

    client.publish(topic, payload)
    print(f"[{name}] -> {topic} : {payload}", flush=True)
    time.sleep(period)
