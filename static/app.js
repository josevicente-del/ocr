/**
 * Lógica del Cliente Frontend: Comunicación con WebSocket y API REST.
 * Maneja eventos de drag & drop, renderizado de tablas, reordenamiento de columnas
 * y asignación interactiva de tratamientos desconocidos.
 */

// Elementos del DOM
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const processingStatus = document.getElementById("processing-status");

// Nuevas barras de progreso duales
const uploadProgressBar = document.getElementById("upload-progress-bar");
const uploadProgressText = document.getElementById("upload-progress-text");
const conversionProgressBar = document.getElementById("conversion-progress-bar");
const conversionProgressText = document.getElementById("conversion-progress-text");
const timeRemaining = document.getElementById("time-remaining");

const metricPages = document.getElementById("metric-pages");
const metricOrders = document.getElementById("metric-orders");
const metricArticles = document.getElementById("metric-articles");
const metricUnresolved = document.getElementById("metric-unresolved");

const columnsList = document.getElementById("columns-list");
const resolverCard = document.getElementById("resolver-card");
const resolverContainer = document.getElementById("resolver-container");
const btnExportExcel = document.getElementById("btn-export-excel");
const btnExportCsv = document.getElementById("btn-export-csv");
const btnReset = document.getElementById("btn-reset");
const tableBody = document.getElementById("table-body");
const loaderOverlay = document.getElementById("loader-overlay");

// Estado Local
let currentColumns = [];
let socket = null;
let ordersData = {}; // Guarda los pedidos consolidados para actualizar incrementalmente la UI

// Lista de tratamientos estándar ERP para el selector
const STANDARD_ERP_TREATMENTS = [
    "ANODIZADO PLATA GRATA",
    "RAL BLANCO",
    "ROBLE RUSTICO-S",
    "PINO NUDO (BC-1)",
    "PLATA MATE",
    "RAL 7016 TEXTURADO"
];

// --- Inicialización y WebSocket ---
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    socket = new WebSocket(wsUrl);
    
    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        if (data.type === "init" || data.type === "progress") {
            if (data.is_processing || data.type === "progress") {
                processingStatus.classList.remove("hidden");
                const percent = data.total_pages > 0 ? (data.processed_pages / data.total_pages) * 100 : 0;
                
                conversionProgressBar.style.width = `${percent}%`;
                conversionProgressText.innerText = `Procesando página ${data.processed_pages} de ${data.total_pages}...`;
                
                if (data.expected_time_remaining > 0) {
                    timeRemaining.innerText = `Tiempo restante estimado: ${data.expected_time_remaining}s`;
                } else {
                    timeRemaining.innerText = "Tiempo restante estimado: calculando...";
                }

                // Actualizar incrementalmente la interfaz si vienen datos de página individuales
                if (data.page_num && data.page_data) {
                    ordersData[data.page_num] = data.page_data;
                    updateUIFromOrders(ordersData);
                }
            } else {
                processingStatus.classList.add("hidden");
            }
        } else if (data.type === "completed") {
            conversionProgressBar.style.width = "100%";
            conversionProgressText.innerText = "¡Procesamiento completo!";
            timeRemaining.innerText = "";
            setTimeout(() => {
                processingStatus.classList.add("hidden");
                refreshStatus();
            }, 1500);
        } else if (data.type === "reset") {
            ordersData = {};
            updateUIFromOrders(ordersData);
            refreshStatus();
        }
    };
    
    socket.onclose = function() {
        // Intentar reconectar después de 3 segundos
        setTimeout(connectWebSocket, 3000);
    };
}

// --- Peticiones API REST ---

// --- Actualización Reactiva de la Interfaz ---
function updateUIFromOrders(orders) {
    const orderNumbers = new Set();
    let totalArticles = 0;
    const unresolvedItems = [];
    
    Object.entries(orders).forEach(([pageNum, data]) => {
        if (data.order_number && !data.order_number.startsWith("UNKNOWN")) {
            orderNumbers.add(data.order_number);
        }
        (data.articles || []).forEach(art => {
            totalArticles++;
            if (art.needs_resolution) {
                unresolvedItems.push({
                    page_num: parseInt(pageNum),
                    order_number: data.order_number,
                    code: art.code,
                    description: art.description,
                    treatment_raw: art.treatment_raw
                });
            }
        });
    });
    
    // Actualizar Métricas en tiempo real
    metricPages.innerText = Object.keys(orders).length;
    metricOrders.innerText = orderNumbers.size;
    metricArticles.innerText = totalArticles;
    metricUnresolved.innerText = unresolvedItems.length;
    
    // Habilitar/Deshabilitar botones de exportación
    btnExportExcel.disabled = (totalArticles === 0);
    btnExportCsv.disabled = (totalArticles === 0);
    
    // Renderizar Resolutor de Tratamientos
    renderResolver(unresolvedItems);
    
    // Renderizar Tabla Principal de Pedidos
    renderTable(orders);
}

async function refreshStatus() {
    loaderOverlay.classList.remove("hidden");
    try {
        const res = await fetch("/api/status");
        const status = await res.json();
        
        // Renderizar Columnas
        currentColumns = status.column_order;
        renderColumns();
        
        // Asignar estado local e iniciar actualización de UI
        ordersData = status.orders_data;
        updateUIFromOrders(ordersData);
        
    } catch (e) {
        console.error("Error al obtener estado:", e);
    } finally {
        loaderOverlay.classList.add("hidden");
    }
}

// --- Renderizadores del DOM ---

function renderColumns() {
    columnsList.innerHTML = "";
    currentColumns.forEach((col, idx) => {
        const item = document.createElement("div");
        item.className = "column-item";
        
        // Texto de la columna
        const span = document.createElement("span");
        span.innerText = `${idx + 1}. ${col}`;
        item.appendChild(span);
        
        // Botones de subir/bajar para cambiar el orden
        const controls = document.createElement("div");
        controls.className = "column-controls";
        
        const btnUp = document.createElement("button");
        btnUp.className = "column-btn";
        btnUp.innerHTML = '<i class="fa-solid fa-chevron-up"></i>';
        btnUp.disabled = (idx === 0);
        btnUp.onclick = () => moveColumn(idx, idx - 1);
        
        const btnDown = document.createElement("button");
        btnDown.className = "column-btn";
        btnDown.innerHTML = '<i class="fa-solid fa-chevron-down"></i>';
        btnDown.disabled = (idx === currentColumns.length - 1);
        btnDown.onclick = () => moveColumn(idx, idx + 1);
        
        controls.appendChild(btnUp);
        controls.appendChild(btnDown);
        item.appendChild(controls);
        columnsList.appendChild(item);
    });
}

async function moveColumn(fromIdx, toIdx) {
    // Intercambiar elementos en el array local
    const temp = currentColumns[fromIdx];
    currentColumns[fromIdx] = currentColumns[toIdx];
    currentColumns[toIdx] = temp;
    
    // Guardar en el servidor
    try {
        await fetch("/api/columns", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ column_order: currentColumns })
        });
        renderColumns();
    } catch (e) {
        console.error("Error al reordenar columnas:", e);
    }
}

function renderResolver(unresolvedItems) {
    resolverContainer.innerHTML = "";
    
    if (unresolvedItems.length === 0) {
        resolverCard.classList.add("hidden");
        return;
    }
    
    resolverCard.classList.remove("hidden");
    
    // Obtener tratamientos desconocidos únicos
    const uniqueRawTreatments = {};
    unresolvedItems.forEach(item => {
        if (!uniqueRawTreatments[item.treatment_raw]) {
            uniqueRawTreatments[item.treatment_raw] = [];
        }
        uniqueRawTreatments[item.treatment_raw].push(item);
    });
    
    Object.keys(uniqueRawTreatments).forEach(raw => {
        const items = uniqueRawTreatments[raw];
        const rep = items[0];
        
        const div = document.createElement("div");
        div.className = "resolver-item";
        
        // Info del tratamiento
        const info = document.createElement("div");
        info.className = "resolver-item-info";
        
        const label = document.createElement("span");
        label.className = "resolver-item-label";
        label.innerText = "Tratamiento leído por OCR:";
        
        const rawText = document.createElement("span");
        rawText.className = "resolver-item-raw";
        rawText.innerText = raw;
        
        const meta = document.createElement("span");
        meta.className = "resolver-item-meta";
        meta.innerText = `Encontrado en Pág. ${items.map(i => i.page_num).join(", ")} (Pedido: ${rep.order_number})`;
        
        info.appendChild(label);
        info.appendChild(rawText);
        info.appendChild(meta);
        div.appendChild(info);
        
        // Selector de mapeo
        const select = document.createElement("select");
        select.className = "resolver-select";
        
        // Opción por defecto
        const defOpt = document.createElement("option");
        defOpt.value = "";
        defOpt.innerText = "Selecciona mapeo ERP...";
        select.appendChild(defOpt);
        
        // Opciones estándar
        STANDARD_ERP_TREATMENTS.forEach(t => {
            const opt = document.createElement("option");
            opt.value = t;
            opt.innerText = t;
            select.appendChild(opt);
        });
        
        // Opción personalizada
        const customOpt = document.createElement("option");
        customOpt.value = "CUSTOM";
        customOpt.innerText = "[Escribir valor personalizado...]";
        select.appendChild(customOpt);
        
        select.onchange = async function() {
            let mappedVal = select.value;
            if (mappedVal === "") return;
            
            if (mappedVal === "CUSTOM") {
                const userInput = prompt(`Escribe el nombre del tratamiento ERP correcto para '${raw}':`);
                if (userInput && userInput.trim() !== "") {
                    mappedVal = userInput.trim();
                } else {
                    select.value = "";
                    return;
                }
            }
            
            // Enviar resolución al backend
            loaderOverlay.classList.remove("hidden");
            try {
                await fetch("/api/resolve", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        treatment_raw: raw,
                        treatment_mapped: mappedVal
                    })
                });
                refreshStatus();
            } catch (e) {
                console.error("Error al resolver tratamiento:", e);
                loaderOverlay.classList.add("hidden");
            }
        };
        
        div.appendChild(select);
        resolverContainer.appendChild(div);
    });
}

function renderTable(ordersData) {
    tableBody.innerHTML = "";
    
    const pages = Object.keys(ordersData).map(Number).sort((a, b) => a - b);
    
    if (pages.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.className = "empty-table";
        td.colSpan = 11;
        td.innerText = "No se han procesado archivos en este lote. Sube un PDF para comenzar.";
        tr.appendChild(td);
        tableBody.appendChild(tr);
        return;
    }
    
    pages.forEach(pageNum => {
        const page = ordersData[pageNum];
        const orderNum = page.order_number;
        const date = page.date;
        const client = page.client || "";
        
        page.articles.forEach(art => {
            const tr = document.createElement("tr");
            
            // Pág
            const tdPage = document.createElement("td");
            tdPage.innerText = pageNum;
            tr.appendChild(tdPage);
            
            // Pedido
            const tdOrder = document.createElement("td");
            tdOrder.innerText = orderNum;
            tr.appendChild(tdOrder);
            
            // Fecha
            const tdDate = document.createElement("td");
            tdDate.innerText = date;
            tr.appendChild(tdDate);
            
            // Cliente
            const tdClient = document.createElement("td");
            tdClient.innerText = client;
            tr.appendChild(tdClient);
            
            // Código
            const tdCode = document.createElement("td");
            tdCode.innerText = art.code;
            tr.appendChild(tdCode);
            
            // Cant
            const tdQty = document.createElement("td");
            tdQty.innerText = art.quantity;
            tr.appendChild(tdQty);
            
            // Descripción
            const tdDesc = document.createElement("td");
            tdDesc.innerText = art.description;
            tr.appendChild(tdDesc);
            
            // Mapeado
            const tdTreat = document.createElement("td");
            tdTreat.innerText = art.treatment_mapped;
            tr.appendChild(tdTreat);
            
            // Serie
            const tdSerie = document.createElement("td");
            tdSerie.innerText = art.serie || "";
            tr.appendChild(tdSerie);
            
            // Medida
            const tdMeasure = document.createElement("td");
            tdMeasure.innerText = art.measure || "";
            tr.appendChild(tdMeasure);
            
            // Estado
            const tdStatus = document.createElement("td");
            const indicator = document.createElement("div");
            indicator.className = "status-indicator";
            
            if (art.needs_resolution) {
                indicator.className += " status-pending";
                indicator.innerHTML = '<i class="fa-solid fa-circle-question"></i> Pendiente';
            } else {
                indicator.className += " status-ok";
                indicator.innerHTML = '<i class="fa-solid fa-circle-check"></i> Listo';
            }
            tdStatus.appendChild(indicator);
            tr.appendChild(tdStatus);
            
            tableBody.appendChild(tr);
        });
    });
}

// --- Eventos y Drag & Drop ---

// Abrir selector de archivos al hacer clic en la zona de drop
dropZone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", function() {
    if (fileInput.files.length > 0) {
        uploadFile(fileInput.files[0]);
    }
});

// Eventos dragover / dragleave / drop
dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
        uploadFile(e.dataTransfer.files[0]);
    }
});

function uploadFile(file) {
    if (!file.name.endsWith(".pdf")) {
        alert("Por favor, sube un archivo PDF válido.");
        return;
    }
    
    const formData = new FormData();
    formData.append("file", file);
    
    // Mostrar paneles e inicializar barras
    processingStatus.classList.remove("hidden");
    
    uploadProgressBar.style.width = "0%";
    uploadProgressText.innerText = "Preparando subida del archivo...";
    
    conversionProgressBar.style.width = "0%";
    conversionProgressText.innerText = "Esperando que finalice la carga del archivo...";
    timeRemaining.innerText = "Tiempo restante estimado: calculando...";
    
    const xhr = new XMLHttpRequest();
    
    // Escuchar el progreso de subida (upload progress) en tiempo real
    xhr.upload.onprogress = function(event) {
        if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            uploadProgressBar.style.width = `${percent}%`;
            
            const loadedMB = (event.loaded / (1024 * 1024)).toFixed(1);
            const totalMB = (event.total / (1024 * 1024)).toFixed(1);
            uploadProgressText.innerText = `Subiendo archivo: ${percent}% (${loadedMB} MB de ${totalMB} MB)...`;
        }
    };
    
    // Escuchar la respuesta final de la petición
    xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
            uploadProgressBar.style.width = "100%";
            uploadProgressText.innerText = "¡PDF cargado correctamente! Iniciando conversión...";
            console.log("Archivo cargado con éxito, procesamiento iniciado.");
        } else {
            let errorMsg = "Ocurrió un error en el servidor.";
            try {
                const err = JSON.parse(xhr.responseText);
                errorMsg = err.message || errorMsg;
            } catch (e) {}
            alert(`Error: ${errorMsg}`);
            processingStatus.classList.add("hidden");
        }
    };
    
    // Escuchar errores de red/subida
    xhr.onerror = function() {
        alert("Ocurrió un error de red al subir el archivo.");
        processingStatus.classList.add("hidden");
    };
    
    xhr.open("POST", "/api/upload");
    xhr.send(formData);
}

// Botones de acción
btnExportExcel.addEventListener("click", () => {
    window.open("/api/export?format=xlsx", "_blank");
});

btnExportCsv.addEventListener("click", () => {
    window.open("/api/export?format=csv", "_blank");
});

btnReset.addEventListener("click", async () => {
    loaderOverlay.classList.remove("hidden");
    try {
        await fetch("/api/reset", { method: "POST" });
        // Limpieza visual inmediata en el cliente
        metricPages.innerText = "0";
        metricOrders.innerText = "0";
        metricArticles.innerText = "0";
        metricUnresolved.innerText = "0";
        btnExportExcel.disabled = true;
        btnExportCsv.disabled = true;
        resolverCard.classList.add("hidden");
        tableBody.innerHTML = '<tr><td colspan="11" class="empty-table">No se han procesado archivos en este lote. Sube un PDF para comenzar.</td></tr>';
        
        await refreshStatus();
    } catch (e) {
        console.error("Error al reiniciar la aplicación:", e);
    } finally {
        loaderOverlay.classList.add("hidden");
    }
});

// Iniciar aplicación al cargar
window.onload = function() {
    connectWebSocket();
    refreshStatus();
};
