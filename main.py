import os
import requests
import pandas as pd
import numpy as np

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1489396160")

def send_telegram_signal(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error al enviar a Telegram: {e}")

def get_binance_klines(symbol, interval, limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'qav', 'num_trades', 'tb_base', 'tb_quote', 'ignore'
    ])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    return df

# CÁLCULO DE INDICADORES TÉCNICOS
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, lower

# DETECCIÓN DE PATRONES DE VELAS
def is_pinbar_bullish(df):
    last = df.iloc[-1]
    candle_range = last['high'] - last['low']
    lower_wick = min(last['open'], last['close']) - last['low']
    return candle_range > 0 and (lower_wick / candle_range) >= 0.6

def is_pinbar_bearish(df):
    last = df.iloc[-1]
    candle_range = last['high'] - last['low']
    upper_wick = last['high'] - max(last['open'], last['close'])
    return candle_range > 0 and (upper_wick / candle_range) >= 0.6

# LÓGICA DE ANÁLISIS INTEGRADA
def analyze_setup(symbol):
    df_15m = get_binance_klines(symbol, '15m', limit=100)
    
    # 1. Indicadores
    df_15m['rsi'] = calculate_rsi(df_15m['close'])
    df_15m['bb_upper'], df_15m['bb_lower'] = calculate_bollinger(df_15m['close'])
    
    last = df_15m.iloc[-1]
    price = last['close']
    
    # 2. Liquidez (Barridas de los últimos 20 periodos)
    recent_low = df_15m['low'].iloc[-21:-1].min()
    recent_high = df_15m['high'].iloc[-21:-1].max()
    
    sweep_low = last['low'] < recent_low  # Liquidez tomada por abajo
    sweep_high = last['high'] > recent_high # Liquidez tomada por arriba
    
    # 3. Condiciones de Entradas
    
    # LONG: RSI < 35 + Cierre fuera/toque BB inferior + Sweep Liquidez + Pinbar Alcista
    if (last['rsi'] < 35) and (last['low'] <= last['bb_lower']) and sweep_low and is_pinbar_bullish(df_15m):
        pe = price
        sl = round(last['low'] * 0.996, 2)
        risk = pe - sl
        tp1 = round(pe + (risk * 1.5), 2)
        tp2 = round(pe + (risk * 3.0), 2)
        
        return (
            f"🟢 <b>LONG</b>\n"
            f"💵 <b>PAR/USDT:</b> {symbol}\n"
            f"❗<b>APALANCAMIENTO:</b> 10x\n"
            f"🚪<b>PE:</b> {pe}\n"
            f"📍<b>TP1:</b> {tp1}\n"
            f"📍<b>TP2:</b> {tp2}\n"
            f"❌<b>SL:</b> {sl}"
        )

    # SHORT: RSI > 65 + Cierre fuera/toque BB superior + Sweep Liquidez + Pinbar Bajista
    elif (last['rsi'] > 65) and (last['high'] >= last['bb_upper']) and sweep_high and is_pinbar_bearish(df_15m):
        pe = price
        sl = round(last['high'] * 1.004, 2)
        risk = sl - pe
        tp1 = round(pe - (risk * 1.5), 2)
        tp2 = round(pe - (risk * 3.0), 2)
        
        return (
            f"🔴 <b>SHORT</b>\n"
            f"💵 <b>PAR/USDT:</b> {symbol}\n"
            f"❗<b>APALANCAMIENTO:</b> 10x\n"
            f"🚪<b>PE:</b> {pe}\n"
            f"📍<b>TP1:</b> {tp1}\n"
            f"📍<b>TP2:</b> {tp2}\n"
            f"❌<b>SL:</b> {sl}"
        )

    return None

SYMBOLS = ["SOLUSDT", "BTCUSDT", "ETHUSDT"]

if __name__ == "__main__":
    for symbol in SYMBOLS:
        signal = analyze_setup(symbol)
        if signal:
            send_telegram_signal(signal)
        else:
            print(f"[{symbol}] SIN SEÑAL")
