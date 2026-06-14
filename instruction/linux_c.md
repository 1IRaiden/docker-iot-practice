# Linux C — Развёртывание сервера (InfluxDB + mqtt_bridge + Grafana)

**Роль машины:** Server — принимает данные из MQTT, хранит в БД, визуализирует  
**IP адрес:** 192.168.3.12  
**ОС:** Debian 13 (Trixie)

---

## 1. Установка Docker

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian bookworm stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo usermod -aG docker $USER
newgrp docker
```

---

## 2. Настройка сети

```bash
sudo ip addr add 192.168.3.12/24 dev enp0s8
sudo ip link set enp0s8 up
```

Постоянная настройка:
```bash
sudo tee /etc/systemd/network/10-enp0s8.network << EOF
[Match]
Name=enp0s8

[Network]
Address=192.168.3.12/24
EOF

sudo systemctl enable systemd-networkd
sudo systemctl restart systemd-networkd
```

Проверка связи с Linux B:
```bash
ping 192.168.3.10 -c 3
# 3 packets transmitted, 3 received, 0% packet loss
```

---

## 3. Структура файлов сервера

```
vms/server/
├── docker-compose.yml
├── influxdb/
│   └── scripts/
│       └── influxdb-init.iql     ← создание БД и пользователя
├── telegraf/
│   └── telegraf.conf             ← конфиг telegraf (резервный)
├── mqtt_bridge/
│   ├── bridge.py                 ← Python-сервис MQTT → InfluxDB
│   ├── Dockerfile
│   └── requirements.txt
└── grafana/
    └── provisioning/
        ├── datasources/
        │   └── default.yaml      ← подключение к InfluxDB
        └── dashboards/
            ├── default.yaml      ← настройки провизионирования
            └── sensors.json      ← JSON дашборда
```

---

## 4. Конфигурация InfluxDB

Файл `influxdb/scripts/influxdb-init.iql` выполняется при первом запуске контейнера:

```sql
CREATE DATABASE sensors;
CREATE USER telegraf WITH PASSWORD 'telegraf' WITH ALL PRIVILEGES;
```

Папка монтируется в `/docker-entrypoint-initdb.d` — это стандартный механизм инициализации InfluxDB 1.8.

---

## 5. Конфигурация Telegraf

Файл `telegraf/telegraf.conf` монтируется через volume. Содержит:
- `[[outputs.influxdb]]` — запись в InfluxDB по алиасу `influxdb:8086` (не IP!)
- `[[inputs.mqtt_consumer]]` — подписка на `sensors/#` от брокера на Linux B

> **Примечание:** В процессе развёртывания telegraf 1.25 и 1.30 возвращали ошибку
> `network Error: EOF` при подключении к mosquitto 1.6 на Debian 13. Проблема
> воспроизводилась независимо от версии telegraf и настроек mosquitto.
> Конфиг telegraf сохранён в репозитории, но для реальной работы используется
> собственный сервис `mqtt_bridge`.

---

## 6. mqtt_bridge — замена telegraf

Python-сервис `bridge.py` реализует ту же функциональность что и telegraf:
подписывается на MQTT-брокер и записывает данные в InfluxDB.

Используемые библиотеки:
- `paho-mqtt==1.6.1` — подключение к MQTT
- `influxdb==5.3.2` — запись в InfluxDB 1.8

Measurement в InfluxDB: `mqtt_consumer` (совпадает с тем что пишет telegraf),
поэтому дашборды Grafana работают одинаково в обоих случаях.

Теги каждой точки:
- `topic` — полный путь топика, например `sensors/temperature/temp_boiler`
- `sensor` — имя датчика, например `temp_boiler`

---

## 7. Конфигурация Grafana

### Datasource (datasources/default.yaml)

Подключение к InfluxDB задаётся через провизионирование — файл применяется
автоматически при старте Grafana. Адрес БД указан через алиас контейнера:

```yaml
url: http://influxdb:8086
database: sensors
```

### Дашборд (dashboards/sensors.json)

Дашборд **IoT Sensor Dashboard** провизионируется автоматически и содержит 5 панелей:
- Температура — timeseries, все датчики типа `temperature`
- Давление — timeseries, все датчики типа `pressure`
- Ток — timeseries, все датчики типа `current`
- Влажность — timeseries, все датчики типа `humidity`
- Среднее по всем датчикам — stat (агрегированное значение)

Обновление данных: каждые 5 секунд (`"refresh": "5s"`).

---

## 8. docker-compose.yml

Все сервисы находятся в одной сети `server-net` и общаются по именам контейнеров:

```yaml
services:
  influxdb:    # порт 8086 (внутри сети)
  telegraf:    # подключается к influxdb по алиасу
  mqtt_bridge: # подключается к influxdb по алиасу, к mosquitto по IP
  grafana:     # порт 3000 (пробрасывается наружу), подключается к influxdb по алиасу
```

Volumes:
- `influx_data` — именованный volume для данных InfluxDB
- `grafana_data` — именованный volume для данных Grafana (дашборды сохраняются при пересоздании)
- `./influxdb/scripts` — bind mount для скрипта инициализации
- `./telegraf` — bind mount для конфига telegraf
- `./grafana/` — bind mount для конфигов Grafana

---

## 9. Запуск сервера

```bash
cd vms/server
docker compose up -d
```

При первом запуске Docker скачивает образы (~300 МБ) и создаёт именованные volumes.

Проверка что все контейнеры запустились:
```bash
docker compose ps
# influxdb     Up
# telegraf     Up
# mqtt_bridge  Up
# grafana      Up
```

---

## 10. Проверка данных в InfluxDB

```bash
# Проверить что БД создана
docker exec -it influxdb influx -execute "SHOW DATABASES"
# sensors
# _internal

# Проверить что данные поступают
docker exec -it influxdb influx -database sensors \
  -execute "SELECT * FROM mqtt_consumer LIMIT 10"

# Посмотреть все измерения
docker exec -it influxdb influx -database sensors \
  -execute "SHOW MEASUREMENTS"
# current
# humidity
# mqtt_consumer
# pressure
# temperature
```

---

## 11. Открытие Grafana

В VirtualBox для Linux C добавляем проброс порта:
- **Host Port:** 3000 → **Guest Port:** 3000

Открыть в браузере: `http://127.0.0.1:3000`

- Логин: `admin` / Пароль: `admin`
- Перейти: **Dashboards → IoT Sensor Dashboard**

Дашборд отображает данные в реальном времени со всех 6 датчиков.

---

## Итог

На Linux C развёрнут стек из 4 контейнеров в единой Docker-сети. InfluxDB хранит временные ряды, mqtt_bridge обеспечивает приём данных с MQTT-брокера и запись в БД, Grafana визуализирует данные через провизионированный дашборд. Конфигурационные файлы каждого сервиса подключены через volume, что позволяет изменять настройки без пересборки образов.
