# Usar una imagen base de Python oficial y liviana
FROM python:3.11-slim

# Instalar dependencias del sistema requeridas para PyMuPDF y Tesseract OCR (con soporte para español)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar requerimientos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Configurar variables de entorno para producción Linux
ENV TESSERACT_CMD="/usr/bin/tesseract"
ENV TESSDATA_PREFIX="/usr/share/tesseract-ocr/5/tessdata"

# Exponer el puerto por defecto de la aplicación
EXPOSE 8000

# Comando para iniciar la aplicación usando Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
