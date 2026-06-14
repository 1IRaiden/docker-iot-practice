# Linux B — Развёртывание MQTT-брокера Mosquitto

**Роль машины:** Gateway — принимает сообщения от симуляторов и раздаёт подписчикам  
**IP адрес:** 192.168.3.10  
**ОС:** Debian 13 (Trixie)

---

## 1. Установка Docker

Аналогично Linux A — используем репозиторий Bookworm:

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

Проверка:
```bash
docker --version
```

---

## 2. Настройка сети

Linux B — клонированная машина, IP назначаем вручную. Интерфейс `enp0s8` подключён к внутренней сети VirtualBox `intnet_ab`.

```bash
# Временно
sudo ip addr add 192.168.3.10/24 dev enp0s8
sudo ip link set enp0s8 up
```

Постоянная настройка через systemd-networkd:
```bash
sudo tee /etc/systemd/network/10-enp0s8.network << EOF
[Match]
Name=enp0s8

[Network]
Address=192.168.3.10/24
EOF

sudo systemctl enable systemd-networkd
sudo systemctl restart systemd-networkd
```

Проверка IP:
```bash
ip a | grep "inet " | grep -v 127
# inet 10.0.2.15/24 ...       <- NAT (интернет)
# inet 192.168.3.10/24 ...    <- внутренняя сеть
```

---

## 3. Открытие порта в файрволе

Порт 1883 (MQTT) должен быть открыт для входящих подключений от Linux A и Linux C:

```bash
sudo apt install -y ufw

# Обязательно открыть SSH, чтобы не потерять доступ
sudo ufw allow 22/tcp

# Открыть порт MQTT
sudo ufw allow 1883/tcp

# Включить файрвол
sudo ufw enable

# Проверка
sudo ufw status
# 22/tcp   ALLOW
# 1883/tcp ALLOW
```

---

## 4. Конфигурационный файл Mosquitto

Файл `vms/gateway/mosquitto/mosquitto.conf` монтируется в контейнер через volume:

```
listener 1883
allow_anonymous true
allow_zero_length_clientid true
protocol mqtt

log_dest stdout
log_type all
```

Ключевые параметры:
- `listener 1883` — слушать на порту 1883
- `allow_anonymous true` — разрешить подключение без аутентификации
- `allow_zero_length_clientid true` — разрешить пустые client ID (нужно для совместимости)
- `log_dest stdout` — логи в stdout (видны через `docker logs`)

---

## 5. Запуск Mosquitto

Используем скрипт `start.sh` или запускаем вручную:

```bash
cd vms/gateway/mosquitto

docker run -d \
  --name mosquitto \
  --restart unless-stopped \
  -p 1883:1883 \
  -v $(pwd)/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro \
  eclipse-mosquitto:1.6
```

Параметры запуска:
- `-d` — фоновый режим
- `--restart unless-stopped` — автозапуск при перезагрузке
- `-p 1883:1883` — проброс порта (хост:контейнер)
- `-v` — volume для конфигурационного файла (только чтение `:ro`)
- `eclipse-mosquitto:1.6` — используем версию 1.6, так как 2.0 имела проблемы совместимости с telegraf

---

## 6. Проверка работы

Проверка логов брокера:
```bash
docker logs mosquitto
# 1779846143: Config loaded from /mosquitto/config/mosquitto.conf.
# 1779846143: Opening ipv4 listen socket on port 1883.
# 1779846143: mosquitto version 1.6.x running
```

Тест подписки (после запуска симуляторов на Linux A):
```bash
docker exec mosquitto mosquitto_sub -h localhost -t "sensors/#" -v
# sensors/temperature/temp_boiler 20.34
# sensors/pressure/press_main_line 1012.80
# sensors/current/current_motor_a 9.06
```

В логах брокера при получении сообщений:
```
Received PUBLISH from temp_boiler (d0, q1, r0, m60, 'sensors/temperature/temp_boiler', ... (5 bytes))
Sending PUBLISH to auto-XXX (d0, q0, r0, m0, 'sensors/temperature/temp_boiler', ... (5 bytes))
```

---

## Итог

На Linux B развёрнут Mosquitto MQTT-брокер версии 1.6 в Docker-контейнере. Конфигурационный файл подключён через volume. Порт 1883 открыт в файрволе. Брокер принимает сообщения от 6 симуляторов на Linux A и раздаёт их подписчикам (Linux C).
