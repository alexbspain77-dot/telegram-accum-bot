#!/usr/bin/env python3
import os
import json
import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests
import ccxt
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_CHAT_IDS = [cid.strip() for cid in os.getenv("ALLOWED_CHAT_IDS", "").split(",") if cid.strip()]

EXCHANGE_ID = os.getenv("EXCHANGE", "binance").strip()
QUOTE_ASSET = os.getenv("QUOTE_ASSET", "USDT").strip().upper()
TIMEFRAME = os.getenv("TIMEFRAME", "1h").strip()
CANDLE_LOOKBACK = int(os.getenv("CANDLE_LOOKBACK", "400"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "5"))

BB_WIDTH_PCTILE = int(os.getenv("BB_WIDTH_PCTILE", "20"))
ATRP_PCTILE = int(os.getenv("ATRP_PCTILE", "30"))
RANGE_LOOKBACK = int(os.getenv("RANGE_LOOKBACK", "120"))
EMA_PERIOD = int(os.getenv("EMA_PERIOD", "50"))
OBV_SLOPE_LOOKBACK = int(os.getenv("OBV_SLOPE_LOOKBACK", "30"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "3.0"))

# New feature params
ADX_PERIOD = int(os.getenv("ADX_PERIOD", "14"))
ADX_PCTILE = int(os.getenv("ADX_PCTILE", "30"))
KC_MULTIPLIER = float(os.getenv("KC_MULTIPLIER", "1.5"))
SR_PCTILE = int(os.getenv("SR_PCTILE", "20"))
CLIMAX_VOL_PCTILE = int(os.getenv("CLIMAX_VOL_PCTILE", "95"))
CLIMAX_SPREAD_PCTILE = int(os.getenv("CLIMAX_SPREAD_PCTILE", "80"))
CLIMAX_LOOKBACK = int(os.getenv("CLIMAX_LOOKBACK", "25"))
CLIMAX_WEIGHT = float(os.getenv("CLIMAX_WEIGHT", "0.5"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "subscribers.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

STABLECOINS = {"USDT","USDC","BUSD","TUSD","FDUSD","DAI","USDE","PYUSD"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("accum_bot")
os.makedirs(DATA_DIR, exist_ok=True)

def now_utc(): return datetime.now(timezone.utc)

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def ema(arr: np.ndarray, period: int) -> np.ndarray:
    if period <= 1: return arr.astype(float)
    alpha = 2 / (period + 1)
    out = np.empty(len(arr), dtype=float); out[:] = np.nan
    if len(arr)==0: return out
    out[0] = float(arr[0])
    for i in range(1, len(arr)): out[i] = alpha * arr[i] + (1 - alpha) * out[i-1]
    return out

def rolling_std(arr: np.ndarray, period: int) -> np.ndarray:
    out = np.full(len(arr), np.nan, dtype=float)
    if period <= 1: return out
    for i in range(period-1, len(arr)): out[i] = np.std(arr[i-period+1:i+1], ddof=1)
    return out

def true_range(high, low, close):
    tr = np.empty(len(close), dtype=float)
    tr[0] = high[0] - low[0]
    for i in range(1, len(close)):
        tr[i] = max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))
    return tr

def atr(high, low, close, period=14):
    return ema(true_range(high, low, close), period)

def obv(close, volume):
    out = np.zeros(len(close), dtype=float)
    for i in range(1, len(close)):
        if close[i] > close[i-1]: out[i] = out[i-1] + volume[i]
        elif close[i] < close[i-1]: out[i] = out[i-1] - volume[i]
        else: out[i] = out[i-1]
    return out

def linreg_slope(y: np.ndarray) -> float:
    n = len(y)
    if n < 2 or np.all(np.isnan(y)): return 0.0
    x = np.arange(n, dtype=float); xm = x.mean(); ym = np.nanmean(y)
    num = np.nansum((x-xm)*(y-ym)); den = np.nansum((x-xm)**2)
    return 0.0 if den==0 else float(num/den)

# --- New indicator helpers ---
def wilder_ema(arr: np.ndarray, period: int) -> np.ndarray:
    out = np.full(len(arr), np.nan, dtype=float)
    if len(arr)==0 or period<=0: return out
    alpha = 1.0/period; out[0]=arr[0]
    for i in range(1,len(arr)): out[i] = out[i-1] + alpha*(arr[i]-out[i-1])
    return out

def adx(high, low, close, period=14):
    n = len(close)
    plusDM = np.zeros(n); minusDM=np.zeros(n)
    for i in range(1,n):
        up = high[i]-high[i-1]; dn = low[i-1]-low[i]
        plusDM[i] = max(up,0.0) if up>dn else 0.0
        minusDM[i]= max(dn,0.0) if dn>up else 0.0
    tr = true_range(high, low, close)
    atr_w = wilder_ema(tr, period)
    plusDI = np.where(atr_w==0,0.0, 100.0*wilder_ema(plusDM,period)/atr_w)
    minusDI= np.where(atr_w==0,0.0, 100.0*wilder_ema(minusDM,period)/atr_w)
    dx = np.where((plusDI+minusDI)==0,0.0, 100.0*np.abs(plusDI-minusDI)/(plusDI+minusDI))
    adx_vals = wilder_ema(dx, period)
    return adx_vals, plusDI, minusDI

def keltner_width(high, low, close, period=20, mult=1.5):
    mid = ema(close, period)
    atr_vals = atr(high, low, close, period)
    upper = mid + mult*atr_vals; lower = mid - mult*atr_vals
    return upper - lower

def squeeze_ratio(bb_width_abs, kc_width):
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(kc_width==0, np.nan, bb_width_abs/kc_width)

def detect_volume_climax(df: pd.DataFrame, vol_pctile=95, spread_pctile=80, lookback=25):
    close = df["close"].to_numpy(float)
    open_ = df["open"].to_numpy(float)
    high  = df["high"].to_numpy(float)
    low   = df["low"].to_numpy(float)
    vol   = df["volume"].to_numpy(float)
    spread= high - low
    hist_len = min(len(vol), 240)
    vol_hist = vol[-hist_len:]; sp_hist = spread[-hist_len:]
    def thr(arr,p):
        arr = arr[~np.isnan(arr)]
        return np.nan if len(arr)<20 else float(np.percentile(arr,p))
    vthr = thr(vol_hist, vol_pctile); sthr = thr(sp_hist, spread_pctile)
    has_buy=has_sell=False
    rng = min(lookback, len(vol))
    for i in range(len(vol)-rng, len(vol)):
        if not np.isnan(vthr) and not np.isnan(sthr) and vol[i]>=vthr and spread[i]>=sthr:
            if close[i]>open_[i]: has_buy=True
            elif close[i]<open_[i]: has_sell=True
    return {"buying": has_buy, "selling": has_sell}

# --- Market data ---
def get_top_100_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = dict(vs_currency="usd", order="market_cap_desc", per_page=100, page=1, sparkline=False)
    r = requests.get(url, params=params, timeout=30); r.raise_for_status()
    coins = r.json(); syms=[]
    for c in coins:
        sym = c.get("symbol","").upper(); name = c.get("name","")
        if sym in STABLECOINS: continue
        if "USD" in name.upper() and "COIN" in name.upper(): continue
        if sym: syms.append(sym)
    seen=set(); uniq=[]
    for s in syms:
        if s not in seen: seen.add(s); uniq.append(s)
    return uniq

def init_exchange(exchange_id: str):
    ex_class = getattr(ccxt, exchange_id)
    ex = ex_class({"enableRateLimit": True})
    ex.load_markets()
    return ex

def map_symbols_to_pairs(ex, base_symbols: List[str], quote: str) -> List[str]:
    pairs=[]
    for sym in base_symbols:
        pair=f"{sym}/{quote}"
        if pair in ex.markets and ex.markets[pair].get("active", True): pairs.append(pair)
    return pairs

def fetch_ohlcv(ex, symbol: str, timeframe: str, limit: int):
    try:
        ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not ohlcv: return None
        df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        return df
    except Exception as e:
        log.warning(f"fetch_ohlcv failed for {symbol}: {e}")
        return None

# --- Detection logic ---
@dataclass
class SetupResult:
    symbol: str
    side: Optional[str]
    score: float
    reasons: List[str]
    last_close: float
    timeframe: str

def detect_setups(df: pd.DataFrame, symbol: str) -> Optional[SetupResult]:
    if df is None or len(df) < max(EMA_PERIOD, RANGE_LOOKBACK, 120): return None

    close = df["close"].to_numpy(float)
    open_ = df["open"].to_numpy(float)
    high  = df["high"].to_numpy(float)
    low   = df["low"].to_numpy(float)
    vol   = df["volume"].to_numpy(float)

    mid = ema(close, 20); std = rolling_std(close, 20)
    upper = mid + 2*std; lower = mid - 2*std
    bb_width_abs = (upper - lower)
    bb_width = bb_width_abs / np.where(mid==0, 1, mid)

    atr_vals = atr(high, low, close, 14)
    atrp = atr_vals / np.where(close==0, 1, close)

    ema50 = ema(close, EMA_PERIOD)

    obv_vals = obv(close, vol)
    look = min(OBV_SLOPE_LOOKBACK, len(obv_vals))
    obv_slope = linreg_slope(obv_vals[-look:])

    rng_look = min(RANGE_LOOKBACK, len(close))
    recent = close[-rng_look:]
    r_hi, r_lo = float(np.nanmax(recent)), float(np.nanmin(recent))
    pos = 0.5 if r_hi==r_lo else (close[-1]-r_lo)/(r_hi-r_lo)

    def pct_rank(series: np.ndarray, current: float) -> float:
        arr = series[~np.isnan(series)]
        if len(arr)<10: return 100.0
        return float(np.sum(arr<=current))/len(arr)*100.0

    bb_pct = pct_rank(bb_width[-180:], bb_width[-1])
    atrp_pct = pct_rank(atrp[-180:], atrp[-1])

    adx_vals, plusDI, minusDI = adx(high, low, close, ADX_PERIOD)
    kc_w = keltner_width(high, low, close, 20, KC_MULTIPLIER)
    sr_ratio = squeeze_ratio(bb_width_abs, kc_w)
    adx_pct = pct_rank(adx_vals[-180:], adx_vals[-1])
    sr_pct  = pct_rank(sr_ratio[-180:], sr_ratio[-1])

    reasons=[]; score=0.0; squeeze=False

    if bb_pct <= BB_WIDTH_PCTILE:
        squeeze=True; score+=1.0; reasons.append(f"BB width pctile {bb_pct:.1f}% ≤ {BB_WIDTH_PCTILE}%")
    if atrp_pct <= ATRP_PCTILE:
        score+=1.0; reasons.append(f"ATR% pctile {atrp_pct:.1f}% ≤ {ATRP_PCTILE}%")
    if sr_pct <= SR_PCTILE:
        squeeze=True; score+=1.0; reasons.append(f"Squeeze ratio (BB/KC) pctile {sr_pct:.1f}% ≤ {SR_PCTILE}%")
    if adx_pct <= ADX_PCTILE:
        score+=0.5; reasons.append(f"ADX pctile {adx_pct:.1f}% ≤ {ADX_PCTILE}% (low ADX)")

    side=None
    if squeeze:
        if pos>=0.6: side="long"; score+=0.5; reasons.append(f"Near top of {RANGE_LOOKBACK}-bar range (pos {pos:.2f})")
        elif pos<=0.4: side="short"; score+=0.5; reasons.append(f"Near bottom of {RANGE_LOOKBACK}-bar range (pos {pos:.2f})")

    if side=="long":
        if close[-1]>ema50[-1]: score+=1.0; reasons.append(f"Close above EMA{EMA_PERIOD}")
        if obv_slope>0: score+=0.5; reasons.append("OBV slope positive")
    elif side=="short":
        if close[-1]<ema50[-1]: score+=1.0; reasons.append(f"Close below EMA{EMA_PERIOD}")
        if obv_slope<0: score+=0.5; reasons.append("OBV slope negative")

    climax = detect_volume_climax(df, CLIMAX_VOL_PCTILE, CLIMAX_SPREAD_PCTILE, CLIMAX_LOOKBACK)
    if side=="long":
        if climax.get("selling"): score+=CLIMAX_WEIGHT; reasons.append(f"Selling climax last {CLIMAX_LOOKBACK} bars")
        if climax.get("buying"):  score-=CLIMAX_WEIGHT; reasons.append(f"Buying climax last {CLIMAX_LOOKBACK} bars")
    elif side=="short":
        if climax.get("buying"):  score+=CLIMAX_WEIGHT; reasons.append(f"Buying climax last {CLIMAX_LOOKBACK} bars")
        if climax.get("selling"): score-=CLIMAX_WEIGHT; reasons.append(f"Selling climax last {CLIMAX_LOOKBACK} bars")

    if side and score >= MIN_SCORE:
        return SetupResult(symbol=symbol, side=side, score=score, reasons=reasons, last_close=float(close[-1]), timeframe=TIMEFRAME)
    return None

# --- Bot core ---
def get_subscribers():
    data = load_json(SUBSCRIBERS_FILE, [])
    out=[]
    for cid in data:
        try: out.append(int(cid))
        except: pass
    return sorted(set(out))

def add_subscriber(chat_id:int):
    subs=get_subscribers()
    if chat_id not in subs:
        subs.append(chat_id); save_json(SUBSCRIBERS_FILE, subs)

def remove_subscriber(chat_id:int):
    subs=get_subscribers()
    if chat_id in subs:
        subs.remove(chat_id); save_json(SUBSCRIBERS_FILE, subs)

def allowed_chat(chat_id:int)->bool:
    return True if not ALLOWED_CHAT_IDS else (str(chat_id) in ALLOWED_CHAT_IDS)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not allowed_chat(chat_id):
        await update.message.reply_text("Доступ ограничен.")
        return
    add_subscriber(chat_id)
    await update.message.reply_text("Привет! Я шлём сетапы накопления 1h. Команды: /scan, /status, /stop")

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    remove_subscriber(update.effective_chat.id)
    await update.message.reply_text("Ок, отключил оповещения в этот чат.")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = load_json(STATE_FILE, {})
    last_run = st.get("last_run_utc", "—")
    summary = st.get("last_summary", "—")
    txt = (
        f"*Статус*\n"
        f"- Биржа: `{EXCHANGE_ID}`  Пары: `*/{QUOTE_ASSET}`  TF: `{TIMEFRAME}`\n"
        f"- MIN_SCORE={MIN_SCORE}\n"
        f"- Последний запуск (UTC): {last_run}\n"
        f"- Итог: {summary}\n"
        f"Команды: /scan, /stop"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Запускаю сканирование…")
    results = await run_scan_and_alert(context.application, broadcast=False, reply_chat_id=update.effective_chat.id)
    await update.message.reply_text("Готово. " + ("Сетапов не найдено." if not results else f"Найдено: {len(results)}."))

def format_alert(res: 'SetupResult', market_symbol: str) -> str:
    side_str = "LONG" if res.side=="long" else "SHORT"
    tv_ticker = "BINANCE:" + market_symbol.replace("/", "")
    reasons = "\n".join([f"• {r}" for r in res.reasons])
    return (
        f"*Accumulation under {side_str}* — `{market_symbol}` on `{res.timeframe}`\n"
        f"Last close: `{res.last_close:.6g}`\n"
        f"Score: *{res.score:.1f}* (>= {MIN_SCORE})\n"
        f"{reasons}\n"
        f"`{tv_ticker}` on TradingView"
    )

async def run_scan_and_alert(app, broadcast=True, reply_chat_id: Optional[int]=None):
    st = {"last_run_utc": now_utc().strftime("%Y-%m-%d %H:%M:%S"), "found": 0, "last_summary": ""}
    try:
        ex = init_exchange(EXCHANGE_ID)
    except Exception as e:
        log.exception("Exchange init failed")
        if reply_chat_id:
            await app.bot.send_message(chat_id=reply_chat_id, text=f"Ошибка инициализации биржи: {e}")
        return []
    try:
        top_syms = get_top_100_coins()
    except Exception as e:
        log.exception("Fetching top-100 failed")
        if reply_chat_id:
            await app.bot.send_message(chat_id=reply_chat_id, text=f"Ошибка получения топ-100: {e}")
        return []

    pairs = map_symbols_to_pairs(ex, top_syms, QUOTE_ASSET)
    if not pairs:
        if reply_chat_id:
            await app.bot.send_message(chat_id=reply_chat_id, text=f"Нет пар с /{QUOTE_ASSET} на {EXCHANGE_ID}.")
        return []

    found = []
    for pair in pairs:
        df = fetch_ohlcv(ex, pair, TIMEFRAME, CANDLE_LOOKBACK)
        if df is None: continue
        res = detect_setups(df, pair)
        if res: found.append((pair, res))
        time.sleep(ex.rateLimit/1000.0 if hasattr(ex,"rateLimit") else 0.2)

    st["found"] = len(found)
    st["last_summary"] = ", ".join([f"{p}({r.side[0]} {r.score:.1f})" for p, r in found]) if found else "—"
    save_json(STATE_FILE, st)

    if found:
        subscribers = [reply_chat_id] if reply_chat_id else get_subscribers()
        for pair, res in found:
            msg = format_alert(res, pair)
            for chat_id in subscribers:
                if not allowed_chat(chat_id): continue
                try: await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.MARKDOWN)
                except Exception as e: log.warning(f"Send failed to {chat_id}: {e}")
    return found

def seconds_until_next_minute(minute: int) -> int:
    now = datetime.now()
    target = now.replace(second=0, microsecond=0, minute=minute)
    if target <= now: target += timedelta(hours=1)
    return int((target - now).total_seconds())

async def scheduled_job(context: ContextTypes.DEFAULT_TYPE):
    await run_scan_and_alert(context.application, broadcast=True)

def main():
    if not TELEGRAM_BOT_TOKEN: raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("scan", cmd_scan))
    delay = seconds_until_next_minute(SCHEDULE_MINUTE)
    app.job_queue.run_repeating(scheduled_job, interval=3600, first=delay, name="hourly_scan")
    log.info("Bot started. Waiting for messages...")
    app.run_polling(close_loop=False, drop_pending_updates=True)

if __name__ == "__main__":
    main()
