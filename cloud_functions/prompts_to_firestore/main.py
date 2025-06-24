import base64
import json
from google.cloud import firestore

def prompt_to_firestore(event, context):
    db = firestore.Client()
    data = base64.b64decode(event['data']).decode('utf-8')
    msg = json.loads(data)
    role = msg.get('role')
    if not role:
        print('No role in PubSub message')
        return
    # Чтение промпта из GCS
    from google.cloud import storage
    client = storage.Client()
    bucket = client.get_bucket('aya-shared')
    blob = bucket.blob(f'prompts/{role}.txt')
    text = blob.download_as_text()
    db.collection('prompts').document(role).set({'text': text})
    print(f'Prompt for {role} updated in Firestore')

