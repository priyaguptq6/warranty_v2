"""
app.py - MUDIT COMPUTERS Warranty System v2 with Auto-Scheduler
"""
import os, socket, json, uuid
from datetime import date

# Load environment variables from .env file (if exists)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars

from flask import (Flask, render_template, request, redirect,
                   url_for, jsonify, flash, session, send_from_directory)
from functools import wraps
from modules.database import (
    init_db, get_db, get_all_claims, get_claim_by_id, get_claim_history,
    get_claim_images, get_claim_dealer, get_claim_payments,
    update_claim_status, get_dashboard_stats, get_all_dealers,
    get_dealer_by_id, get_dealer_stats, get_all_technicians, log_notification
)
from modules.notifications import send_notification
from modules.ai_helper import analyze_device_image, analyze_damage_image, suggest_diagnosis, is_configured
try:
    from modules.firebase_db import (
        is_firebase_enabled, create_remote_claim, update_remote_claim_status,
        append_remote_history, append_remote_payment, append_remote_image,
        append_remote_dealer_assignment, upload_to_storage
    )
except ImportError:
    def is_firebase_enabled():
        return False
    def create_remote_claim(*args, **kwargs):
        return False
    def update_remote_claim_status(*args, **kwargs):
        return False
    def append_remote_history(*args, **kwargs):

        return False
    def append_remote_image(*args, **kwargs):
        return False
    def append_remote_dealer_assignment(*args, **kwargs):
        return False
    def upload_to_storage(*args, **kwargs):
        return None
from modules.scheduler import start_scheduler, get_scheduler_status, run_job_now, notify_customer_item_returned

app = Flask(__name__)
import sqlite3
import os
# --- YE CODE LINE 53 PAR PASTE KAREIN ---
def initialize_railway_database():
    import sqlite3
    db_path = os.path.join(os.getcwd(), 'warranty.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Saari tables jo Railway ko chahiye
    cursor.execute('CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT UNIQUE, email TEXT, address TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, brand TEXT, model_name TEXT, serial_number TEXT, purchase_date TEXT, warranty_expiry TEXT, warranty_status TEXT)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS service_claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, product_id INTEGER, 
        customer_name TEXT, serial_number TEXT, product_model TEXT, issue_desc TEXT, 
        accessories TEXT, status TEXT DEFAULT 'Received', final_cost REAL, 
        advance_paid REAL DEFAULT 0, estimated_cost REAL, received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, feedback_rating INTEGER, feedback_comment TEXT)''')
    conn.commit()
    conn.close()
    print("✅ Railway Database Tables Ready!")

# AB ISE SAHI NAAM SE CALL KAREIN
initialize_railway_database()
app.secret_key = "mudit_computers_v2_secret_2024"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXT  = {"jpg","jpeg","png","webp"}
ADMIN_USER   = "admin"
ADMIN_PASS   = "mudit@123"
ALL_STATUSES = ["Received","Diagnosis In Progress","Awaiting Parts","Sent to Dealer",
                "Under Repair","Repaired","Quality Check","Ready for Pickup","Delivered","Cancelled"]
STATUS_COLORS = {"Received":"#3b82f6","Diagnosis In Progress":"#8b5cf6","Awaiting Parts":"#f59e0b",
    "Sent to Dealer":"#6366f1","Under Repair":"#f97316","Repaired":"#10b981",
    "Quality Check":"#06b6d4","Ready for Pickup":"#22c55e","Delivered":"#16a34a","Cancelled":"#ef4444"}
DEALER_STATUSES = ["Pending","Received by Dealer","In Repair","Returned","Cancelled"]
PAYMENT_MODES   = ["Cash","UPI","Card","Online","Cheque"]

def allowed_file(fn): return "." in fn and fn.rsplit(".",1)[1].lower() in ALLOWED_EXT
def save_upload(file, cid, prefix):
    ext = file.filename.rsplit(".",1)[1].lower()
    fn  = f"{prefix}_{cid}_{uuid.uuid4().hex[:8]}.{ext}"
    folder = os.path.join(app.config["UPLOAD_FOLDER"], str(cid))
    os.makedirs(folder, exist_ok=True)
    local_path = os.path.join(folder, fn)
    file.seek(0)  # Reset file pointer in case it was read before
    file.save(local_path)
    rel = f"uploads/{cid}/{fn}"

    # Upload to Firebase Storage
    firebase_url = upload_to_storage(local_path, f"uploads/{cid}/{fn}")
    if firebase_url:
        rel = firebase_url  # Use Firebase URL

    return rel
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"
def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
        return f(*a,**kw)
    return dec

# Customer routes
@app.route("/")
def index(): return render_template("index.html")

@app.route("/submit", methods=["GET","POST"])
def submit_claim():
    if request.method == "POST":
        data = request.form
        for fld in ["name","phone","brand","model_name","serial_number","issue_desc"]:
            if not data.get(fld,"").strip():
                flash(f"'{fld.replace('_',' ').title()}' zaroor bharein.","error")
                return render_template("customer_form.html")
        try:
            with get_db() as conn:
                ex = conn.execute("SELECT id FROM customers WHERE phone=?",(data["phone"].strip(),)).fetchone()
                if ex:
                    cid = ex["id"]
                    conn.execute("UPDATE customers SET name=?,email=? WHERE id=?",
                        (data["name"].strip(),data.get("email","").strip(),cid))
                else:
                    cid = conn.execute("INSERT INTO customers(name,phone,email,address) VALUES(?,?,?,?)",
                        (data["name"].strip(),data["phone"].strip(),
                         data.get("email","").strip(),data.get("address","").strip())).lastrowid
                we = data.get("warranty_expiry") or None
                ws = "Unknown"
                if we: ws = "Under Warranty" if date.fromisoformat(we) >= date.today() else "Out of Warranty"
                pid = conn.execute("INSERT INTO products(customer_id,brand,model_name,serial_number,purchase_date,warranty_expiry,warranty_status) VALUES(?,?,?,?,?,?,?)",
                    (cid,data["brand"].strip(),data["model_name"].strip(),data["serial_number"].strip(),
                     data.get("purchase_date") or None,we,ws)).lastrowid
                clid = conn.execute("INSERT INTO service_claims(customer_id,product_id,issue_desc,accessories) VALUES(?,?,?,?)",
                    (cid,pid,data["issue_desc"].strip(),data.get("accessories","").strip())).lastrowid
                conn.execute("INSERT INTO status_history(claim_id,old_status,new_status,changed_by,note) VALUES(?,?,?,?,?)",
                    (clid,None,"Received","System","Customer self-service form"))
            f = request.files.get("intake_photo")
            if f and f.filename and allowed_file(f.filename):
                fb = f.read()
                rel = save_upload(f,clid,"intake")
                ai_extracted = None
                mime="image/jpeg" if f.filename.lower().endswith((".jpg",".jpeg")) else "image/png"
                
                # AI Analysis of customer's intake photo
                if is_configured():
                    try:
                        res = analyze_device_image(fb, mime)
                        if res.get("success"):
                            ai_extracted = json.dumps(res)
                            # Try to update product info if better than manual entry
                            brand = res.get('brand','').strip()
                            model = res.get('model_name','').strip()
                            serial = res.get('serial_number','').strip()
                            if brand and not data.get("brand"):
                                data["brand"] = brand
                            if model and not data.get("model_name"):
                                data["model_name"] = model
                            if serial and not data.get("serial_number"):
                                data["serial_number"] = serial
                    except Exception as e:
                        print(f"[AI] Customer intake photo analysis error: {e}")
                
                with get_db() as conn:
                    conn.execute("INSERT INTO claim_images(claim_id,image_type,filename,ai_extracted,notes) VALUES(?,?,?,?,?)",
                        (clid,"intake",rel,ai_extracted,"Customer intake photo"))
            try:
                if is_firebase_enabled():
                    customer = {
                        "name": data["name"].strip(),
                        "phone": data["phone"].strip(),
                        "email": data.get("email","").strip(),
                        "address": data.get("address","").strip()
                    }
                    product = {
                        "brand": data["brand"].strip(),
                        "model_name": data["model_name"].strip(),
                        "serial_number": data["serial_number"].strip(),
                        "purchase_date": data.get("purchase_date") or None,
                        "warranty_expiry": data.get("warranty_expiry") or None,
                        "warranty_status": ws
                    }
                    claim = {
                        "issue_desc": data["issue_desc"].strip(),
                        "status": "Received",
                        "accessories": data.get("accessories",""),
                        "received_at": str(date.today())
                    }
                    create_remote_claim(clid, customer, product, claim)
            except Exception:
                pass
            return redirect(url_for("claim_submitted",claim_id=clid))
        except Exception as e: flash(f"Error: {e}","error")
    return render_template("customer_form.html")

@app.route("/submitted/<int:claim_id>")
def claim_submitted(cid=None,claim_id=None):
    claim_id = claim_id or cid
    return render_template("submitted.html",claim=get_claim_by_id(claim_id),claim_id=claim_id)

@app.route("/track")
def track_claim():
    phone=request.args.get("phone","").strip(); ciq=request.args.get("claim_id","").strip(); claims=[]
    if phone or ciq:
        with get_db() as conn:
            q = """SELECT sc.id,sc.status,sc.received_at,sc.updated_at,sc.estimated_cost,sc.final_cost,sc.advance_paid,p.brand,p.model_name,p.serial_number,c.name AS customer_name FROM service_claims sc JOIN customers c ON c.id=sc.customer_id JOIN products p ON p.id=sc.product_id"""
            if ciq: rows = conn.execute(q+" WHERE sc.id=?",(ciq,)).fetchall()
            else:   rows = conn.execute(q+" WHERE c.phone=? ORDER BY sc.received_at DESC",(phone,)).fetchall()
            claims = [dict(r) for r in rows]
    return render_template("track.html",claims=claims,phone=phone,claim_id_q=ciq,
        status_colors=STATUS_COLORS,all_statuses=ALL_STATUSES)

@app.route("/track/<int:claim_id>/timeline")
def track_timeline(claim_id):
    return render_template("track_timeline.html",history=get_claim_history(claim_id),
        claim_id=claim_id,status_colors=STATUS_COLORS)

@app.route("/kiosk")
def kiosk(): return render_template("kiosk.html",status_colors=STATUS_COLORS)

@app.route("/feedback/<int:claim_id>",methods=["GET","POST"])
def feedback(claim_id):
    claim=get_claim_by_id(claim_id)
    if not claim: return "Not found",404
    if request.method=="POST":
        with get_db() as conn:
            conn.execute("UPDATE service_claims SET feedback_rating=?,feedback_comment=? WHERE id=?",
                (int(request.form.get("rating",5)),request.form.get("comment","").strip(),claim_id))
        return render_template("feedback_thanks.html",claim=claim)
    return render_template("feedback.html",claim=claim)
# Admin routes
@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    if session.get("admin_logged_in"): return redirect(url_for("admin_dashboard"))
    if request.method=="POST":
        data = request.get_json()
        if data and 'idToken' in data:
            try:
                from firebase_admin import auth
                decoded_token = auth.verify_id_token(data['idToken'])
                uid = decoded_token['uid']
                # Optionally check if uid is admin
                session["admin_logged_in"] = True
                session["firebase_uid"] = uid
                return jsonify({"success": True})
            except Exception as e:
                return jsonify({"error": str(e)}), 401
        # Fallback for old method
        if request.form.get("username")==ADMIN_USER and request.form.get("password")==ADMIN_PASS:
            session["admin_logged_in"]=True; return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials.","error")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout(): session.clear(); return redirect(url_for("admin_login"))

@app.route("/admin")
@login_required
def admin_dashboard():
    sf=request.args.get("status",""); sq=request.args.get("q","").strip()
    return render_template("admin_dashboard.html",claims=get_all_claims(sf or None,sq or None),
        stats=get_dashboard_stats(),all_statuses=ALL_STATUSES,status_filter=sf,search_query=sq,
        status_colors=STATUS_COLORS,local_ip=get_local_ip())

@app.route("/admin/claim/<int:claim_id>")
@login_required
def admin_claim_detail(claim_id):
    claim=get_claim_by_id(claim_id)
    if not claim: flash("Not found.","error"); return redirect(url_for("admin_dashboard"))
    return render_template("admin_claim_detail.html",claim=claim,history=get_claim_history(claim_id),
        images=get_claim_images(claim_id),dealer=get_claim_dealer(claim_id),
        payments=get_claim_payments(claim_id),dealers=get_all_dealers(),
        technicians=get_all_technicians(),all_statuses=ALL_STATUSES,
        dealer_statuses=DEALER_STATUSES,payment_modes=PAYMENT_MODES,
        status_colors=STATUS_COLORS,ai_enabled=is_configured(),today=str(date.today()))

@app.route("/admin/claim/<int:claim_id>/update",methods=["POST"])
@login_required
def admin_update_status(claim_id):
    ns=request.form.get("status","").strip(); tn=request.form.get("technician_note","").strip() or None
    fc=request.form.get("final_cost","").strip(); tid=request.form.get("technician_id","").strip() or None
    if ns not in ALL_STATUSES: flash("Invalid status.","error"); return redirect(url_for("admin_claim_detail",claim_id=claim_id))
    try: fcv=float(fc) if fc else None
    except: fcv=None
    old_claim = get_claim_by_id(claim_id)
    update_claim_status(claim_id,ns,tn,fcv,int(tid) if tid else None)
    try:
        if is_firebase_enabled():
            update_remote_claim_status(claim_id, ns, technician_note=tn, final_cost=fcv,
                                       technician_id=int(tid) if tid else None)
            if old_claim:
                append_remote_history(claim_id, old_claim.get("status"), ns, "Admin", tn)
    except Exception:
        pass
    claim=get_claim_by_id(claim_id)
    if claim: send_notification(claim_id,claim["customer_name"],claim["phone"],claim.get("email",""),f"{claim['brand']} {claim['model_name']}",ns,tn)
    flash(f"Status → '{ns}' | Customer notified! ✅","success")
    return redirect(url_for("admin_claim_detail",claim_id=claim_id))

@app.route("/admin/claim/<int:claim_id>/upload-image",methods=["POST"])
@login_required
def upload_image(claim_id):
    it=request.form.get("image_type","other"); nt=request.form.get("notes","").strip(); file=request.files.get("image_file")
    if not file or not file.filename or not allowed_file(file.filename):
        flash("Valid image karein.","error"); return redirect(url_for("admin_claim_detail",claim_id=claim_id))
    fb=file.read(); ai_data=None; mime="image/jpeg" if file.filename.lower().endswith((".jpg",".jpeg")) else "image/png"
    rel=save_upload(file,claim_id,it)
    
    # AI Analysis for intake and damage photos
    if it=="intake" and is_configured():
        try:
            res=analyze_device_image(fb,mime); ai_data=json.dumps(res)
            if res.get("success"):
                brand = res.get('brand','').strip()
                model = res.get('model_name','').strip()
                serial = res.get('serial_number','').strip()
                if brand or model or serial:
                    flash(f"✅ AI Found: {brand} {model} S/N:{serial}","success")
                else:
                    flash(f"⚠️ Photo analysed but details unclear. Manual entry needed.","warning")
            else:
                flash(f"⚠️ AI: {res.get('error','Could not extract details')}","warning")
        except Exception as e:
            flash(f"⚠️ AI analysis failed: {str(e)[:100]}","warning")
    elif it=="damage" and is_configured():
        try:
            res=analyze_damage_image(fb,mime); ai_data=json.dumps(res)
            if res.get("success") and res.get("report"):
                nt=nt or res.get("report","")
                flash(f"✅ Damage report: {res.get('overall_condition','Unknown')}","success")
            else:
                flash(f"⚠️ Damage analysis done. Check notes.","info")
        except Exception as e:
            flash(f"⚠️ Damage analysis failed: {str(e)[:100]}","warning")
    elif not is_configured() and it in ("intake","damage"):
        flash(f"❌ AI not configured. Fill ANTHROPIC_API_KEY in config.txt","error")
    
    image_record = {
        "image_type": it,
        "filename": rel,
        "ai_extracted": ai_data,
        "notes": nt,
        "uploaded_at": str(date.today())
    }
    with get_db() as conn:
        conn.execute("INSERT INTO claim_images(claim_id,image_type,filename,ai_extracted,notes) VALUES(?,?,?,?,?)",(claim_id,it,rel,ai_data,nt))
    try:
        if is_firebase_enabled():
            append_remote_image(claim_id, image_record)
    except Exception:
        pass
    flash("Image uploaded!","success"); return redirect(url_for("admin_claim_detail",claim_id=claim_id))

@app.route("/admin/claim/<int:claim_id>/assign-dealer",methods=["POST"])
@login_required
def assign_dealer(claim_id):
    did=request.form.get("dealer_id")
    if not did: flash("Dealer select karein.","error"); return redirect(url_for("admin_claim_detail",claim_id=claim_id))
    try: dcv=float(request.form.get("dealer_cost","") or 0) or None
    except: dcv=None
    assignment = {
        "dealer_id": int(did),
        "sent_date": request.form.get("sent_date") or str(date.today()),
        "expected_return": request.form.get("expected_return") or None,
        "dealer_job_no": request.form.get("dealer_job_no","") or None,
        "items_sent": request.form.get("items_sent","") or None,
        "repair_type": request.form.get("repair_type","warranty"),
        "dealer_cost": dcv,
        "notes": request.form.get("notes","") or None,
        "status": "Pending"
    }
    with get_db() as conn:
        conn.execute("INSERT INTO dealer_assignments(claim_id,dealer_id,sent_date,expected_return,dealer_job_no,items_sent,repair_type,dealer_cost,notes,status) VALUES(?,?,?,?,?,?,?,?,?,'Pending')",
            (claim_id,did,assignment["sent_date"],assignment["expected_return"],
             assignment["dealer_job_no"],assignment["items_sent"],
             assignment["repair_type"],dcv,assignment["notes"]))
        conn.execute("UPDATE service_claims SET status='Sent to Dealer',updated_at=datetime('now','localtime') WHERE id=?",(claim_id,))
        conn.execute("INSERT INTO status_history(claim_id,old_status,new_status,changed_by,note) VALUES(?,?,'Sent to Dealer','Admin',?)",
            (claim_id,"Under Repair",f"Sent to dealer #{did}"))
    try:
        if is_firebase_enabled():
            append_remote_dealer_assignment(claim_id, assignment)
    except Exception:
        pass
    flash(f"Dealer ko assign kiya!","success"); return redirect(url_for("admin_claim_detail",claim_id=claim_id))

@app.route("/admin/claim/<int:claim_id>/dealer-return",methods=["POST"])
@login_required
def dealer_return(claim_id):
    rs=request.form.get("return_status","Returned"); nt=request.form.get("notes","") or None
    try: dcv=float(request.form.get("dealer_cost","") or 0) or None
    except: dcv=None
    return_record = {
        "actual_return": request.form.get("actual_return") or str(date.today()),
        "status": rs,
        "dealer_cost": dcv,
        "notes": nt
    }
    with get_db() as conn:
        conn.execute("UPDATE dealer_assignments SET actual_return=?,status=?,dealer_cost=COALESCE(?,dealer_cost),notes=COALESCE(?,notes) WHERE claim_id=?",
            (return_record["actual_return"],rs,dcv,nt,claim_id))
        if rs=="Returned":
            conn.execute("UPDATE service_claims SET status='Under Repair',updated_at=datetime('now','localtime') WHERE id=?",(claim_id,))
            conn.execute("INSERT INTO status_history(claim_id,old_status,new_status,changed_by,note) VALUES(?,'Sent to Dealer','Under Repair','Admin',?)",(claim_id,f"Returned from dealer. {nt or ''}"))
    try:
        if is_firebase_enabled():
            append_remote_dealer_assignment(claim_id, return_record)
    except Exception:
        pass
    if rs=="Returned":
        notify_customer_item_returned(claim_id)   # AUTO NOTIFY
    flash("Dealer return recorded! Customer auto-notified. ✅","success")
    return redirect(url_for("admin_claim_detail",claim_id=claim_id))

@app.route("/admin/claim/<int:claim_id>/add-payment",methods=["POST"])
@login_required
def add_payment(claim_id):
    try: a=float(request.form.get("amount","") or 0); assert a>0
    except: flash("Valid amount enter karein.","error"); return redirect(url_for("admin_claim_detail",claim_id=claim_id))
    pt=request.form.get("payment_type","advance")
    payment_record = {
        "amount": a,
        "payment_mode": request.form.get("payment_mode","Cash"),
        "payment_type": pt,
        "reference_no": request.form.get("reference_no","") or None,
        "notes": request.form.get("notes","") or None,
        "paid_at": str(date.today())
    }
    with get_db() as conn:
        conn.execute("INSERT INTO payments(claim_id,amount,payment_mode,payment_type,reference_no,notes) VALUES(?,?,?,?,?,?)",
            (claim_id,a,payment_record["payment_mode"],pt,payment_record["reference_no"],payment_record["notes"]))
        if pt=="advance": conn.execute("UPDATE service_claims SET advance_paid=COALESCE(advance_paid,0)+? WHERE id=?",(a,claim_id))
    try:
        if is_firebase_enabled():
            append_remote_payment(claim_id, payment_record)
    except Exception:
        pass
    flash(f"Payment ₹{a:,.0f} recorded!","success"); return redirect(url_for("admin_claim_detail",claim_id=claim_id))

@app.route("/admin/claim/<int:claim_id>/delivery-photo",methods=["POST"])
@login_required
def upload_delivery_photo(claim_id):
    file=request.files.get("delivery_photo")
    if not file or not file.filename or not allowed_file(file.filename):
        flash("Valid image karein.","error"); return redirect(url_for("admin_claim_detail",claim_id=claim_id))
    rel=save_upload(file,claim_id,"delivery")
    with get_db() as conn:
        conn.execute("INSERT INTO claim_images(claim_id,image_type,filename,notes) VALUES(?,?,?,?)",(claim_id,"delivery",rel,"Delivery proof"))
    flash("Delivery photo uploaded!","success"); return redirect(url_for("admin_claim_detail",claim_id=claim_id))

# Dealer management
@app.route("/admin/dealers")
@login_required
def admin_dealers():
    dealers=get_all_dealers(active_only=False)
    with get_db() as conn:
        for d in dealers: d["total_assignments"]=conn.execute("SELECT COUNT(*) FROM dealer_assignments WHERE dealer_id=?",(d["id"],)).fetchone()[0]
    return render_template("dealers.html",dealers=dealers)

@app.route("/admin/dealers/add",methods=["GET","POST"])
@login_required
def add_dealer():
    if request.method=="POST":
        data=request.form
        if not data.get("name","").strip() or not data.get("phone","").strip():
            flash("Name aur Phone zaroor.","error"); return render_template("dealer_form.html",dealer=None)
        with get_db() as conn:
            conn.execute("INSERT INTO dealers(name,contact_person,phone,email,address,city,specialization,gst_number,notes) VALUES(?,?,?,?,?,?,?,?,?)",
                (data["name"].strip(),data.get("contact_person","").strip(),data["phone"].strip(),data.get("email","").strip(),
                 data.get("address","").strip(),data.get("city","").strip(),data.get("specialization","").strip(),
                 data.get("gst_number","").strip(),data.get("notes","").strip()))
        flash("Dealer add ho gaya!","success"); return redirect(url_for("admin_dealers"))
    return render_template("dealer_form.html",dealer=None)

@app.route("/admin/dealers/<int:dealer_id>")
@login_required
def dealer_detail(dealer_id):
    dealer=get_dealer_by_id(dealer_id)
    if not dealer: flash("Not found.","error"); return redirect(url_for("admin_dealers"))
    return render_template("dealer_detail.html",dealer=dealer,stats=get_dealer_stats(dealer_id))

@app.route("/admin/dealers/<int:dealer_id>/edit",methods=["GET","POST"])
@login_required
def edit_dealer(dealer_id):
    dealer=get_dealer_by_id(dealer_id)
    if not dealer: return redirect(url_for("admin_dealers"))
    if request.method=="POST":
        data=request.form
        with get_db() as conn:
            conn.execute("UPDATE dealers SET name=?,contact_person=?,phone=?,email=?,address=?,city=?,specialization=?,gst_number=?,notes=?,is_active=? WHERE id=?",
                (data["name"].strip(),data.get("contact_person","").strip(),data["phone"].strip(),data.get("email","").strip(),
                 data.get("address","").strip(),data.get("city","").strip(),data.get("specialization","").strip(),
                 data.get("gst_number","").strip(),data.get("notes","").strip(),1 if data.get("is_active") else 0,dealer_id))
        flash("Updated!","success"); return redirect(url_for("dealer_detail",dealer_id=dealer_id))
    return render_template("dealer_form.html",dealer=dealer)

@app.route("/admin/technicians")
@login_required
def admin_technicians(): return render_template("technicians.html",technicians=get_all_technicians())

@app.route("/admin/technicians/add",methods=["POST"])
@login_required
def add_technician():
    name=request.form.get("name","").strip()
    if name:
        with get_db() as conn: conn.execute("INSERT INTO technicians(name,phone,skill) VALUES(?,?,?)",(name,request.form.get("phone","").strip(),request.form.get("skill","").strip()))
        flash(f"'{name}' added!","success")
    return redirect(url_for("admin_technicians"))

# ── Auto Reminders Admin Page ─────────────────────────────────────────────

@app.route("/admin/reminders")
@login_required
def admin_reminders():
    with get_db() as conn:
        overdue = [dict(r) for r in conn.execute("""
            SELECT da.claim_id, da.expected_return, da.sent_date,
                   CAST(julianday('now') - julianday(da.expected_return) AS INT) AS days_overdue,
                   d.name AS dealer_name, d.phone AS dealer_phone,
                   p.brand, p.model_name, p.serial_number,
                   c.name AS customer_name, c.phone AS customer_phone
            FROM dealer_assignments da JOIN dealers d ON d.id=da.dealer_id
            JOIN service_claims sc ON sc.id=da.claim_id
            JOIN customers c ON c.id=sc.customer_id JOIN products p ON p.id=sc.product_id
            WHERE da.status IN ('Pending','Received by Dealer','In Repair')
              AND da.expected_return IS NOT NULL AND da.expected_return < date('now')
            ORDER BY days_overdue DESC""").fetchall()]

        pending_pickup = [dict(r) for r in conn.execute("""
            SELECT sc.id, sc.updated_at,
                   CAST(julianday('now') - julianday(sc.updated_at) AS INT) AS days_waiting,
                   sc.final_cost, sc.advance_paid,
                   c.name AS customer_name, c.phone, p.brand, p.model_name
            FROM service_claims sc JOIN customers c ON c.id=sc.customer_id
            JOIN products p ON p.id=sc.product_id
            WHERE sc.status='Ready for Pickup' ORDER BY days_waiting DESC""").fetchall()]

        notif_log = [dict(r) for r in conn.execute("""
            SELECT n.*, sc.id AS cid FROM notifications n
            LEFT JOIN service_claims sc ON sc.id=n.claim_id
            ORDER BY n.sent_at DESC LIMIT 40""").fetchall()]

    return render_template("admin_reminders.html",
        sched_status=get_scheduler_status(),
        overdue=overdue, pending_pickup=pending_pickup, notif_log=notif_log,
        shop_name=__import__('modules.notifications', fromlist=['SHOP_NAME']).SHOP_NAME,
        shop_phone=__import__('modules.notifications', fromlist=['SHOP_PHONE']).SHOP_PHONE)

@app.route("/admin/reminders/run/<job_id>",methods=["POST"])
@login_required
def run_reminder_now(job_id):
    ok=run_job_now(job_id)
    flash(f"Job '{job_id}' started!" if ok else f"Job '{job_id}' nahi mila.","success" if ok else "error")
    return redirect(url_for("admin_reminders"))

@app.route("/admin/reminders/send-now",methods=["POST"])
@login_required
def send_reminder_now():
    phone=request.form.get("phone","").strip(); message=request.form.get("message","").strip()
    cid=request.form.get("claim_id","")
    if not phone or not message: flash("Phone aur message dono chahiye.","error"); return redirect(url_for("admin_reminders"))
    from modules.notifications import send_whatsapp
    res=send_whatsapp(phone,message)
    if res.get("success"):
        log_notification(int(cid) if cid.isdigit() else None,None,"whatsapp",message,"sent")
        flash(f"Message queue ho gaya → {phone}","success")
    else: flash(f"Failed: {res.get('error','Unknown')}","error")
    return redirect(url_for("admin_reminders"))

# AI API
@app.route("/api/ai/status")
def api_ai_status():
    """Check if AI (Anthropic) is configured and working."""
    if is_configured():
        return jsonify({"success": True, "ai_enabled": True, "message": "✅ AI is ready for photo analysis"})
    else:
        return jsonify({"success": False, "ai_enabled": False, "message": "❌ AI not configured. Add ANTHROPIC_API_KEY to config.txt"})

@app.route("/api/ai/analyze-image",methods=["POST"])
@login_required
def api_analyze_image():
    if not is_configured(): return jsonify({"success":False,"error":"config.txt mein API key daalen"})
    file=request.files.get("image")
    if not file: return jsonify({"success":False,"error":"No image"})
    fb=file.read(); mime="image/jpeg" if file.filename.lower().endswith((".jpg",".jpeg")) else "image/png"
    return jsonify(analyze_device_image(fb,mime))

@app.route("/api/ai/suggest-diagnosis",methods=["POST"])
@login_required
def api_suggest_diagnosis():
    data=request.get_json()
    return jsonify({"success":True,"suggestion":suggest_diagnosis(data.get("issue",""),data.get("brand",""),data.get("model",""))})

@app.route("/api/kiosk/search")
def api_kiosk_search():
    q=request.args.get("q","").strip()
    if not q: return jsonify([])
    with get_db() as conn:
        base="SELECT sc.id,sc.status,sc.received_at,sc.updated_at,p.brand,p.model_name,c.name AS customer_name,c.phone FROM service_claims sc JOIN customers c ON c.id=sc.customer_id JOIN products p ON p.id=sc.product_id"
        if q.isdigit(): rows=conn.execute(base+" WHERE sc.id=?",(q,)).fetchall()
        else: rows=conn.execute(base+" WHERE c.phone LIKE ? ORDER BY sc.received_at DESC LIMIT 5",(f"%{q}%",)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/stats")
@login_required
def api_stats(): return jsonify(get_dashboard_stats())

@app.route("/static/uploads/<path:filename>")
def serve_upload(filename): return send_from_directory(app.config["UPLOAD_FOLDER"],filename)

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory(app.static_folder, 'service-worker.js')

if __name__ == "__main__":
    print("""
    +-------------------------------------------------------+
    |        MUDIT COMPUTERS - Warranty System v2           |
    +-------------------------------------------------------+
    | Customer Form  : http://localhost:5000/submit         |
    | Shop Kiosk     : http://localhost:5000/kiosk          |
    | Admin Panel    : http://localhost:5000/admin          |
    | Reminders      : http://localhost:5000/admin/reminders|
    +-------------------------------------------------------+
    | AUTO-SCHEDULER RUNNING:                               |
    | Dealer overdue -> Every 6 hours                       |
    | Pickup reminder -> Daily 12:00 PM                     |
    +-------------------------------------------------------+
    """)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)