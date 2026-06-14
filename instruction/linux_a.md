# Linux A — Развёртывание симуляторов датчиков

**Роль машины:** Client — публикует данные датчиков на MQTT-брокер  
**IP адрес:** 192.168.3.11  
**ОС:** Debian 13 (Trixie)

---

## 1. Установка Docker

Debian 13 не поддерживается официальным репозиторием Docker напрямую, поэтому используем репозиторий для Debian 12 (Bookworm) — пакеты полностью совместимы.

```bash
# Обновить пакеты
sudo apt update && sudo apt upgrade -y

# Установить зависимости
sudo apt install -y ca-certificates curl gnupg

# Добавить GPG-ключ Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Добавить репозиторий Docker (явно указываем bookworm)
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian bookworm stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установить Docker Engine и Compose plugin
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

Проверка:
```bash
docker --version      # Docker version 29.x
docker compose version # Docker Compose version v5.x
```

---

## 2. Настройка сети

Машина клонирована, поэтому внутренняя сеть `intnet_ab` (VirtualBox) не получила IP автоматически. Назначаем вручную:

```bash
# Временно (до перезагрузки)
sudo ip addr add 192.168.3.11/24 dev enp0s8
sudo ip link set enp0s8 up
```

Чтобы IP сохранялся после перезагрузки:
```bash
sudo tee /etc/systemd/network/10-enp0s8.network << EOF
[Match]
Name=enp0s8

[Network]
Address=192.168.3.11/24
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

## 3. Авторизация в DockerHub

```bash
docker login
# Ввести username и password от hub.docker.com
```

---

## 4. Создание файлов симулятора

Все файлы находятся в `vms/client/simulator/`.

### entity/sensor.py

Базовый класс `Sensor` и 4 наследника:

- `Temperature` — температура в °C, синусоидальный профиль
- `Pressure` — давление в hPa, косинусоидальный дрейф
- `Current` — ток в А, синусоидальная нагрузка
- `Humidity` — влажность в %, косинусоидальный профиль

В каждой формуле используется дата рождения (`BIRTH_YEAR`, `BIRTH_MONTH`) как коэффициент генерации значений.

### main.py

MQTT-клиент на `paho-mqtt`. Читает конфигурацию из переменных среды:
- `SIM_HOST` — адрес брокера
- `SIM_TYPE` — тип датчика
- `SIM_NAME` — имя датчика
- `SIM_PERIOD` — период публикации в секундах
- `SIM_TOPIC_FORMAT` — формат топика: `value` (дефолт) или `json`

### Dockerfile

```dockerfile
FROM python:alpine3.19
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

---

## 5. Сборка и публикация образа на DockerHub

```bash
cd vms/client/simulator

# Сборка образа
docker build -t iiyaemikoii/data-simulator:latest .

# Проверка
docker images | grep data-simulator

# Публикация
docker push iiyaemikoii/data-simulator:latest
```

Образ доступен по адресу: `https://hub.docker.com/r/iiyaemikoii/data-simulator`

---

## 6. Запуск 6 контейнеров

`docker-compose.yml` описывает 6 контейнеров разных типов датчиков:

| Сервис | Тип | Имя датчика | Период |
|--------|-----|-------------|--------|
| temp_sensor_1 | temperature | temp_boiler | 5 сек |
| temp_sensor_2 | temperature | temp_ambient | 3 сек |
| pressure_sensor_1 | pressure | press_main_line | 7 сек |
| current_sensor_1 | current | current_motor_a | 2 сек |
| current_sensor_2 | current | current_motor_b | 2 сек |
| humidity_sensor_1 | humidity | hum_warehouse | 10 сек |

```bash
cd vms/client/simulator
docker compose up -d
docker compose ps
```

Проверка логов одного контейнера:
```bash
docker compose logs -f temp_sensor_1
# [temp_boiler] -> sensors/temperature/temp_boiler : 20.34
# [temp_boiler] -> sensors/temperature/temp_boiler : 19.76
```

---

## Итог

На Linux A развёрнуто 6 контейнеров-симуляторов, каждый публикует данные своего датчика на MQTT-брокер Linux B каждые N секунд. Образ опубликован на DockerHub и доступен для скачивания командой `docker pull iiyaemikoii/data-simulator:latest`.
