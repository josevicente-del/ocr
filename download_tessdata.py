# -*- coding: utf-8 -*-
"""
Script para descargar los archivos de idioma de Tesseract (eng y spa)
y guardarlos localmente en d:\Antigravity\oc3\tessdata.
"""

import os
import urllib.request
import shutil

TESSDATA_DIR = r"d:\Antigravity\oc3\tessdata"
os.makedirs(TESSDATA_DIR, exist_ok=True)

LANG_URLS = {
    "spa.traineddata": "https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata",
    "eng.traineddata": "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata"
}

def download_lang(name, url):
    dest = os.path.join(TESSDATA_DIR, name)
    if os.path.exists(dest):
        print(f"El archivo {name} ya existe.")
        return
        
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    print(f"Descargando {name} desde {url}...")
    try:
        with urllib.request.urlopen(req) as response, open(dest, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print(f"Descarga de {name} completada con éxito.")
    except Exception as e:
        print(f"Error descargando {name}: {e}")

def main():
    print("=== DESCARGANDO DATOS DE IDIOMAS DE TESSERACT ===")
    for name, url in LANG_URLS.items():
        download_lang(name, url)
    print("=== PROCESO COMPLETADO ===")

if __name__ == "__main__":
    main()
