"""Tier 3 Multimodal Vision API via OpenRouter."""
import base64
import logging
import os
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


async def extract_via_openrouter_vision(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    api_key: Optional[str] = None,
) -> Optional[str]:
    """Sends document image to OpenRouter Vision API for text/field extraction."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key or not image_bytes:
        return None

    try:
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{b64_img}"

        payload = {
            "model": "google/gemini-2.0-flash-001",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all text and KYC fields (Name, Date of Birth, Document Number, Expiry Date) from this identity document verbatim.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        },
                    ],
                }
            ],
            "max_tokens": 1000,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            return None
    except Exception as e:
        logger.warning("OpenRouter Vision API call failed, falling back to regex: %s", e)
        return None
