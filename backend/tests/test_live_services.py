import asyncio
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv(r"e:\SIH2026\project\BIS-Compass\backend\.env", override=True)

async def test():
    # 1. NVIDIA
    api_key_nv = os.getenv("NVIDIA_API_KEY")
    headers_nv = {"Authorization": f"Bearer {api_key_nv}", "Content-Type": "application/json"}
    schema = {
        "type": "object",
        "properties": {
            "product_name": {"type": "string"},
            "materials": {"type": "array", "items": {"type": "string"}},
            "intended_use": {"type": "string"}
        },
        "required": ["product_name", "materials"]
    }
    payload_nv = {
        "model": os.getenv("NVIDIA_CHAT_MODEL"),
        "messages": [
            {"role": "system", "content": f"You must respond with valid JSON that strictly conforms to this schema:\n{json.dumps(schema)}"},
            {"role": "user", "content": "I manufacture stainless steel water bottles."}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Testing NVIDIA with schema...")
        res_nv = await client.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers_nv, json=payload_nv)
        print("NVIDIA status:", res_nv.status_code)
        if res_nv.status_code == 200:
            print("NVIDIA content:", res_nv.json()["choices"][0]["message"]["content"])
        else:
            print("NVIDIA error:", res_nv.text)

        # 2. Groq
        api_key_gr = os.getenv("GROQ_API_KEY")
        headers_gr = {"Authorization": f"Bearer {api_key_gr}", "Content-Type": "application/json"}
        payload_gr = {
            "model": os.getenv("GROQ_CHAT_MODEL"),
            "messages": [
                {"role": "system", "content": f"You must respond with valid JSON that strictly conforms to this schema:\n{json.dumps(schema)}"},
                {"role": "user", "content": "I manufacture stainless steel water bottles."}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        print("\nTesting Groq with schema...")
        res_gr = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers_gr, json=payload_gr)
        print("Groq status:", res_gr.status_code)
        if res_gr.status_code == 200:
            print("Groq content:", res_gr.json()["choices"][0]["message"]["content"])
        else:
            print("Groq error:", res_gr.text)

if __name__ == "__main__":
    asyncio.run(test())
