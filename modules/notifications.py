"""
notifications.py — WhatsApp + Email notification system
"""

import smtplib, threading, time, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = "your_email@gmail.com"       # ← Change
SMTP_PASSWORD = "your_app_password"          # ← Gmail App Password
SHOP_NAME     = "MUDIT COMPUTERS"
SHOP_PHONE    = "+91-XXXXXXXXXX"
SHOP_ADDRESS  = "Your Shop Address, Kanpur"

STATUS_MESSAGES = {
    "Received":               "✅ {name} ji, aapka {item} hamare paas received ho gaya. Claim #{claim_id}. Jald update milega. — {shop}",
    "Diagnosis In Progress":  "🔍 {name} ji, aapke {item} (#{claim_id}) ki diagnosis chal rahi hai. — {shop}",
    "Awaiting Parts":         "⏳ {name} ji, aapke {item} (#{claim_id}) ke parts order ho gaye hain. — {shop}",
    "Sent to Dealer":         "📦 {name} ji, aapka {item} (#{claim_id}) service center bhej diya gaya. 5-7 din lagenge. — {shop}",
    "Under Repair":           "🔧 {name} ji, aapke {item} (#{claim_id}) ki repair shuru ho gayi! — {shop}",
    "Repaired":               "🎉 {name} ji, aapka {item} (#{claim_id}) REPAIR ho gaya! Pickup ke liye aayein: {address} — {shop}",
    "Quality Check":          "🔬 {name} ji, aapka {item} (#{claim_id}) quality check mein hai. Kal tak ready! — {shop}",
    "Ready for Pickup":       "📱 {name} ji, aapka {item} (#{claim_id}) READY FOR PICKUP! Aaj aayein: {address}. — {shop}",
    "Delivered":              "🙏 Shukriya {name} ji! Aapka {item} (#{claim_id}) deliver ho gaya. Review dein! — {shop}",
    "Cancelled":              "ℹ️ {name} ji, claim #{claim_id} cancel ho gaya. Details: {phone}. — {shop}",
}

def build_message(status, name, item, claim_id):
    t = STATUS_MESSAGES.get(status,
        "Hello {name}! {item} (#{claim_id}) status: {status}. — {shop}")
    return t.format(name=name, item=item, claim_id=claim_id,
                    status=status, shop=SHOP_NAME,
                    phone=SHOP_PHONE, address=SHOP_ADDRESS)

def send_email(to_email, subject, html_body):
    if not to_email or "@" not in to_email:
        return {"success": False, "error": "Invalid email"}
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{SHOP_NAME} <{SMTP_USER}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls(); s.login(SMTP_USER, SMTP_PASSWORD)
            s.sendmail(SMTP_USER, to_email, msg.as_string())
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_whatsapp(phone, message):
    try:
        import pywhatkit as pwk
        phone = phone.strip().replace(" ","").replace("-","")
        if not phone.startswith("+"): phone = "+91" + phone
        now = time.localtime()
        h, m = now.tm_hour, now.tm_min + 2
        if m >= 60: h += 1; m -= 60
        pwk.sendwhatmsg(phone, message, h, m, wait_time=15, tab_close=True, close_time=5)
        return {"success": True}
    except ImportError:
        return {"success": False, "error": "pywhatkit not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_notification(claim_id, customer_name, customer_phone,
                       customer_email, item_name, new_status, tech_note=None):
    from modules.database import log_notification
    message = build_message(new_status, customer_name, item_name, claim_id)
    subject = f"[{SHOP_NAME}] {item_name} — {new_status}"
    html = f"""<html><body style="font-family:Arial;background:#f5f5f5;padding:20px">
    <div style="max-width:500px;margin:auto;background:#fff;border-radius:12px;overflow:hidden">
    <div style="background:#0f1e35;padding:20px;text-align:center">
        <h2 style="color:#fff;margin:0">🖥️ {SHOP_NAME}</h2>
        <p style="color:#93c5fd;margin:4px 0">Service Update</p>
    </div>
    <div style="padding:24px">
        <h3 style="color:#0f1e35">Status: <span style="color:#1d4ed8">{new_status}</span></h3>
        <p style="color:#374151">{message}</p>
        {'<div style="background:#f0f7ff;padding:12px;border-left:4px solid #2563eb;border-radius:4px;margin-top:12px"><b>Note:</b> '+tech_note+'</div>' if tech_note else ''}
        <div style="background:#f8fafc;padding:14px;border-radius:8px;margin-top:16px;font-size:13px">
            <b>Claim ID:</b> #{claim_id} &nbsp;|&nbsp; <b>Device:</b> {item_name}
        </div>
    </div>
    <div style="background:#f0f4ff;padding:14px;text-align:center;font-size:12px;color:#6b7280">
        {SHOP_ADDRESS} | {SHOP_PHONE}
    </div></div></body></html>"""

    if customer_email:
        r = send_email(customer_email, subject, html)
        log_notification(claim_id, None, "email", message,
                         "sent" if r["success"] else "failed")

    def _wa():
        r = send_whatsapp(customer_phone, message)
        log_notification(claim_id, None, "whatsapp", message,
                         "sent" if r["success"] else "failed")
    threading.Thread(target=_wa, daemon=True).start()
