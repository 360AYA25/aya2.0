import os
import openai
import asyncio

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
openai.api_key = os.environ["OPENAI_KEY"]

async def ask_gpt(prompt: str, topic: str) -> str:
    loop = asyncio.get_running_loop()
    resp = await loop.run_in_executor(
        None,
        lambda: openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": f"topic: {topic}"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
        ),
    )
    return resp.choices[0].message['content'].strip()

