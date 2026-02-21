import os
import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
from bs4 import BeautifulSoup
import re

# PANDORA OS V12 - GOLD RELEASE (DEBUG MODE)
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

SOURCES = [
    {"name": "G1-DF", "url": "https://g1.globo.com/rss/df/"},
    {"name": "Metrópoles", "url": "https://www.metropoles.com/distrito-federal/seguranca/feed"},
    {"name": "Agência Brasília", "url": "https://www.agenciabrasilia.df.gov.br/feed/"}
]

def run_osint_pipeline():
    total_count = 0
    ref = db.reference('alertas_seguranca')
    
    print("🛰️ PANDORA: Iniciando Ingestão...")

    for source in SOURCES:
        try:
            # Bypass de Cache e User-Agent Realista
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Cache-Control': 'no-cache'
            }
            response = requests.get(source['url'], timeout=15, headers=headers)
            
            # Debug de Tamanho: Se for < 1000, o site bloqueou o GCP
            print(f"📡 {source['name']} - Bytes recebidos: {len(response.content)}")

            # Mudança Tática: 'html.parser' é mais tolerante a erros de fechamento de tag no RSS
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find_all('item')
            
            if not items:
                # Fallback: Algumas fontes usam 'entry' (padrão Atom)
                items = soup.find_all('entry')

            print(f"📰 {source['name']}: {len(items)} itens filtrados.")

            for i, item in enumerate(items):
                if i >= 5: break # Pega as 5 primeiras para garantir o teste
                
                # Tenta pegar título de várias formas possíveis (title ou atom:title)
                titulo = item.title.text if item.title else "Sem Título"
                
                # INJEÇÃO DIRETA (BYPASS TOTAL PARA VALIDAR O FIREBASE)
                ref.push({
                    'regiao': "Setor Central",
                    'mensagem': f"[{source['name']}] {titulo}",
                    'nivel_risco': 0.8,
                    'categoria': 'info',
                    'lat': -15.7941,
                    'lng': -47.8825,
                    'timestamp': int(time.time() * 1000)
                })
                total_count += 1
                
        except Exception as e:
            print(f"❌ ERRO {source['name']}: {str(e)}")

    return f"Fim. {total_count} registros injetados.", 200

@functions_framework.http
def process_data(request):
    return run_osint_pipeline()
