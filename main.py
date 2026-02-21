import os
import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
from bs4 import BeautifulSoup
import re

# PANDORA OS V12 - GOLD RELEASE
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
    
    # 🕵️ MÁSCARA DE BROWSER (Header Realista)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive'
    }

    print("🛰️ PANDORA: Iniciando Ingestão camuflada...")

    for source in SOURCES:
        try:
            # Faz a requisição simulando um navegador
            response = requests.get(source['url'], timeout=15, headers=headers)
            
            # Auditoria de Resposta
            print(f"📡 {source['name']} | Status: {response.status_code} | Bytes: {len(response.content)}")

            if response.status_code != 200:
                print(f"⚠️ {source['name']} bloqueou o acesso (Status {response.status_code}).")
                continue

            # Parser tolerante a erros de XML em fluxos HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find_all(['item', 'entry'])
            
            print(f"📰 {source['name']}: {len(items)} notícias lidas.")

            for i, item in enumerate(items):
                if i >= 5: break # Limite de 5 notícias por fonte para teste
                
                titulo = "Sem Título"
                if item.title:
                    titulo = item.title.text.strip()
                
                # PERSISTÊNCIA NO FIREBASE
                ref.push({
                    'regiao': "Setor Central",
                    'mensagem': f"[{source['name']}] {titulo}",
                    'nivel_risco': 0.7,
                    'categoria': 'info',
                    'lat': -15.7941,
                    'lng': -47.8825,
                    'timestamp': int(time.time() * 1000)
                })
                total_count += 1
                
        except Exception as e:
            print(f"❌ ERRO {source['name']}: {str(e)}")

    return f"Fim da rodada. {total_count} registros injetados.", 200

@functions_framework.http
def process_data(request):
    return run_osint_pipeline()
