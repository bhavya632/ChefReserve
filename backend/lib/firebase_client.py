import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from dotenv import load_dotenv

load_dotenv()


def _load_firebase_credentials():
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if service_account_json:
        try:
            return credentials.Certificate(json.loads(service_account_json))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON."
            ) from exc

    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT", "").strip()
    if service_account_path:
        return credentials.Certificate(service_account_path)

    return None


def init_firestore():
    if firebase_admin._apps:
        return firestore.client()

    cred = _load_firebase_credentials()
    if cred:
        firebase_admin.initialize_app(cred)
    else:
        try:
            firebase_admin.initialize_app()
        except Exception as exc:
            raise RuntimeError(
                "Firebase initialization failed. Set FIREBASE_SERVICE_ACCOUNT_JSON "
                "or FIREBASE_SERVICE_ACCOUNT, or configure ADC."
            ) from exc

    return firestore.client()

db = init_firestore()
