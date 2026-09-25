import os
import re
import io
import json
import base64
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
    def _extract_with_gemini_vision(cls, image_bytes: bytes, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Extracts S/N and REF with near 100% precision using Google Gemini Flash Vision API.
        """
        if not api_key:
            return None

        try:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

            prompt = (
                "Eres un experto en lectura de etiquetas técnicas de electromedicina y mantenimiento hospitalario.\n"
                "Analiza la imagen de la etiqueta adjunta con máxima precisión y extrae:\n"
                "1. 'serial_number': El Número de Serie exacto (identificado como S/N, SN, Serial Number, Nº Serie, etc.).\n"
                "2. 'ref_number': El Número de Referencia o Modelo (identificado como REF, Reference, Model, Service#, etc.).\n"
                "3. 'candidates': Lista con números de serie adicionales o códigos secundarios si los hay.\n"
                "4. 'ref_candidates': Lista con referencias o códigos de modelo secundarios si los hay.\n\n"
                "Responde ÚNICAMENTE un JSON válido con esta estructura exacta:\n"
                "{\n"
                '  "serial_number": "...",\n'
                '  "ref_number": "...",\n'
                '  "candidates": ["..."],\n'
                '  "ref_candidates": ["..."],\n'
                '  "confidence": "high"\n'
                "}\n"
                "Si algún campo no aparece en la imagen, déjalo como cadena vacía \"\"."
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

            resp = requests.post(url, json=payload, timeout=12)
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

                            return {
                                "success": True,
                                "serial_number": sn,
                                "ref_number": ref,
                                "candidates": all_sn_cand,
                                "ref_candidates": all_ref_cand,
                                "barcodes": [],
                                "extracted_text": f"Google Gemini Vision Detection:\nS/N: {sn}\nREF: {ref}",
                                "confidence": "high",
                                "engine": "gemini_vision",
                                "message": f"IA Gemini Detectado: {' | '.join(msg_parts)}"
                            }
            else:
                print(f"Gemini Vision API status {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"Gemini Vision error: {e}. Falling back to local OCR pipeline.")

        return None

    @staticmethod
    def _find_label_crops(image: Image.Image) -> List[Image.Image]:
        """
        Uses contour detection to find the most prominent rectangular label regions
        in addition to the full image.
        """
        crops = [image]
        if not CV2_AVAILABLE:
            return crops

        try:
            img_np = np.array(image.convert("RGB"))
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            h_img, w_img = gray.shape

            # Adaptive threshold for finding label boxes
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 5)
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            candidate_boxes = []
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if (w > w_img * 0.18 and h > h_img * 0.03 and (w * h) < (w_img * h_img * 0.85)):
                    candidate_boxes.append((w * h, x, y, w, h))

            candidate_boxes.sort(key=lambda item: item[0], reverse=True)
            for _, x, y, w, h in candidate_boxes[:4]:
                pad_x = int(w * 0.05)
                pad_y = int(h * 0.05)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(w_img, x + w + pad_x)
                y2 = min(h_img, y + h + pad_y)
                crop_arr = img_np[y1:y2, x1:x2]
                crops.append(Image.fromarray(crop_arr))
        except Exception as e:
            print(f"Label crop error: {e}")

        return crops

    @staticmethod
    def _preprocess_crop(crop_img: Image.Image) -> List[Image.Image]:
        """Prepares high-resolution grayscale and enhanced variations for a crop."""
        variations = []
        w, h = crop_img.size
        
        if w < 1200 or h < 600:
            scale = max(2.0, 1400.0 / max(w, h))
            scaled = crop_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        else:
            scaled = crop_img

        gray = scaled.convert("L")
        
        # 1. High contrast grayscale
        enhancer = ImageEnhance.Contrast(gray)
        high_c = enhancer.enhance(1.8)
        variations.append(high_c)

        # 2. Sharpened
        sharpened = high_c.filter(ImageFilter.SHARPEN)
        variations.append(sharpened)

        return variations

    @staticmethod
    def _read_barcodes(image: Image.Image) -> List[Dict[str, str]]:
        """Extracts and filters barcodes/QR codes that actually contain a Serial Number."""
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
        except Exception as e:
            print(f"Barcode decode warning: {e}")
            
        return valid_barcodes

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalizes OCR misrecognized characters in S/N and REF headers.
        """
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
    def _extract_text_tesseract(image: Image.Image) -> Tuple[str, List[str]]:
        """Extracts raw text across candidate label regions and variations."""
        if not PYTESSERACT_AVAILABLE:
            return "", []

        crops = OCRService._find_label_crops(image)
        all_passes = []

        for crop in crops:
            variations = OCRService._preprocess_crop(crop)
            for var in variations:
                for psm in [6, 11, 3]:
                    try:
                        config = f"--oem 3 --psm {psm}"
                        text = pytesseract.image_to_string(var, config=config)
                        if text.strip():
                            all_passes.append(text)
                    except Exception:
                        pass

        combined_text = "\n".join(all_passes)
        return combined_text, all_passes

    @staticmethod
    def _parse_serial_numbers(text_passes: List[str]) -> List[Dict[str, Any]]:
        """
        Parses text specifically searching for the exact requested keys.
        """
        regex_patterns = [
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
        """
        Parses text specifically searching for the 'REF' / 'REFERENCE' / 'REFERENCIA' key.
        """
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
        Main entrypoint:
        1. If Gemini API Key is provided, uses Google Gemini Vision (highest accuracy).
        2. Fallback to local Tesseract OCR and OpenCV pipeline.
        """
        effective_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if effective_key:
            gemini_result = cls._extract_with_gemini_vision(image_bytes, effective_key.strip())
            if gemini_result and gemini_result.get("success"):
                return gemini_result

        result = {
            "success": False,
            "serial_number": "",
            "ref_number": "",
            "candidates": [],
            "ref_candidates": [],
            "barcodes": [],
            "extracted_text": "",
            "confidence": "none",
            "message": ""
        }

        try:
            image = Image.open(io.BytesIO(image_bytes))
            try:
                image = ImageOps.exif_transpose(image)
            except Exception:
                pass

            # 1. Barcode scanning
            barcodes = cls._read_barcodes(image)
            result["barcodes"] = barcodes

            # 2. OCR text extraction across candidate regions
            combined_text, passes = cls._extract_text_tesseract(image)
            result["extracted_text"] = combined_text

            # 3. Parse Serial Numbers
            candidates = cls._parse_serial_numbers(passes if passes else [combined_text])

            # 4. Parse REF numbers
            ref_candidates = cls._parse_ref_numbers(passes if passes else [combined_text])
            result["ref_candidates"] = [r["value"] for r in ref_candidates]
            if ref_candidates:
                result["ref_number"] = ref_candidates[0]["value"]

            # 5. Integrate valid Barcodes
            for b in barcodes:
                b_val = b["data"].strip().upper()
                if len(b_val) >= 3 and b_val not in [c["value"] for c in candidates]:
                    candidates.append({
                        "value": b_val,
                        "score": 150,
                        "source": f"Código ({b['type']})",
                        "match": f"Código ({b['type']}): {b_val}"
                    })

            result["candidates"] = [c["value"] for c in candidates]

            if candidates:
                result["serial_number"] = candidates[0]["value"]
                result["success"] = True
                result["confidence"] = "high" if candidates[0]["score"] >= 200 else "medium"
                
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
                result["message"] = f"Detectado desde código de barras: {result['serial_number']}"
            else:
                result["success"] = False
                result["confidence"] = "low"
                result["message"] = "No se encontró S/N o REF en la imagen. Puede ingresarlo manualmente."

        except Exception as e:
            result["success"] = False
            result["message"] = f"Error al procesar la imagen: {str(e)}"

        return result
