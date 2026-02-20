import os
import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
from bs4 import BeautifulSoup

# =============================================================================
# PROJETO: PANDORA OS (V12) - NÚCLEO DE INGESTÃO OSINT
# DESCRIÇÃO: Resolve a falta de microdados da SSP via Scraping e Geocoding.
# CUSTO: $0.00 (OpenStreetMap + Metrópoles RSS/HTML)
# =============================================================================

# Inicialização do Firebase Realtime Database
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

@functions_framework.http
def process_data(request):
    """
    Ponto de Entrada Único:
    1. Aceita POST manual (CURL).
    2. Pode ser agendado para rodar o Scraping automaticamente.
    """
    request_json = request.get_json(silent=True)
    
    # MODO 1: SCRAPING AUTOMÁTICO (Se o payload for vazio ou comando 'scan')
    if not request_json or request_json.get('action') == 'scan':
        return run_osint_pipeline()

    # MODO 2: INGESTÃO MANUAL/DIRETA (CURL)
    return manual_ingestion(request_json)

def manual_ingestion(data):
    """Processa dados enviados manualmente via CURL/SSP."""
    regiao = data.get('regiao', 'Distrito Federal')
    lat = data.get('lat')
    lng = data.get('lng')

    # Enriquecimento de localização se faltar coordenada
    if lat is None or lng is None:
        lat, lng = resolve_geo_df(regiao)

    save_to_rtdb({
        'regiao': regiao,
        'mensagem': data.get('mensagem', f"Alerta tático em {regiao}"),
        'nivel_risco': float(data.get('nivel_risco', 0.5)),
        'lat': lat,
        'lng': lng,
        'timestamp': int(time.time() * 1000)
    })
    return "Ingestão manual concluída.", 200

def run_osint_pipeline():
    """Varre portais de notícias para extrair microdados de incidentes."""
    try:
        # Alvo: Seção de Segurança do Metrópoles (Alta frequência no DF)
        url = "https://www.metropoles.com/distrito-federal/seguranca/feed"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'xml')
        
        items = soup.find_all('item', limit=10)
        count = 0

        for item in items:
            titulo = item.title.text
            # Filtragem por palavras-chave de risco
            if any(p in titulo.lower() for p in ['tiroteio', 'assalto', 'furto', 'crime', 'preso', 'morte']):
                # Extração de endereço simplificada (padrão 'em [Local]')
                partes = titulo.split(" em ")
                local_raw = partes[-1] if len(partes) > 1 else "Brasília"
                
                lat, lng = resolve_geo_df(local_raw)
                
                save_to_rtdb({
                    'regiao': local_raw,
                    'mensagem': titulo,
                    'nivel_risco': 0.85, # Notícia de jornal tem peso alto
                    'lat': lat,
                    'lng': lng,
                    'timestamp': int(time.time() * 1000)
                })
                count += 1
        
        return f"Pipeline OSINT finalizada. {count} novos alertas gerados.", 200
    except Exception as e:
        return f"Erro na Pipeline OSINT: {str(e)}", 500

def resolve_geo_df(localizacao):
    """
    RESOLVER GEOGRÁFICO CUSTO ZERO (Nominatim/OSM).
    Converte padrões de Brasília (QNL, SQS, Setores) em Lat/Lng.
    """
    try:
        # Padronização para aumentar o acerto no DF
        query = f"{localizacao}, Distrito Federal, Brazil"
        url = "https://nominatim.openstreetmap.org/search"
        headers = {'User-Agent': 'Pandora_OS_Sovereign_v12'}
        
        # Respeitar limite da API gratuita (1 segundo)
        time.sleep(1.1)
        res = requests.get(url, params={'q': query, 'format': 'json', 'limit': 1}, headers=headers)
        data = res.json()
        
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except:
        pass
    
    # Fallback: Marco Zero de Brasília
    return -15.7941, -47.8825

def save_to_rtdb(payload):
    """Persistência no nó de produção da Pandora."""
    ref = db.reference('alertas_seguranca')
    ref.push(payload)
