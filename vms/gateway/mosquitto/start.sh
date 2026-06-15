#!/bin/bash
# Скрипт запуска Mosquitto на Linux B
# Запускать из папки vms/gateway/mosquitto/

set -e

CONF_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTAINER_NAME="mosquitto"

echo "=== Запуск Mosquitto MQTT брокера ==="

# Открыть порт в файрволе
sudo apt install -y ufw 2>/dev/null || true
sudo ufw allow 22/tcp
sudo ufw allow 1883/tcp
sudo ufw --force enable
echo "[OK] Порт 1883 открыт"

# Остановить старый контейнер если есть
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Запустить брокер
docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p 1883:1883 \
  -v "$CONF_DIR/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro" \
  eclipse-mosquitto:1.6

echo "[OK] Mosquitto запущен"
echo "     Проверка: docker logs $CONTAINER_NAME"
echo "     Тест:     docker exec $CONTAINER_NAME mosquitto_sub -h localhost -t 'sensors/#' -v"
