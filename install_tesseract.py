# -*- coding: utf-8 -*-
"""
Script de instalación automatizada de Tesseract portable y datos en español.
Descarga e instala Tesseract localmente en el espacio de trabajo sin requerir permisos de administrador.
"""

import os
import urllib.request
import subprocess
import time
import shutil

INSTALL_DIR = r"d:\Antigravity\oc3\tesseract"
INSTALLER_URL = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
TESSDATA_SPA_URL = "https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata"
INSTALLER_FILE = "tesseract_installer.exe"

def download_file_with_user_agent(url, filename):
    """
    Descarga un archivo enviando una cabecera User-Agent de navegador para evitar errores 403 Forbidden.
    """
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    print(f"Iniciando descarga de {url} -> {filename}...")
    with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    print(f"Descarga de {filename} completada exitosamente.")

def main():
    print("=== INICIANDO INSTALACIÓN DE TESSERACT PORTABLE ===")
    
    # 1. Descargar el instalador de UB Mannheim
    if not os.path.exists(INSTALLER_FILE):
        try:
            download_file_with_user_agent(INSTALLER_URL, INSTALLER_FILE)
        except Exception as e:
            print(f"Error descargando el instalador de Tesseract: {e}")
            return
    else:
        print("El instalador de Tesseract ya existe localmente.")

    # 2. Ejecutar el instalador de forma silenciosa (/S) en el directorio local (/D)
    os.makedirs(INSTALL_DIR, exist_ok=True)
    print(f"Instalando Tesseract de forma silenciosa en: {INSTALL_DIR}...")
    
    cmd = f'"{os.path.abspath(INSTALLER_FILE)}" /S /D={INSTALL_DIR}'
    
    try:
        p = subprocess.Popen(cmd, shell=True)
        print("Esperando a que la instalación silenciosa finalice...")
        p.wait()
        print("Instalación silenciosa completada.")
    except Exception as e:
        print(f"Error al ejecutar instalador: {e}")
        return

    # Verificar que el ejecutable existe
    tesseract_exe = os.path.join(INSTALL_DIR, "tesseract.exe")
    for _ in range(15):
        if os.path.exists(tesseract_exe):
            break
        time.sleep(1)
        
    if not os.path.exists(tesseract_exe):
        print(f"ERROR: No se encontró tesseract.exe en {INSTALL_DIR}. Es posible que la instalación haya fallado.")
        return
        
    print(f"Tesseract detectado en: {tesseract_exe}")

    # 3. Descargar datos del idioma español (spa.traineddata)
    tessdata_dir = os.path.join(INSTALL_DIR, "tessdata")
    os.makedirs(tessdata_dir, exist_ok=True)
    spa_path = os.path.join(tessdata_dir, "spa.traineddata")
    
    if not os.path.exists(spa_path):
        try:
            download_file_with_user_agent(TESSDATA_SPA_URL, spa_path)
        except Exception as e:
            print(f"Error descargando spa.traineddata: {e}")
            return
    else:
        print("Los datos de idioma español ya existen.")

    # 4. Limpieza del instalador
    if os.path.exists(INSTALLER_FILE):
        try:
            os.remove(INSTALLER_FILE)
            print("Instalador temporal eliminado para limpiar el espacio de trabajo.")
        except Exception as e:
            print(f"No se pudo eliminar el instalador temporal: {e}")
            
    # Probar que funciona
    try:
        res = subprocess.run([tesseract_exe, "--version"], capture_output=True, text=True)
        print("\n=== VERIFICACIÓN DE TESSERACT ===")
        print(res.stdout)
        print("=================================")
    except Exception as e:
        print(f"Error al verificar Tesseract: {e}")

if __name__ == "__main__":
    main()
