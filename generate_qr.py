"""
generate_qr.py — QR Code generator for shop counter
Run: python generate_qr.py
Phir static/customer_qr.png print karein aur counter par lagayein.
"""
import socket, os
import qrcode
from PIL import Image, ImageDraw, ImageFont

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def generate_qr(page="submit"):
    ip  = get_local_ip()
    url = f"http://{ip}:5000/{page}"
    print(f"[QR] Generating for: {url}")

    qr = qrcode.QRCode(version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_H,
                        box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f1e35", back_color="white")
    w, h = img.size
    final = Image.new("RGB", (w, h + 70), "white")
    final.paste(img, (0, 0))
    draw = ImageDraw.Draw(final)

    try:
        font_b = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        font_s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except Exception:
        font_b = font_s = ImageFont.load_default()

    draw.text((w//2, h+8),  "MUDIT COMPUTERS",   fill="#0f1e35", font=font_b, anchor="mt")
    draw.text((w//2, h+32), "Scan to Submit Service Request", fill="#64748b", font=font_s, anchor="mt")
    draw.text((w//2, h+50), url, fill="#1d4ed8", font=font_s, anchor="mt")

    out = os.path.join(os.path.dirname(__file__), "static", "customer_qr.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    final.save(out)
    print(f"[QR] ✅ Saved: {out}")
    print(f"[QR]    Print aur counter par lagayein!")

if __name__ == "__main__":
    generate_qr("submit")
    generate_qr("kiosk")   # Kiosk QR bhi banata hai
