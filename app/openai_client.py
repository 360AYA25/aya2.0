import openai, os, asyncio

openai.api_key = os.environ["OPENAI_KEY"]

async def ask_gpt(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    resp = await loop.run_in_executor(
        None,
        lambda: openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        ),
    )
    return resp.choices[0].message.content.strip()

