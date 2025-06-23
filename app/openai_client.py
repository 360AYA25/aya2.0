import os
import openai

openai.api_key = os.environ["OPENAI_KEY"]


async def ask_gpt(user_id: str, prompt: str) -> str:
    """
    Unified wrapper for ChatCompletion.
    """
    resp = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"user_id:{user_id}"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=512,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()

