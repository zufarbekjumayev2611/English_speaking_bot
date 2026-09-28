# English Speaking Bot

Telegram bot + mini app: o'quvchi ingliz tilida og'zaki javob beradi,
sun'iy intellekt uni 5 mezon bo'yicha baholaydi va CEFR darajasini beradi.

- Ovozni matnga aylantirish: Groq Whisper
- Baholash: Groq (gpt-oss-120b)
- Savollar admin panel orqali qo'shiladi
- `EXAM_LANGUAGE=tr` qilib turk tili uchun ham ishlatsa bo'ladi

## Tuzilma

| Fayl | Vazifasi |
|---|---|
| `main.py` | Bot va serverni birga ishga tushiradi |
| `config.py` | Sozlamalar (muhit o'zgaruvchilaridan) |
| `languages.py` | Til sozlamalari (en / tr) |
| `bot.py` | O'quvchi menyusi va admin panel |
| `web.py` | Mini app serveri va API |
| `stt.py` | Ovozni matnga aylantirish |
| `grader.py` | Baholash |
| `db.py` | SQLite baza |
| `webapp/index.html` | Mini app interfeysi |
| `run_local.sh` | Kompyuterda sinash uchun (cloudflared tunnel bilan) |

## Muhit o'zgaruvchilari

| Nomi | Tavsif |
|---|---|
| `BOT_TOKEN` | @BotFather bergan token |
| `GROQ_API_KEY` | console.groq.com dan olingan kalit |
| `ADMIN_IDS` | Admin Telegram ID'lari, vergul bilan |
| `WEBAPP_URL` | Server manzili (https://...) |
| `EXAM_LANGUAGE` | `en` yoki `tr` (standart: `en`) |

Kalitlarni hech qachon kodga yoki GitHub'ga yozmang.

## Lokal ishga tushirish (Mac)

```bash
brew install cloudflared
cp .env.example .env   # keyin .env ni to'ldiring
./run_local.sh
```

## Render'ga joylash

- New → Web Service → shu repo
- Build Command: `pip install -r requirements.txt`
- Start Command: `python main.py`
- Environment bo'limiga yuqoridagi o'zgaruvchilarni qo'shing
