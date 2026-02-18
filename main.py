import os
import firebase_admin
from firebase_admin import db
import functions_framework

# Inicialização com "warm start" para performance no BRP NX1
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/'
    })

@functions_framework.http
def process_data(request):
    """
    Endpoint real para a EVA disparar alertas no Firebase.
    """
    # Suporta POST com JSON
    request_json = request.get_json(silent=True)
    
    regiao = "Eixo Monumental"
    if request_json and 'regiao' in request_json:
        regiao = request_json['regiao']

    try:
        mensagem = f"⚠️ PANDORA: Alerta de segurança detectado em {regiao}."
        
        # Escrita direta no Barramento de Tempo Real
        ref = db.reference('alertas_seguranca')
        ref.push({
            'mensagem': mensagem,
            'timestamp': {'.sv': 'timestamp'},
            'nivel_risco': 0.95,
            'origem': 'GCP_CloudRun_Sentinel'
        })
        
        return "Alerta enviado para a EVA com sucesso!", 200
    except Exception as e:
        return f"Erro na integração: {str(e)}", 500
