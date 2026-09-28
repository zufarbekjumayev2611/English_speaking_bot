"""Groq orqali baholash (bepul rejada ishlaydi, GROQ_API_KEY bilan).
Barcha javoblar BITTA so'rovda baholanadi - bu tejamkorroq."""
import json
import re

import aiohttp

from config import EXAM_LANGUAGE, GRADER_MODEL, GROQ_API_KEY
from languages import LANGUAGES

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = LANGUAGES[EXAM_LANGUAGE]["grader_prompt"]


class GraderError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(f"Groq {status}: {detail}")
        self.status = status


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


async def _ask(messages: list[dict], json_mode: bool) -> str:
    payload = {
        "model": GRADER_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_completion_tokens": 2500,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if "gpt-oss" in GRADER_MODEL:
        payload["reasoning_effort"] = "low"  # kamroq "o'ylash" = tezroq va kamroq token

    async with aiohttp.ClientSession() as session:
        async with session.post(
            GROQ_CHAT_URL,
            json=payload,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=aiohttp.ClientTimeout(total=90),
        ) as resp:
            body = await resp.json(content_type=None)
            if resp.status != 200:
                raise GraderError(resp.status, str(body)[:500])
            return body["choices"][0]["message"]["content"] or ""


def _metrics(transcript: str, duration, allotted) -> str:
    """Og'zaki nutq o'lchovlari: model ravonlikni faqat matndan emas, raqamlardan ham ko'rsin."""
    words = len(transcript.split())
    duration = float(duration or 0)
    info = [f"so'zlar soni: {words}"]
    if duration >= 3:
        info.append(f"yozuv davomiyligi: {duration:.0f} s")
        info.append(f"nutq tezligi: ~{words / (duration / 60):.0f} so'z/daqiqa")
    if allotted:
        info.append(f"ajratilgan vaqt: {allotted} s")
        if duration >= 3:
            info.append(f"vaqtdan foydalanish: {min(100, duration / allotted * 100):.0f}%")
    return "O'lchovlar: " + ", ".join(info)


async def grade(answers: list[dict]) -> dict:
    """answers: [{"position", "question", "transcript", "has_photo"}]"""
    parts = []
    for a in answers:
        photo = " (savolda rasm bor edi - o'quvchi rasmni tasvirlashi kerak edi)" if a.get("has_photo") else ""
        transcript = (a.get("transcript") or "").strip()
        parts.append(
            f"{a['position']}-savol{photo}: {a['question']}\n"
            f"{_metrics(transcript, a.get('duration_sec'), a.get('answer_sec'))}\n"
            f"O'quvchi gapirgan nutq (transkripsiya): {transcript or '(hech narsa eshitilmadi)'}"
        )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]

    try:
        text = await _ask(messages, json_mode=True)
    except GraderError as e:
        # Ba'zi modellar JSON rejimini qo'llamaydi - oddiy rejimda qayta so'raymiz.
        if e.status != 400:
            raise
        text = await _ask(messages, json_mode=False)
    result = _extract_json(text)

    # Umumiy ball va darajani modelga emas, kodga hisoblatamiz - doim to'g'ri chiqadi.
    s = result.get("scores") or {}
    vals = []
    for k in ("task", "grammar", "vocabulary", "coherence", "fluency"):
        try:
            v = max(0, min(10, round(float(s.get(k, 0)))))
        except (TypeError, ValueError):
            v = 0
        s[k] = v
        vals.append(v)
    result["scores"] = s
    result["total"] = round(sum(vals) / len(vals) * 10)
    result["level"] = level_for(result["total"])
    result.setdefault("summary", "")
    result["mistakes"] = [m for m in (result.get("mistakes") or []) if isinstance(m, dict)][:5]
    result["tips"] = [str(t) for t in (result.get("tips") or [])][:3]
    return result


def level_for(total: int) -> str:
    for limit, level in ((30, "A1"), (45, "A2"), (60, "B1"), (75, "B2"), (90, "C1")):
        if total < limit:
            return level
    return "C2"
