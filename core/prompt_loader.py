from google.cloud import firestore
from typing import Dict

_PROMPT_CACHE: Dict[str, str] = {}

def load_prompts_from_firestore() -> Dict[str, str]:
    db = firestore.Client()
    prompts_ref = db.collection("prompts")
    docs = prompts_ref.stream()
    prompts = {}
    for doc in docs:
        prompts[doc.id] = doc.to_dict().get("prompt", "")
    return prompts

def reload_prompts() -> None:
    global _PROMPT_CACHE
    _PROMPT_CACHE = load_prompts_from_firestore()

def get_prompt(role: str) -> str:
    return _PROMPT_CACHE.get(role, "")

# При инициализации сразу загружаем промпты
reload_prompts()
