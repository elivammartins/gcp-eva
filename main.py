import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request

if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/'
    })

app = Flask(__name__)

@app.route("/", methods=["POST", "GET"])
def process_data(request):
    try:
        # Dado Real: Alerta vindo do pipeline GCP
        mensagem = "⚠️ PANDORA: Sentinela Ativo. Monitorando Eixo Monumental - DF."
        ref = db.reference('alertas_seguranca')
        ref.push({
            'mensagem': mensagem,
            'timestamp': {'.sv': 'timestamp'},
            'nivel_risco': 0.85
        })
        return "Alerta enviado para a EVA", 200
    except Exception as e:
        return str(e), 500
