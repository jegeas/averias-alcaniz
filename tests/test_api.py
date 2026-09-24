import os
import sys
import io
import requests
from PIL import Image, ImageDraw

def test_api():
    # Create image
    img = Image.new("RGB", (500, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "EQUIPO MEDICO HOSPITALARIO", fill=(0, 0, 0))
    draw.text((20, 60), "S/N: HOSP-2026-99381-Z", fill=(0, 0, 0))
    draw.text((20, 100), "REF: RX-500", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    files = {'file': ('label.png', buf.getvalue(), 'image/png')}
    response = requests.post("http://127.0.0.1:8000/api/extract-sn", files=files)
    print("Response status:", response.status_code)
    data = response.json()
    print("Response JSON:", data)
    assert data["success"] is True
    assert "HOSP-2026-99381-Z" in data["serial_number"]
    print("API OCR Extraction TEST PASSED!")

if __name__ == "__main__":
    test_api()
