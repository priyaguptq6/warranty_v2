"""
database.py — Full schema for Professional Warranty & Repair Management System
Tables: customers, products, service_claims, dealers, dealer_assignments,
        claim_images, payments, technicians, feedback, status_history, notifications
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "warranty.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:

        # ── Customers ────────────────────────────────────────────────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            phone      TEXT NOT NULL UNIQUE,
            email      TEXT,
            address    TEXT,
            created_at DATETIME DEFAULT (datetime('now','localtime'))
        )""")

        # ── Dealers ──────────────────────────────────────────────────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS dealers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            contact_person  TEXT,
            phone           TEXT NOT NULL,
            email           TEXT,
            address         TEXT NOT NULL,
            city            TEXT,
            specialization  TEXT,   -- e.g. "Dell, HP Laptops", "Printers"
            gst_number      TEXT,
            notes           TEXT,
            is_active       INTEGER DEFAULT 1,
            created_at      DATETIME DEFAULT (datetime('now','localtime'))
        )""")

        # ── Technicians ──────────────────────────────────────────────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS technicians (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            phone      TEXT,
            skill      TEXT,
            is_active  INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT (datetime('now','localtime'))
        )""")

        # ── Products ─────────────────────────────────────────────────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id     INTEGER NOT NULL REFERENCES customers(id),
            brand           TEXT NOT NULL,
            model_name      TEXT NOT NULL,
            serial_number   TEXT NOT NULL,
            purchase_date   DATE,
            warranty_expiry DATE,
            warranty_status TEXT DEFAULT 'Unknown'
                CHECK(warranty_status IN ('Under Warranty','Out of Warranty','Unknown')),
            created_at      DATETIME DEFAULT (datetime('now','localtime'))
        )""")

        # ── Service Claims ───────────────────────────────────────────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS service_claims (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id      INTEGER NOT NULL REFERENCES customers(id),
            product_id       INTEGER NOT NULL REFERENCES products(id),
            technician_id    INTEGER REFERENCES technicians(id),
            issue_desc       TEXT NOT NULL,
            accessories      TEXT,
            status           TEXT NOT NULL DEFAULT 'Received'
                CHECK(status IN (
                    'Received','Diagnosis In Progress','Awaiting Parts',
                    'Sent to Dealer','Under Repair','Repaired',
                    'Quality Check','Ready for Pickup','Delivered','Cancelled'
                )),
            technician_note  TEXT,
            estimated_cost   REAL DEFAULT 0,
            advance_paid     REAL DEFAULT 0,
            final_cost       REAL,
            balance_due      REAL GENERATED ALWAYS AS
                             (COALESCE(final_cost,0) - COALESCE(advance_paid,0)) VIRTUAL,
            received_at      DATETIME DEFAULT (datetime('now','localtime')),
            updated_at       DATETIME DEFAULT (datetime('now','localtime')),
            delivered_at     DATETIME,
            feedback_rating  INTEGER CHECK(feedback_rating BETWEEN 1 AND 5),
            feedback_comment TEXT
        )""")

        # ── Dealer Assignments ───────────────────────────────────────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS dealer_assignments (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id         INTEGER NOT NULL REFERENCES service_claims(id),
            dealer_id        INTEGER NOT NULL REFERENCES dealers(id),
            sent_date        DATE NOT NULL DEFAULT (date('now','localtime')),
            expected_return  DATE,
            actual_return    DATE,
            dealer_job_no    TEXT,       -- dealer's own reference number
            items_sent       TEXT,       -- description of what was sent
            condition_sent   TEXT,       -- physical condition when sent
            repair_type      TEXT,       -- warranty / chargeable / DOA
            dealer_cost      REAL,       -- what dealer charged us
            notes            TEXT,
            status           TEXT DEFAULT 'Pending'
                CHECK(status IN ('Pending','Received by Dealer','In Repair',
                                 'Returned','Cancelled')),
            created_at       DATETIME DEFAULT (datetime('now','localtime'))
        )""")

        # ── Claim Images ─────────────────────────────────────────────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS claim_images (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id         INTEGER NOT NULL REFERENCES service_claims(id),
            image_type       TEXT NOT NULL
                CHECK(image_type IN ('intake','delivery','damage','repair','other')),
            filename         TEXT NOT NULL,
            ai_extracted     TEXT,   -- JSON from AI analysis
            notes            TEXT,
            uploaded_at      DATETIME DEFAULT (datetime('now','localtime'))
        )""")

        # ── Payments ─────────────────────────────────────────────────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id     INTEGER NOT NULL REFERENCES service_claims(id),
            amount       REAL NOT NULL,
            payment_mode TEXT DEFAULT 'Cash'
                CHECK(payment_mode IN ('Cash','UPI','Card','Online','Cheque')),
            payment_type TEXT DEFAULT 'advance'
                CHECK(payment_type IN ('advance','final','partial','refund')),
            reference_no TEXT,
            notes        TEXT,
            paid_at      DATETIME DEFAULT (datetime('now','localtime'))
        )""")

        # ── Status History ───────────────────────────────────────────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS status_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id   INTEGER NOT NULL REFERENCES service_claims(id),
            old_status TEXT,
            new_status TEXT NOT NULL,
            changed_by TEXT DEFAULT 'Admin',
            note       TEXT,
            changed_at DATETIME DEFAULT (datetime('now','localtime'))
        )""")

        # ── Notifications Log ────────────────────────────────────────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id    INTEGER REFERENCES service_claims(id),
            customer_id INTEGER REFERENCES customers(id),
            channel     TEXT NOT NULL,
            message     TEXT NOT NULL,
            status      TEXT DEFAULT 'pending',
            sent_at     DATETIME DEFAULT (datetime('now','localtime'))
        )""")

        # ── Indexes ──────────────────────────────────────────────────────────
        conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_status   ON service_claims(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_customer ON service_claims(customer_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_da_claim        ON dealer_assignments(claim_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_da_dealer       ON dealer_assignments(dealer_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_claim    ON claim_images(claim_id)")

    print(f"[DB] ✅ Database initialized: {DB_PATH}")


# ═══════════════════════════ QUERY HELPERS ════════════════════════════════════

def get_all_claims(status_filter=None, search=None):
    with get_db() as conn:
        query = """
            SELECT sc.id, sc.status, sc.issue_desc, sc.technician_note,
                   sc.estimated_cost, sc.final_cost, sc.advance_paid,
                   sc.received_at, sc.updated_at, sc.feedback_rating,
                   c.name AS customer_name, c.phone, c.email,
                   p.brand, p.model_name, p.serial_number, p.warranty_status,
                   t.name AS technician_name,
                   da.dealer_id,
                   d.name AS dealer_name
            FROM service_claims sc
            JOIN customers c ON c.id = sc.customer_id
            JOIN products  p ON p.id = sc.product_id
            LEFT JOIN technicians t ON t.id = sc.technician_id
            LEFT JOIN dealer_assignments da ON da.claim_id = sc.id
            LEFT JOIN dealers d ON d.id = da.dealer_id
            WHERE 1=1
        """
        params = []
        if status_filter:
            query += " AND sc.status = ?"
            params.append(status_filter)
        if search:
            query += """ AND (
                c.name LIKE ? OR c.phone LIKE ? OR
                p.serial_number LIKE ? OR p.model_name LIKE ?
            )"""
            s = f"%{search}%"
            params += [s, s, s, s]
        query += " ORDER BY sc.received_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_claim_by_id(claim_id):
    with get_db() as conn:
        row = conn.execute("""
            SELECT sc.*, c.name AS customer_name, c.phone, c.email, c.address,
                   p.brand, p.model_name, p.serial_number, p.warranty_status,
                   p.purchase_date, p.warranty_expiry,
                   t.name AS technician_name
            FROM service_claims sc
            JOIN customers c ON c.id = sc.customer_id
            JOIN products  p ON p.id = sc.product_id
            LEFT JOIN technicians t ON t.id = sc.technician_id
            WHERE sc.id = ?
        """, (claim_id,)).fetchone()
        return dict(row) if row else None


def get_claim_history(claim_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM status_history WHERE claim_id=? ORDER BY changed_at",
            (claim_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_claim_images(claim_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM claim_images WHERE claim_id=? ORDER BY uploaded_at",
            (claim_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_claim_dealer(claim_id):
    with get_db() as conn:
        row = conn.execute("""
            SELECT da.*, d.name AS dealer_name, d.phone AS dealer_phone,
                   d.address AS dealer_address, d.city AS dealer_city
            FROM dealer_assignments da
            JOIN dealers d ON d.id = da.dealer_id
            WHERE da.claim_id = ?
            ORDER BY da.created_at DESC LIMIT 1
        """, (claim_id,)).fetchone()
        return dict(row) if row else None


def get_claim_payments(claim_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM payments WHERE claim_id=? ORDER BY paid_at",
            (claim_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_claim_status(claim_id, new_status, technician_note=None,
                         final_cost=None, technician_id=None, changed_by="Admin"):
    with get_db() as conn:
        claim = conn.execute(
            "SELECT status FROM service_claims WHERE id=?", (claim_id,)
        ).fetchone()
        if not claim:
            return False
        old_status = claim["status"]
        conn.execute("""
            UPDATE service_claims
            SET status=?,
                technician_note=COALESCE(?,technician_note),
                final_cost=COALESCE(?,final_cost),
                technician_id=COALESCE(?,technician_id),
                updated_at=datetime('now','localtime'),
                delivered_at=CASE WHEN ?='Delivered'
                             THEN datetime('now','localtime') ELSE delivered_at END
            WHERE id=?
        """, (new_status, technician_note, final_cost, technician_id,
              new_status, claim_id))
        conn.execute("""
            INSERT INTO status_history(claim_id,old_status,new_status,changed_by,note)
            VALUES(?,?,?,?,?)
        """, (claim_id, old_status, new_status, changed_by, technician_note))
        return True


def log_notification(claim_id, customer_id, channel, message, status):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO notifications(claim_id,customer_id,channel,message,status)
            VALUES(?,?,?,?,?)
        """, (claim_id, customer_id, channel, message, status))


# ── Dealer helpers ─────────────────────────────────────────────────────────

def get_all_dealers(active_only=True):
    with get_db() as conn:
        q = "SELECT * FROM dealers"
        if active_only:
            q += " WHERE is_active=1"
        q += " ORDER BY name"
        return [dict(r) for r in conn.execute(q).fetchall()]


def get_dealer_by_id(dealer_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM dealers WHERE id=?", (dealer_id,)).fetchone()
        return dict(row) if row else None


def get_dealer_stats(dealer_id):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT da.*, sc.status AS claim_status, sc.received_at,
                   c.name AS customer_name, c.phone,
                   p.brand, p.model_name, p.serial_number
            FROM dealer_assignments da
            JOIN service_claims sc ON sc.id = da.claim_id
            JOIN customers c ON c.id = sc.customer_id
            JOIN products p ON p.id = sc.product_id
            WHERE da.dealer_id = ?
            ORDER BY da.sent_date DESC
        """, (dealer_id,)).fetchall()
        items = [dict(r) for r in rows]
        total_cost = sum(i.get("dealer_cost") or 0 for i in items)
        pending    = sum(1 for i in items if i["status"] in ("Pending","Received by Dealer","In Repair"))
        returned   = sum(1 for i in items if i["status"] == "Returned")
        return {"assignments": items, "total_cost": total_cost,
                "pending": pending, "returned": returned, "total": len(items)}


def get_dashboard_stats():
    with get_db() as conn:
        s = {}
        s["total"]     = conn.execute("SELECT COUNT(*) FROM service_claims").fetchone()[0]
        s["received"]  = conn.execute(
            "SELECT COUNT(*) FROM service_claims WHERE status='Received'").fetchone()[0]
        s["in_repair"] = conn.execute(
            "SELECT COUNT(*) FROM service_claims WHERE status IN "
            "('Diagnosis In Progress','Under Repair','Awaiting Parts','Sent to Dealer')"
        ).fetchone()[0]
        s["ready"]     = conn.execute(
            "SELECT COUNT(*) FROM service_claims WHERE status IN "
            "('Repaired','Quality Check','Ready for Pickup')"
        ).fetchone()[0]
        s["delivered"] = conn.execute(
            "SELECT COUNT(*) FROM service_claims WHERE status='Delivered'").fetchone()[0]
        rev = conn.execute(
            "SELECT COALESCE(SUM(final_cost),0) FROM service_claims WHERE status='Delivered'"
        ).fetchone()[0]
        s["revenue"] = f"₹{rev:,.0f}"
        s["at_dealer"] = conn.execute(
            "SELECT COUNT(*) FROM dealer_assignments WHERE status IN "
            "('Pending','Received by Dealer','In Repair')"
        ).fetchone()[0]
        pending_balance = conn.execute(
            "SELECT COALESCE(SUM(final_cost - advance_paid),0) FROM service_claims "
            "WHERE status='Ready for Pickup' AND final_cost IS NOT NULL"
        ).fetchone()[0]
        s["pending_balance"] = f"₹{pending_balance:,.0f}"
        return s


def get_all_technicians():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM technicians WHERE is_active=1 ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]
