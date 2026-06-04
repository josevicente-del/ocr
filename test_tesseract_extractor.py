# -*- coding: utf-8 -*-
"""
Script de prueba para Tesseract OCR sobre la página 1.
"""

import fitz
import pytesseract
from PIL import Image
import io
import re

# Configurar ruta a Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def test_ocr_page_1():
    doc = fitz.open("Cosas/20260604142405.pdf")
    page = doc[0]
    
    # Renderizar a 150 DPI
    pix = page.get_pixmap(dpi=150)
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    # Configuración de tessdata local
    import os
    tessdata_dir = "d:/Antigravity/oc3/tessdata"
    os.environ["TESSDATA_PREFIX"] = tessdata_dir
    config = f'--tessdata-dir {tessdata_dir}'
    
    print("Ejecutando Tesseract OCR...")
    tsv_data = pytesseract.image_to_data(img, lang="spa+eng", config=config)
    
    print("Datos TSV recibidos. Primeras 15 líneas:")
    lines = tsv_data.split('\n')
    for line in lines[:15]:
        print(line)
        
    # Agrupar y mapear
    words = []
    header = True
    for line in lines:
        if not line.strip():
            continue
        fields = line.split('\t')
        if header:
            header = False
            continue
        if len(fields) >= 12:
            text = fields[11].strip()
            if not text:
                continue
            left = int(fields[6])
            top = int(fields[7])
            width = int(fields[8])
            height = int(fields[9])
            
            # Escalar a puntos del PDF (72/150 = 0.48)
            x0 = top * 0.48
            y0 = left * 0.48
            x1 = (top + height) * 0.48
            y1 = (left + width) * 0.48
            
            words.append((x0, y0, x1, y1, text))
            
    # Imprimir palabras detectadas en el encabezado (x <= 170, y <= 320)
    print("\n=== Palabras del Encabezado ===")
    header_words = [w for w in words if w[0] <= 170 and w[1] <= 320]
    header_words.sort(key=lambda w: w[1]) # ordenar de izquierda a derecha
    print(" ".join([w[4] for w in header_words]))
    
    # Imprimir palabras que parecen códigos de artículos (x > 170, y en [35, 92])
    print("\n=== Códigos de Artículos Detectados ===")
    code_words = [w for w in words if w[0] > 170 and 35 <= w[1] <= 92]
    code_words.sort(key=lambda w: w[0]) # ordenar de arriba a abajo
    for c in code_words:
        print(f"Cód: {c[4]} | x={c[0]:.2f}, y={c[1]:.2f}")

if __name__ == "__main__":
    test_ocr_page_1()
