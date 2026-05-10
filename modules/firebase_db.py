import os
import json
import tempfile
import firebase_admin
from firebase_admin import credentials, firestore, storage

FIREBASE_SERVICE_ACCOUNT = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
FIRESTORE_CLIENT = None
STORAGE_BUCKET = None


def _load_service_account():
    if FIREBASE_SERVICE_ACCOUNT and os.path.exists(FIREBASE_SERVICE_ACCOUNT):
        return FIREBASE_SERVICE_ACCOUNT

    if FIREBASE_SERVICE_ACCOUNT_JSON:
        try:
            data = json.loads(FIREBASE_SERVICE_ACCOUNT_JSON)
        except Exception as exc:
            print(f"[Firebase] Invalid FIREBASE_SERVICE_ACCOUNT_JSON: {exc}")
            return None
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(data, tmp)
        tmp.close()
        return tmp.name

    return None


def _get_firestore():
    global FIRESTORE_CLIENT
    if FIRESTORE_CLIENT is not None:
        return FIRESTORE_CLIENT

    keyfile = _load_service_account()
    if not keyfile:
        print("[Firebase] FIREBASE_SERVICE_ACCOUNT or FIREBASE_SERVICE_ACCOUNT_JSON not configured.")
        return None

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(keyfile)
            firebase_admin.initialize_app(cred)
        FIRESTORE_CLIENT = firestore.client()
        print("[Firebase] Firestore initialized.")
        return FIRESTORE_CLIENT
    except Exception as exc:
        print(f"[Firebase] Failed to initialize Firestore: {exc}")
        return None


def _get_storage_bucket():
    global STORAGE_BUCKET
    if STORAGE_BUCKET is not None:
        return STORAGE_BUCKET

    if not firebase_admin._apps:
        keyfile = _load_service_account()
        if keyfile:
            cred = credentials.Certificate(keyfile)
            firebase_admin.initialize_app(cred)

    try:
        STORAGE_BUCKET = storage.bucket()
        print("[Firebase] Storage initialized.")
        return STORAGE_BUCKET
    except Exception as exc:
        print(f"[Firebase] Failed to initialize Storage: {exc}")
        return None


def is_firebase_enabled():
    return _get_firestore() is not None


def _claim_doc(claim_id):
    db = _get_firestore()
    return db.collection("service_claims").document(str(claim_id)) if db else None


def create_remote_claim(claim_id, customer, product, claim, images=None, history=None):
    doc = _claim_doc(claim_id)
    if not doc:
        return False
    payload = {
        "customer": customer,
        "product": product,
        "claim": claim,
        "images": images or [],
        "payments": [],
        "dealer_assignments": [],
        "history": history or []
    }
    doc.set(payload, merge=True)
    return True


def update_remote_claim_status(claim_id, status, technician_note=None, final_cost=None, technician_id=None):
    doc = _claim_doc(claim_id)
    if not doc:
        return False
    changes = {
        "claim.status": status,
        "claim.technician_note": technician_note,
        "claim.final_cost": final_cost,
        "claim.technician_id": technician_id,
        "claim.updated_at": firestore.SERVER_TIMESTAMP
    }
    # Remove None values so merge doesn't overwrite with null
    changes = {k: v for k, v in changes.items() if v is not None}
    doc.set(changes, merge=True)
    return True


def append_remote_history(claim_id, old_status, new_status, changed_by, note):
    doc = _claim_doc(claim_id)
    if not doc:
        return False
    entry = {
        "old_status": old_status,
        "new_status": new_status,
        "changed_by": changed_by,
        "note": note,
        "changed_at": firestore.SERVER_TIMESTAMP
    }
    doc.update({"history": firestore.ArrayUnion([entry])})
    return True


def append_remote_payment(claim_id, payment):
    doc = _claim_doc(claim_id)
    if not doc:
        return False
    doc.update({"payments": firestore.ArrayUnion([payment])})
    return True


def append_remote_image(claim_id, image):
    doc = _claim_doc(claim_id)
    if not doc:
        return False
    doc.update({"images": firestore.ArrayUnion([image])})
    return True


def append_remote_dealer_assignment(claim_id, assignment):
    doc = _claim_doc(claim_id)
    if not doc:
        return False
    doc.update({"dealer_assignments": firestore.ArrayUnion([assignment])})
    return True


def upload_to_storage(file_path, destination_blob_name):
    bucket = _get_storage_bucket()
    if not bucket:
        return None
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    blob.make_public()
    return blob.public_url
