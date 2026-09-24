# 🏥 App de Avisos de Avería - Electromedicina (Hospital de Alcañiz)

Aplicación web para la extracción automática de **Número de Serie (S/N)** y **Referencia (REF)** desde fotografías de etiquetas de equipos médicos e industriales, y redacción/envío automático de avisos de avería vía **Outlook 365**.

---

## ✨ Características

- 📷 **Captura flexible**: Carga por arrastrar y soltar, selector de archivos, cámara (móviles/tablets) o pegado directo desde el portapapeles (`Ctrl+V`).
- 🔍 **Motor OCR Especializado**: Detección de etiquetas médicas con símbolos normativos ISO (`[SN]`, `[REF]`), códigos de barras (Code128, DataMatrix, QR) y números de serie.
- ✉️ **Envío Nativo vía Outlook 365**: Conexión con el cliente de escritorio de Windows (o SMTP Office 365) adjuntando la fotografía.
- 📋 **Plantilla Oficial Integrada**:
  - **Destinatario**: `clientes.sistemas.medicos@philips.com`
  - **Asunto**: `Avería [Referencia adquirida]`
  - **Cuerpo**: Redacción oficial de Joaquín Egea Serrano (Técnico de Electromedicina del Hospital de Alcañiz).

---

## 🚀 Puesta en Marcha en Windows

### 1. Requisitos
- Windows 10 u 11 con Microsoft Outlook 365 instalado.
- Python 3.10+ y Tesseract OCR (instalables fácilmente).

### 2. Ejecución con 1 Clic
Haz doble clic en el archivo:
```bat
iniciar_app.bat
```
El script instalará automáticamente las dependencias si faltan y abrirá la aplicación en tu navegador en:
👉 `http://localhost:8000`

---

## 🌐 Estructura del Repositorio

```text
├── app.py                     # Servidor FastAPI y endpoints REST
├── config.json                # Configuración de destinatarios y plantillas
├── requirements.txt           # Dependencias de Python
├── iniciar_app.bat            # Lanzador de Windows en 1 clic
├── services/
│   ├── ocr_service.py         # Motor OCR y extracción de S/N y REF
│   ├── email_service.py       # Envío por Outlook 365 y plantillas HTML
│   └── config_service.py      # Gestión de ajustes
├── templates/
│   └── index.html             # Interfaz web responsiva moderna
└── tests/
    ├── test_services.py       # Tests unitarios para OCR y plantillas
    └── test_api.py            # Tests de integración para endpoints
```

---

## ☁️ ¿Se puede alojar en la Nube (GitHub / Servidor Web)?

Sí. Si se aloja en un servidor Linux/Cloud (como GitHub Codespaces, Azure, Render o Docker):
1. **El motor de OCR y la Web** funcionan de forma idéntica en cualquier sistema operativo.
2. **Para el envío de correo desde la nube**: En lugar de la sesión local de Outlook (que requiere Windows), se utiliza el modo **SMTP Office 365** (`smtp.office365.com`) o **Microsoft Graph API**, configurable desde el panel de ajustes.
