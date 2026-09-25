import json
import os
from typing import Any, Dict

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "default_recipient": "clientes.sistemas.medicos@philips.com",
    "subject_prefix": "Avería",
    "default_body_template": "Se remite la información y número de serie del equipo:\n\n- Número de Serie (S/N): {sn}\n- Observaciones / Incidencia: {text}\n- Fecha y hora de registro: {datetime}",
    "attach_image": True,
    "email_method": "outlook_com",  # "outlook_com" or "smtp"
    "smtp_host": "smtp.office365.com",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
    "port": 8000,
    "host": "0.0.0.0"
}


class ConfigService:
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Loads configuration safely without recursion."""
        config = DEFAULT_CONFIG.copy()
        
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        config.update(data)
        except Exception as e:
            print(f"Error loading config from file: {e}. Using defaults.")

        # Environment variable overrides (useful for Cloud/Render deployment)
        if "PORT" in os.environ:
            try:
                config["port"] = int(os.environ["PORT"])
            except Exception:
                pass
        if "HOST" in os.environ:
            config["host"] = os.environ["HOST"]
        if "DEFAULT_RECIPIENT" in os.environ:
            config["default_recipient"] = os.environ["DEFAULT_RECIPIENT"]
        if "EMAIL_METHOD" in os.environ:
            config["email_method"] = os.environ["EMAIL_METHOD"]
        if "SMTP_HOST" in os.environ:
            config["smtp_host"] = os.environ["SMTP_HOST"]
        if "SMTP_PORT" in os.environ:
            try:
                config["smtp_port"] = int(os.environ["SMTP_PORT"])
            except Exception:
                pass
        if "SMTP_USER" in os.environ:
            config["smtp_user"] = os.environ["SMTP_USER"]
        if "SMTP_PASSWORD" in os.environ:
            config["smtp_password"] = os.environ["SMTP_PASSWORD"]
        if "GEMINI_API_KEY" in os.environ:
            config["gemini_api_key"] = os.environ["GEMINI_API_KEY"].strip()
        elif "GOOGLE_API_KEY" in os.environ:
            config["gemini_api_key"] = os.environ["GOOGLE_API_KEY"].strip()

        return config

    @staticmethod
    def save_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Saves configuration to config.json safely."""
        config = DEFAULT_CONFIG.copy()
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        config.update(data)
        except Exception:
            pass

        config.update(new_config)

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

        return config
