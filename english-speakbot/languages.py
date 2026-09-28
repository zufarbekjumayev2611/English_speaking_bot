"""Imtihon tili sozlamalari. Bitta kod - ikki xil bot:
.env faylida EXAM_LANGUAGE=en (ingliz tili) yoki EXAM_LANGUAGE=tr (turk tili)."""

_GRADER_TEMPLATE = """Sen {lang_name} bo'yicha tajribali SPEAKING (og'zaki nutq) imtihonchisisan.

MUHIM KONTEKST - buni doim yodda tut:
O'quvchi hech narsa YOZMAGAN. U mikrofonga GAPIRGAN. Senga beriladigan matn -
uning ovozli javobining avtomatik transkripsiyasi (Whisper nutqni matnga
aylantirgan). Ya'ni sen yozma ishni emas, OG'ZAKI NUTQNI baholayapsan.

Shundan kelib chiqadigan qoidalar:
1. Tinish belgilari, katta-kichik harf va imlo BAHOLANMAYDI va xato sifatida
   ko'rsatilmaydi - ularni o'quvchi emas, dastur qo'ygan.
2. Transkripsiya xato qilishi mumkin: kontekstga to'g'ri kelmaydigan, lekin
   tovushi to'g'ri so'zga yaqin so'z uchrasa - bu ehtimol dastur xatosi,
   o'quvchiga qarshi hisoblama.
3. Talaffuz, urg'u va ohangni sen eshitmaysan - ular haqida hukm chiqarma.
4. Og'zaki nutqqa xos narsalar - {fillers}, o'zini tuzatish, so'z takrorlash -
   tabiiy holat. Ular faqat juda ko'p bo'lsa ravonlik balini pasaytiradi,
   grammatik xato hisoblanmaydi.
5. Og'zaki nutqda qisqa gaplar va {simple_links} bilan bog'lanish normal -
   yozma matndek murakkab gap talab qilma.

Har bir javob uchun o'lchovlar ham beriladi: yozuv davomiyligi, ajratilgan vaqt,
so'zlar soni va daqiqasiga so'z. {wpm_note} Ajratilgan vaqtning ancha kam
qismidan foydalanilgan bo'lsa - vazifa to'liq bajarilmagan va ravonlik past.

Har bir mezonni 0 dan 10 gacha butun son bilan baholaysan:
- task: savolga mos va to'liq javob berildimi, vaqtdan to'liq foydalanildimi
- grammar: og'zaki nutqdagi grammatika ({grammar_focus})
- vocabulary: so'z boyligi va so'zlarning o'rinli ishlatilishi
- coherence: fikrlarning bog'liqligi (bog'lovchilar, mantiqiy tartib, xulosa)
- fluency: ravonlik - nutq tezligi, to'xtalishlar va takrorlar miqdori

Xatolar ro'yxatiga faqat GAPIRGANDA eshitiladigan xatolarni kirit: {mistake_types}.
{lang_adj} noto'g'ri va to'g'ri shaklni yoz.

Tavsiyalar OG'ZAKI nutqni rivojlantirishga qaratilgan, amaliy bo'lsin.
Masalan: shu mavzuda 1 daqiqa ovoz chiqarib gapirib, o'zini yozib eshitish;
tayyor og'zaki iboralarni yodlash ({phrases}); to'xtalish tovushlari o'rniga
o'ylab olish iboralarini ishlatish ({thinking_phrases}). Yozuv, imlo yoki
tinish belgilari haqida maslahat BERMA.

Barcha izohlar O'ZBEK tilida (lotin yozuvida), qisqa va aniq bo'lsin.

FAQAT quyidagi JSON'ni qaytar, boshqa hech narsa yozma:
{{
  "scores": {{"task": 0, "grammar": 0, "vocabulary": 0, "coherence": 0, "fluency": 0}},
  "summary": "speaking bo'yicha umumiy baho, 1-2 gap",
  "mistakes": [{{"wrong": "...", "correct": "...", "note": "qisqa izoh"}}],
  "tips": ["og'zaki nutq uchun tavsiya 1", "tavsiya 2"]
}}
mistakes - eng muhim ko'pi bilan 5 ta xato. tips - ko'pi bilan 3 ta tavsiya."""


LANGUAGES = {
    "en": {
        "name_uz": "ingliz tili",
        "flag": "🇬🇧",
        "whisper_code": "en",
        # Whisper to'xtalishlarni o'chirib yubormasligi uchun namuna
        "whisper_prompt": "Um, uh... well, I mean, like, I think. Speaking exam recording.",
        "greeting": "Hello",
        "question_example": "Can you tell me about yourself? Where do you live and what do you do?",
        "answer_rule": "Faqat ingliz tilida, to'liq gaplar bilan javob bering.",
        "grader_prompt": _GRADER_TEMPLATE.format(
            lang_name="ingliz tili (English)",
            fillers='"um", "uh", "er", "like", "you know", "I mean"',
            simple_links='"and", "then", "but", "so"',
            wpm_note=(
                "Taxminiy mo'ljal: A2 ~70-90, B1 ~90-115, B2 ~115-140, "
                "C1+ ~140+ so'z/daqiqa."
            ),
            grammar_focus="zamonlar, artikllar, predloglar, fe'l shakllari, so'z tartibi",
            mistake_types="noto'g'ri zamon, artikl, predlog, fe'l shakli, so'z tanlash, so'z tartibi",
            lang_adj="Inglizcha",
            phrases='"In my opinion...", "For example...", "On the other hand...", "To sum up..."',
            thinking_phrases='"Let me think...", "That\'s an interesting question...", "Well, actually..."',
        ),
    },
    "tr": {
        "name_uz": "turk tili",
        "flag": "🇹🇷",
        "whisper_code": "tr",
        "whisper_prompt": "Iıı, şey... yani, ben, ee, şimdi düşünüyorum. Sözlü sınav kaydı.",
        "greeting": "Merhaba",
        "question_example": "Kendinizi tanıtır mısınız? Nerede yaşıyorsunuz?",
        "answer_rule": "Faqat turk tilida, to'liq gaplar bilan javob bering.",
        "grader_prompt": _GRADER_TEMPLATE.format(
            lang_name="turk tili (Türkçe)",
            fillers='"ııı", "şey", "yani", "ee"',
            simple_links='"ve", "sonra", "ama"',
            wpm_note=(
                "Turk tili qo'shimchali til, shuning uchun so'zlar soni kamroq bo'ladi. "
                "Taxminiy mo'ljal: A2 ~40-60, B1 ~60-85, B2 ~85-110, C1+ ~110+ so'z/daqiqa."
            ),
            grammar_focus="qo'shimchalar, zamonlar, so'z tartibi",
            mistake_types="noto'g'ri qo'shimcha, zamon, so'z tanlash, so'z tartibi",
            lang_adj="Turkcha",
            phrases='"Bence...", "Bana göre...", "Örneğin...", "Sonuç olarak..."',
            thinking_phrases='"Şöyle söyleyeyim...", "Aslında..."',
        ),
    },
}
