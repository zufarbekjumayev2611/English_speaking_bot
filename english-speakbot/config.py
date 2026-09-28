"""Barcha sozlamalar muhit o'zgaruvchilaridan (Render -> Environment) olinadi.
Maxfiy kalitlarni HECH QACHON kod ichiga yozmang - repo public."""
import os


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} muhit o'zgaruvchisi topilmadi. Render -> Environment bo'limiga qo'shing.")
    return value


BOT_TOKEN = _required("BOT_TOKEN")
GROQ_API_KEY = _required("GROQ_API_KEY")

# Mini app va API shu manzilda ishlaydi (Render service manzili), https:// bilan.
WEBAPP_URL = _required("WEBAPP_URL").rstrip("/")

# Adminlar: vergul bilan ajratilgan Telegram ID'lar, masalan "111111111,222222222"
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x]

# Baholovchi model - Groq'dagi bepul model (xuddi shu GROQ_API_KEY bilan ishlaydi).
GRADER_MODEL = os.getenv("GRADER_MODEL", "openai/gpt-oss-120b")

# Imtihon tili: "en" - ingliz tili, "tr" - turk tili (.env: EXAM_LANGUAGE=en)
EXAM_LANGUAGE = os.getenv("EXAM_LANGUAGE", "en").strip().lower()
if EXAM_LANGUAGE not in ("en", "tr"):
    raise RuntimeError("EXAM_LANGUAGE faqat 'en' yoki 'tr' bo'lishi mumkin.")

# Groq Whisper - nutqni matnga aylantiradi.
STT_MODEL = os.getenv("STT_MODEL", "whisper-large-v3-turbo")

DB_PATH = os.getenv("DB_PATH", "speakbot.db")
PORT = int(os.getenv("PORT", "8080"))


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
