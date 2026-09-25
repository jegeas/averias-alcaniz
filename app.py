import os
import sys
import base64
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.config_service import ConfigService
from services.ocr_service import OCRService
from services.email_service import EmailService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(title="S/N Extractor & Mail App", description="Extracción de Número de Serie y Envío de Correo vía Outlook 365")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


class ConfigUpdateRequest(BaseModel):
    default_recipient: Optional[str] = None
    subject_prefix: Optional[str] = None
    default_body_template: Optional[str] = None
    attach_image: Optional[bool] = True
    email_method: Optional[str] = "outlook_com"
    smtp_host: Optional[str] = "smtp.office365.com"
    smtp_port: Optional[int] = 587
    smtp_user: Optional[str] = ""
    smtp_password: Optional[str] = ""
    gemini_api_key: Optional[str] = ""


import socket

def get_local_ip() -> str:
    """Detects the primary LAN IPv4 address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    config = ConfigService.load_config()
    local_ip = get_local_ip()
    port = config.get("port", 8000)
    mobile_url = f"http://{local_ip}:{port}"
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"config": config, "local_ip": local_ip, "mobile_url": mobile_url}
    )


@app.get("/api/network-info")
async def get_network_info():
    local_ip = get_local_ip()
    config = ConfigService.load_config()
    port = config.get("port", 8000)
    return {
        "local_ip": local_ip,
        "port": port,
        "mobile_url": f"http://{local_ip}:{port}"
    }


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)

@app.get("/api/config")
async def get_config():
    return ConfigService.load_config()


@app.post("/api/config")
async def update_config(payload: ConfigUpdateRequest):
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = ConfigService.save_config(update_data)
    return {"success": True, "config": updated}


@app.post("/api/extract-sn")
async def extract_sn(file: UploadFile = File(...)):
    """Extracts Serial Number and Barcode from uploaded image."""
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="El archivo subido está vacío.")
        
        config = ConfigService.load_config()
        api_key = config.get("gemini_api_key", None)
        result = OCRService.extract_from_image_bytes(contents, api_key=api_key)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error procesando imagen: {str(e)}", "serial_number": ""}
        )


@app.post("/api/send-email")
async def send_email(
    sn: str = Form(""),
    ref: str = Form(""),
    text: str = Form(""),
    recipient: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    attach_image: bool = Form(True),
    file: Optional[UploadFile] = File(None)
):
    """Sends the formatted email with S/N, REF, notes, and attachment."""
    config = ConfigService.load_config()

    target_recipient = (recipient or "").strip() or config.get("default_recipient", "").strip()
    if not target_recipient:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Debe especificar una dirección de correo electrónico de destino."}
        )

    # Subject formatting based on REF (or S/N fallback)
    prefix = config.get("subject_prefix", "[Aviso de Equipo]").strip()
    clean_sn = sn.strip()
    clean_ref = ref.strip()

    if not subject or not subject.strip():
        if clean_ref:
            target_subject = f"{prefix} {clean_ref}".strip()
        elif clean_sn:
            target_subject = f"{prefix} S/N: {clean_sn}".strip()
        else:
            target_subject = f"{prefix} Aviso de Equipo".strip()
    else:
        target_subject = subject.strip()

    # Process image bytes if attached
    image_bytes = None
    image_name = "foto_equipo.jpg"
    if attach_image and file:
        try:
            image_bytes = await file.read()
            if file.filename:
                image_name = file.filename
        except Exception as e:
            print(f"Error reading file for attachment: {e}")

    email_method = config.get("email_method", "outlook_com")

    if email_method == "smtp":
        result = EmailService.send_via_smtp(
            to=target_recipient,
            subject=target_subject,
            sn=clean_sn,
            text=text,
            ref=clean_ref,
            smtp_config=config,
            image_bytes=image_bytes,
            image_filename=image_name
        )
    else:
        # Default to local Outlook 365
        result = EmailService.send_via_outlook_com(
            to=target_recipient,
            subject=target_subject,
            sn=clean_sn,
            text=text,
            ref=clean_ref,
            image_bytes=image_bytes,
            image_filename=image_name
        )

    return JSONResponse(content=result)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "SN-Mail-App"}


if __name__ == "__main__":
    import uvicorn
    config = ConfigService.load_config()
    port = int(os.environ.get("PORT", config.get("port", 8000)))
    host = os.environ.get("HOST", config.get("host", "0.0.0.0"))
    uvicorn.run(app, host=host, port=port)
