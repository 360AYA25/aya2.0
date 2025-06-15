from google.cloud import firestore_async

db = firestore_async.Client()

async def save_dialog(uid: str, collection: str, message: dict):
    """
    uid         – id пользователя Telegram
    collection  – например 'christianity'
    message     – {role:'user'|'bot', text:'...'}
    """
    doc = db.collection("dialogs").document(uid).collection(collection).document()
    await doc.set(message)

async def load_history(uid: str, collection: str, limit: int = 20):
    q = (
        db.collection("dialogs").document(uid)
          .collection(collection).order_by("timestamp", direction=firestore_async.Enum.DESCENDING)
          .limit(limit)
    )
    return [doc.to_dict() async for doc in q.stream()]
