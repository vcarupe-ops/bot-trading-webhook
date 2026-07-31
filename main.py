from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TOKEN = "8984021178:AAFBj-mCo_AfAEDoK1i3EnIvNh1YiUtOncg"
CHAT_ID = "1489396160"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON payload received"}), 400

    direccion = data.get("direccion", "").upper()
    par = data.get("par", "")
    apalancamiento = data.get("apalancamiento", "")
    pe = data.get("pe", "")
    tp1 = data.get("tp1", "")
    tp2 = data.get("tp2", "")
    tp3 = data.get("tp3", "")
    sl = data.get("sl", "")

    if direccion == "LONG":
        emoji = "🟢"
    elif direccion == "SHORT":
        emoji = "🔴"
    else:
        return jsonify({"status": "error", "message": "Dirección inválida"}), 400

    mensaje = (
        f"{emoji} <b>{direccion}</b>\n"
        f"💵 <b>{par}</b>\n"
        f"❗ <b>APALANCAMIENTO:</b> {apalancamiento}\n"
        f"🚪 <b>PE:</b> {pe}\n"
        f"📍 <b>TP1:</b> {tp1}\n"
    )
    
    if tp2:
        mensaje += f"📍 <b>TP2:</b> {tp2}\n"
    if tp3:
        mensaje += f"📍 <b>TP3:</b> {tp3}\n"
        
    mensaje += f"❌ <b>SL:</b> {sl}"

    enviar_telegram(mensaje)
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
  
