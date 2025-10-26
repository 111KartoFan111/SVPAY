#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}RFID Balance System - Запуск${NC}"
echo -e "${GREEN}================================${NC}\n"

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 не найден!${NC}"
    echo "Установите Python3 и попробуйте снова."
    exit 1
fi

echo -e "${YELLOW}Проверка зависимостей...${NC}"

# Проверка и установка зависимостей
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --quiet
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Зависимости установлены${NC}\n"
    else
        echo -e "${RED}✗ Ошибка установки зависимостей${NC}"
        exit 1
    fi
else
    echo -e "${RED}Файл requirements.txt не найден!${NC}"
    exit 1
fi

# Получение локального IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="localhost"
fi

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Сервер запускается в фоновом режиме...${NC}"
echo -e "${GREEN}================================${NC}\n"

# Проверяем, не запущен ли уже gunicorn
if pgrep -f gunicorn > /dev/null; then
    echo -e "${YELLOW}Gunicorn уже запущен. Перезапуск...${NC}"
    pkill gunicorn
    sleep 2
fi

# Запуск сервера Gunicorn в фоновом режиме (nohup)
nohup gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app -b 0.0.0.0:7000 > gunicorn.log 2>&1 &

if [ $? -eq 0 ]; then
    echo -e "Веб-интерфейс доступен по адресу:"
    echo -e "${YELLOW}http://${LOCAL_IP}:7000${NC}\n"
    echo -e "Сервер запущен в фоне. Логи пишутся в ${GREEN}gunicorn.log${NC}"
    echo -e "Для остановки используйте ${RED}./stop.sh${NC}\n"
else
    echo -e "${RED}✗ Ошибка запуска Gunicorn.${NC}"
    echo "Проверьте ${RED}gunicorn.log${NC} для деталей."
fi

echo -e "${GREEN}================================${NC}\n"
