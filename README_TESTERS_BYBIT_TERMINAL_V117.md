# Bybit Trading Terminal v117 — инструкция для тестировщиков

## 1. Что это за программа

Bybit Trading Terminal v117 — это локальный веб‑терминал для анализа криптовалютного рынка, построенный как гибридная система:

- рыночная структура;
- orderflow / delta / DOM;
- Smart Money Concepts;
- Smart Zones;
- Pattern Engine;
- Phase Engine;
- Decision Engine v3;
- ML / Ensemble слой;
- Explainability UI;
- Performance Logging;
- PnL Tracking.

Терминал запускается локально на компьютере пользователя и открывается через браузер.

---

## 2. Что нужно для запуска

### Требования

- Python 3.10+
- Интернет
- Браузер Chrome / Safari / Edge
- macOS / Windows / Linux

### Установка зависимостей

После распаковки архива перейти в папку проекта:

```bash
cd bybit_terminal_v117_PNL_ENGINE
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

Если `pip` не найден:

```bash
pip3 install -r requirements.txt
```

---

## 3. Запуск

В папке проекта выполнить:

```bash
python main.py
```

или:

```bash
python3 main.py
```

После запуска открыть в браузере:

```text
http://localhost:5000
```

---

## 4. Основные разделы терминала

### Dashboard

Главная страница терминала. Показывает:

- список монет;
- карточки сигналов;
- confidence;
- направление LONG / SHORT / NEUTRAL;
- Decision Engine v3;
- ML / Ensemble оценку;
- Smart Zones;
- фазы рынка;
- паттерны;
- риск / качество сигнала.

---

## 5. Окно графика

Окно графика показывает:

- свечной график;
- EMA;
- RSI;
- Smart Zones;
- FVG;
- BoS;
- уровни риска;
- Entry / Stop Loss / Take Profit;
- DOM / Order Book;
- Footprint / Delta;
- Decision Engine v3;
- Explainability;
- PnL;
- Stats.

---

## 6. Режимы интерфейса графика

В окне графика доступны режимы:

### CLEAN

Минимальный режим для торговли.

Показывает только самое важное:

- цену;
- основную активную зону;
- ключевые уровни;
- базовый сигнал.

Подходит для обычной работы.

### PRO

Расширенный режим.

Показывает:

- Smart Zones;
- FVG;
- BoS;
- EMA;
- Decision Engine;
- расширенный контекст.

Подходит для анализа.

### DEBUG

Максимально подробный режим.

Показывает всё, включая технические данные.

Использовать для диагностики и проверки логики.

### FOCUS

Скрывает правую панель и оставляет максимум места для графика.

---

## 7. Decision Engine v3

Decision Engine v3 — главный модуль принятия решений.

Он рассчитывает:

- probability — вероятность успешного сценария;
- EV — ожидаемую ценность сделки;
- grade — качество сигнала;
- action — действие;
- permission — разрешение на сделку.

Возможные действия:

```text
TRADE              — сигнал разрешён
WAIT_CONFIRMATION  — нужно подтверждение
NO_TRADE           — сделки нет
BLOCKED            — вход заблокирован
```

---

## 8. Какие данные учитывает Decision Engine

Decision Engine v3 учитывает:

- scenario;
- orderflow;
- phase;
- patterns;
- smart zones;
- liquidity sweeps;
- risk / RR / EV;
- confluence;
- MTF;
- regime proxy.

---

## 9. Phase Engine

Phase Engine определяет фазу рынка:

```text
ACCUMULATION
DISTRIBUTION
MIXED_ABSORPTION
NEUTRAL
```

Фаза используется для повышения или понижения confidence.

---

## 10. Pattern Engine

Pattern Engine анализирует формации:

- compression;
- breakout;
- range;
- continuation;
- reversal;
- spring / manipulation logic.

Паттерны влияют на Decision Engine.

---

## 11. Smart Zones

Smart Zones — зоны повышенной рыночной важности.

Они могут быть:

- danger zone;
- manipulation zone;
- FVG retest zone;
- breakout zone;
- breakdown zone.

Зоны влияют на вероятность и могут блокировать сделку.

---

## 12. Orderflow / DOM / Footprint

Терминал анализирует поток ордеров:

- buy pressure;
- sell pressure;
- delta;
- weighted delta;
- absorption;
- imbalance;
- institutional score.

DOM / Order Book показывает состояние стакана.

Footprint / Delta показывает дисбаланс покупок и продаж.

---

## 13. ML / Ensemble Layer

В систему встроен ML / Ensemble слой.

Он комбинирует:

- вероятностную модель;
- эвристики Decision Engine;
- rule-based scoring.

Если ML-модель отсутствует, терминал не падает и использует fallback-логику.

---

## 14. Explainability UI

Блок Explainability показывает, почему система приняла решение.

Он выводит наиболее значимые компоненты:

- orderflow;
- phase;
- smart zones;
- risk;
- confluence;
- regime;
- liquidity.

Это помогает понять не только сигнал, но и причину его появления.

---

## 15. Performance Logging

Терминал записывает сигналы в лог:

```text
logs/performance.jsonl
```

В лог попадает:

- время сигнала;
- decision;
- фичи;
- phase;
- orderflow;
- pattern;
- результат, если он доступен.

---

## 16. PnL Engine v1

PnL Engine отслеживает сделки:

```text
сигнал → открытие → TP/SL → закрытие → результат
```

Результаты сохраняются в:

```text
logs/trades.jsonl
```

API статистики:

```text
/api/pnl
```

Показывает:

- количество сделок;
- суммарный PnL.

Важно: v1 — это внутренняя симуляция / tracking. Это не реальное биржевое исполнение.

---

## 17. Stats

В UI есть блок Stats.

Он показывает:

- количество сигналов;
- winrate;
- PnL;
- общую статистику работы системы.

---

## 18. Telegram

Если Telegram включён, терминал может отправлять сигналы в Telegram.

Для работы Telegram нужен:

- bot token;
- chat_id пользователя;
- включение Telegram в настройках.

Если Telegram не настроен, терминал продолжит работать без него.

---

## 19. Watchlist

Watchlist позволяет сохранять список монет.

Функции:

- добавление монет;
- сохранение списка;
- восстановление после перезапуска;
- работа с аккаунтом пользователя.

---

## 20. Аккаунты

В терминале есть базовая система аккаунтов:

- регистрация;
- логин;
- сохранение пользовательского watchlist;
- Telegram-настройки пользователя.

Данные сохраняются локально в папке проекта.

---

## 21. API endpoints

Основные API:

```text
/api/v7/signals
/api/v7/chart/<symbol>
/api/v7/heatmap
/api/pnl
/api/stats
/api/watchlist
/api/account/login
/api/account/register
```

---

## 22. Как тестировать

Рекомендуемый порядок тестирования:

1. Распаковать архив.
2. Установить зависимости.
3. Запустить `python main.py`.
4. Открыть `http://localhost:5000`.
5. Проверить Dashboard.
6. Открыть график монеты.
7. Переключить CLEAN / PRO / DEBUG.
8. Проверить блоки:
   - Decision Engine v3;
   - Explainability;
   - Smart Zones;
   - PnL;
   - Stats.
9. Добавить монеты в Watchlist.
10. Перезапустить терминал и проверить сохранение.

---

## 23. Возможные ошибки

### ModuleNotFoundError

Решение:

```bash
pip install -r requirements.txt
```

### Порт 5000 занят

Запустить на другом порту или закрыть старый процесс.

### Нет данных на графике

Проверить интернет и доступ к API Bybit.

### Telegram не отправляет

Проверить bot token и chat_id.

---

## 24. Важные ограничения

Текущая версия предназначена для тестирования и анализа.

Она не является финансовой рекомендацией.

PnL Engine v1 не исполняет реальные ордера на бирже.

Для реальной торговли нужен отдельный Execution Engine с подключением Bybit API.

---

## 25. Что нужно собирать от тестировщиков

Просите тестировщиков сообщать:

- какие ошибки появились;
- на какой монете;
- какой режим UI;
- что было в Error Dashboard;
- скриншот;
- лог из терминала;
- работал ли график;
- пришёл ли Telegram-сигнал;
- сохранился ли Watchlist.

---

## 26. Краткое описание для GitHub

```text
Adaptive crypto trading terminal with real-time market analysis,
Decision Engine v3, ML/Ensemble scoring, Smart Zones, Orderflow,
Explainability UI, Performance Logging and PnL Tracking.
```

---

## 27. Дисклеймер

Программа предназначена для исследовательского и тестового использования.

Торговля криптовалютами связана с высоким риском.

Автор и тестировщики самостоятельно несут ответственность за использование системы.
