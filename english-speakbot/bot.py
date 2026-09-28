"""Telegram bot: o'quvchilar uchun imtihon tanlash, adminlar uchun savollar paneli."""
import time

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

import db
from config import EXAM_LANGUAGE, WEBAPP_URL, is_admin
from languages import LANGUAGES

LANG = LANGUAGES[EXAM_LANGUAGE]

router = Router()
router.message.filter(F.chat.type == "private")

BTN_EXAMS = "🎙 Imtihon topshirish"
BTN_ADMIN = "⚙️ Admin panel"


class NewExam(StatesGroup):
    title = State()


class NewQuestion(StatesGroup):
    text = State()
    photo = State()
    prep = State()
    answer = State()


def main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=BTN_EXAMS)]]
    if is_admin(user_id):
        rows.append([KeyboardButton(text=BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


# ================= O'QUVCHI =================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await db.save_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(
        f"{LANG['greeting']}, {message.from_user.first_name}! 👋\n\n"
        f"Bu bot {LANG['name_uz']}dan speaking imtihonini sun'iy intellekt yordamida o'tkazadi. "
        "Savolga ovoz bilan javob berasiz, bot esa grammatika, so'z boyligi va mazmun "
        "bo'yicha baholab, xatolaringizni ko'rsatadi.\n\n"
        "Boshlash uchun pastdagi tugmani bosing 👇",
        reply_markup=main_keyboard(message.from_user.id),
    )


@router.message(F.text == BTN_EXAMS)
async def list_exams_for_student(message: Message):
    exams = await db.list_active_exams()
    if not exams:
        await message.answer("Hozircha ochiq imtihon yo'q. Keyinroq qayta urinib ko'ring.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🎙 {e['title']}",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}/?exam={e['id']}&t={int(time.time())}"),
                )
            ]
            for e in exams
        ]
    )
    await message.answer(
        "Imtihonni tanlang. Tinch joyda bo'ling va mikrofonga ruxsat bering 🎧",
        reply_markup=kb,
    )


# ================= ADMIN: imtihonlar =================

async def _admin_panel_view():
    exams = await db.list_exams()
    lines = ["⚙️ <b>Admin panel</b>\n"]
    rows = []
    if not exams:
        lines.append("Hali imtihon yo'q. Birinchisini yarating.")
    for e in exams:
        status = "🟢" if e["is_active"] else "⚪️"
        lines.append(f"{status} <b>{e['title']}</b> — {e['q_count']} ta savol")
        rows.append([InlineKeyboardButton(text=f"{status} {e['title']}", callback_data=f"exam:{e['id']}")])
    rows.append([InlineKeyboardButton(text="➕ Yangi imtihon", callback_data="exam_new")])
    rows.append([InlineKeyboardButton(text="📊 Oxirgi natijalar", callback_data="results")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


async def _exam_view(exam_id: int):
    exam = await db.get_exam(exam_id)
    if not exam:
        return "Imtihon topilmadi.", None
    questions = await db.get_questions(exam_id)
    status = "🟢 Ochiq (o'quvchilarga ko'rinadi)" if exam["is_active"] else "⚪️ Yopiq"
    lines = [f"📚 <b>{exam['title']}</b>\n{status}\n"]
    if not questions:
        lines.append("Savollar yo'q. «➕ Savol qo'shish» tugmasini bosing.")
    for i, q in enumerate(questions, 1):
        photo = " 🖼" if q["photo_file_id"] else ""
        lines.append(f"<b>{i}.</b>{photo} {q['text']}\n    ⏳ {q['prep_sec']} s tayyorlanish, 🎙 {q['answer_sec']} s javob")
    rows = [[InlineKeyboardButton(text="➕ Savol qo'shish", callback_data=f"q_new:{exam_id}")]]
    for i, q in enumerate(questions, 1):
        rows.append([InlineKeyboardButton(text=f"🗑 {i}-savolni o'chirish", callback_data=f"q_del:{q['id']}")])
    toggle = "⚪️ Yopish" if exam["is_active"] else "🟢 O'quvchilarga ochish"
    rows.append([InlineKeyboardButton(text=toggle, callback_data=f"exam_toggle:{exam_id}")])
    rows.append([InlineKeyboardButton(text="🗑 Imtihonni o'chirish", callback_data=f"exam_del_ask:{exam_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == BTN_ADMIN)
@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    text, kb = await _admin_panel_view()
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "admin")
async def admin_panel_cb(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.clear()
    text, kb = await _admin_panel_view()
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("exam:"))
async def open_exam(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    text, kb = await _exam_view(int(callback.data.split(":")[1]))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "exam_new")
async def new_exam(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(NewExam.title)
    await callback.message.answer("Imtihon nomini yozing.\nMasalan: <i>Speaking mock #1</i>", parse_mode="HTML")
    await callback.answer()


@router.message(NewExam.title)
async def new_exam_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        return await message.answer("Nomni matn ko'rinishida yozing.")
    exam_id = await db.create_exam(title[:100])
    await state.clear()
    text, kb = await _exam_view(exam_id)
    await message.answer("✅ Imtihon yaratildi. Endi savollar qo'shing.")
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("exam_toggle:"))
async def toggle_exam(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    exam_id = int(callback.data.split(":")[1])
    exam = await db.get_exam(exam_id)
    if not exam["is_active"] and not await db.get_questions(exam_id):
        return await callback.answer("Avval kamida bitta savol qo'shing.", show_alert=True)
    await db.set_exam_active(exam_id, not exam["is_active"])
    text, kb = await _exam_view(exam_id)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer("Saqlandi")


@router.callback_query(F.data.startswith("exam_del_ask:"))
async def delete_exam_ask(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    exam_id = int(callback.data.split(":")[1])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"exam_del:{exam_id}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=f"exam:{exam_id}"),
            ]
        ]
    )
    await callback.message.edit_text("Imtihon va uning barcha savollari o'chiriladi. Davom etasizmi?", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("exam_del:"))
async def delete_exam(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await db.delete_exam(int(callback.data.split(":")[1]))
    text, kb = await _admin_panel_view()
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer("O'chirildi")


@router.callback_query(F.data == "results")
async def show_results(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    rows = await db.recent_results(20)
    if not rows:
        text = "Hali hech kim imtihon topshirmagan."
    else:
        lines = ["📊 <b>Oxirgi 20 ta natija</b>\n"]
        for r in rows:
            lines.append(f"{r['full_name'] or '?'} — <b>{r['score']}</b>/100 ({r['level']}), {r['title'] or '?'}")
        text = "\n".join(lines)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin")]])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# ================= ADMIN: savol qo'shish =================

SKIP_PHOTO = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Rasmsiz davom etish ➡️", callback_data="q_nophoto")]])


def _seconds_kb(prefix: str, options: list[int]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"{s} s", callback_data=f"{prefix}:{s}") for s in options]]
    )


@router.callback_query(F.data.startswith("q_new:"))
async def new_question(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(NewQuestion.text)
    await state.update_data(exam_id=int(callback.data.split(":")[1]))
    await callback.message.answer(
        f"1/4. Savol matnini yozing ({LANG['name_uz']}da).\n"
        f"Masalan: <i>{LANG['question_example']}</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(NewQuestion.text)
async def new_question_text(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        return await message.answer("Savolni matn ko'rinishida yozing.")
    await state.update_data(text=text[:1000])
    await state.set_state(NewQuestion.photo)
    await message.answer(
        "2/4. Savolga rasm kerak bo'lsa, rasmni yuboring (masalan, «rasmni tasvirlang» topshirig'i uchun).",
        reply_markup=SKIP_PHOTO,
    )


async def _ask_prep(message: Message, state: FSMContext):
    await state.set_state(NewQuestion.prep)
    await message.answer("3/4. O'quvchiga tayyorlanish uchun qancha vaqt beriladi?", reply_markup=_seconds_kb("q_prep", [0, 15, 30, 60]))


@router.message(NewQuestion.photo, F.photo)
async def new_question_photo(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await _ask_prep(message, state)


@router.callback_query(NewQuestion.photo, F.data == "q_nophoto")
async def new_question_nophoto(callback: CallbackQuery, state: FSMContext):
    await state.update_data(photo=None)
    await _ask_prep(callback.message, state)
    await callback.answer()


@router.message(NewQuestion.photo)
async def new_question_photo_wrong(message: Message):
    await message.answer("Rasm yuboring yoki «Rasmsiz davom etish» tugmasini bosing.", reply_markup=SKIP_PHOTO)


@router.callback_query(NewQuestion.prep, F.data.startswith("q_prep:"))
async def new_question_prep(callback: CallbackQuery, state: FSMContext):
    await state.update_data(prep=int(callback.data.split(":")[1]))
    await state.set_state(NewQuestion.answer)
    await callback.message.edit_text(
        "4/4. Javob berish uchun qancha vaqt beriladi?", reply_markup=_seconds_kb("q_ans", [30, 60, 90, 120])
    )
    await callback.answer()


@router.callback_query(NewQuestion.answer, F.data.startswith("q_ans:"))
async def new_question_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await db.add_question(data["exam_id"], data["text"], data.get("photo"), data["prep"], int(callback.data.split(":")[1]))
    await state.clear()
    await callback.message.edit_text("✅ Savol qo'shildi.")
    text, kb = await _exam_view(data["exam_id"])
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("q_del:"))
async def delete_question(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    q = await db.get_question(int(callback.data.split(":")[1]))
    if not q:
        return await callback.answer("Savol topilmadi.")
    await db.delete_question(q["id"])
    text, kb = await _exam_view(q["exam_id"])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer("O'chirildi")
