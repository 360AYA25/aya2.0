import base64
import json
import logging
from fastapi import FastAPI, Request
from google.cloud import storage, firestore

app = FastAPI()
logging.basicConfig(level=logging.INFO)

@app.post("/")
async def handle_pubsub(request: Request):
    envelope = await request.json()
    logging.info(f"Received envelope: {envelope}")

    if not envelope or 'message' not in envelope:
        logging.error("No Pub/Sub message received!")
        return {"status": "error", "reason": "No Pub/Sub message"}

    pubsub_message = envelope["message"]

    # Парсим сообщение
    data = pubsub_message.get("data")
    if data:
        payload = base64.b64decode(data).decode("utf-8")
        logging.info(f"Decoded data: {payload}")
        try:
            message_json = json.loads(payload)
        except Exception:
            message_json = {"raw": payload}
    else:
        message_json = {}

    # Пример: читаем promt для роли из GCS и пишем в Firestore
    role = message_json.get("role", "default")
    gcs_path = f"prompts/{role}.txt"
    bucket_name = "aya-shared"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)

    try:
        prompt_text = blob.download_as_text()
        logging.info(f"Loaded prompt for {role}: {prompt_text[:60]}...")
    except Exception as e:
        logging.error(f"Failed to load {gcs_path} from GCS: {e}")
        return {"status": "error", "reason": f"Cannot load {gcs_path} from GCS"}

    # Запись в Firestore
    db = firestore.Client()
    doc_ref = db.collection("prompts").document(role)
    doc_ref.set({"prompt": prompt_text})
    logging.info(f"Prompt for {role} saved to Firestore.")

    return {"status": "ok", "role": role}
