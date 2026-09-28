#!/bin/bash
# Botni kompyuterda (Mac) ishga tushirish.
# Telegram mini app faqat https:// manzilda ochiladi, shuning uchun
# cloudflared bepul vaqtinchalik https manzil (tunnel) beradi.
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "❌ .env fayl topilmadi. .env.example ni nusxalab .env qiling va to'ldiring:"
  echo "   cp .env.example .env && open -e .env"
  exit 1
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "❌ cloudflared o'rnatilmagan. O'rnating:  brew install cloudflared"
  exit 1
fi

# 1) Python muhiti (faqat birinchi marta yaratiladi)
if [ ! -d .venv ]; then
  echo "📦 Python muhiti yaratilmoqda..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

# 2) Kalitlarni .env dan yuklash
set -a; source .env; set +a
export PORT=8080

# 3) https tunnel ochish va manzilini olish
echo "🌐 Tunnel ochilmoqda..."
cloudflared tunnel --url "http://localhost:$PORT" > tunnel.log 2>&1 &
TUNNEL_PID=$!
trap 'kill $TUNNEL_PID 2>/dev/null' EXIT

for i in $(seq 1 30); do
  WEBAPP_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' tunnel.log | head -1 || true)
  [ -n "$WEBAPP_URL" ] && break
  sleep 1
done
if [ -z "$WEBAPP_URL" ]; then
  echo "❌ Tunnel manzili olinmadi. tunnel.log faylini ko'ring."
  exit 1
fi
export WEBAPP_URL
echo "✅ Mini app manzili: $WEBAPP_URL"
echo "🤖 Bot ishga tushdi. To'xtatish uchun: Ctrl + C"

# 4) Botni ishga tushirish
python main.py
