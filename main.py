import firebase_admin
from firebase_admin import db
import functions_framework
import requests
import time

if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

@functions_framework.http
def process_data(request):
    data = request.get_json(silent=True)
    regiao = data.get('regiao', 'Brasília')
    
    # Tenta obter coordenadas. Se não vierem, busca no ViaCEP/Nominatim (Grátis)
    lat = data.get('lat')
    lng = data.get('lng')
    
    if lat is None or lng is None:
        lat, lng = free_geo_resolver(regiao)

    try:
        ref = db.reference('alertas_seguranca')
        ref.push({
            'regiao': regiao,
            'mensagem': data.get('mensagem', f"Alerta em {regiao}"),
            'nivel_risco': data.get('nivel_risco', 0.5),
            'lat': lat,
            'lng': lng,
            'timestamp': int(time.time() * 1000)
        })
        return "Dados processados com sucesso!", 200
    except Exception as e:
        return f"Falha na Pipeline: {e}", 500

def free_geo_resolver(localizacao):
    """
    RESOLVER DE LOCALIZAÇÃO CUSTO ZERO.
    Tenta ViaCEP (se for CEP) ou Nominatim (OpenStreetMap).
    """
    try:
        # 1. Se for CEP (8 dígitos)
        if localizacao.isdigit() and len(localizacao) == 8:
            res = requests.get(f"https://viacep.com.br/ws/{localizacao}/json/").json()
            # Nota: ViaCEP não dá Lat/Lng, precisaríamos de uma tabela de de-para.
            # Como alternativa, usamos o Nominatim (OSM)
            pass 

        # 2. Busca no OpenStreetMap (Gratuito para baixo volume)
        url = f"https://nominatim.openstreetmap.org/search?q={localizacao},Brasilia&format=json&limit=1"
        headers = {'User-Agent': 'Pandora_OS_Project'}
        response = requests.get(url, headers=headers).json()
        
        if response:
            return float(response[0]['lat']), float(response[0]['lon'])
    except:
        pass
    
    # Fallback de segurança (Marco Zero de Brasília)
    return -15.7941, -47.8825
