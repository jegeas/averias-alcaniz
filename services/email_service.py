import os
import sys
import datetime
import tempfile
import base64
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, Optional

try:
    import win32com.client
    import pythoncom
    WIN32COM_AVAILABLE = True
except Exception:
    WIN32COM_AVAILABLE = False


class EmailService:
    @staticmethod
    def generate_html_body(sn: str, text: str, ref: str = "", has_attachment: bool = False) -> str:
        """Generates the official HTML body for the electromedicine breakdown report."""
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        ref_display = ref.strip() if ref and ref.strip() else "[No especificada]"
        sn_display = sn.strip() if sn and sn.strip() else "[No especificado]"
        desc_display = text.strip() if text and text.strip() else "[Sin descripción detallada]"
        formatted_desc = desc_display.replace("\n", "<br>")

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background-color: #f4f6f9;
            margin: 0;
            padding: 20px;
            color: #2c3e50;
        }}
        .container {{
            max-width: 650px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border: 1px solid #e1e4e8;
        }}
        .header {{
            background: linear-gradient(135deg, #0078d4, #005a9e);
            color: #ffffff;
            padding: 22px 28px;
        }}
        .header h2 {{
            margin: 0;
            font-size: 20px;
            font-weight: 600;
        }}
        .header p {{
            margin: 4px 0 0 0;
            font-size: 13px;
            opacity: 0.9;
        }}
        .content {{
            padding: 28px;
            font-size: 15px;
            line-height: 1.7;
            color: #333333;
        }}
        .intro-paragraph {{
            margin-bottom: 20px;
            line-height: 1.7;
        }}
        .highlight {{
            font-weight: bold;
            color: #005a9e;
        }}
        .equipment-card {{
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-left: 4px solid #0078d4;
            border-radius: 6px;
            padding: 16px 20px;
            margin: 20px 0;
        }}
        .data-row {{
            margin-bottom: 8px;
            font-size: 14px;
        }}
        .data-row:last-child {{
            margin-bottom: 0;
        }}
        .data-label {{
            font-weight: 700;
            color: #475569;
            display: inline-block;
            min-width: 140px;
        }}
        .data-val {{
            font-family: 'Consolas', 'Courier New', monospace;
            font-weight: 700;
            color: #0f172a;
            font-size: 15px;
        }}
        .desc-box {{
            background-color: #fffbeb;
            border: 1px solid #fef3c7;
            border-left: 4px solid #f59e0b;
            border-radius: 6px;
            padding: 14px 18px;
            margin: 18px 0;
            font-size: 14px;
            color: #78350f;
        }}
        .desc-title {{
            font-weight: bold;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
            color: #b45309;
        }}
        .closing {{
            margin-top: 24px;
            line-height: 1.6;
        }}
        .badge-attached {{
            display: inline-block;
            background-color: #e0f2fe;
            color: #0369a1;
            padding: 6px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 16px;
        }}
        .footer {{
            background-color: #f1f5f9;
            text-align: center;
            padding: 14px;
            font-size: 12px;
            color: #64748b;
            border-top: 1px solid #e2e8f0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Aviso de Avería - Electromedicina</h2>
            <p>Hospital de Alcañiz</p>
        </div>
        <div class="content">
            <p class="intro-paragraph">
                Me llamo <strong>Joaquín Egea Serrano</strong>. Soy el técnico de electromedicina del hospital de Alcañiz.
                El motivo del correo es informar de la avería del equipo <span class="highlight">{ref_display}</span> con número de serie <span class="highlight">{sn_display}</span>.
            </p>

            <div class="equipment-card">
                <div class="data-row">
                    <span class="data-label">Referencia (REF):</span>
                    <span class="data-val">{ref_display}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">Nº de Serie (S/N):</span>
                    <span class="data-val">{sn_display}</span>
                </div>
            </div>

            <div class="desc-box">
                <div class="desc-title">Avería detectada</div>
                <div>{formatted_desc}</div>
            </div>

            <div class="closing">
                <p>Quedo a su disposición para resolver cualquier duda.</p>
                <p><strong>Un cordial saludo</strong>,<br>
                Joaquín Egea Serrano<br>
                <em>Técnico de Electromedicina - Hospital de Alcañiz</em></p>
            </div>

            {"<div class='badge-attached'>📎 Se adjunta la fotografía de la etiqueta del equipo</div>" if has_attachment else ""}
        </div>
        <div class="footer">
            Fecha y hora de registro: {now_str}
        </div>
    </div>
</body>
</html>
"""
        return html

    @classmethod
    def send_via_outlook_com(
        cls,
        to: str,
        subject: str,
        sn: str,
        text: str,
        ref: str = "",
        image_bytes: Optional[bytes] = None,
        image_filename: str = "foto_equipo.jpg",
        display_only: bool = False
    ) -> Dict[str, Any]:
        """
        Sends email using the local Outlook 365 client via win32com or PowerShell fallback.
        """
        temp_img_path = None
        try:
            if image_bytes:
                temp_dir = tempfile.gettempdir()
                temp_img_path = os.path.join(temp_dir, f"sn_capture_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                with open(temp_img_path, "wb") as f:
                    f.write(image_bytes)

            html_body = cls.generate_html_body(sn, text, ref=ref, has_attachment=bool(temp_img_path))

            # Method A: Try pythoncom / win32com
            if WIN32COM_AVAILABLE:
                try:
                    pythoncom.CoInitialize()
                    outlook = win32com.client.Dispatch("Outlook.Application")
                    mail = outlook.CreateItem(0)  # 0 = olMailItem
                    mail.To = to
                    mail.Subject = subject
                    mail.HTMLBody = html_body

                    if temp_img_path and os.path.exists(temp_img_path):
                        mail.Attachments.Add(temp_img_path)

                    if display_only:
                        mail.Display(True)
                    else:
                        mail.Send()

                    return {
                        "success": True,
                        "message": f"Correo enviado correctamente vía Outlook a: {to}",
                        "method": "win32com"
                    }
                except Exception as e:
                    print(f"win32com error: {e}. Trying PowerShell COM interop...")
                finally:
                    pythoncom.CoUninitialize()

            # Method B: PowerShell COM Interop Fallback
            ps_script = f"""
$ErrorActionPreference = 'Stop'
$outlook = New-Object -ComObject Outlook.Application
$mail = $outlook.CreateItem(0)
$mail.To = @'
{to}
'@
$mail.Subject = @'
{subject}
'@
$mail.HTMLBody = @'
{html_body}
'@
"""
            if temp_img_path and os.path.exists(temp_img_path):
                escaped_path = temp_img_path.replace("'", "''")
                ps_script += f"\n$mail.Attachments.Add('{escaped_path}')\n"

            if display_only:
                ps_script += "\n$mail.Display()\n"
            else:
                ps_script += "\n$mail.Send()\n"

            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
            if res.returncode == 0:
                return {
                    "success": True,
                    "message": f"Correo enviado correctamente vía Outlook (PowerShell) a: {to}",
                    "method": "powershell_com"
                }
            else:
                return {
                    "success": False,
                    "message": f"Error al enviar desde Outlook: {res.stderr.strip()}",
                    "error": res.stderr
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error general al enviar correo: {str(e)}"
            }
        finally:
            if temp_img_path and os.path.exists(temp_img_path):
                try:
                    os.remove(temp_img_path)
                except Exception:
                    pass

    @classmethod
    def send_via_smtp(
        cls,
        to: str,
        subject: str,
        sn: str,
        text: str,
        smtp_config: Dict[str, Any],
        ref: str = "",
        image_bytes: Optional[bytes] = None,
        image_filename: str = "foto_equipo.jpg"
    ) -> Dict[str, Any]:
        """Sends email via Office 365 SMTP."""
        try:
            host = smtp_config.get("smtp_host", "smtp.office365.com")
            port = int(smtp_config.get("smtp_port", 587))
            user = smtp_config.get("smtp_user", "")
            password = smtp_config.get("smtp_password", "")

            if not user or not password:
                return {
                    "success": False,
                    "message": "Faltan credenciales SMTP (usuario/contraseña) en la configuración."
                }

            msg = MIMEMultipart()
            msg["From"] = user
            msg["To"] = to
            msg["Subject"] = subject

            html_body = cls.generate_html_body(sn, text, ref=ref, has_attachment=bool(image_bytes))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            if image_bytes:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(image_bytes)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{image_filename}"')
                msg.attach(part)

            server = smtplib.SMTP(host, port)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)
            server.sendmail(user, [to], msg.as_string())
            server.quit()

            return {
                "success": True,
                "message": f"Correo enviado exitosamente vía SMTP a: {to}",
                "method": "smtp"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al enviar correo por SMTP: {str(e)}"
            }
