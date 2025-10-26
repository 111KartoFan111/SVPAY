#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${RED}Остановка сервера Gunicorn...${NC}"

# Ищем и останавливаем процесс Gunicorn
if pgrep -f gunicorn > /dev/null; then
    pkill gunicorn
    sleep 1
    if pgrep -f gunicorn > /dev/null; then
        echo -e "${RED}Не удалось остановить. Принудительная остановка...${NC}"
        pkill -9 gunicorn
    fi
    echo -e "${GREEN}Сервер остановлен.${NC}"
else
    echo -e "${GREEN}Сервер Gunicorn не был запущен.${NC}"
fi

exit 0
