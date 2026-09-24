# 📘 Guía Completa de Arquitectura y Replicación del Proyecto
## Sistema de Extracción OCR de Etiquetas y Automatización de Avisos por Correo (Outlook 365 / Cloud)

---

## 🎯 1. Visión General del Proyecto

Esta aplicación es una solución integral diseñada para optimizar los partes de avería y registro de equipos técnicos mediante visión artificial y automatización de correo electrónico:

1. **Captura Rápida de Imagen**: Fotografiar una etiqueta desde el móvil (cámara directa), arrastrar un archivo o pegar un pantallazo del portapapeles (`Ctrl+V`).
2. **Procesamiento de Imagen y OCR Inteligente**: Detección automática y extracción de campos clave como **Número de Serie (S/N)**, **Referencia de Fabricante (REF)** y **Códigos de Barras / QR**.
3. **Generación Automática del Parte y Envío**: Redacción de una plantilla oficial personalizada con los datos extraídos y envío automático del correo mediante la sesión abierta de **Outlook 365** (o vía SMTP en la nube), adjuntando la fotografía original.
4. **Acceso Universal Multi-dispositivo**: Accesible desde el ordenador local, red local Wi-Fi y desde cualquier móvil Android/iOS con datos 4G/5G mediante un dominio fijo seguro con HTTPS.

---

## 🏗️ 2. Arquitectura y Stack Tecnológico

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFAZ DE USUARIO                      │
│   (HTML5 + Tailwind CSS + Lucide Icons + Cámara Móvil)      │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────┐
│                    BACKEND (FastAPI / Python)                │
│                         app.py                              │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
┌──────────────▼─────────────┐   ┌─────────────▼──────────────┐
│     MOTOR OCR Y VISIÓN     │   │      SERVICIO DE CORREO     │
│   - Tesseract OCR (5.4)    │   │   - Outlook COM (win32com) │
│   - OpenCV (Preprocesado)  │   │   - PowerShell Fallback    │
│   - PyZbar (Barcodes / QR) │   │   - SMTP Office 365 Direct │
│   - Regex Normalization    │   │   - Plantillas HTML        │
└────────────────────────────┘   └────────────────────────────┘
```

### Componentes Técnicos:
- **Backend**: Python 3.11+, FastAPI (asíncrono y de alto rendimiento), Uvicorn, Pydantic.
- **Visión Artificial y OCR**:
  - `Tesseract OCR 5.4` con paquetes de idioma `spa` (Español) y `eng` (Inglés).
  - `OpenCV` (detección de contornos de etiquetas, corrección de perspectiva, umbralizado adaptativo Otsu y CLAHE).
  - `pyzbar` para decodificación de códigos de barras (Code128, DataMatrix, QR).
  - Normalizador de símbolos normativos ISO médicos (`[SN]`, `[REF]`, etc.).
- **Automatización de Correo**:
  - `win32com.client` / PowerShell COM Interop: Envía a través del cliente Outlook instalado en Windows sin pedir credenciales ni sufrir bloqueos por doble factor (MFA).
  - `smtplib` + `email.mime`: Envío directo por SMTP (`smtp.office365.com`) para despliegues en servidores cloud (Linux/Docker).
- **Frontend Web**:
  - Diseño responsivo moderno (móvil y escritorio) con Tailwind CSS (CDN).
  - API de Cámara nativa (`capture="environment"` para cámara trasera).
  - API de Portapapeles (captura de `Ctrl+V` y arrastrar y soltar).
  - Generador de QR dinámico (`qrcode.js`) para conexión rápida.
- **Acceso Remoto y Red**:
  - ngrok Python SDK / Cloudflare Tunnels para salida segura con HTTPS a internet.

---

## 📁 3. Estructura de Archivos del Proyecto

```text
├── app.py                             # Servidor FastAPI y endpoints API REST
├── config.json                        # Archivo JSON con configuración y plantillas
├── requirements.txt                   # Librerías de Python requeridas
├── Dockerfile                         # Contenedor para despliegue en la nube
├── .gitignore                         # Exclusiones para control de versiones Git
├── README.md                          # Documentación del repositorio
├── GUIA_PROYECTO_Y_REPLICACION.md     # Este manual técnico de arquitectura
│
├── iniciar_app.bat                    # Lanzador 1 clic (Modo local en PC / Wi-Fi)
├── iniciar_con_dominio_fijo.bat       # Lanzador 1 clic (Modo dominio permanente ngrok)
├── iniciar_con_acceso_remoto.bat      # Lanzador 1 clic (Modo túnel Cloudflare)
├── crear_inicio_automatico_windows.bat # Configura el inicio automático al encender el PC
├── run_permanent_tunnel.py            # Servidor + túnel persistente con autoreconexión
├── run_with_tunnel.ps1                # Script PowerShell para túnel Cloudflare
│
├── services/
│   ├── __init__.py
│   ├── config_service.py              # Carga y guardado de ajustes de configuración
│   ├── ocr_service.py                 # Pipeline de visión artificial y extracción OCR
│   └── email_service.py               # Generador de plantilla HTML y envío por Outlook/SMTP
│
├── templates/
│   └── index.html                     # Interfaz gráfica web responsiva
│
└── tests/
    ├── test_services.py               # Tests unitarios de OCR, Email y Config
    └── test_api.py                    # Tests de integración de endpoints REST
```

---

## ⚙️ 4. Explicación de los Módulos Clave

### A. Módulo OCR y Extracción (`services/ocr_service.py`)
1. **Pipeline de Detección de Etiquetas**:
   - Convierte la imagen a escala de grises y aplica filtro Gaussiano.
   - Detecta los contornos rectangulares dominantes (las etiquetas adhesivas) y genera recortes optimizados.
   - Aplica binarización adaptativa Otsu + aumento de contraste para mejorar el texto borroso o con brillos.
2. **Normalización de Texto**:
   - Sustituye variantes comunes como `[SN]`, `(SN)`, `|SN|`, `S/N:`, `Serial Number:` por `SN:`.
   - Sustituye `[REF]`, `|REF|`, `REF:` por `REF:`.
3. **Extracción por Expresiones Regulares**:
   - `SN`: Busca secuencias alfanuméricas de longitud típica (4 a 25 caracteres) situadas tras la etiqueta.
   - `REF`: Extrae el código de modelo/referencia (ej: `862199 M2703A`).
   - `Barcodes`: Extrae cadenas de códigos de barras (Code128 / QR de inventario).

### B. Módulo de Correo (`services/email_service.py`)
1. **Envío por Outlook de Escritorio (COM)**:
   - Se comunica con el proceso `Outlook.Application` activo en Windows.
   - Crea un elemento `MailItem(0)`, inserta el destinatario, asunto, cuerpo HTML formateado y adjunta la imagen temporal.
   - Llama a `.Send()` (envío automático) o `.Display()` (si se desea revisar antes de enviar).
2. **Envío por SMTP**:
   - Soporte para autenticación Office 365 mediante TLS en puerto 587 para entornos Docker o servidores Linux.
3. **Plantilla HTML Responsiva**:
   - Tarjetas destacadas con código de colores para **S/N** y **REF**.
   - Cuadro descriptivo con la avería redactada.
   - Bloque de firma y aviso de archivo adjunto.

### C. Módulo de Configuración (`services/config_service.py` & `config.json`)
Permite modificar los parámetros centrales sin alterar el código fuente:
```json
{
  "default_recipient": "clientes.sistemas.medicos@philips.com",
  "subject_prefix": "Avería",
  "default_body_template": "Me llamo Joaquín Egea Serrano...",
  "attach_image": true,
  "email_method": "outlook_com",
  "port": 8000,
  "host": "0.0.0.0"
}
```

---

## 🔄 5. Guía de Replicación para Nuevas Necesidades

Si deseas clonar y adaptar esta aplicación para **otro hospital, otro fabricante (Siemens, GE, Dräger, etc.) o para mantenimiento general de instalaciones**, sigue estos pasos:

### 📝 Paso 1: Duplicar la Carpeta del Proyecto
Copia la carpeta entera a una nueva ubicación (ej: `APPs/Avisos_Siemens` o `APPs/Mantenimiento_Climatizacion`).

---

### 📝 Paso 2: Adaptar el Destinatario y Plantilla en `config.json`
Edita [`config.json`](file:///c:/Users/JoaquínEgeaSerrano/OneDrive%20-%20Agenor%20Mantenimientos/Escritorio/AGENOR%20MANTENIMIENTOS/APPs/Correo/config.json) con los nuevos datos:
```json
{
  "default_recipient": "soporte.tecnico@nuevo-proveedor.com",
  "subject_prefix": "Parte de Trabajo",
  "email_method": "outlook_com"
}
```

---

### 📝 Paso 3: Personalizar el Texto del Mensaje en `services/email_service.py`
Para cambiar el remitente, cargo, ubicación o estilo del correo, abre [`services/email_service.py`](file:///c:/Users/JoaquínEgeaSerrano/OneDrive%20-%20Agenor%20Mantenimientos/Escritorio/AGENOR%20MANTENIMIENTOS/APPs/Correo/services/email_service.py) y edita la función `generate_html_body`:

```python
# Ejemplo para otro departamento:
intro = f"""
Me llamo <strong>Tu Nombre</strong>. Técnico de mantenimiento de la sede X.
Se notifica la incidencia sobre el equipo con Referencia <strong>{ref_display}</strong> 
y Número de Serie <strong>{sn_display}</strong>.
"""
```

---

### 📝 Paso 4: Añadir o Modificar Campos OCR en `services/ocr_service.py`
Si necesitas extraer campos adicionales (por ejemplo: `LOTE`, `MODELO`, `CADUCIDAD` o `UBICACIÓN`):

1. **Añadir el patrón regex en `ocr_service.py`**:
```python
# Ejemplo para extraer LOTE:
def _parse_lot_numbers(text: str) -> List[str]:
    patterns = [
        r'(?:LOT|LOTE)[\s:\-\.\|]+([A-Z0-9\-_]{4,20})',
    ]
    # Lógica de búsqueda
```
2. **Añadir el campo en el resultado del endpoint `/api/extract-sn` en `app.py`**.
3. **Añadir el campo en la interfaz `templates/index.html`** para que se muestre en pantalla.

---

### 📝 Paso 5: Modificar Título y Textos de la Web en `templates/index.html`
En [`templates/index.html`](file:///c:/Users/JoaquínEgeaSerrano/OneDrive%20-%20Agenor%20Mantenimientos/Escritorio/AGENOR%20MANTENIMIENTOS/APPs/Correo/templates/index.html), modifica los títulos del encabezado:
- Cambia `<title>` y `<h1>Avisos de Avería</h1>`.
- Ajusta los textos de ayuda o logotipos.

---

## 🚀 6. Modos de Ejecución Disponibles

| Archivo Batch | Descripción | Caso de Uso |
| :--- | :--- | :--- |
| **`iniciar_app.bat`** | Inicia el servidor web local en `http://localhost:8000`. | Uso en el mismo PC o en dispositivos conectados a la misma red Wi-Fi. |
| **`iniciar_con_dominio_fijo.bat`** | Inicia el servidor + túnel ngrok permanente (`https://tu-dominio.ngrok-free.dev`). | **Recomendado**: Para acceder desde el móvil con **datos 4G/5G** desde cualquier lugar con dirección fija. |
| **`iniciar_con_acceso_remoto.bat`** | Inicia el servidor + túnel temporal de Cloudflare HTTPS. | Acceso remoto gratuito e inmediato sin registro. |
| **`crear_inicio_automatico_windows.bat`** | Crea un acceso directo en la carpeta de inicio de Windows. | Para que la app arranque sola en segundo plano al encender el PC. |

---

## ☁️ 7. Despliegue en la Nube (Sin depender del PC)

Si se desea alojar en un servidor cloud (Render, Railway, Docker, Azure):

1. **Crear repositorio en GitHub** y subir los archivos del proyecto.
2. **Conectar con Render.com** (o cualquier plataforma Docker).
3. La plataforma detectará el [`Dockerfile`](file:///c:/Users/JoaquínEgeaSerrano/OneDrive%20-%20Agenor%20Mantenimientos/Escritorio/AGENOR%20MANTENIMIENTOS/APPs/Correo/Dockerfile) y desplegará el servicio en Linux con Tesseract y OpenCV preinstalados.
4. En los ajustes de la app (`config.json`), seleccionar `email_method: "smtp"` e introducir las credenciales de Office 365.

---

## 🛠️ 8. Preguntas Frecuentes y Solución de Problemas (Troubleshooting)

- **Problema: En Windows sale "no se encontró Python"**:
  - *Causa*: El alias ficticio de Microsoft Store de Windows 11 interfiere.
  - *Solución*: Los scripts `.bat` del proyecto ya están configurados para llamar directamente a `%LOCALAPPDATA%\Programs\Python311\python.exe`.
- **Problema: Outlook no envía el correo**:
  - *Causa*: Outlook de escritorio no está abierto o tiene un cuadro de diálogo modal bloqueado.
  - *Solución*: Asegurarse de tener el programa Microsoft Outlook 365 abierto con la sesión iniciada.
- **Problema: Al abrir en el móvil sale "Endpoint Offline (ERR_NGROK_3200)"**:
  - *Causa*: El ordenador está apagado o no se ha ejecutado `iniciar_con_dominio_fijo.bat`.
  - *Solución*: Iniciar el archivo `.bat` en el ordenador y comprobar que la ventana negra permanece abierta.
- **Problema: Caracteres o tildes extrañas en consola**:
  - *Solución*: Todos los scripts incorporan `chcp 65001` (UTF-8) o codificación ASCII limpia compatible con PowerShell 5.1.

---

*Desarrollado y mantenido para Electromedicina y Mantenimiento Técnico.*
