"""Mini app backend: sahifani beradi, audio qabul qiladi, transkripsiya va baholashni boshqaradi."""
import hashlib
import hmac
import json
import logging
import os
import time
from urllib.parse import parse_qsl

from aiogram import Bot
from aiohttp import web

import db
import grader
import stt
from config import ADMIN_IDS, BOT_TOKEN, EXAM_LANGUAGE
from languages import LANGUAGES

WEBAPP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp")
MAX_AUDIO_BYTES = 15 * 1024 * 1024
INIT_DATA_MAX_AGE = 24 * 3600

log = logging.getLogger("web")


# ---------- Telegram foydalanuvchisini tekshirish ----------

def verify_init_data(init_data: str) -> dict | None:
    """Mini app'dan kelgan so'rov haqiqatan Telegram'dan va shu foydalanuvchidan
    ekanini tekshiradi. Soxta so'rovlar (boshqa odam nomidan) rad etiladi."""
    if not init_data:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash")
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, received_hash):
            return None
        if time.time() - int(pairs.get("auth_date", "0")) > INIT_DATA_MAX_AGE:
            return None
        return json.loads(pairs["user"])
    except Exception:
        return None


def _user_or_401(request: web.Request) -> dict:
    user = verify_init_data(request.headers.get("X-Init-Data", ""))
    if not user:
        raise web.HTTPUnauthorized(text=json.dumps({"error": "Botni Telegram ichidan qayta oching."}), content_type="application/json")
    return user


def _error(status: int, message: str):
    return web.json_response({"error": message}, status=status)


# ---------- Sahifa ----------

async def index(request: web.Request):
    return web.FileResponse(
        os.path.join(WEBAPP_DIR, "index.html"),
        headers={"Cache-Control": "no-store"},
    )


# ---------- API ----------

async def start_exam(request: web.Request):
    user = _user_or_401(request)
    exam_id = int(request.match_info["exam_id"])
    exam = await db.get_exam(exam_id)
    if not exam or not exam["is_active"]:
        return _error(404, "Bu imtihon hozir yopiq.")
    questions = await db.get_questions(exam_id)
    if not questions:
        return _error(404, "Bu imtihonda hali savol yo'q.")

    await db.save_user(user["id"], " ".join(filter(None, [user.get("first_name"), user.get("last_name")])), user.get("username"))
    attempt_id = await db.create_attempt(user["id"], exam_id)
    return web.json_response(
        {
            "attempt_id": attempt_id,
            "title": exam["title"],
        "flag": LANGUAGES[EXAM_LANGUAGE]["flag"],
        "answer_rule": LANGUAGES[EXAM_LANGUAGE]["answer_rule"],
            "questions": [
                {
                    "id": q["id"],
                    "text": q["text"],
                    "photo": f"/api/photo/{q['id']}" if q["photo_file_id"] else None,
                    "prep_sec": q["prep_sec"],
                    "answer_sec": q["answer_sec"],
                }
                for q in questions
            ],
        }
    )


_photo_cache: dict[int, bytes] = {}


async def question_photo(request: web.Request):
    question_id = int(request.match_info["question_id"])
    if question_id not in _photo_cache:
        q = await db.get_question(question_id)
        if not q or not q["photo_file_id"]:
            raise web.HTTPNotFound()
        bot: Bot = request.app["bot"]
        file = await bot.get_file(q["photo_file_id"])
        data = await bot.download_file(file.file_path)
        _photo_cache[question_id] = data.read()
    return web.Response(body=_photo_cache[question_id], content_type="image/jpeg", headers={"Cache-Control": "max-age=3600"})


async def _own_attempt(user: dict, attempt_id: int):
    attempt = await db.get_attempt(attempt_id)
    if not attempt or attempt["telegram_id"] != user["id"]:
        return None
    return attempt


async def upload_answer(request: web.Request):
    user = _user_or_401(request)
    form = await request.post()
    try:
        attempt_id = int(form["attempt_id"])
        question_id = int(form["question_id"])
        audio_field = form["audio"]
        duration = max(0.0, min(float(form.get("duration") or 0), 600.0))
    except (KeyError, ValueError):
        return _error(400, "So'rov noto'g'ri.")

    attempt = await _own_attempt(user, attempt_id)
    if not attempt or attempt["status"] != "in_progress":
        return _error(403, "Bu urinish yakunlangan yoki sizga tegishli emas.")

    audio = audio_field.file.read()
    if len(audio) > MAX_AUDIO_BYTES:
        return _error(413, "Yozuv juda katta.")

    transcript = ""
    if len(audio) > 1000:  # juda kichik fayl = deyarli bo'sh yozuv
        try:
            transcript = await stt.transcribe(audio, audio_field.content_type)
        except Exception:
            log.exception("Transkripsiya xatosi (attempt %s)", attempt_id)
            return _error(503, "Ovozni matnga aylantirib bo'lmadi. Qayta yozib ko'ring.")

    await db.save_answer(attempt_id, question_id, transcript, duration)
    return web.json_response({"ok": True, "heard": bool(transcript)})


def _result_message(title: str, r: dict) -> str:
    s = r.get("scores", {})
    lines = [
        f"🎙 <b>{title}</b> natijasi\n",
        f"Umumiy ball: <b>{r['total']}/100</b>  •  Daraja: <b>{r['level']}</b>\n",
        f"✅ Vazifa: {s.get('task', 0)}/10",
        f"📐 Grammatika: {s.get('grammar', 0)}/10",
        f"📚 So'z boyligi: {s.get('vocabulary', 0)}/10",
        f"🔗 Izchillik: {s.get('coherence', 0)}/10",
        f"🗣 Ravonlik: {s.get('fluency', 0)}/10\n",
        r.get("summary", ""),
    ]
    if r.get("mistakes"):
        lines.append("\n<b>Asosiy xatolar:</b>")
        for m in r["mistakes"][:5]:
            lines.append(f"❌ {m.get('wrong', '')} → ✅ {m.get('correct', '')}\n    <i>{m.get('note', '')}</i>")
    if r.get("tips"):
        lines.append("\n<b>Tavsiyalar:</b>")
        lines += [f"• {t}" for t in r["tips"][:3]]
    return "\n".join(lines)


async def finish_exam(request: web.Request):
    user = _user_or_401(request)
    body = await request.json()
    attempt = await _own_attempt(user, int(body.get("attempt_id", 0)))
    if not attempt:
        return _error(403, "Urinish topilmadi.")
    if attempt["status"] == "done":
        return web.json_response(json.loads(attempt["result_json"]))

    answers = await db.get_answers(attempt["id"])
    if not answers:
        return _error(400, "Hech bir javob yozib olinmadi.")

    bot: Bot = request.app["bot"]
    try:
        result = await grader.grade(answers)
    except Exception as e:
        log.exception("Baholash xatosi (attempt %s)", attempt["id"])
        if getattr(e, "status", None) == 429:
            # Groq bepul rejasi limiti (daqiqalik yoki kunlik) - biroz kutish kerak.
            return _error(503, "Hozir baholash navbati band. Javoblaringiz saqlandi - "
                               "1-2 daqiqadan keyin «Qayta urinish»ni bosing.")
        if getattr(e, "status", None) in (401, 403):
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, "⚠️ Groq kaliti ishlamayapti (GROQ_API_KEY) - imtihonlar baholanmayapti.")
                except Exception:
                    pass
        return _error(503, "Baholashda xatolik bo'ldi. Bir daqiqadan keyin «Qayta urinish»ni bosing.")

    await db.finish_attempt(attempt["id"], result["total"], result["level"], result)

    exam = await db.get_exam(attempt["exam_id"])
    title = exam["title"] if exam else "Imtihon"
    try:
        await bot.send_message(user["id"], _result_message(title, result), parse_mode="HTML")
    except Exception:
        log.exception("Natijani o'quvchiga yuborib bo'lmadi")
    name = user.get("first_name", "?")
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"📥 {name} (<code>{user['id']}</code>) — {title}: <b>{result['total']}/100</b> ({result['level']})", parse_mode="HTML")
        except Exception:
            pass
    return web.json_response(result)


def create_app(bot: Bot) -> web.Application:
    app = web.Application(client_max_size=MAX_AUDIO_BYTES + 1024 * 1024)
    app["bot"] = bot
    app.router.add_get("/", index)
    app.router.add_get("/health", lambda r: web.Response(text="ok"))
    app.router.add_get("/api/exam/{exam_id}", start_exam)
    app.router.add_get("/api/photo/{question_id}", question_photo)
    app.router.add_post("/api/answer", upload_answer)
    app.router.add_post("/api/finish", finish_exam)
    return app
