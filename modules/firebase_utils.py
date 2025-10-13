# modules/firebase_utils.py
from __future__ import annotations
import os, time, json
from typing import Dict, Any

SIMULATE = os.getenv("SIMULATE", "0") == "1" or not os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

def save_user_data(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Salva dados no RTDB; no modo simulado, grava em /tmp e retorna OK."""
    if SIMULATE:
        path = f"/tmp/nutrisigno_session_{user_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"user_id": user_id, "data": data, "ts": int(time.time())}, f, ensure_ascii=False, indent=2)
        return {"ok": True, "mode": "simulated", "path": path}

    # Real Firebase
    import firebase_admin
    from firebase_admin import credentials, db
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        firebase_admin.initialize_app(cred, {"databaseURL": os.getenv("FIREBASE_DB_URL")})
    ref = db.reference(f"nutrisigno/sessions/{user_id}")
    ref.push().set({"data": data, "ts": int(time.time())})
    return {"ok": True, "mode": "firebase"}

def upload_pdf(local_path: str, dest_path: str) -> str:
    """Envia PDF ao Storage; no modo simulado, retorna file://."""
    if SIMULATE:
        return f"file://{local_path}"

    import firebase_admin
    from firebase_admin import storage
    if not firebase_admin._apps:
        raise RuntimeError("Firebase não inicializado")
    bucket = storage.bucket()
    blob = bucket.blob(dest_path)
    blob.upload_from_filename(local_path, content_type="application/pdf")
    blob.make_public()
    return blob.public_url