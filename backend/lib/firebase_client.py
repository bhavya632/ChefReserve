import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()

def init_firestore():
    if firebase_admin._apps:
        return firestore.client()

    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT", "").strip()
    if service_account_path:
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    else:
        try:
            firebase_admin.initialize_app()
        except Exception as exc:
            raise RuntimeError(
                "Firebase initialization failed. Set FIREBASE_SERVICE_ACCOUNT "
                "or run `gcloud auth application-default login` for ADC."
            ) from exc

    return firestore.client()

db = init_firestore()
