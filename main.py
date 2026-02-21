import os
import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
from bs4 import BeautifulSoup
import re

# =============================================================================
# PROJETO: PANDORA OS (V12-GOLD)
# MÓDULO: INGESTOR OSINT
# DESCRIÇÃO: Coleta dados do G1, Metrópoles e Agência BSB.
#            Garante a visibilidade tática no cockpit do HB20.
# =============================================================================

# Inicialização do Firebase com verificação de instância
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

# REGEX AMPLIADO: Termos mais comuns no jornalismo policial e de trânsito do DF
TACTICAL_KEYWORDS = {
    'danger': (r'tiroteio|assalto|furto|crime|preso|morte|homicídio|facada|polícia|pmdf|corpo|detido|roubo|investiga|presos|militar|civil|arma|disparos', 1.0),
    'traffic': (r'acidente|capotamento|atropelamento|colisão|congestionamento|trânsito|eptg|estrutural|br-020|sia|leste|oeste|eixão|parado|km', 0.6),
    'infra': (r'obras|interdição|alagamento|manutenção|falta de energia|caesb|der|detran', 0.4)
}

SOURCES = [
    {"name": "G1-DF", "url": "https://g1.globo.com/rss/df/"},
    {"name": "Metrópoles", "url": "https://www.metropoles.com/distrito-federal/seguranca/feed"},
    {"name": "Agência Brasília", "url": "https://www.agenciabrasilia.df.gov.br/feed/"}
]

def run_osint_pipeline():
    total_count = 0
    ref = db.reference('alertas_seguranca')
    
    print("🚀 PANDORA: Iniciando varredura tática nas fontes OSINT...")

    for source in SOURCES:
        try:
            # Headers para evitar bloqueio (User-Agent tático)
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) PandoraOS/12.0'}
            response = requests.get(source['url'], timeout=15, headers=headers)
            
            # Usando o parser XML do BeautifulSoup
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            
            print(f"📡 FONTE: {source['name']} | ITENS ENCONTRADOS: {len(items)}")

            for item in items:
                titulo = item.title.text
                # Log de debug para auditoria no Cloud Logging
                print(f"🔍 ANALISANDO: {titulo[:60]}...") 
                
                text_to_analyze = titulo.lower()
                matched = False

                for key, (pattern, weight) in TACTICAL_KEYWORDS.items():
                    if re.search(pattern, text_to_analyze):
                        # Extração inteligente de local: Tenta pegar o que vem após "em" ou "no/na"
                        local_match = re.search(r'(?:em|no|na)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', titulo)
                        local_raw = local_match.group(1) if local_match else "Distrito Federal"
                        
                        # Resolução de Geo (com Fallback para Brasília Centro)
                        lat, lng = resolve_geo_df(local_raw)
                        
                        payload = {
                            'regiao': local_raw,
                            'mensagem': f"[{source['name']}] {titulo}",
                            'nivel_risco': weight,
                            'categoria': key,
                            'lat': lat,
                            'lng': lng,
                            'timestamp': int(time.time() * 1000)
                        }
                        
                        ref.push(payload)
                        print(f"✅ INJETADO: {titulo[:40]} | Local: {local_raw}")
                        total_count += 1
                        matched = True
                        break # Encontrou uma categoria, pula para o próximo item
                
        except Exception as e:
            print(f"❌ ERRO NA FONTE {source['name']}: {str(e)}")

    return f"Fim da rodada. {total_count} registros injetados.", 200

def resolve_geo_df(local):
    """Fallback Geográfico Tático para o DF"""
    l = local.lower()
    if "taguatinga" in l: return -15.8322, -48.0511
    if "ceilândia" in l or "ceilandia" in l: return -15.8174, -48.1130
    if "sia" in l: return -15.7941, -47.9584
    if "guará" in l or "guara" in l: return -15.8235, -47.9772
    if "gama" in l: return -16.0125, -48.0674
    # Centro de Brasília (Rodoviária)
    return -15.7941, -47.8825

@functions_framework.http
def process_data(request):
    # Aceita GET ou POST para facilitar o Scheduler
    return run_osint_pipeline()
