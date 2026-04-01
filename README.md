# Бархатный путь — Telegram бот регистрации

## Что умеет
- регистрация участников
- уникальный порядковый номер
- запрет дублей по Telegram ID и телефону
- меню участника
- показ своей информации
- отправка картинки меню
- личная консультация
- админ-меню
- Excel-выгрузка за сегодня / неделю / месяц
- сброс базы по паролю

## Быстрый запуск локально
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="YOUR_BOT_TOKEN"
export ADMIN_IDS="123456789"
export ADMIN_RESET_PASSWORD="StrongPassword"
export MENU_IMAGE_PATH="menu_today.jpg"
export CONSULTATION_PHONE="+79991234567"
python bot.py
```

## Деплой на сервер
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
git clone <YOUR_REPOSITORY_URL>
cd barhatnyy-put-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
