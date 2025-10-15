"""Utilities for persisting and retrieving user data in Firebase.

The NutriSigno application stores form submissions and generated plans
in Firebase’s Realtime Database or, when running in simulation mode,
into local files under `/tmp`.  This module abstracts away the details
of talking to the database.  It also exposes a helper for reloading
previous sessions given a user ID so that dashboards or reports can be
revisited via a link.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

# In simulation mode we don’t talk to Firebase at all.  We activate
# simulation either explicitly by setting SIMULATE=1 or when no
# Firebase credentials are provided.  This makes local development
# seamless and avoids raising errors when the environment is not
# configured for cloud access.
SIMULATE: bool = os.getenv("SIMULATE", "0") == "1" or not os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS"
)

def save_user_data(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Persist user data into the database.

    When running in simulation mode the data is simply written to a JSON
    file under `/tmp` named ``nutrisigno_session_{user_id}.json``.  When
    running in production the function will initialise the Firebase
    application if necessary and push the data into the realtime
    database.

    Parameters
    ----------
    user_id:
        Unique identifier for the session, typically a UUID.
    data:
        Dictionary of form inputs and other metadata to store.

    Returns
    -------
    dict
        A result object describing where the data was stored.
    """
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


def load_user_data(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user data previously stored with :func:`save_user_data`.

    In simulation mode this reads the JSON file written by
    :func:`save_user_data` and returns the ``data`` field.  In
    production it queries the Firebase realtime database and returns
    the most recent entry for the given user ID.  If no data can be
    found the function returns ``None``.

    Parameters
    ----------
    user_id:
        The identifier originally passed to :func:`save_user_data`.

    Returns
    -------
    Optional[Dict[str, Any]]
        The stored user data dictionary or ``None`` if not found.
    """
    if not user_id:
        return None
    if SIMULATE:
        path = f"/tmp/nutrisigno_session_{user_id}.json"
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            return payload.get("data")
        except Exception:
            return None

    # Real Firebase
    import firebase_admin
    from firebase_admin import credentials, db

    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        firebase_admin.initialize_app(cred, {"databaseURL": os.getenv("FIREBASE_DB_URL")})
    ref = db.reference(f"nutrisigno/sessions/{user_id}")
    try:
        entries = ref.get()
    except Exception:
        return None
    if not entries:
        return None
    # Firebase returns a dict keyed by push IDs; we take the newest by timestamp
    if isinstance(entries, dict):
        latest = max(entries.values(), key=lambda x: x.get("ts", 0))
        return latest.get("data")
    return None