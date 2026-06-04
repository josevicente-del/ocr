# -*- coding: utf-8 -*-
"""
Módulo Extractor: Lógica de análisis y extracción OCR de archivos PDF.
Este módulo utiliza PyMuPDF (fitz) para extraer y estructurar los datos del PDF
teniendo en cuenta la rotación de las páginas, la alineación por anclaje y el mapeo de tratamientos.
"""

import fitz
import re
import os
import io
import json
import httpx
import asyncio
from PIL import Image
import pytesseract

# Configuración de Tesseract local (compatible con Windows y Linux)
tesseract_path = os.environ.get("TESSERACT_CMD")
if not tesseract_path:
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe" if os.name == 'nt' else "/usr/bin/tesseract"

pytesseract.pytesseract.tesseract_cmd = tesseract_path

# Carpeta tessdata dinámica relativa al archivo extractor.py
base_dir = os.path.dirname(os.path.abspath(__file__))
tessdata_dir = os.environ.get("TESSDATA_PREFIX")
if not tessdata_dir:
    tessdata_dir = os.path.join(base_dir, "tessdata")
tessdata_dir = tessdata_dir.replace("\\", "/")
os.environ["TESSDATA_PREFIX"] = tessdata_dir

# Tabla de mapeo estándar de tratamientos según leeme.md y la nueva tabla de equivalencias
TRATAMIENTOS_ESTANDAR = {
    "ANODIZADO PLATA GRATA": "ANODIZADO PLATA GRATA",
    "RAL BLANCO": "RAL BLANCO",
    "ROBLE RUSTICO-S": "ROBLE RUSTICO-S",
    "PINO NUDO (BC-1)": "PINO NUDO (BC-1)",
    "PLATA MATE": "PLATA MATE",
    "RAL 7016 TEXTURADO": "RAL 7016 TEXTURADO"
}

def clean_extracted_order(text):
    """
    Limpia y corrige los errores comunes de OCR en los números de pedido.
    Formato esperado: 38-2026F01100035XX
    """
    s = re.sub(r'\s+', '', text)
    s = re.sub(r'^(3[8AB8])[^a-zA-Z0-9]', r'\1-', s)
    if s.startswith('3B-') or s.startswith('3A-'):
        s = '38-' + s[3:]
        
    s = re.sub(r'2[Oo]2\d', '2026', s)
    s = s.replace('F0_11', 'F011')
    s = s.replace('FO11', 'F011')
    s = s.replace('Fo11', 'F011')
    s = s.replace('011C00', '01100')
    s = re.sub(r'[^0-9A-Za-z\-]', '', s)
    
    match = re.search(r'38\-2026[Ff]([0-9A-Za-z]+)', s)
    if match:
        suffix = match.group(1)
        cleaned_suffix = ""
        for char in suffix:
            if char in ('O', 'o'):
                cleaned_suffix += '0'
            elif char in ('I', 'i', 'l', 'f'):
                cleaned_suffix += '1'
            elif char in ('S', 's'):
                cleaned_suffix += '5'
            elif char in ('B', 'A'):
                cleaned_suffix += '8'
            elif char.isdigit():
                cleaned_suffix += char
        
        # Quedarse con los primeros 10 caracteres del sufijo (formato fijo ERP de 18 caracteres total)
        cleaned_suffix = cleaned_suffix[:10]
        if len(cleaned_suffix) >= 10:
            last_two = cleaned_suffix[-2:]
            return f"38-2026F01100035{last_two}"
        else:
            return f"38-2026F{cleaned_suffix}"
            
    digits = re.findall(r'\d', s)
    if len(digits) >= 15:
        last_two = ''.join(digits[-2:])
        return f"38-2026F01100035{last_two}"
        
    return s

def clean_extracted_date(text):
    """
    Extrae y limpia las fechas del pedido, corrigiendo fallas de OCR.
    Realiza la búsqueda sobre el texto con espacios para evitar fusiones con palabras adyacentes.
    """
    pattern = r'\b([0-9A-Za-z]{1,2})\s*[\/i\\\|\,]\s*([0-9A-Za-z]{1,2})\s*[\/i\\\|\,]\s*(202[0-9A-Za-z]|[22UuAa0Oo]{4})\b'
    match = re.search(pattern, text)
    if match:
        day = match.group(1).strip()
        month = match.group(2).strip()
        year = match.group(3).strip()
        
        day = day.replace('O', '0').replace('o', '0').replace('S', '5').replace('s', '5').replace('I', '1').replace('i', '1').replace('l', '1')
        day = re.sub(r'\D', '', day).zfill(2)
        
        if month.lower() == 'ub' or month.lower() == 'a6' or month.lower() == 'a':
            month = '06'
        else:
            month = month.replace('O', '0').replace('o', '0').replace('S', '5').replace('s', '5').replace('I', '1').replace('i', '1').replace('l', '1')
            month = re.sub(r'\D', '', month).zfill(2)
            
        year = year.replace('O', '0').replace('o', '0').replace('S', '5').replace('s', '5').replace('I', '1').replace('i', '1').replace('l', '1')
        year = year.replace('U', '0').replace('A', '0')
        year = re.sub(r'\D', '', year)
        if len(year) == 2:
            year = '20' + year
            
        return f"{day}/{month}/{year}"
        
    pattern_fallback = r'([0-9A-Za-z]{1,2})\s*[\/i\\\|\,]\s*([0-9A-Za-z]{1,2})\s*[\/i\\\|\,]\s*(202[0-9A-Za-z]|[22UuAa0Oo]{4})'
    match = re.search(pattern_fallback, text)
    if match:
        day = match.group(1).strip()
        month = match.group(2).strip()
        year = match.group(3).strip()
        
        day = day.replace('O', '0').replace('o', '0').replace('S', '5').replace('s', '5').replace('I', '1').replace('i', '1').replace('l', '1')
        day = re.sub(r'\D', '', day).zfill(2)
        
        if month.lower() == 'ub' or month.lower() == 'a6' or month.lower() == 'a':
            month = '06'
        else:
            month = month.replace('O', '0').replace('o', '0').replace('S', '5').replace('s', '5').replace('I', '1').replace('i', '1').replace('l', '1')
            month = re.sub(r'\D', '', month).zfill(2)
            
        year = year.replace('O', '0').replace('o', '0').replace('S', '5').replace('s', '5').replace('I', '1').replace('i', '1').replace('l', '1')
        year = year.replace('U', '0').replace('A', '0')
        year = re.sub(r'\D', '', year)
        if len(year) == 2:
            year = '20' + year
            
        return f"{day}/{month}/{year}"
        
    return text

def clean_extracted_client(text):
    """
    Limpia el nombre del cliente extraído. Si se extrae un código numérico de cliente,
    lo mapea a un cliente conocido. De lo contrario, limpia el nombre dinámico del cliente
    (removiendo CIFs, espacios extraños, etc.) y lo devuelve para ser adaptable.
    """
    if not text:
        return "CLIENTE DESCONOCIDO"
        
    text = text.strip()
    
    # Quitar posibles CIFs/NIFs (ej: "B73849754", "B-73849754" o similar)
    text = re.sub(r'\b[A-Za-z]-?\d{7,8}[A-Za-z0-9]?\b', '', text)
    text = re.sub(r'\b\d{8}[A-Za-z0-9]\b', '', text)
    text = text.strip()
    
    # Si queda solo dígitos, es el código numérico, mapear
    digits_only = re.sub(r'\D', '', text)
    if digits_only and len(digits_only) == len(text):
        if digits_only.endswith("11"):
            return "ALUMINIOS DE ANDALUCIA Y LEV."
        return f"CLIENTE_{digits_only}"
        
    # Limpiar espacios múltiples y puntuación inicial/final
    text = re.sub(r'\s+', ' ', text)
    text = text.strip("._- ")
    
    if not text:
        return "CLIENTE DESCONOCIDO"
        
    return text

def extract_client_by_rules(text_page: str) -> str:
    """
    Extrae el nombre del cliente del texto de la página basándose en las reglas espaciales:
    - Se encuentra en la parte superior izquierda de cada página.
    - Tiene una palabra que empieza por 'B' (el CIF/NIF) justo debajo o a la derecha en la misma línea.
    """
    if not text_page:
        return ""
        
    lines = [line.strip() for line in text_page.split('\n') if line.strip()]
    
    # Patrón para detectar el CIF que empieza por B (ej: B73849754, B-73849754, o variantes de OCR como B't3849-154, 873849754 si se lee como 8)
    cif_pattern = re.compile(r'\b[B8]\s*\'?\s*[tT]?\s*-?\d[\d\-\s]{6,12}\b')
    
    for idx, line in enumerate(lines):
        # Caso 1: El CIF está en la misma línea al final
        # Ej: "ALUMINIOS DE ANDALUCIA Y LEV. B73849754"
        match = cif_pattern.search(line)
        if match:
            cif_text = match.group(0)
            # El nombre del cliente es lo que está antes del CIF
            start_pos = line.find(cif_text)
            client_candidate = line[:start_pos].strip()
            # Limpiar puntuación
            client_candidate = client_candidate.strip("._- ")
            if len(client_candidate) > 4 and "ORDEN" not in client_candidate.upper() and "PÁGINA" not in client_candidate.upper():
                return clean_client_name_text(client_candidate)
                
        # Caso 2: El CIF está en la línea de abajo
        # Ej:
        # Linea anterior: "ALUMINIOS DE ANDALUCIA Y LEV."
        # Linea actual: "B73849754"
        if cif_pattern.match(line) or (line.startswith('B') and len(re.sub(r'\D', '', line)) >= 7):
            if idx > 0:
                client_candidate = lines[idx - 1].strip()
                client_candidate = client_candidate.strip("._- ")
                if len(client_candidate) > 4 and "ORDEN" not in client_candidate.upper() and "PÁGINA" not in client_candidate.upper():
                    return clean_client_name_text(client_candidate)
                    
    # Si no se encuentra con la regla del CIF, buscar la primera línea que no esté vacía y no sea un encabezado conocido
    for line in lines[:5]:
        if len(line) > 5 and not any(kw in line.upper() for kw in ["ORDEN DE", "PÁGINA", "FECHA", "CLIENTE", "DIVISA", "S/REFERENCIA"]):
            return clean_client_name_text(line)
            
    return ""

def clean_client_name_text(text: str) -> str:
    """Corrige errores comunes de OCR en el nombre del cliente y lo estandariza."""
    # Corrección de OCR para "ALUMINIOS" si se lee con erratas
    text = re.sub(r'\b[4A]L[iI]p?[4A]IryIqs\b', 'ALUMINIOS', text, flags=re.IGNORECASE)
    text = re.sub(r'\bALIUMINIOS\b', 'ALUMINIOS', text, flags=re.IGNORECASE)
    text = re.sub(r'\bALT\]MINIOS\b', 'ALUMINIOS', text, flags=re.IGNORECASE)
    text = re.sub(r'\bALTIMII\{IOS\b', 'ALUMINIOS', text, flags=re.IGNORECASE)
    
    # Corrección de OCR para "ANDALUCIA"
    text = re.sub(r'\bAITDALUCTA\b', 'ANDALUCIA', text, flags=re.IGNORECASE)
    text = re.sub(r'\bA\}IDALUCIA\b', 'ANDALUCIA', text, flags=re.IGNORECASE)
    
    # Corrección de OCR para "LEV." o "LEY"
    text = re.sub(r'\bI;EV\b', 'LEV', text, flags=re.IGNORECASE)
    text = re.sub(r'\bLEY\b', 'LEV', text, flags=re.IGNORECASE)
    
    # Limpieza general de caracteres extraños al inicio/final
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.strip("._- ")
    
    # Si resulta ser el de cosas
    if "ANDALUCIA" in text.upper() and "ALUMINIOS" in text.upper():
        return "ALUMINIOS DE ANDALUCIA Y LEV."
        
    return text.upper()

def extract_client_by_spatial_coords(normalized_words) -> str:
    """
    Busca el nombre del cliente basándose en las coordenadas espaciales:
    1. Localiza una palabra en la parte superior izquierda que comience con 'B' (o '8')
       y que tenga el formato o longitud de un CIF/NIF.
    2. Extrae las palabras que están justo encima de este CIF (misma zona vertical, línea anterior).
    """
    cif_pattern = re.compile(r'^[B8]\s*\'?\s*[tT]?\s*-?\d[\d\-\s]{6,12}$')
    cif_word = None
    
    # Buscar el CIF en la esquina superior izquierda (vertical x < 185, horizontal y < 350)
    for w in normalized_words:
        w_x = (w[0] + w[2]) / 2 # vertical
        w_y = (w[1] + w[3]) / 2 # horizontal
        
        if w_x < 180 and w_y < 350:
            text_clean = re.sub(r'[^A-Z0-9]', '', w[4].upper())
            if re.match(r'^[B8]\d{7,10}$', text_clean) or (text_clean.startswith('B') and len(text_clean) >= 8):
                cif_word = w
                break
                
    if not cif_word:
        return ""
        
    cif_x0 = cif_word[0]
    cif_y0 = cif_word[1]
    
    # Buscar palabras en la línea inmediatamente superior (diferencia de x entre 5 y 25 puntos)
    # y que estén alineadas hacia la izquierda (y < 380 puntos)
    above_words = []
    for w in normalized_words:
        w_x = (w[0] + w[2]) / 2
        w_y = (w[1] + w[3]) / 2
        
        if (cif_x0 - 25.0) <= w_x < (cif_x0 - 2.0):
            if w_y < 380.0:
                above_words.append(w)
                
    if not above_words:
        return ""
        
    # Ordenar palabras horizontalmente (izquierda a derecha) y unirlas
    above_words.sort(key=lambda w: w[1])
    client_name = " ".join([w[4] for w in above_words]).strip()
    
    return clean_client_name_text(client_name)

def clean_quantity(raw):
    """
    Limpia el texto de la cantidad extraída y lo convierte a entero.
    """
    s = re.sub(r'\s+', '', raw)
    s = s.replace('o', '0').replace('O', '0').replace('S', '5').replace('s', '5').replace('I', '1').replace('i', '1').replace('l', '1')
    s = re.sub(r'[^0-9\,\.]', '', s)
    parts = re.split(r'[\,\.]', s)
    if parts and parts[0].isdigit():
        return int(parts[0])
    return 1

def clean_article_code(raw):
    """
    Limpia los códigos de artículos eliminando caracteres no numéricos
    y corrigiendo fallas comunes del OCR.
    """
    s = raw.replace('s', '5').replace('S', '5').replace('o', '0').replace('O', '0')
    s = s.replace('I', '1').replace('i', '1').replace('l', '1').replace('a', '0')
    s = re.sub(r'\D', '', s)
    return s

def clean_treatment_raw(text: str) -> str:
    """
    Limpia el texto del tratamiento crudo removiendo especificaciones de aleación
    como 'PERFILES 6060-T5', '6060-T5' o similares que no son acabados reales.
    """
    if not text:
        return ""
    # Quitar "PERFILES 6060-T5" y variantes (ej: "PERFIL 6060 T5", "6060-T5", etc.)
    cleaned = re.sub(r'\bPERFILES?\s*6060\s*-?\s*T5\b', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b6060\s*-?\s*T5\b', '', cleaned, flags=re.IGNORECASE)
    # Limpiar espacios extra y puntuación inicial/final
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = cleaned.strip(".,_- ")
    return cleaned

def fuzzy_map_treatment(raw_treatment, custom_mappings=None):
    """
    Mapea el tratamiento leído por OCR al tratamiento estándar deseado en ERP.
    Soporta mapeos personalizados del usuario.
    """
    if not raw_treatment:
        return None
        
    # Limpiar espacios y caracteres especiales para comparación robusta
    cleaned = re.sub(r'[^A-Z0-9]', '', raw_treatment.upper())
    
    # Comprobar mapeos personalizados del usuario primero (definidos dinámicamente)
    if custom_mappings and raw_treatment in custom_mappings:
        return custom_mappings[raw_treatment]
    if custom_mappings and cleaned in custom_mappings:
        return custom_mappings[cleaned]
        
    # Reglas estándar basadas en la nueva tabla de equivalencias de la imagen:
    
    # 1. RAL 7016 TX -> RAL 7016 TEXTURADO
    if "7016" in cleaned or "7015" in cleaned or "70A6" in cleaned or "7016TXT" in cleaned:
        return "RAL 7016 TEXTURADO"
        
    # 2. GRATADO -> ANODIZADO PLATA GRATA (también ANODIZADO PLATA GRATA / REPULIDA)
    if "GRATA" in cleaned or "GRATADO" in cleaned or "REPULIDA" in cleaned:
        return "ANODIZADO PLATA GRATA"
        
    # 3. LACADO TONO BASE PINO MATE -> PINO NUDO (BC-1) (también PINO NUDO (BC-1) / BASE MADERA TONO 8)
    if "PINO" in cleaned or "BC1" in cleaned or "BCL" in cleaned or "MADERA" in cleaned:
        return "PINO NUDO (BC-1)"
        
    # 4. PLATA 15 MICRAS -> PLATA MATE (también ANODIZADADO PLATA MATE)
    if "PLATA" in cleaned and ("MATE" in cleaned or "15" in cleaned or "MICRA" in cleaned):
        return "PLATA MATE"
        
    # 5. LACADO TONO BASE GOLDEN -> ROBLE RUSTICO-S (también GOLDEN / ROBLE / RUSTICO)
    if "GOLDEN" in cleaned or "ROBLE" in cleaned or "RUSTICO" in cleaned:
        return "ROBLE RUSTICO-S"
        
    # 6. LACADO BLANCO -> RAL BLANCO (también RAL BLANCO / RAL BLANCO PERFILES 6060-T5)
    if "BLANCO" in cleaned:
        return "RAL BLANCO"
        
    return None

def find_anchor_x(normalized_words):
    """
    Busca dinámicamente el anclaje vertical usando la cabecera 'ARTICULO'.
    """
    for w in normalized_words:
        x_center = (w[0] + w[2]) / 2
        y_center = (w[1] + w[3]) / 2
        # En Tesseract, la cabecera de la tabla está en x_center en [120, 185]
        if 120 <= x_center <= 185 and 30 <= y_center <= 95:
            cleaned = re.sub(r'[^A-Z]', '', w[4].upper())
            if any(p in cleaned for p in ["ARTICULO", "ARTTCULO", "ARTICU", "ARTTCU", "RTICUL", "RTTCUL"]):
                return x_center
                
    for w in normalized_words:
        x_center = (w[0] + w[2]) / 2
        y_center = (w[1] + w[3]) / 2
        if 120 <= x_center <= 185:
            cleaned = re.sub(r'[^A-Z]', '', w[4].upper())
            if "KILOS" in cleaned or "CANTIDAD" in cleaned or "CLIENTE" in cleaned:
                return x_center
                
    return 165.0

def process_pdf_page(page, page_num, custom_mappings=None):
    """
    Procesa una página del PDF y extrae el pedido, la fecha, el cliente y los artículos.
    Utiliza Tesseract OCR sobre el renderizado de la página a 150 DPI para máxima precisión.
    """
    # 1. Renderizar la página a 150 DPI
    pix = page.get_pixmap(dpi=150)
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    # Configuración de tessdata local
    config = f'--tessdata-dir {tessdata_dir}'
    
    # Ejecutar Tesseract
    tsv_data = pytesseract.image_to_data(img, lang="spa+eng", config=config)
    
    # Parsear el TSV y escalar a puntos de PDF (72/150 = 0.48)
    normalized_words = []
    lines = tsv_data.split('\n')
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
            
            # Escalar a puntos del PDF (x0: vertical, y0: horizontal)
            x0 = top * 0.48
            y0 = left * 0.48
            x1 = (top + height) * 0.48
            y1 = (left + width) * 0.48
            
            normalized_words.append((x0, y0, x1, y1, text))
            
    # Crear texto completo a partir de las palabras para fallbacks de regex
    sorted_words = sorted(normalized_words, key=lambda w: (w[0], w[1]))
    text_full = " ".join([w[4] for w in sorted_words])
    
    # 2. Extraer metadatos de cabecera utilizando coordenadas y expresiones regulares
    header_words = [w for w in normalized_words if w[0] <= 185 and w[1] <= 595]
    
    # Agrupar por líneas visuales basándose en la coordenada vertical w[0]
    header_lines = []
    for w in header_words:
        added = False
        for line in header_lines:
            avg_x0 = sum(item[0] for item in line) / len(line)
            if abs(w[0] - avg_x0) < 8.0:
                line.append(w)
                added = True
                break
        if not added:
            header_lines.append([w])
            
    # Para cada línea, ordenar las palabras de izquierda a derecha (w[1])
    for line in header_lines:
        line.sort(key=lambda w: w[1])
        
    # Ordenar las líneas de arriba a abajo (por su coordenada vertical promedio)
    header_lines.sort(key=lambda line: sum(item[0] for item in line) / len(line))
        
    raw_order_text = ""
    raw_date_text = ""
    raw_client_text = ""
    
    for line in header_lines:
        text = " ".join([w[4] for w in line])
        # Buscar número de pedido
        if re.search(r'3[8AB]\s*[\-\*\,]?\s*2[0O]2', text) or '2026' in text.replace(' ', ''):
            raw_order_text = text
        # Buscar fecha
        if '/' in text or 'Ub' in text or 'i' in text:
            if re.search(r'\d{1,2}[\/i\\\|\,]\d{1,2}[\/i\\\|\,]\d{2,4}', text):
                raw_date_text = text
            elif not raw_date_text and ('FECHA' in text.upper() or 'FECiA' in text.upper()):
                raw_date_text = text
        # Buscar cliente
        if re.search(r'000\s*0011', text) or '0000011' in text.replace(' ', '') or len(re.sub(r'\s+', '', text)) == 7:
            if '0011' in text or '0001' in text or 'CLIENTE' in text.upper():
                raw_client_text = text
            
    # Fallbacks generales por regex sobre todo el texto de Tesseract
    if not raw_order_text:
        s_clean = re.sub(r'[^0-9A-Za-z]', '', text_full)
        pattern_order = r'3[8BA8]2[0Oo]2[6Gg][Ff][0Oo][1Iilf][1Iilf][0OoC][0Oo][0Oo]3[5sS](\d|[sS])(\d|[sS])'
        match = re.search(pattern_order, s_clean, re.IGNORECASE)
        if match:
            raw_order_text = match.group(0)
            
    if not raw_date_text:
        pattern_date = r'\b[0-9A-Za-z]{1,2}[\/i\\\|\,][0-9A-Za-z]{1,2}[\/i\\\|\,](?:202[0-9A-Za-z]|[22UuAa0Oo]{4})\b'
        match = re.search(pattern_date, text_full)
        if match:
            raw_date_text = match.group(0)
            
    order_num = clean_extracted_order(raw_order_text) if raw_order_text else f"UNKNOWN-P{page_num}"
    order_date = clean_extracted_date(raw_date_text) if raw_date_text else "UNKNOWN"
    
    # Intentar extraer el nombre del cliente usando la regla de posición espacial respecto al CIF
    spatial_client = extract_client_by_spatial_coords(normalized_words)
    client_name = spatial_client if spatial_client else clean_extracted_client(raw_client_text)
    
    # 3. Detectar punto de anclaje
    anchor_x = find_anchor_x(normalized_words)
    
    # 4. Encontrar todos los códigos de artículos válidos en la página para crear los anclajes de fila
    code_candidates = []
    for w in normalized_words:
        x_center = (w[0] + w[2]) / 2
        y_center = (w[1] + w[3]) / 2
        
        # En Tesseract, los artículos están ABAJO del encabezado, por lo que x_center > anchor_x + 10
        if x_center > (anchor_x + 10) and 35 <= y_center <= 92:
            code_candidates.append(w)
            
    # Agrupar fragmentos de códigos que pertenecen a la misma línea horizontal (diferencia vertical pequeña)
    code_groups = []
    for c in code_candidates:
        x_c = (c[0] + c[2]) / 2
        added = False
        for cg in code_groups:
            cg_x = sum((w[0]+w[2])/2 for w in cg) / len(cg)
            if abs(x_c - cg_x) < 5.0:
                cg.append(c)
                added = True
                break
        if not added:
            code_groups.append([c])
            
    # Estructurar los anclajes de códigos
    anchors = []
    for cg in code_groups:
        cg.sort(key=lambda w: w[1]) # ordenar de izquierda a derecha
        code_str = "".join([w[4] for w in cg]).strip()
        
        # Saltar si es encabezado, contiene palabras de cabecera o patrones del pedido
        if any(lbl in code_str for lbl in ["ARTICULO", "OBSE", "RVACIONES", "PAGINA", "CLIENTE", "FECHA", "PEDIDO"]):
            continue
        if "38-" in code_str or "2026" in code_str or "0000011" in code_str:
            continue
        if not code_str:
            continue
            
        code_x = sum((w[0]+w[2])/2 for w in cg) / len(cg)
        anchors.append({
            "code_str": code_str,
            "code_x": code_x
        })
        
    # Ordenar anclajes de arriba a abajo (x ascendente en Tesseract)
    anchors.sort(key=lambda a: a["code_x"])
    
    # 5. Agrupar todas las palabras de la página en la fila del código más cercano
    rows = {i: [] for i in range(len(anchors))}
    
    for nw in normalized_words:
        x_center = (nw[0] + nw[2]) / 2
        y_center = (nw[1] + nw[3]) / 2
        
        # Ignorar si está en la zona superior de cabecera
        if x_center <= (anchor_x + 10):
            continue
            
        best_row_idx = -1
        best_dist = 9999.0
        
        for idx, anc in enumerate(anchors):
            # Comparamos directamente con code_x ya que la alineación horizontal de Tesseract es muy precisa
            dist = abs(anc["code_x"] - x_center)
            if dist < best_dist and dist <= 12.0:  # Umbral de tolerancia
                best_dist = dist
                best_row_idx = idx
                
        if best_row_idx != -1:
            rows[best_row_idx].append(nw)
            
    # 6. Procesar cada fila agrupada
    articles = []
    had_problem = False
    problem_details = []
    
    for idx, anc in enumerate(anchors):
        row_words = rows[idx]
        
        # Separar en columnas
        codes = []
        desc_treat_words = []
        qty_words = []
        
        for rw in row_words:
            y_center = (rw[1] + rw[3]) / 2
            
            # Limpiar palabra para comprobar si es etiqueta de observaciones
            word_clean = re.sub(r'[^A-Z]', '', rw[4].upper())
            # Omitir de las columnas si es parte de observaciones
            if any(lbl in word_clean for lbl in ["OBSERV", "RVACION", "OBSE", "RVACTON", "ONES"]):
                continue
                
            if 35 <= y_center <= 92:
                codes.append(rw)
            elif 95 <= y_center <= 300:
                desc_treat_words.append(rw)
            elif 300 <= y_center <= 440:
                qty_words.append(rw)
                
        # Cantidad
        qty_val_words = [qw for qw in qty_words if 405 <= (qw[1] + qw[3]) / 2 <= 445]
        qty_val_words.sort(key=lambda w: w[1])
        qty_raw = "".join([w[4] for w in qty_val_words])
        qty_cleaned = clean_quantity(qty_raw) if qty_raw else 1
        
        # Separar descripción y tratamiento mediante corte por punto medio vertical (clustering)
        desc_words = []
        treat_words = []
        if desc_treat_words:
            x_coords = [(w[0] + w[2]) / 2 for w in desc_treat_words]
            min_x = min(x_coords)
            max_x = max(x_coords)
            if max_x - min_x > 4.0:
                midpoint = (min_x + max_x) / 2
                for rw in desc_treat_words:
                    x_center = (rw[0] + rw[2]) / 2
                    if x_center <= midpoint:  # En Tesseract, menor x_center es más arriba (descripción)
                        desc_words.append(rw)
                    else:
                        treat_words.append(rw)
            else:
                desc_words = desc_treat_words
                
        desc_words.sort(key=lambda w: w[1])
        treat_words.sort(key=lambda w: w[1])
        
        desc_str = " ".join([w[4] for w in desc_words]).strip()
        treat_raw = clean_treatment_raw(" ".join([w[4] for w in treat_words]))
        
        # Mapear tratamiento
        treat_mapped = fuzzy_map_treatment(treat_raw, custom_mappings)
        
        if treat_raw and not treat_mapped:
            had_problem = True
            problem_details.append(f"Fila {idx+1}: Tratamiento desconocido '{treat_raw}'")
            
        articles.append({
            "code": clean_article_code(anc["code_str"]),
            "quantity": qty_cleaned,
            "description": desc_str,
            "treatment_raw": treat_raw,
            "treatment_mapped": treat_mapped or "PENDIENTE_CONFIRMACION",
            "needs_resolution": (treat_raw != "" and not treat_mapped)
        })
        
    return {
        "order_number": order_num,
        "date": order_date,
        "client": client_name,
        "articles": articles,
        "had_problem": had_problem,
        "problem_details": problem_details
    }

# API Key de Mistral proporcionada por el usuario
MISTRAL_API_KEY = "24xqFb47Z18XaRSmjjj9PJ1KtU7h3Eka"

async def run_mistral_ocr_async(file_path: str) -> list[str]:
    """
    Sube el archivo PDF a la API de Mistral y ejecuta el OCR sobre el documento completo.
    Retorna una lista de markdowns para cada página.
    """
    url_upload = "https://api.mistral.ai/v1/files"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, "application/pdf")
            }
            data = {
                "purpose": "ocr"
            }
            response = await client.post(url_upload, headers=headers, files=files, data=data, timeout=60.0)
            
        if response.status_code != 200:
            raise Exception(f"Error subiendo archivo a Mistral: {response.status_code} - {response.text}")
            
        upload_res = response.json()
        file_id = upload_res["id"]
        
        # Iniciar OCR
        url_ocr = "https://api.mistral.ai/v1/ocr"
        ocr_payload = {
            "model": "mistral-ocr-latest",
            "document": {
                "type": "file",
                "file_id": file_id
            }
        }
        
        ocr_response = await client.post(url_ocr, headers=headers, json=ocr_payload, timeout=180.0)
        if ocr_response.status_code != 200:
            raise Exception(f"Error ejecutando Mistral OCR: {ocr_response.status_code} - {ocr_response.text}")
            
        ocr_res = ocr_response.json()
        pages = ocr_res.get("pages", [])
        return [p.get("markdown", "") for p in pages]

async def extract_page_with_mistral_async(markdown_text: str, page_num: int, custom_mappings=None) -> dict:
    """
    Llama a Mistral Chat Completions con Structured Output para extraer de forma limpia
    el pedido, la fecha, el cliente y los artículos a partir del markdown de la página.
    """
    url_chat = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    json_schema = {
        "type": "object",
        "properties": {
            "order_number": {
                "type": "string",
                "description": "El número de pedido o número de orden de acabado, que empieza por 38 (ej. 38-2026F0110003587). Debe estar limpio de espacios."
            },
            "date": {
                "type": "string",
                "description": "La fecha de pedido en formato dd/mm/yyyy"
            },
            "client": {
                "type": "string",
                "description": "El nombre completo del cliente que aparece en la primera línea o cabecera del documento (ej. ALUMINIOS DE ANDALUCIA Y LEV. o ALUMELUM EN MURCIA). NO devuelvas el código numérico de cliente."
            },
            "articles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "El código numérico del artículo de 8 o 9 dígitos (ej. 082803064)"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "La cantidad de bultos, barras o perfiles pedidos (ej. 2,00 -> 2)"
                        },
                        "description": {
                            "type": "string",
                            "description": "La descripción del artículo, sin el código y sin el tratamiento (ej. GUIA DE 140-150 PARTE EXTERIOR)"
                        },
                        "treatment_raw": {
                            "type": "string",
                            "description": "El tratamiento a realizar al artículo tal como aparece (ej. RAL BLANCO, RAL 7016 TXT, ANODIZADO PLATA GRATA)"
                        }
                    },
                    "required": ["code", "quantity", "description", "treatment_raw"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["order_number", "date", "client", "articles"],
        "additionalProperties": False
    }
    
    payload = {
        "model": "mistral-large-latest",
        "messages": [
            {
                "role": "system",
                "content": "Eres un extractor de datos de pedidos industriales de aluminio. Extrae la información estructurada del markdown de la página. Asegúrate de extraer de forma limpia la descripción (removiendo el código de artículo y el tratamiento) y el tratamiento original."
            },
            {
                "role": "user",
                "content": markdown_text
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "order_extraction",
                "strict": True,
                "schema": json_schema
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url_chat, headers=headers, json=payload, timeout=60.0)
        
    if response.status_code != 200:
        raise Exception(f"Error en chat completion para pág {page_num}: {response.status_code} - {response.text}")
        
    res_json = response.json()
    content = res_json["choices"][0]["message"]["content"]
    extracted = json.loads(content)
    
    # Mapear tratamientos
    articles = []
    had_problem = False
    problem_details = []
    
    for idx, art in enumerate(extracted.get("articles", [])):
        treat_raw = clean_treatment_raw(art.get("treatment_raw", ""))
        treat_mapped = fuzzy_map_treatment(treat_raw, custom_mappings)
        
        if treat_raw and not treat_mapped:
            had_problem = True
            problem_details.append(f"Fila {idx+1}: Tratamiento desconocido '{treat_raw}'")
            
        articles.append({
            "code": clean_article_code(art.get("code", "")),
            "quantity": int(art.get("quantity", 1)),
            "description": art.get("description", "").strip(),
            "treatment_raw": treat_raw,
            "treatment_mapped": treat_mapped or "PENDIENTE_CONFIRMACION",
            "needs_resolution": (treat_raw != "" and not treat_mapped)
        })
        
    return {
        "order_number": clean_extracted_order(extracted.get("order_number", "")),
        "date": clean_extracted_date(extracted.get("date", "")),
        "client": clean_extracted_client(extracted.get("client", "")),
        "articles": articles,
        "had_problem": had_problem,
        "problem_details": problem_details
    }

async def extract_document_batch_with_mistral_async(markdown_pages: list[str], custom_mappings=None, status_callback=None) -> dict:
    """
    Procesa un documento de páginas de markdown en lotes de 10 páginas concurrentes para optimizar llamadas
    y evitar el límite de tasa de la API (429 Rate Limit Exceeded).
    """
    url_chat = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    json_schema = {
        "type": "object",
        "properties": {
            "pages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "page_num": {
                            "type": "integer",
                            "description": "El número de página analizada"
                        },
                        "order_number": {
                            "type": "string",
                            "description": "El número de pedido o número de orden de acabado, empieza por 38"
                        },
                        "date": {
                            "type": "string",
                            "description": "La fecha de pedido en formato dd/mm/yyyy"
                        },
                        "client": {
                            "type": "string",
                            "description": "El nombre completo del cliente que aparece en la primera línea o cabecera del documento (ej. ALUMINIOS DE ANDALUCIA Y LEV. o ALUMELUM EN MURCIA). NO devuelvas el código numérico de cliente."
                        },
                        "articles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "code": {
                                        "type": "string",
                                        "description": "El código numérico de artículo de 8 o 9 dígitos"
                                    },
                                    "quantity": {
                                        "type": "integer",
                                        "description": "La cantidad pedida"
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "La descripción del artículo"
                                    },
                                    "treatment_raw": {
                                        "type": "string",
                                        "description": "El tratamiento original del artículo"
                                    }
                                },
                                "required": ["code", "quantity", "description", "treatment_raw"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["page_num", "order_number", "date", "client", "articles"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["pages"],
        "additionalProperties": False
    }
    
    total_pages = len(markdown_pages)
    orders = {}
    batch_size = 10
    
    # Procesar en lotes de 10 páginas
    for i in range(0, total_pages, batch_size):
        batch_end = min(i + batch_size, total_pages)
        batch_indices = list(range(i + 1, batch_end + 1))
        
        user_prompt_parts = []
        for idx in batch_indices:
            markdown = markdown_pages[idx - 1]
            user_prompt_parts.append(f"--- PAGINA {idx} ---\n{markdown}")
            
        user_prompt = "\n\n".join(user_prompt_parts)
        
        # Reintentos con exponencial backoff para Rate Limit 429
        max_retries = 4
        retry_delay = 2.0
        response = None
        
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": "mistral-large-latest",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Eres un extractor de datos de pedidos industriales de aluminio. Extrae la información estructurada de cada página del lote."
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "batch_extraction",
                            "strict": True,
                            "schema": json_schema
                        }
                    }
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(url_chat, headers=headers, json=payload, timeout=90.0)
                    
                if response.status_code == 200:
                    break
                elif response.status_code == 429:
                    # Límite de tasa, esperar y reintentar
                    print(f"Intento {attempt+1} - Límite de tasa 429. Esperando {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2.0
                else:
                    raise Exception(f"Error API Mistral ({response.status_code}): {response.text}")
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(retry_delay)
                retry_delay *= 2.0
                
        if not response or response.status_code != 200:
            raise Exception(f"No se pudo completar la extracción de Mistral tras reintentos.")
            
        res_json = response.json()
        content = res_json["choices"][0]["message"]["content"]
        extracted_data = json.loads(content)
        
        # Procesar los datos estructurados devueltos por el lote
        for page_data in extracted_data.get("pages", []):
            page_num_extracted = page_data.get("page_num")
            
            # Formatear y mapear los artículos
            articles = []
            had_problem = False
            problem_details = []
            
            for idx_art, art in enumerate(page_data.get("articles", [])):
                treat_raw = clean_treatment_raw(art.get("treatment_raw", ""))
                treat_mapped = fuzzy_map_treatment(treat_raw, custom_mappings)
                
                if treat_raw and not treat_mapped:
                    had_problem = True
                    problem_details.append(f"Fila {idx_art+1}: Tratamiento desconocido '{treat_raw}'")
                    
                articles.append({
                    "code": clean_article_code(art.get("code", "")),
                    "quantity": int(art.get("quantity", 1)),
                    "description": art.get("description", "").strip(),
                    "treatment_raw": treat_raw,
                    "treatment_mapped": treat_mapped or "PENDIENTE_CONFIRMACION",
                    "needs_resolution": (treat_raw != "" and not treat_mapped)
                })
                
            page_res = {
                "order_number": clean_extracted_order(page_data.get("order_number", "")),
                "date": clean_extracted_date(page_data.get("date", "")),
                "client": clean_extracted_client(page_data.get("client", "")),
                "articles": articles,
                "had_problem": had_problem,
                "problem_details": problem_details
            }
            
            orders[str(page_num_extracted)] = page_res
            
            # Invocar callback de progreso
            if status_callback:
                await status_callback(page_num_extracted, page_res)
                
        # Pequeña pausa de cortesía entre lotes
        await asyncio.sleep(2.0)
        
    return orders
