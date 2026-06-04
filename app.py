# -*- coding: utf-8 -*-
"""
Servidor Backend: FastAPI + Uvicorn + WebSockets.
Maneja la subida de archivos PDF, procesamiento en segundo plano,
resolución interactiva de tratamientos, reordenamiento de columnas y exportación Excel.
"""

import os
import json
import time
import asyncio
import re
import io
import csv
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import openpyxl
import fitz
from typing import List, Dict, Any

from extractor import process_pdf_page, run_mistral_ocr_async, extract_page_with_mistral_async, extract_document_batch_with_mistral_async

app = FastAPI(title="OCR ERP Order Processor")

# Directorios de trabajo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_FILE = os.path.join(BASE_DIR, "db.json")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Estado global / Base de datos en memoria y persistida en db.json
db_state = {
    "is_processing": False,
    "processed_pages": 0,
    "total_pages": 0,
    "elapsed_time": 0.0,
    "expected_time_remaining": 0.0,
    "orders": {},  # página -> datos de pedido
    "custom_mappings": {
        # Pre-cargar algunas correcciones de OCR obvias para evitar preguntar de más
        "RALBIANCO": "RAL BLANCO",
        "RAL.I]],ANCO": "RAL BLANCO",
        "RAtBIANCO": "RAL BLANCO",
        "RALBIANEO": "RAL BLANCO",
        "RALBIA}ICO": "RAL BLANCO",
        "RAtBI.ANCO": "RAL BLANCO",
        "RALBI,1\\NCO": "RAL BLANCO",
        "RALBI,AIiTCO": "RAL BLANCO",
        "RALBLANCO": "RAL BLANCO"
    },
    "column_order": [
        "Fecha Pedido",
        "BAR Pedidas",
        "DESDESG",
        "Cliente",
        "Nmero Pedido Cliente",
        "Tratamiento"
    ]
}

# Clientes WebSocket conectados
active_connections: List[WebSocket] = []

def load_db():
    """Carga el estado de la base de datos si existe el archivo db.json."""
    global db_state
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                # Mantener los mapeos predefinidos y fusionar con los guardados
                saved_mappings = saved.get("custom_mappings", {})
                db_state["custom_mappings"].update(saved_mappings)
                db_state["orders"] = saved.get("orders", {})
                db_state["column_order"] = saved.get("column_order", db_state["column_order"])
                db_state["processed_pages"] = saved.get("processed_pages", 0)
                db_state["total_pages"] = saved.get("total_pages", 0)
        except Exception as e:
            print(f"Error cargando db.json: {e}")

def save_db():
    """Guarda el estado actual en db.json."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "orders": db_state["orders"],
                "custom_mappings": db_state["custom_mappings"],
                "column_order": db_state["column_order"],
                "processed_pages": db_state["processed_pages"],
                "total_pages": db_state["total_pages"]
            }, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error guardando db.json: {e}")

load_db()

async def broadcast_status(data: Dict[str, Any]):
    """Envía el estado actual a todos los clientes WebSocket conectados de forma no bloqueante."""
    async def send_safe(connection):
        try:
            await asyncio.wait_for(connection.send_json(data), timeout=0.5)
        except Exception:
            pass
            
    if active_connections:
        await asyncio.gather(*(send_safe(conn) for conn in active_connections), return_exceptions=True)

async def process_pdf_background(file_path: str):
    """Tarea en segundo plano que procesa el archivo PDF página por página."""
    global db_state
    db_state["is_processing"] = True
    db_state["processed_pages"] = 0
    db_state["orders"] = {}
    save_db()
    
    try:
        doc = fitz.open(file_path)
        total = len(doc)
        db_state["total_pages"] = total
        
        start_time = time.time()
        
        try:
            # 1. Notificar al WebSocket que estamos subiendo a Mistral
            await broadcast_status({
                "type": "progress",
                "processed_pages": 0,
                "total_pages": total,
                "expected_time_remaining": 30.0,
                "had_problem": False,
                "status_text": "Subiendo y analizando documento con Mistral OCR..."
            })
            
            # 2. Ejecutar Mistral OCR sobre el PDF completo
            markdown_pages = await run_mistral_ocr_async(file_path)
            
            # Si el OCR no devolvió las páginas esperadas, lanzar error
            if len(markdown_pages) < total:
                raise Exception(f"Mistral OCR devolvió {len(markdown_pages)} páginas, pero el PDF tiene {total}")
                
            # 3. Procesar las páginas secuencialmente en lotes de 10 para evitar Rate Limit 429
            async def progress_callback(page_num, res):
                # Guardar el resultado de la página procesada en tiempo real
                db_state["orders"][str(page_num)] = res
                db_state["processed_pages"] = len(db_state["orders"])
                elapsed = time.time() - start_time
                db_state["elapsed_time"] = elapsed
                
                avg_time = elapsed / db_state["processed_pages"] if db_state["processed_pages"] > 0 else 1.0
                remaining = total - db_state["processed_pages"]
                db_state["expected_time_remaining"] = avg_time * remaining
                
                # Persistir el progreso parcial
                save_db()
                
                # Notificar progreso vía WebSocket
                await broadcast_status({
                    "type": "progress",
                    "processed_pages": db_state["processed_pages"],
                    "total_pages": total,
                    "expected_time_remaining": round(db_state["expected_time_remaining"], 1),
                    "had_problem": res["had_problem"]
                })
                
            orders_extracted = await extract_document_batch_with_mistral_async(
                markdown_pages, 
                db_state["custom_mappings"], 
                status_callback=progress_callback
            )
            db_state["orders"].update(orders_extracted)
            save_db()
            
        except Exception as mistral_err:
            print(f"Error procesando con Mistral (se inicia fallback a Tesseract local): {mistral_err}")
            # Resetear estado y contador
            db_state["processed_pages"] = 0
            db_state["orders"] = {}
            save_db()
            
            # Fallback a Tesseract local (ejecutado de forma asíncrona para no bloquear el loop)
            start_time = time.time()
            for idx in range(total):
                page = doc[idx]
                page_num = idx + 1
                
                # Ejecutar process_pdf_page en un hilo separado para evitar bloquear el bucle de eventos de FastAPI.
                # De este modo, la API (ej: /api/status) y los WebSockets siguen respondiendo durante el OCR local.
                res = await asyncio.to_thread(process_pdf_page, page, page_num, db_state["custom_mappings"])
                db_state["orders"][str(page_num)] = res
                
                db_state["processed_pages"] = page_num
                elapsed = time.time() - start_time
                db_state["elapsed_time"] = elapsed
                
                avg_time = elapsed / page_num
                remaining_pages = total - page_num
                db_state["expected_time_remaining"] = avg_time * remaining_pages
                
                save_db()
                
                await broadcast_status({
                    "type": "progress",
                    "processed_pages": page_num,
                    "total_pages": total,
                    "expected_time_remaining": round(db_state["expected_time_remaining"], 1),
                    "had_problem": res["had_problem"]
                })
                
                # Pausa mínima
                await asyncio.sleep(0.02)
                
    except Exception as e:
        print(f"Error en procesamiento de PDF: {e}")
    finally:
        db_state["is_processing"] = False
        db_state["expected_time_remaining"] = 0.0
        save_db()
        await broadcast_status({
            "type": "completed",
            "processed_pages": db_state["processed_pages"],
            "total_pages": db_state["total_pages"]
        })

# --- Modelos de Petición Pydantic ---
class ResolveTreatmentRequest(BaseModel):
    treatment_raw: str
    treatment_mapped: str

class ColumnOrderRequest(BaseModel):
    column_order: List[str]

# --- Endpoints API ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Maneja las conexiones WebSocket para notificaciones en tiempo real."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Enviar estado actual al conectar
        await websocket.send_json({
            "type": "init",
            "is_processing": db_state["is_processing"],
            "processed_pages": db_state["processed_pages"],
            "total_pages": db_state["total_pages"],
            "expected_time_remaining": round(db_state["expected_time_remaining"], 1)
        })
        while True:
            # Mantener la conexión abierta
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.post("/api/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Sube un archivo PDF e inicia el procesamiento."""
    if db_state["is_processing"]:
        return JSONResponse(status_code=400, content={"message": "Ya hay un procesamiento en curso."})
        
    if not file.filename.endswith(".pdf"):
        return JSONResponse(status_code=400, content={"message": "El archivo debe ser un PDF válido."})
        
    file_path = os.path.join(UPLOAD_DIR, "current_input.pdf")
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    background_tasks.add_task(process_pdf_background, file_path)
    
    return {"message": "Carga completada, procesando...", "total_pages": db_state["total_pages"]}

@app.get("/api/status")
async def get_status():
    """Retorna el estado de la base de datos de extracción actual."""
    # Contar órdenes únicas procesadas
    order_numbers = set()
    total_articles = 0
    unresolved_items = []
    
    for page_num, data in db_state["orders"].items():
        if data.get("order_number") and not data.get("order_number").startswith("UNKNOWN"):
            order_numbers.add(data["order_number"])
        for art in data.get("articles", []):
            total_articles += 1
            if art.get("needs_resolution"):
                unresolved_items.append({
                    "page_num": int(page_num),
                    "order_number": data.get("order_number"),
                    "code": art.get("code"),
                    "description": art.get("description"),
                    "treatment_raw": art.get("treatment_raw")
                })
                
    return {
        "is_processing": db_state["is_processing"],
        "processed_pages": db_state["processed_pages"],
        "total_pages": db_state["total_pages"],
        "orders_count": len(order_numbers),
        "articles_count": total_articles,
        "unresolved_count": len(unresolved_items),
        "unresolved_items": unresolved_items,
        "column_order": db_state["column_order"],
        "orders_data": db_state["orders"]
    }

@app.post("/api/resolve")
async def resolve_treatment(req: ResolveTreatmentRequest):
    """Guarda la resolución manual de un tratamiento y actualiza los registros asociados."""
    global db_state
    raw = req.treatment_raw
    mapped = req.treatment_mapped
    
    # Guardar en mapeos
    db_state["custom_mappings"][raw] = mapped
    # También limpiar y guardar el mapeo alfanumérico simplificado
    cleaned_raw = re.sub(r'[^A-Z0-9]', '', raw.upper())
    db_state["custom_mappings"][cleaned_raw] = mapped
    
    # Actualizar todos los artículos procesados que coincidan
    updated_count = 0
    for page_num, data in db_state["orders"].items():
        page_updated = False
        for art in data.get("articles", []):
            art_raw_cleaned = re.sub(r'[^A-Z0-9]', '', art.get("treatment_raw", "").upper())
            if art.get("treatment_raw") == raw or art_raw_cleaned == cleaned_raw:
                art["treatment_mapped"] = mapped
                art["needs_resolution"] = False
                updated_count += 1
                page_updated = True
        if page_updated:
            # Recalcular si la página tiene problemas
            has_prob = any(a.get("needs_resolution") for a in data.get("articles", []))
            data["had_problem"] = has_prob
            
    save_db()
    return {"message": "Tratamiento resuelto", "updated_count": updated_count}

@app.post("/api/columns")
async def configure_columns(req: ColumnOrderRequest):
    """Actualiza la ordenación de las columnas para el Excel de salida."""
    global db_state
    db_state["column_order"] = req.column_order
    save_db()
    return {"message": "Orden de columnas guardado."}

def generate_safe_filename(client: str, date: str, ext: str) -> str:
    """
    Genera un nombre de archivo seguro combinando el cliente, la fecha del pedido y la hora actual.
    Ejemplo: ALUMELUM_EN_MURCIA_04_06_2026_192400.xlsx
    """
    # Limpiar cliente (quitar caracteres especiales, espacios a guiones bajos, etc.)
    c_clean = re.sub(r'[^a-zA-Z0-9]', '_', client.upper())
    c_clean = re.sub(r'_+', '_', c_clean).strip('_')
    
    # Limpiar fecha del pedido
    d_clean = re.sub(r'[^a-zA-Z0-9]', '_', date)
    d_clean = re.sub(r'_+', '_', d_clean).strip('_')
    
    # Timestamp actual (HHMMSS)
    timestamp = time.strftime("%H%M%S")
    
    # Si cliente o fecha están vacíos o no válidos
    if not c_clean:
        c_clean = "CLIENTE"
    if not d_clean:
        d_clean = "FECHA"
        
    return f"{c_clean}_{d_clean}_{timestamp}.{ext}"

@app.get("/api/export")
async def export_data(format: str = "xlsx"):
    """Genera y descarga el archivo (Excel o CSV) consolidado de salida con nombre dinámico."""
    if not db_state["orders"]:
        return JSONResponse(status_code=400, content={"message": "No hay datos para exportar."})
        
    # Intentar obtener el cliente y la fecha del primer pedido válido procesado
    client_name = "CLIENTE"
    order_date = "FECHA"
    
    for page_num, data in sorted(db_state["orders"].items(), key=lambda x: int(x[0])):
        c = data.get("client")
        d = data.get("date")
        if c and not c.startswith("UNKNOWN") and c.strip():
            client_name = c.strip()
        if d and not d.startswith("UNKNOWN") and d.strip():
            order_date = d.strip()
            
    cols = db_state["column_order"]
    
    if format == "csv":
        # Exportar a CSV con codificación UTF-8 y delimitador punto y coma (;) para mayor compatibilidad con Excel
        output = io.StringIO()
        # Escribir BOM de UTF-8 para compatibilidad directa con Excel en Windows
        output.write('\ufeff')
        
        writer = csv.writer(output, delimiter=';', lineterminator='\n')
        # Escribir cabecera
        writer.writerow(cols)
        
        # Escribir filas
        for page_num, data in sorted(db_state["orders"].items(), key=lambda x: int(x[0])):
            order_num = data.get("order_number")
            order_date_val = data.get("date")
            client_val = data.get("client")
            
            for art in data.get("articles", []):
                row_data = []
                for col in cols:
                    if col == "Fecha Pedido":
                        row_data.append(order_date_val)
                    elif col == "BAR Pedidas":
                        row_data.append(art.get("quantity"))
                    elif col == "DESDESG":
                        code = art.get("code", "")
                        desc = art.get("description", "")
                        row_data.append(f"{code} {desc}".strip())
                    elif col == "Cliente":
                        row_data.append(client_val)
                    elif col == "Nmero Pedido Cliente":
                        row_data.append(order_num)
                    elif col == "Tratamiento":
                        row_data.append(art.get("treatment_mapped"))
                    else:
                        row_data.append("")
                writer.writerow(row_data)
                
        csv_content = output.getvalue()
        output.close()
        
        filename = generate_safe_filename(client_name, order_date, "csv")
        headers = {
            "Content-Disposition": f"attachment; filename={filename}"
        }
        return Response(content=csv_content, media_type="text/csv", headers=headers)
        
    else:
        # Por defecto, exportar a Excel (xlsx)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Hoja1"
        
        ws.append(cols)
        
        for page_num, data in sorted(db_state["orders"].items(), key=lambda x: int(x[0])):
            order_num = data.get("order_number")
            order_date_val = data.get("date")
            client_val = data.get("client")
            
            for art in data.get("articles", []):
                row_data = []
                for col in cols:
                    if col == "Fecha Pedido":
                        row_data.append(order_date_val)
                    elif col == "BAR Pedidas":
                        row_data.append(art.get("quantity"))
                    elif col == "DESDESG":
                        code = art.get("code", "")
                        desc = art.get("description", "")
                        row_data.append(f"{code} {desc}".strip())
                    elif col == "Cliente":
                        row_data.append(client_val)
                    elif col == "Nmero Pedido Cliente":
                        row_data.append(order_num)
                    elif col == "Tratamiento":
                        row_data.append(art.get("treatment_mapped"))
                    else:
                        row_data.append("")
                ws.append(row_data)
                
        filename = generate_safe_filename(client_name, order_date, "xlsx")
        
        # Guardar en buffer de memoria sin crear archivos físicos
        output = io.BytesIO()
        wb.save(output)
        xlsx_data = output.getvalue()
        output.close()
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}"
        }
        return Response(
            content=xlsx_data, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            headers=headers
        )

@app.post("/api/reset")
async def reset_app():
    """Reinicia la aplicación borrando todos los registros, mapeos manuales e inputs."""
    global db_state
    db_state["orders"] = {}
    db_state["processed_pages"] = 0
    db_state["total_pages"] = 0
    db_state["elapsed_time"] = 0.0
    db_state["expected_time_remaining"] = 0.0
    db_state["is_processing"] = False
    
    # Limpiar archivo temporal actual si existe
    file_path = os.path.join(UPLOAD_DIR, "current_input.pdf")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
            
    save_db()
    await broadcast_status({"type": "reset"})
    return {"message": "Aplicación reiniciada correctamente."}

# Servir archivos estáticos del frontend
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Ejecutar en localhost puerto 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
