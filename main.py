import os
import firebase_admin
from firebase_admin import db
import functions_framework
import time

# Inicialização com a URL do Realtime Database (RTDB)
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

@functions_framework.http
def process_data(request):
    request_json = request.get_json(silent=True)
    
    # 1. Extração do Input (CURL ou SSP)
    regiao = request_json.get('regiao', 'Distrito Federal') if request_json else 'Distrito Federal'
    nivel_risco = request_json.get('nivel_risco', 0.95)
    lat = request_json.get('lat')
    lng = request_json.get('lng')

    try:
        # 2. LOGICA HÍBRIDA: Se lat/lng estiverem vazios, resolvemos via Base Local/CEP
        if lat is None or lng is None:
            lat, lng = resolve_location_fallback(regiao)

        # 3. CONTRATO DE DADOS PANDORA (Enriquecido)
        # Sincronizado com o seu nó 'alertas_seguranca' visto no console
        ref = db.reference('alertas_seguranca')
        ref.push({
            'regiao': regiao,
            'mensagem': f"⚠️ PANDORA: Alerta de segurança detectado em {regiao}.",
            'nivel_risco': float(nivel_risco),
            'lat': float(lat),
            'lng': float(lng),
            'origem': 'GCP_CloudRun_Sentinel',
            'timestamp': int(time.time() * 1000) # Epoch para cálculo de 5km
        })
        
        return "Alerta Tático processado e geolocalizado com sucesso!", 200
    except Exception as e:
        return f"Erro na Pipeline: {str(e)}", 500

def resolve_location_fallback(descricao):
    """
    Busca cirúrgica na base de CEP/IBGE (Virtualizada para Stress Test).
    """
    base_brasilia = {
        "Eixo Taguatinga": (-15.8345, -48.0560),
        "Ed. Village Pituba": (-15.8345, -48.0560),
        "Esplanada": (-15.7941, -47.8825),
        "Ceilândia Centro": (-15.8200, -48.1100)
    }
    
    # Varredura inteligente na descrição para encontrar coordenadas
    for local, coords in base_brasilia.items():
        if local.lower() in descricao.lower():
            return coords
            
    # Default: Centro de Brasília (Segurança de trajeto)
    return -15.7941, -47.8825
