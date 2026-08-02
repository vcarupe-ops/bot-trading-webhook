import os
import requests
import pandas as pd
import numpy as np

# Configuración desde GitHub Secrets
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = ["SOLUSDT", "BTCUSDT", "ETHUSDT"]

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Variables de entorno de Telegram no configuradas.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Notificación enviada a Telegram.")
    except Exception as e:
        print(f"❌ Error al enviar mensaje a Telegram: {e}")

def get_klines(symbol, interval, limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # Validar si Binance retornó un error en vez de una lista de velas
        if not isinstance(data, list):
            print(f"⚠️ Respuesta inesperada de Binance para {symbol}: {data}")
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convertir tipos de datos
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['open'] = df['open'].astype(float)
        return df
    except Exception as e:
        print(f"❌ Error obteniendo klines para {symbol}: {e}")
        return pd.DataFrame()

def calculate_indicators(df):
    if df.empty or len(df) < 20:
        return df

    # RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Bandas de Bollinger (20, 2)
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['std'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['sma20'] + (df['std'] * 2)
    df['bb_lower'] = df['sma20'] - (df['std'] * 2)

    return df

def analyze_setup(symbol):
    df_15m = get_klines(symbol, "15m")
    df_1h = get_klines(symbol, "1h")

    # Validación de seguridad para evitar IndexError
    if df_15m.empty or df_1h.empty or len(df_15m) < 20 or len(df_1h) < 20:
        print(f"⚠️ Datos insuficientes para {symbol}. Omitiendo evaluación...")
        return None

    df_15m = calculate_indicators(df_15m)
    df_1h = calculate_indicators(df_1h)

    last_15m = df_15m.iloc[-1]
    last_1h = df_1h.iloc[-1]

    close = last_15m['close']
    low = last_15m['low']
    high = last_15m['high']
    rsi = last_15m['rsi']
    bb_lower = last_15m['bb_lower']
    bb_upper = last_15m['bb_upper']

    # Lógica de confluencia LONG
    if rsi < 30 and low <= bb_lower:
        sl = round(low * 0.995, 2)
        tp1 = round(close * 1.015, 2)
        tp2 = round(close * 1.03, 2)
        
        msg = (
            f"🟢 **LONG**\n"
            f"💵 **PAR/USDT:** {symbol}\n"
            f"❗ **APALANCAMIENTO:** 10x - 20x\n"
            f"🚪 **PE:** {close}\n"
            f"📍 **TP1:** {tp1}\n"
            f"📍 **TP2:** {tp2}\n"
            f"❌ **SL:** {sl}"
        )
        return msg

    # Lógica de confluencia SHORT
    elif rsi > 70 and high >= bb_upper:
        sl = round(high * 1.005, 2)
        tp1 = round(close * 0.985, 2)
        tp2 = round(close * 0.97, 2)

        msg = (
            f"🔴 **SHORT**\n"
            f"💵 **PAR/USDT:** {symbol}\n"
            f"❗ **APALANCAMIENTO:** 10x - 20x\n"
            f"🚪 **PE:** {close}\n"
            f"📍 **TP1:** {tp1}\n"
            f"📍 **TP2:** {tp2}\n"
            f"❌ **SL:** {sl}"
        )
        return msg

    return None

def main():
    print("🤖 Iniciando escaneo de mercado...")
    signals_found = 0
    
    for symbol in SYMBOLS:
        print(f"Analizando {symbol}...")
        signal = analyze_setup(symbol)
        if signal:
            print(f"🎯 ¡Señal encontrada para {symbol}!")
            send_telegram_message(signal)
            signals_found += 1

    if signals_found == 0:
        print("SIN SEÑAL")

if __name__ == "__main__":
    main()
    
