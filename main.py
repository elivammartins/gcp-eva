import os
import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
from bs4 import BeautifulSoup
import re

# =============================================================================
# PROJETO: PANDORA OS (V12-GOLD) - INGESTÃO OSINT COM GEO-AUDIT
# DESCRIÇÃO: Varre G1, Metrópoles e Agência BSB. 
#            Garante integridade de Lat/Lng para o mapa de calor do HB20.
# =============================================================================

if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

# Cérebro de Classificação: Palavras-chave -> Nível de Risco
TACTICAL_KEYWORDS = {
    'danger': (r'tiroteio|assalto|furto|crime|preso|morte|homicídio|facada|polícia|pmdf|corpo', 1.0),
    'traffic': (r'acidente|capotamento|atropelamento|engavetamento|colisão|congestionamento|capotou', 0.6),
    'infra': (r'buraco|obras|interdição|alagamento|pista fechada|manutenção|asfalto', 0.4)
}

SOURCES = [
    {"name": "G1-DF", "url": "https://g1.globo.com/rss/df/", "type": "xml"},
    {"name": "Metrópoles", "url": "https://www.metropoles.com/distrito-federal/seguranca/feed", "type": "xml"},
    {"name": "Agência Brasília", "url": "https://www.agenciabrasilia.df.gov.br/feed/", "type": "xml"}
]

@functions_framework.http
def process_data(request):
    request_json = request.get_json(silent=True)
    
    # MODO AUTOMÁTICO (Scheduler)
    if not request_json or request_json.get('action') == 'scan':
        return run_osint_pipeline()

    # MODO MANUAL (CURL)
    return manual_ingestion(request_json)

def run_osint_pipeline():
    total_count = 0
    seen_titles = set()

    try:
        for source in SOURCES:
            response = requests.get(source['url'], timeout=15)
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item', limit=10) 

            for item in items:
                titulo = item.title.text
                if titulo in seen_titles: continue
                
                risk_level = 0.3 
                category = "info"
                
                text_to_analyze = titulo.lower()
                for key, (pattern, weight) in TACTICAL_KEYWORDS.items():
                    if re.search(pattern, text_to_analyze):
                        risk_level = weight
                        category = key
                        break
                
                # Filtragem de relevância (Apenas alertas de risco médio/alto)
                if risk_level >= 0.4:
                    # Extração de Local: Busca padrão "em [Local]" ou "[Local]: "
                    partes = re.split(r' em |: ', titulo)
                    local_raw = partes[-1].strip() if len(partes) > 1 else "Distrito Federal"
                    
                    # GEO-AUDIT: Obtendo Lat/Lng sem inversão
                    lat, lng = resolve_geo_df(local_raw)
                    
                    save_to_rtdb({
                        'regiao': local_raw,
                        'mensagem': f"[{source['name']}] {titulo}",
                        'nivel_risco': risk_level,
                        'categoria': category,
                        'lat': lat,  # Garantido -15.x
                        'lng': lng,  # Garantido -47.x
                        'timestamp': int(time.time() * 1000)
                    })
                    seen_titles.add(titulo)
                    total_count += 1
        
        return f"Pipeline Gold: {total_count} alertas sincronizados.", 200
    except Exception as e:
        return f"Erro na Pipeline OSINT: {str(e)}", 500

def resolve_geo_df(localizacao):
    """
    Geolocalização Nominatim validada para o quadrilátero do DF.
    Garante que Longitude e Latitude não sejam invertidas.
    """
    try:
        # Refina a busca para o DF para evitar duplicatas globais
        query = f"{localizacao}, Distrito Federal, Brazil"
        url = "https://nominatim.openstreetmap.org/search"
        headers = {'User-Agent': 'Pandora_OS_V12_Gold_Ingestor'}
        
        time.sleep(1.1) # Throttling obrigatório da API gratuita
        res = requests.get(url, params={'q': query, 'format': 'json', 'limit': 1}, headers=headers)
        data = res.json()
        
        if data:
            lat = float(data[0]['lat'])
            lng = float(data[0]['lon'])
            
            # Sanity Check: No DF, Lat é aprox -15 e Lng é aprox -47
            if -16.5 < lat < -15.0 and -48.5 < lng < -47.0:
                return lat, lng
            else:
                # Se cair fora do DF, retorna o centro de Brasília
                return -15.7941, -47.8825
    except:
        pass
    return -15.7941, -47.8825 # Fallback: Rodoviária do Plano Piloto

def manual_ingestion(data):
    """Processa o seu CURL garantindo a ordem Lat/Lng."""
    regiao = data.get('regiao', 'Taguatinga')
    lat = float(data.get('lat', -15.8322))
    lng = float(data.get('lng', -48.0511))

    save_to_rtdb({
        'regiao': regiao,
        'mensagem': data.get('mensagem', 'Alerta Manual'),
        'nivel_risco': float(data.get('nivel_risco', 1.0)),
        'lat': lat,
        'lng': lng,
        'timestamp': int(time.time() * 1000)
    })
    return "Manual OK", 200

def save_to_rtdb(payload):
    ref = db.reference('alertas_seguranca')
    ref.push(payload)
