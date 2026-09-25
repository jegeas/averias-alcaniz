import os
import re
import io
import json
import base64
import time
import requests
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np

# Optional OpenCV
try:
    import cv2
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False

# Optional barcode scanning
try:
    from pyzbar.pyzbar import decode as decode_barcode
    PYZBAR_AVAILABLE = True
except Exception:
    PYZBAR_AVAILABLE = False

# Optional pytesseract
try:
    import pytesseract
    tesseract_candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for cand in tesseract_candidates:
        if os.path.exists(cand):
            pytesseract.pytesseract.tesseract_cmd = cand
            break
    PYTESSERACT_AVAILABLE = True
except Exception:
    PYTESSERACT_AVAILABLE = False


class OCRService:
    @classmethod
    def _extract_with_gemini_vision(cls, image_bytes: bytes, api_key: str, logs: List[str]) -> Optional[Dict[str, Any]]:
        """
        Extracts S/N and REF using Google Gemini Vision API.
        """
        clean_key = (api_key or "").strip()
        if not clean_key:
            logs.append("[INFO] Gemini: No se ha configurado API Key.")
            return None

        if not clean_key.startswith("AIzaSy"):
            logs.append(f"[AVISO] Gemini: La API Key configurada ('{clean_key[:8]}...') no es valida. Las claves oficiales de Google empiezan por 'AIzaSy'.")
            return None

        logs.append("[INICIO] Gemini: Enviando imagen al modelo Google Gemini 1.5/2.0 Flash Vision...")
        t0 = time.time()

        try:
            img = Image.open(io.BytesIO(image_bytes))
            w, h = img.size
            if max(w, h) > 1600:
                scale = 1600.0 / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=85)
                payload_bytes = buf.getvalue()
            else:
                payload_bytes = image_bytes

            b64_image = base64.b64encode(payload_bytes).decode("utf-8")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"

            prompt = (
                "Eres un experto en lectura e inventario de etiquetas de electromedicina y equipamiento hospitalario.\n"
                "Analiza la imagen de la etiqueta adjunta con maxima precision y extrae:\n"
                "1. 'serial_number': El Numero de Serie exacto (identificado como S/N, SN, Serial Number, Nº Serie, o en el codigo UDI / (21)).\n"
                "2. 'ref_number': El Numero de Referencia o Modelo (identificado como REF, Reference, Model, Service#, etc.).\n"
                "3. 'candidates': Lista con numeros de serie alternativos si los hay.\n"
                "4. 'ref_candidates': Lista con referencias o codigos de modelo alternativos si los hay.\n\n"
                "Responde UNICAMENTE un JSON valido con esta estructura exacta:\n"
                "{\n"
                '  "serial_number": "...",\n'
                '  "ref_number": "...",\n'
                '  "candidates": ["..."],\n'
                '  "ref_candidates": ["..."],\n'
                '  "confidence": "high"\n'
                "}\n"
                "Si algun campo no aparece en la imagen, dejalo como cadena vacia \"\"."
            )

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inlineData": {
                                    "mimeType": "image/jpeg",
                                    "data": b64_image
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.0
                }
            }

            resp = requests.post(url, json=payload, timeout=8)
            elapsed = round(time.time() - t0, 2)

            if resp.status_code == 200:
                data = resp.json()
                candidates_obj = data.get("candidates", [])
                if candidates_obj and "content" in candidates_obj[0]:
                    parts = candidates_obj[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        raw_text = parts[0]["text"].strip()
                        if raw_text.startswith("```"):
                            raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
                            raw_text = re.sub(r"\n?```$", "", raw_text)
                        parsed = json.loads(raw_text)

                        sn = str(parsed.get("serial_number", "")).strip()
                        ref = str(parsed.get("ref_number", "")).strip()
                        cand = parsed.get("candidates", [])
                        ref_cand = parsed.get("ref_candidates", [])

                        if sn or ref:
                            all_sn_cand = ([sn] if sn else []) + [c for c in cand if c and c != sn]
                            all_ref_cand = ([ref] if ref else []) + [r for r in ref_cand if r and r != ref]

                            msg_parts = []
                            if sn:
                                msg_parts.append(f"S/N: {sn}")
                            if ref:
                                msg_parts.append(f"REF: {ref}")

                            logs.append(f"[OK] Gemini: Respuesta exitosa en {elapsed}s. S/N: {sn} | REF: {ref}")

                            return {
                                "success": True,
                                "serial_number": sn,
                                "ref_number": ref,
                                "candidates": all_sn_cand,
                                "ref_candidates": all_ref_cand,
                                "barcodes": [],
                                "extracted_text": f"Google Gemini Vision ({elapsed}s):\nS/N: {sn}\nREF: {ref}",
                                "confidence": "high",
                                "engine": "gemini_vision",
                                "message": f"IA Gemini Detectado: {' | '.join(msg_parts)}",
                                "elapsed_time": elapsed,
                                "logs": logs
                            }
            else:
                logs.append(f"[AVISO] Gemini: Error HTTP {resp.status_code} ({resp.text[:100]}). Usando motor local de respaldo...")
        except Exception as e:
            logs.append(f"[AVISO] Gemini: Excepcion ({str(e)}). Usando motor local de respaldo...")

        return None

    @staticmethod
    def _read_barcodes(image: Image.Image, logs: List[str]) -> List[Dict[str, str]]:
        """Extracts and filters barcodes/QR codes."""
        valid_barcodes = []
        if not PYZBAR_AVAILABLE:
            return valid_barcodes
        
        try:
            decoded = decode_barcode(image)
            for item in decoded:
                raw_data = item.data.decode("utf-8", errors="ignore").strip()
                btype = item.type
                
                if "NSerie" in raw_data and not re.search(r"(?i)NSerie\s*[:=\s#-]+\s*([A-Za-z0-9\-_]+)", raw_data):
                    sn_match = re.search(r"(?i)(?:SN|S/N|NSerie)\s*[:=\s#-]+\s*([A-Za-z0-9\-_]+)", raw_data)
                    if sn_match:
                        valid_barcodes.append({"type": btype, "data": sn_match.group(1).strip()})
                    continue

                if raw_data:
                    valid_barcodes.append({"type": btype, "data": raw_data})
                    logs.append(f"[CODIGO] Detectado ({btype}): {raw_data}")
        except Exception as e:
            pass
            
        return valid_barcodes

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalizes OCR misrecognized characters."""
        normalized = text
        normalized = re.sub(r"(?i)(?:[\\\|\(\[\{]|\b)SN[\\\|\)\]\}]", "SN: ", normalized)
        normalized = re.sub(r"(?i)(?:[\\\|\(\[\{]|\b)S\s*[\/\.]\s*N[\\\|\)\]\}]", "S/N: ", normalized)
        normalized = re.sub(r"(?i)(?:[\\\|\(\[\{]|\b)REF[\\\|\)\]\}]", "REF: ", normalized)
        normalized = re.sub(r"(?i)\bS[I1|l!]\s*[\/\.,;: -]\s*N\b", "S/N", normalized)
        normalized = re.sub(r"(?i)\bS[I1|l!]\s*N\b", "SN", normalized)
        normalized = re.sub(r"(?i)\bSerial\s*(?:Number|No\.?|Num\.?|#)?\b", "Serial Number", normalized)
        normalized = re.sub(r"(?i)\bN[a-zA-Z0-9º°\.\-\/]*\s*(?:de\s+)?serie\b", "S/N", normalized)
        return normalized

    @staticmethod
    def _extract_text_tesseract_fast(image: Image.Image, logs: List[str]) -> Tuple[str, List[str]]:
        """Fast, single-pass OCR optimized for cloud/containers."""
        if not PYTESSERACT_AVAILABLE:
            logs.append("[AVISO] Tesseract no esta instalado en este sistema.")
            return "", []

        t0 = time.time()
        passes = []

        try:
            w, h = image.size
            scale = max(1.0, 1400.0 / max(w, h)) if max(w, h) < 1400 else 1.0
            if scale > 1.0:
                scaled = image.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)
            else:
                scaled = image

            gray = scaled.convert("L")
            enhancer = ImageEnhance.Contrast(gray)
            high_c = enhancer.enhance(1.6)

            text1 = pytesseract.image_to_string(high_c, config="--oem 3 --psm 6")
            if text1.strip():
                passes.append(text1)

            text2 = pytesseract.image_to_string(high_c, config="--oem 3 --psm 11")
            if text2.strip():
                passes.append(text2)

            elapsed = round(time.time() - t0, 2)
            logs.append(f"[TESSERACT] Analisis local completado en {elapsed}s.")
        except Exception as e:
            logs.append(f"[ERROR] Error en Tesseract: {e}")

        combined = "\n".join(passes)
        return combined, passes

    @staticmethod
    def _parse_serial_numbers(text_passes: List[str]) -> List[Dict[str, Any]]:
        regex_patterns = [
            (r"(?i)\(21\)\s*([A-Za-z0-9\-_./]{4,25})", 450, "UDI (21) S/N"),
            (r"(?i)\bS\s*[\/\.]\s*N[ \t]*[\.:=\s#-]+[ \t]*([A-Za-z0-9\-_./]+)", 350, "S/N"),
            (r"(?i)\bSerial(?:[ \t]*(?:Number|Numbers|No|Num|#))?[ \t]*[\.:=\s#-]+[ \t]*([A-Za-z0-9\-_./]+)", 350, "Serial Number"),
            (r"(?i)\bSN[ \t]*[\.:=\s#-]+[ \t]*([A-Za-z0-9\-_./]+)", 350, "SN"),
            (r"(?i)\((?:21|S)\)[ \t]*([A-Za-z0-9\-_./]{3,25})", 250, "(21) SN"),
            (r"(?i)\bSN([0-9][A-Za-z0-9\-_]{3,25})\b", 200, "SN prefix"),
        ]

        candidate_scores: Dict[str, int] = {}
        candidate_matches: Dict[str, str] = {}
        candidate_sources: Dict[str, str] = {}
        stop_words = ["the", "and", "para", "date", "fecha", "made", "spain", "china", "germany", "device", "inc", "ltd", "ref", "model", "modelo", "service", "salud", "hospital"]

        for raw_pass in text_passes:
            normalized_pass = OCRService._normalize_text(raw_pass)
            lines = normalized_pass.splitlines()

            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue

                for pattern, base_score, source_label in regex_patterns:
                    for match in re.finditer(pattern, line_str):
                        raw_val = match.group(1).strip()
                        clean_val = re.sub(r"\s+", "", raw_val)
                        clean_val = re.sub(r"^[^\w]+|[^\w]+$", "", clean_val).upper()

                        for sw in ["REF", "FECHA", "MOD", "MODEL", "DATE", "MADE", "COD", "LOTE", "LOT", "BATCH", "SERVICE", "GS1"]:
                            if sw in clean_val and not clean_val.startswith(sw):
                                clean_val = clean_val.split(sw)[0].strip()

                        if len(clean_val) >= 3 and clean_val.lower() not in stop_words:
                            current_score = candidate_scores.get(clean_val, 0)
                            candidate_scores[clean_val] = current_score + base_score
                            if clean_val not in candidate_matches:
                                candidate_matches[clean_val] = match.group(0).strip()
                                candidate_sources[clean_val] = source_label

        candidates = []
        for val, score in candidate_scores.items():
            candidates.append({
                "value": val,
                "score": score,
                "source": candidate_sources.get(val, "S/N"),
                "match": candidate_matches.get(val, val)
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

    @staticmethod
    def _parse_ref_numbers(text_passes: List[str]) -> List[Dict[str, Any]]:
        ref_patterns = [
            r"(?i)(?:[\\\|\(\[\{]|\b)REF[\\\|\)\]\}]?[ \t]*[\.:=\s#-]+[ \t]*([A-Za-z0-9\-_./]+(?:[ \t]+[A-Za-z0-9\-_./]+)?)",
            r"(?i)\bReferenc(?:e|ia)[ \t]*[\.:=\s#-]+[ \t]*([A-Za-z0-9\-_./]+(?:[ \t]+[A-Za-z0-9\-_./]+)?)"
        ]

        candidate_scores: Dict[str, int] = {}
        candidate_matches: Dict[str, str] = {}
        stop_words = ["the", "and", "para", "date", "fecha", "made", "spain", "china", "germany", "device", "inc", "ltd", "sn", "s/n", "service", "salud", "hospital"]

        for raw_pass in text_passes:
            normalized_pass = OCRService._normalize_text(raw_pass)
            lines = normalized_pass.splitlines()

            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue

                for pattern in ref_patterns:
                    for match in re.finditer(pattern, line_str):
                        raw_val = match.group(1).strip()
                        clean_val = re.sub(r"^[^\w]+|[^\w]+$", "", raw_val).strip()

                        for sw in ["SN", "S/N", "SERVICE", "GS1", "DATE", "FECHA", "LOT", "BATCH", "MADE"]:
                            match_sw = re.search(rf"(?i)\b{sw}\b", clean_val)
                            if match_sw and match_sw.start() > 0:
                                clean_val = clean_val[:match_sw.start()].strip()

                        clean_val = re.sub(r"^[^\w]+|[^\w]+$", "", clean_val).strip().upper()

                        if len(clean_val) >= 2 and clean_val.lower() not in stop_words:
                            candidate_scores[clean_val] = candidate_scores.get(clean_val, 0) + 10
                            if clean_val not in candidate_matches:
                                candidate_matches[clean_val] = match.group(0).strip()

        candidates = []
        for val, score in candidate_scores.items():
            candidates.append({
                "value": val,
                "score": score,
                "match": candidate_matches.get(val, val)
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

    @classmethod
    def extract_from_image_bytes(cls, image_bytes: bytes, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entrypoint with diagnostics & fast execution.
        """
        logs = [f"[IMAGEN] Recibida ({len(image_bytes) // 1024} KB)."]
        effective_key = (api_key or "").strip() or os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()

        # 1. Attempt Gemini Vision if key provided
        if effective_key:
            gemini_result = cls._extract_with_gemini_vision(image_bytes, effective_key, logs)
            if gemini_result and gemini_result.get("success"):
                return gemini_result

        # 2. Fast Local OCR Fallback
        logs.append("[LOCAL] Ejecutando pipeline de vision local...")
        result = {
            "success": False,
            "serial_number": "",
            "ref_number": "",
            "candidates": [],
            "ref_candidates": [],
            "barcodes": [],
            "extracted_text": "",
            "confidence": "none",
            "engine": "local_tesseract",
            "message": "",
            "logs": logs
        }

        try:
            image = Image.open(io.BytesIO(image_bytes))
            try:
                image = ImageOps.exif_transpose(image)
            except Exception:
                pass

            # 2a. Barcodes
            barcodes = cls._read_barcodes(image, logs)
            result["barcodes"] = barcodes

            # 2b. Fast Tesseract
            combined_text, passes = cls._extract_text_tesseract_fast(image, logs)
            result["extracted_text"] = combined_text

            # 2c. Parse S/N and REF
            candidates = cls._parse_serial_numbers(passes if passes else [combined_text])
            ref_candidates = cls._parse_ref_numbers(passes if passes else [combined_text])

            result["ref_candidates"] = [r["value"] for r in ref_candidates]
            if ref_candidates:
                result["ref_number"] = ref_candidates[0]["value"]
                logs.append(f"[REF] Detectada: {result['ref_number']}")

            for b in barcodes:
                b_val = b["data"].strip().upper()
                if len(b_val) >= 3 and b_val not in [c["value"] for c in candidates]:
                    candidates.append({
                        "value": b_val,
                        "score": 150,
                        "source": f"Codigo ({b['type']})",
                        "match": f"Codigo ({b['type']}): {b_val}"
                    })

            result["candidates"] = [c["value"] for c in candidates]

            if candidates:
                result["serial_number"] = candidates[0]["value"]
                result["success"] = True
                result["confidence"] = "high" if candidates[0]["score"] >= 200 else "medium"
                logs.append(f"[SN] Detectado: {result['serial_number']}")
                
                msg_parts = [f"S/N: {result['serial_number']}"]
                if result["ref_number"]:
                    msg_parts.append(f"REF: {result['ref_number']}")
                result["message"] = f"Detectado: {' | '.join(msg_parts)}"

            elif result["ref_number"]:
                result["success"] = True
                result["confidence"] = "medium"
                result["message"] = f"Referencia detectada (REF): {result['ref_number']}"
            elif barcodes:
                result["serial_number"] = barcodes[0]["data"]
                result["success"] = True
                result["confidence"] = "high"
                result["message"] = f"Detectado desde codigo de barras: {result['serial_number']}"
            else:
                result["success"] = False
                result["confidence"] = "low"
                result["message"] = "No se encontro S/N o REF automaticamente. Ingreselo manualmente."
                logs.append("[INFO] No se detectaron patrones coincidentes.")

        except Exception as e:
            result["success"] = False
            result["message"] = f"Error al procesar la imagen: {str(e)}"
            logs.append(f"[ERROR] {e}")

        result["logs"] = logs
        return result
