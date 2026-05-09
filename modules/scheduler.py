"""
scheduler.py — Automatic Reminder & Notification System
=========================================================
Ye module background mein chalta rehta hai jab bhi app.py run hoti hai.
Koi manual kaam nahi — sab auto!

Jobs:
  1. dealer_overdue_check   → Har 6 ghante: overdue dealer items pe WhatsApp
  2. customer_ready_alert   → Har 1 ghante: "Ready for Pickup" customers ko reminder
  3. daily_admin_summary    → Roz 9:00 AM: admin ko din ka briefing
  4. dealer_followup        → Har 12 ghante: dealer ko "status batao" message
"""

import logging
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

log = logging.getLogger("scheduler")
logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
                    datefmt="%H:%M:%S")

# ── Import lazy to avoid circular imports ─────────────────────────────────────
def _db():
    from modules.database import get_db
    return get_db()

def _wa(phone, msg):
    from modules.notifications import send_whatsapp
    return send_whatsapp(phone, msg)

def _email(to, subject, body):
    from modules.notifications import send_email
    return send_email(to, subject, body)

def _log_notif(claim_id, cust_id, channel, msg, status):
    from modules.database import log_notification
    log_notification(claim_id, cust_id, channel, msg, status)

# ─────────────────────────────────────────────────────────────────────────────
# SHOP CONFIG — yahan apni details daalen
# ─────────────────────────────────────────────────────────────────────────────
from modules.notifications import SHOP_NAME, SHOP_PHONE, SHOP_ADDRESS, SMTP_USER


# ══════════════════════════════════════════════════════════════════════════════
# JOB 1 — Dealer Overdue Reminder
# Kab: Har 6 ghante
# Kya: Jo items expected return date se zyada din dealer ke paas hain
#      unke liye dealer ko WhatsApp bhejo
# ══════════════════════════════════════════════════════════════════════════════
def job_dealer_overdue_check():
    log.info("▶ Running: dealer_overdue_check")
    today_str = str(date.today())
    sent = 0

    try:
        with _db() as conn:
            rows = conn.execute("""
                SELECT da.id, da.claim_id, da.dealer_id, da.expected_return,
                       da.dealer_job_no, da.sent_date, da.items_sent,
                       d.name  AS dealer_name,
                       d.phone AS dealer_phone,
                       p.brand, p.model_name, p.serial_number,
                       c.name  AS customer_name,
                       c.phone AS customer_phone,
                       -- days overdue
                       julianday('now') - julianday(da.expected_return) AS days_overdue
                FROM dealer_assignments da
                JOIN dealers d       ON d.id  = da.dealer_id
                JOIN service_claims sc ON sc.id = da.claim_id
                JOIN customers c     ON c.id  = sc.customer_id
                JOIN products  p     ON p.id  = sc.product_id
                WHERE da.status IN ('Pending','Received by Dealer','In Repair')
                  AND da.expected_return IS NOT NULL
                  AND da.expected_return < ?
                  AND d.phone IS NOT NULL
            """, (today_str,)).fetchall()

        for r in rows:
            days = int(r["days_overdue"] or 0)
            device = f"{r['brand']} {r['model_name']}"
            job_no = r["dealer_job_no"] or "N/A"

            msg = (
                f"📋 Reminder — {SHOP_NAME}\n\n"
                f"Namaskar {r['dealer_name']} ji,\n"
                f"Aapke paas hamare customer ka device {days} din se overdue hai.\n\n"
                f"Device: {device}\n"
                f"Serial: {r['serial_number']}\n"
                f"Job No: {job_no}\n"
                f"Sent Date: {r['sent_date']}\n"
                f"Expected: {r['expected_return']}\n\n"
                f"Kripya jald se update karein ya return karein.\n"
                f"Contact: {SHOP_PHONE}\n"
                f"— {SHOP_NAME}"
            )

            result = _wa(r["dealer_phone"], msg)
            status = "sent" if result.get("success") else "failed"
            _log_notif(r["claim_id"], None, "whatsapp", msg, status)

            log.info(f"  Dealer reminder → {r['dealer_name']} ({r['dealer_phone']}) "
                     f"| {device} | {days}d overdue | {status}")
            sent += 1

    except Exception as e:
        log.error(f"  dealer_overdue_check ERROR: {e}")

    log.info(f"▶ dealer_overdue_check done — {sent} reminder(s) sent")


# ══════════════════════════════════════════════════════════════════════════════
# JOB 2 — Customer "Ready for Pickup" Reminder
# Kab: Har 24 ghante (dopahar 12 baje)
# Kya: Jo items "Ready for Pickup" hain aur customer aaya nahi 2+ din se
# ══════════════════════════════════════════════════════════════════════════════
def job_customer_pickup_reminder():
    log.info("▶ Running: customer_pickup_reminder")
    sent = 0

    try:
        with _db() as conn:
            rows = conn.execute("""
                SELECT sc.id AS claim_id, sc.updated_at, sc.final_cost,
                       sc.advance_paid,
                       c.name  AS customer_name,
                       c.phone AS customer_phone,
                       p.brand, p.model_name,
                       julianday('now') - julianday(sc.updated_at) AS days_waiting
                FROM service_claims sc
                JOIN customers c ON c.id = sc.customer_id
                JOIN products  p ON p.id = sc.product_id
                WHERE sc.status = 'Ready for Pickup'
                  AND julianday('now') - julianday(sc.updated_at) >= 1
            """).fetchall()

        for r in rows:
            days = int(r["days_waiting"] or 0)
            device = f"{r['brand']} {r['model_name']}"
            balance = (r["final_cost"] or 0) - (r["advance_paid"] or 0)
            balance_txt = f"\n💰 Balance: ₹{balance:,.0f}" if balance > 0 else ""

            msg = (
                f"📱 {SHOP_NAME} — Pickup Reminder\n\n"
                f"Namaskar {r['customer_name']} ji!\n"
                f"Aapka {device} (Claim #{r['claim_id']}) {days} din se "
                f"ready hai lekin abhi tak pickup nahi hua.\n"
                f"{balance_txt}\n\n"
                f"Shop timing: 10 AM – 8 PM\n"
                f"Address: {SHOP_ADDRESS}\n"
                f"Contact: {SHOP_PHONE}\n\n"
                f"Jald aayein! — {SHOP_NAME}"
            )

            result = _wa(r["customer_phone"], msg)
            status = "sent" if result.get("success") else "failed"
            _log_notif(r["claim_id"], None, "whatsapp", msg, status)

            log.info(f"  Pickup reminder → {r['customer_name']} | {device} "
                     f"| {days}d waiting | {status}")
            sent += 1

    except Exception as e:
        log.error(f"  customer_pickup_reminder ERROR: {e}")

    log.info(f"▶ customer_pickup_reminder done — {sent} reminder(s) sent")


# ══════════════════════════════════════════════════════════════════════════════
# JOB 3 — Dealer Status Follow-Up
# Kab: Har 12 ghante
# Kya: 3+ din se dealer ke paas hai → status maango
# ══════════════════════════════════════════════════════════════════════════════
def job_dealer_followup():
    log.info("▶ Running: dealer_followup")
    sent = 0

    try:
        with _db() as conn:
            rows = conn.execute("""
                SELECT da.claim_id, da.dealer_job_no, da.sent_date,
                       d.name  AS dealer_name,
                       d.phone AS dealer_phone,
                       p.brand, p.model_name, p.serial_number,
                       julianday('now') - julianday(da.sent_date) AS days_at_dealer
                FROM dealer_assignments da
                JOIN dealers d         ON d.id  = da.dealer_id
                JOIN service_claims sc ON sc.id = da.claim_id
                JOIN products  p       ON p.id  = sc.product_id
                WHERE da.status IN ('Pending','Received by Dealer','In Repair')
                  AND julianday('now') - julianday(da.sent_date) >= 3
                  AND d.phone IS NOT NULL
                  AND (
                    da.expected_return IS NULL
                    OR da.expected_return >= date('now')
                  )
            """).fetchall()

        for r in rows:
            days = int(r["days_at_dealer"] or 0)
            device = f"{r['brand']} {r['model_name']}"
            job_no = r["dealer_job_no"] or "N/A"

            msg = (
                f"🔧 Follow-Up — {SHOP_NAME}\n\n"
                f"{r['dealer_name']} ji,\n"
                f"Device {days} din se aapke paas hai.\n\n"
                f"Device: {device}\n"
                f"S/N: {r['serial_number']}\n"
                f"Job#: {job_no}\n\n"
                f"Kripya current status batayein.\n"
                f"Contact: {SHOP_PHONE} — {SHOP_NAME}"
            )

            result = _wa(r["dealer_phone"], msg)
            status = "sent" if result.get("success") else "failed"
            _log_notif(r["claim_id"], None, "whatsapp", msg, status)

            log.info(f"  Dealer follow-up → {r['dealer_name']} | {device} "
                     f"| {days}d | {status}")
            sent += 1

    except Exception as e:
        log.error(f"  dealer_followup ERROR: {e}")

    log.info(f"▶ dealer_followup done — {sent} sent")


# ══════════════════════════════════════════════════════════════════════════════
# JOB 4 — Daily Admin Summary (Roz 9:00 AM)
# Kab: Daily at 09:00
# Kya: Admin ke phone par din ka summary — kya pending, kya urgent
# ══════════════════════════════════════════════════════════════════════════════
def job_daily_admin_summary():
    log.info("▶ Running: daily_admin_summary")

    try:
        with _db() as conn:
            total      = conn.execute("SELECT COUNT(*) FROM service_claims").fetchone()[0]
            received   = conn.execute("SELECT COUNT(*) FROM service_claims WHERE status='Received'").fetchone()[0]
            in_repair  = conn.execute("SELECT COUNT(*) FROM service_claims WHERE status IN ('Diagnosis In Progress','Under Repair','Awaiting Parts')").fetchone()[0]
            at_dealer  = conn.execute("SELECT COUNT(*) FROM dealer_assignments WHERE status IN ('Pending','Received by Dealer','In Repair')").fetchone()[0]
            ready      = conn.execute("SELECT COUNT(*) FROM service_claims WHERE status IN ('Ready for Pickup','Repaired')").fetchone()[0]
            overdue_da = conn.execute("SELECT COUNT(*) FROM dealer_assignments WHERE status IN ('Pending','Received by Dealer','In Repair') AND expected_return < date('now')").fetchone()[0]
            revenue    = conn.execute("SELECT COALESCE(SUM(final_cost),0) FROM service_claims WHERE status='Delivered' AND date(delivered_at) = date('now')").fetchone()[0]

            # Today's new claims
            new_today = conn.execute(
                "SELECT COUNT(*) FROM service_claims WHERE date(received_at) = date('now')"
            ).fetchone()[0]

            # Pending balance
            balance = conn.execute(
                "SELECT COALESCE(SUM(final_cost - advance_paid),0) FROM service_claims WHERE status='Ready for Pickup' AND final_cost IS NOT NULL"
            ).fetchone()[0]

            # Get admin phone from DB config or use SHOP_PHONE
            admin_phone = SHOP_PHONE

        today_str = datetime.now().strftime("%d %b %Y, %A")
        msg = (
            f"🌅 Good Morning — {SHOP_NAME}\n"
            f"📅 {today_str}\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📊 TODAY'S SUMMARY\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📥 New Claims Today : {new_today}\n"
            f"📋 Total Active     : {total}\n"
            f"⏳ Waiting (New)    : {received}\n"
            f"🔧 In Repair        : {in_repair}\n"
            f"🏪 At Dealer        : {at_dealer}\n"
            f"✅ Ready for Pickup : {ready}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"⚠️  Overdue Dealers  : {overdue_da}\n"
            f"💰 Today Revenue    : ₹{revenue:,.0f}\n"
            f"💳 Balance Pending  : ₹{balance:,.0f}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"{'⚠️  ACTION NEEDED: '+str(overdue_da)+' items overdue at dealer!' if overdue_da else '✅ No overdue items!'}\n"
            f"{'🔔 '+str(ready)+' customer(s) need to pickup!' if ready else ''}\n"
            f"\n— {SHOP_NAME}"
        )

        result = _wa(admin_phone, msg)
        status = "sent" if result.get("success") else "failed"
        log.info(f"  Daily summary → Admin | {status}")

        # Also email if configured
        if SMTP_USER and "@" in SMTP_USER and "your_" not in SMTP_USER:
            html = f"""<html><body style="font-family:Arial;background:#f5f5f5;padding:20px">
            <div style="max-width:500px;margin:auto;background:#fff;border-radius:12px;overflow:hidden">
            <div style="background:#0f1e35;padding:20px;text-align:center">
                <h2 style="color:#fff;margin:0">🌅 Daily Summary</h2>
                <p style="color:#93c5fd;margin:4px 0">{today_str}</p>
            </div>
            <div style="padding:24px">
                <table style="width:100%;border-collapse:collapse;font-size:15px">
                {''.join(f'<tr style="border-bottom:1px solid #f1f5f9"><td style="padding:9px 0;color:#64748b">{k}</td><td style="padding:9px 0;font-weight:700;text-align:right">{v}</td></tr>' for k,v in [
                    ("📥 New Today", new_today), ("📋 Total Active", total),
                    ("⏳ Waiting", received), ("🔧 In Repair", in_repair),
                    ("🏪 At Dealer", at_dealer), ("✅ Ready Pickup", ready),
                    ("⚠️ Overdue", overdue_da), ("💰 Today Revenue", f"₹{revenue:,.0f}"),
                    ("💳 Balance Due", f"₹{balance:,.0f}"),
                ])}
                </table>
                {'<div style="background:#fef2f2;border-left:4px solid #ef4444;padding:12px;margin-top:16px;border-radius:4px"><b style="color:#991b1b">⚠️ Action Needed:</b><br>'+str(overdue_da)+' item(s) overdue at dealer. Send reminders.</div>' if overdue_da else ''}
                {'<div style="background:#f0fdf4;border-left:4px solid #10b981;padding:12px;margin-top:8px;border-radius:4px"><b style="color:#065f46">🔔 Pickup Pending:</b><br>'+str(ready)+' customer(s) have not picked up yet.</div>' if ready else ''}
            </div>
            <div style="background:#f8fafc;padding:14px;text-align:center;font-size:12px;color:#6b7280">
                {SHOP_NAME} — Automated Daily Report
            </div></div></body></html>"""
            _email(SMTP_USER, f"[{SHOP_NAME}] Daily Summary — {today_str}", html)

    except Exception as e:
        log.error(f"  daily_admin_summary ERROR: {e}")

    log.info("▶ daily_admin_summary done")


# ══════════════════════════════════════════════════════════════════════════════
# JOB 5 — Auto notify customer when dealer returns item
# Yeh ek helper function hai — status update par call hota hai (not scheduled)
# ══════════════════════════════════════════════════════════════════════════════
def notify_customer_item_returned(claim_id: int):
    """
    Jab dealer se item wapas aaye → customer ko auto-message bhejo.
    app.py mein dealer_return route se call hota hai.
    """
    try:
        with _db() as conn:
            row = conn.execute("""
                SELECT sc.id, c.name, c.phone, c.email,
                       p.brand, p.model_name
                FROM service_claims sc
                JOIN customers c ON c.id = sc.customer_id
                JOIN products  p ON p.id = sc.product_id
                WHERE sc.id = ?
            """, (claim_id,)).fetchone()

        if not row:
            return

        device = f"{row['brand']} {row['model_name']}"
        msg = (
            f"🔧 Update — {SHOP_NAME}\n\n"
            f"Namaskar {row['name']} ji!\n"
            f"Aapka {device} (Claim #{claim_id}) service center se "
            f"wapas aa gaya hai.\n\n"
            f"Hamare technician ab isko check karenge aur "
            f"jald hi repair complete hogi.\n"
            f"Hum aapko update denge.\n\n"
            f"Contact: {SHOP_PHONE}\n"
            f"— {SHOP_NAME}"
        )

        result = _wa(row["phone"], msg)
        status = "sent" if result.get("success") else "failed"
        _log_notif(claim_id, None, "whatsapp", msg, status)
        log.info(f"  Item returned notify → {row['name']} | {device} | {status}")

    except Exception as e:
        log.error(f"  notify_customer_item_returned ERROR: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULER SETUP
# ══════════════════════════════════════════════════════════════════════════════
_scheduler = None

def start_scheduler():
    """App start hone par call karo — background jobs shuru ho jaate hain."""
    global _scheduler

    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Job 1: Dealer overdue check — har 6 ghante
    _scheduler.add_job(
        job_dealer_overdue_check,
        trigger=IntervalTrigger(hours=6),
        id="dealer_overdue",
        name="Dealer Overdue Reminders",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Job 2: Customer pickup reminder — roz dopahar 12 baje
    _scheduler.add_job(
        job_customer_pickup_reminder,
        trigger=CronTrigger(hour=12, minute=0),
        id="pickup_reminder",
        name="Customer Pickup Reminders",
        replace_existing=True,
    )

    # Job 3: Dealer follow-up — har 12 ghante
    _scheduler.add_job(
        job_dealer_followup,
        trigger=IntervalTrigger(hours=12),
        id="dealer_followup",
        name="Dealer Status Follow-Up",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Job 4: Daily admin summary — roz 9:00 AM
    _scheduler.add_job(
        job_daily_admin_summary,
        trigger=CronTrigger(hour=9, minute=0),
        id="daily_summary",
        name="Daily Admin Summary",
        replace_existing=True,
    )

    _scheduler.start()

    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log.info("✅ AUTO-SCHEDULER STARTED (Asia/Kolkata)")
    log.info("  📦 Dealer overdue check  → Every 6 hours")
    log.info("  🔔 Pickup reminders      → Daily 12:00 PM")
    log.info("  🔧 Dealer follow-up      → Every 12 hours")
    log.info("  🌅 Admin daily summary   → Daily 9:00 AM")
    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Scheduler stopped.")


def get_scheduler_status():
    """Admin page ke liye — scheduler jobs ki list."""
    if not _scheduler or not _scheduler.running:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id":       job.id,
            "name":     job.name,
            "next_run": next_run.strftime("%d %b %Y, %I:%M %p") if next_run else "—",
        })
    return {"running": True, "jobs": jobs}


def run_job_now(job_id: str):
    """Admin se manually ek job turant chalao."""
    job_map = {
        "dealer_overdue":  job_dealer_overdue_check,
        "pickup_reminder": job_customer_pickup_reminder,
        "dealer_followup": job_dealer_followup,
        "daily_summary":   job_daily_admin_summary,
    }
    fn = job_map.get(job_id)
    if fn:
        import threading
        threading.Thread(target=fn, daemon=True).start()
        return True
    return False
