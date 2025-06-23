from typing import Any

_db: Any = None

def get_db():
    global _db
    if _db is None:
        # Тут инициализация, если потребуется
        pass
    return _db

def example_usage():
    db = get_db()
    if db is not None:
        db.collection("some_collection")
    else:
        # обработка случая, когда db не инициализирован
        pass

