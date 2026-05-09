"""
ai_helper.py — AI-powered features using Claude API
1. analyze_device_image() → Extract brand/model/serial from device photo
2. analyze_damage_image() → Describe visible damage
3. generate_diagnosis_note() → AI technician note suggestion
"""

import base64
import json
import re


def _call_claude(messages, system_prompt, max_tokens=800):
    """Internal function to call Claude API."""
    try:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": _get_api_key()
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]

    except Exception as e:
        return json.dumps({"error": str(e)})


def _get_api_key():
    """Load API key from env or config file."""
    import os
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config.txt"
        )
        if os.path.exists(config_path):
            with open(config_path) as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.strip().split("=", 1)[1]
    return key


def analyze_device_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Send device photo to Claude → extract device info automatically.
    Returns dict: {brand, model_name, serial_number, confidence, notes}
    """
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    system = """You are an expert electronics technician AI. 
    When given a photo of a device or its label, extract device information.
    Always respond with ONLY valid JSON, no extra text."""

    messages = [{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": b64
                }
            },
            {
                "type": "text",
                "text": """Analyze this device/label photo and extract:
                Return ONLY this JSON (no markdown, no explanation):
                {
                  "brand": "extracted brand or empty string",
                  "model_name": "extracted model name or empty string",
                  "serial_number": "extracted serial number or empty string",
                  "purchase_date": "YYYY-MM-DD if visible else empty string",
                  "device_type": "Laptop/Desktop/Printer/Monitor/etc",
                  "visible_damage": "describe any visible physical damage, scratches, cracks etc",
                  "confidence": "high/medium/low",
                  "notes": "any other relevant info from label"
                }"""
            }
        ]
    }]

    raw = _call_claude(messages, system, max_tokens=500)

    try:
        # Strip markdown fences if present
        clean = re.sub(r"```[a-z]*\n?", "", raw).strip()
        result = json.loads(clean)
        return {"success": True, **result}
    except Exception:
        return {
            "success": False,
            "error": "Could not parse AI response",
            "raw": raw,
            "brand": "", "model_name": "", "serial_number": "",
            "visible_damage": "", "confidence": "low", "notes": raw[:200]
        }


def analyze_damage_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Analyze damage/condition photo → generate condition report.
    """
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    system = "You are an electronics repair technician. Analyze device condition from photos. Respond only in JSON."

    messages = [{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mime_type, "data": b64}
            },
            {
                "type": "text",
                "text": """Analyze this device condition photo. Return ONLY this JSON:
                {
                  "overall_condition": "Excellent/Good/Fair/Poor/Damaged",
                  "physical_damage": ["list of visible damages"],
                  "screen_condition": "condition or N/A",
                  "body_condition": "scratches/dents/cracks description",
                  "completeness": "all parts present / missing parts description",
                  "report": "2-3 sentence professional condition report in English"
                }"""
            }
        ]
    }]

    raw = _call_claude(messages, system, max_tokens=400)
    try:
        clean = re.sub(r"```[a-z]*\n?", "", raw).strip()
        return {"success": True, **json.loads(clean)}
    except Exception:
        return {"success": False, "report": raw[:300], "overall_condition": "Unknown"}


def suggest_diagnosis(issue_description: str, brand: str, model: str) -> str:
    """
    Given issue description → AI suggests possible causes and repair steps.
    Returns plain text technician note suggestion.
    """
    system = """You are an expert electronics repair technician with 15 years experience.
    Give concise, practical diagnostic suggestions. Keep it under 100 words."""

    messages = [{
        "role": "user",
        "content": f"""Device: {brand} {model}
Issue reported by customer: {issue_description}

Suggest: possible cause, likely repair needed, estimated difficulty (Easy/Medium/Hard).
Keep response concise and professional."""
    }]

    return _call_claude(messages, system, max_tokens=200)


def is_configured() -> bool:
    """Check if API key is available."""
    return bool(_get_api_key())
