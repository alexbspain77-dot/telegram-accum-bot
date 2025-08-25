# Telegram Accumulation Scanner (1h)

Сканер топ-100 монет (CoinGecko) на бирже (по умолчанию Binance spot) с Telegram-ботом.
Ищет «накопление под лонг/шорт» на 1h: сквиз BB/ATR/BB/Keltner, позиция в диапазоне, EMA, OBV, ADX, локальные климаксы объёма.

## Быстрый старт локально (macOS/Linux)
```
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
cp .env.example .env
# заполни TELEGRAM_BOT_TOKEN=...
python3 main.py
```

Команды в Telegram: `/start`, `/status`, `/scan`, `/stop`.

## Новые фичи
- ADX (Wilder) с перцентилем (низкий ADX → консолидация)
- Squeeze Ratio (BB/Keltner)
- Локальные климаксы объёма (всплеск объёма + широкий спред)

## Deploy на Railway (Free Tier)
1. Залей папку в GitHub (как корень).
2. В корне уже есть `Procfile` и `runtime.txt` → Railway запустит `python main.py` (Python 3.11).
3. Railway → New Project → Deploy from GitHub.
4. В Variables: см. `.env.example` (обязательно TELEGRAM_BOT_TOKEN).
5. Сбрось webhook:
```
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/deleteWebhook?drop_pending_updates=true"
```
6. Logs → `Bot started. Waiting for messages...`, в Telegram: `/start`, `/status`, `/scan`.
