import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
import re
import random

VERSION_TAG = "V16-TACTICAL-REFINEMENT"

if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

# Dicionário Geográfico Expandido para o DF
BAIRROS_DF = {
    "taguatinga": (-15.8322, -48.0511),
    "ceilândia": (-15.8174, -48.1130),
    "ceilandia": (-15.8174, -48.1130),
    "guará": (-15.8235, -47.9772),
    "guara": (-15.8235, -47.9772),
    "águas claras": (-15.8381, -48.0251),
    "aguas claras": (-15.8381, -48.0251),
    "samambaia": (-15.8752, -48.0867),
    "gama": (-16.0125, -48.0674),
    "plano piloto": (-15.7941, -47.8825),
    "asa norte": (-15.7662, -47.8719),
    "asa sul": (-15.8132, -47.8977),
    "sudoeste": (-15.7981, -47.9234),
    "sobradinho": (-15.6478, -47.7915),
    "estrutural": (-15.7761, -47.9942)
}

def get_with_retry(url):
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15'}
    try:
        # Cache busting para forçar dados novos
        response = requests.get(f"{url}?v={time.time()}", headers=headers, timeout=12)
        return response.text if (response.status_code == 200 and len(response.text) > 500) else None
    except: return None

@functions_framework.http
def process_data(request):
    print(f"📡 [REFINAMENTO V16] Iniciando...")
    ref = db.reference('alertas_seguranca')
    total_count = 0
    
    # Fontes
    sources = [
        {"name": "G1-DF", "url": "https://g1.globo.com/rss/df/"},
        {"name": "Metrópoles", "url": "https://www.metropoles.com/distrito-federal/feed"},
        {"name": "Agência Brasília", "url": "https://www.agenciabrasilia.df.gov.br/feed/"}
    ]

    for source in sources:
        content = get_with_retry(source['url'])
        if not content: continue

        items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL | re.IGNORECASE)
        
        for i, item_content in enumerate(items):
            if i >= 8: break # Aumentamos para 8 notícias por fonte
            
            title_match = re.search(r'<title>(.*?)</title>', item_content, re.IGNORECASE | re.DOTALL)
            if title_match:
                titulo = title_match.group(1).replace('<![CDATA[', '').replace(']]>', '').strip()
                
                # Identificação de Localidade
                lat, lng = -15.7941, -47.8825 # Default: Rodoviária
                regiao = "DF (Geral)"
                
                for bairro, coords in BAIRROS_DF.items():
                    if bairro in titulo.lower():
                        # Adiciona Jitter (pequena variação) para o Heatmap não sobrepor e sim SOMAR
                        lat = coords[0] + random.uniform(-0.005, 0.005)
                        lng = coords[1] + random.uniform(-0.005, 0.005)
                        regiao = bairro.upper()
                        break

                # Atribuição de Risco (Agressiva para forçar o VERMELHO)
                # Se houver palavras de crime, risco = 2.0 (Força o gradiente do mapa)
                risco = 0.8
                if any(k in titulo.lower() for k in ['tiro', 'morte', 'preso', 'crime', 'polícia', 'assalto', 'roubo', 'homicídio']):
                    risco = 2.5 # Peso triplicado para "queimar" o mapa no vermelho
                
                ref.push({
                    'regiao': regiao,
                    'mensagem': f"[{source['name']}] {titulo}",
                    'nivel_risco': risco,
                    'categoria': 'seguranca',
                    'lat': lat,
                    'lng': lng,
                    'timestamp': int(time.time() * 1000)
                })
                total_count += 1

    return f"Versão: {VERSION_TAG} | Injetados: {total_count}", 200
