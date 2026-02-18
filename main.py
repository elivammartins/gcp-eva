import os
import firebase_admin
from firebase_admin import db
import functions_framework

# Inicialização com a URL completa do Realtime Database
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        # Certifique-se de que esta URL é exatamente a que aparece no console do Firebase
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

@functions_framework.http
def process_data(request):
    request_json = request.get_json(silent=True)
    regiao = request_json.get('regiao', 'Distrito Federal') if request_json else 'Distrito Federal'

    try:
        mensagem = f"⚠️ PANDORA: Alerta de segurança detectado em {regiao}."
        
        # Referência ao nó de alertas
        ref = db.reference('alertas_seguranca')
        ref.push({
            'mensagem': mensagem,
            'timestamp': {'.sv': 'timestamp'},
            'nivel_risco': 0.95,
            'origem': 'GCP_CloudRun_Sentinel'
        })
        
        return "Alerta enviado para a EVA com sucesso!", 200
    except Exception as e:
        # Se o erro persistir, o 'e' nos dirá se é permissão ou URL
        return f"Erro na integração: {str(e)}", 500
