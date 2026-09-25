import os
import sys
import io
import unittest
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.config_service import ConfigService
from services.ocr_service import OCRService
from services.email_service import EmailService


class TestAppServices(unittest.TestCase):
    def test_config_service(self):
        config = ConfigService.load_config()
        self.assertIn("default_recipient", config)
        self.assertIn("subject_prefix", config)
        self.assertIn("email_method", config)

    def test_email_html_generation(self):
        sn = "TEST-SN-998877"
        ref = "862199 M2703A"
        text = "Equipo revisado correctamente en planta 3."
        html = EmailService.generate_html_body(sn, text, ref=ref, has_attachment=True)
        self.assertIn("TEST-SN-998877", html)
        self.assertIn("862199 M2703A", html)
        self.assertIn("Referencia (REF)", html)
        self.assertIn("Equipo revisado correctamente", html)
        self.assertIn("Aviso de Avería", html)
        self.assertIn("Joaquín Egea Serrano", html)

    def test_ocr_extraction_sn_and_ref(self):
        img = Image.new("RGB", (600, 250), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 30), "PHILIPS MEDICAL", fill=(0, 0, 0))
        draw.text((20, 70), "REF: 862199 M2703A", fill=(0, 0, 0))
        draw.text((20, 120), "SN: DE78743189", fill=(0, 0, 0))
        draw.text((20, 170), "Service# 862199", fill=(0, 0, 0))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = OCRService.extract_from_image_bytes(buf.getvalue())
        print("\n[TEST SN + REF RESULT]:", result)
        self.assertTrue(result["success"])
        self.assertIn("DE78743189", result["serial_number"])
        self.assertTrue("862199" in result["ref_number"])

    def test_ocr_extraction_serial_number(self):
        img = Image.new("RGB", (600, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 30), "DEVICE TAG", fill=(0, 0, 0))
        draw.text((20, 80), "Serial Number: SER-99381-Z", fill=(0, 0, 0))
        draw.text((20, 130), "REF: 5040-A", fill=(0, 0, 0))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = OCRService.extract_from_image_bytes(buf.getvalue())
        print("\n[TEST SERIAL NUMBER RESULT]:", result)
        self.assertTrue(result["success"])
        self.assertIn("SER-99381-Z", result["serial_number"])
        self.assertIn("5040-A", result["ref_number"])


if __name__ == "__main__":
    unittest.main()
