import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from aiohttp import web

import database as db

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_ИЛИ_ЗАДАЙ_В_RENDER")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# ================== СОСТОЯНИЯ ==================
class OpenShift(StatesGroup):
    fio = State()
    date = State()
    shift_type = State()
    notes = State()


class CloseShift(StatesGroup):
    incidents = State()
    powder_ral = State()
    powder_weight = State()
    details_name = State()
    details_count = State()


# ================== КЛАВИАТУРЫ ==================
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Открыть смену")],
            [KeyboardButton(text="🔴 Закрыть смену")],
        ],
        resize_keyboard=True,
    )


def shift_type_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="День"), KeyboardButton(text="Ночь")],
        ],
        resize_keyboard=True,
    )


def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def no_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="нет")]],
        resize_keyboard=True,
    )


def powder_more_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ещё цвет", callback_data="powder_more")],
            [InlineKeyboardButton(text="✅ Дальше", callback_data="powder_done")],
        ]
    )


def details_ask_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить деталь", callback_data="details_more")],
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="details_skip")],
            [InlineKeyboardButton(text="✅ Дальше", callback_data="details_done")],
        ]
    )


def details_more_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ещё деталь", callback_data="details_more")],
            [InlineKeyboardButton(text="✅ Дальше", callback_data="details_done")],
        ]
    )


# ================== СТАРТ ==================
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Это бот учёта смен.\n\n"
        "👨‍💻 Создатель: @PHARAOH_G6\n\n"
        "Выбери действие:",
        reply_markup=main_menu(),
    )


# ================== ОТКРЫТИЕ СМЕНЫ ==================
@dp.message(F.text == "🟢 Открыть смену")
async def open_shift_start(message: Message, state: FSMContext):
    existing = db.get_open_shift(message.from_user.id)
    if existing:
        await message.answer(
            f"⚠️ У тебя уже есть открытая смена от {existing[2]} ({existing[3]}).\n"
            "Сначала закрой её."
        )
        return

    await state.set_state(OpenShift.fio)
    await message.answer("Введи ФИО:", reply_markup=cancel_kb())


# Универсальная отмена
@dp.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu())


@dp.message(OpenShift.fio, F.text == "❌ Отмена")
@dp.message(OpenShift.date, F.text == "❌ Отмена")
@dp.message(OpenShift.notes, F.text == "❌ Отмена")
@dp.message(CloseShift.incidents, F.text == "❌ Отмена")
@dp.message(CloseShift.powder_ral, F.text == "❌ Отмена")
@dp.message(CloseShift.powder_weight, F.text == "❌ Отмена")
@dp.message(CloseShift.details_name, F.text == "❌ Отмена")
@dp.message(CloseShift.details_count, F.text == "❌ Отмена")
async def cancel_any(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu())


@dp.message(OpenShift.fio)
async def open_fio(message: Message, state: FSMContext):
    await state.update_data(fio=message.text.strip())
    await state.set_state(OpenShift.date)
    await message.answer("Введи дату смены (например, 12.05.2026):", reply_markup=cancel_kb())


@dp.message(OpenShift.date)
async def open_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text.strip())
    await state.set_state(OpenShift.shift_type)
    await message.answer("Выбери тип смены:", reply_markup=shift_type_kb())


@dp.message(OpenShift.shift_type, F.text.in_(["День", "Ночь"]))
async def open_type(message: Message, state: FSMContext):
    await state.update_data(shift_type=message.text)
    await state.set_state(OpenShift.notes)
    await message.answer(
        "Введи замечания по смене (если нет — напиши «нет»):",
        reply_markup=no_kb(),
    )


@dp.message(OpenShift.shift_type)
async def open_type_invalid(message: Message):
    await message.answer("Пожалуйста, выбери «День» или «Ночь»:", reply_markup=shift_type_kb())


@dp.message(OpenShift.notes)
async def open_notes(message: Message, state: FSMContext):
    data = await state.get_data()
    notes = message.text.strip()

    db.create_shift(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        fio=data["fio"],
        shift_date=data["date"],
        shift_type=data["shift_type"],
        open_notes=notes,
    )
    await state.clear()

    await message.answer(
        "✅ <b>Смена открыта!</b>\n\n"
        f"👤 ФИО: {data['fio']}\n"
        f"📅 Дата: {data['date']}\n"
        f"🕐 Тип: {data['shift_type']}\n"
        f"📝 Замечания: {notes}",
        reply_markup=main_menu(),
    )


# ================== ЗАКРЫТИЕ СМЕНЫ ==================
@dp.message(F.text == "🔴 Закрыть смену")
async def close_shift_start(message: Message, state: FSMContext):
    shift = db.get_open_shift(message.from_user.id)
    if not shift:
        await message.answer("❌ У тебя нет открытой смены.")
        return

    await state.update_data(powders=[], details=[])
    await state.set_state(CloseShift.incidents)
    await message.answer(
        "Введи происшествия на смене (если нет — напиши «нет»):",
        reply_markup=no_kb(),
    )


# --- ПРОИСШЕСТВИЯ ---
@dp.message(CloseShift.incidents)
async def close_incidents(message: Message, state: FSMContext):
    await state.update_data(incidents=message.text.strip())
    await state.set_state(CloseShift.powder_ral)
    await message.answer(
        "Какой был порошок? Введи RAL (например, 9005):",
        reply_markup=cancel_kb(),
    )


# --- ПОРОШОК ---
@dp.message(CloseShift.powder_ral)
async def close_powder_ral(message: Message, state: FSMContext):
    ral = message.text.strip().upper().replace("RAL", "").strip()
    if not ral:
        await message.answer("⚠️ Введи номер RAL (например, 9005):")
        return
    await state.update_data(current_ral=ral)
    await state.set_state(CloseShift.powder_weight)
    await message.answer(f"Сколько килограмм? RAL {ral}:")


@dp.message(CloseShift.powder_weight)
async def close_powder_weight(message: Message, state: FSMContext):
    data = await state.get_data()
    ral = data["current_ral"]
    weight = message.text.strip().replace(",", ".")

    try:
        float(weight)
    except ValueError:
        await message.answer(f"⚠️ Введи число (например, 2.5) для RAL {ral}:")
        return

    powders = data.get("powders", [])
    powders.append({"ral": ral, "weight": weight})
    await state.update_data(powders=powders)

    lines = [f"• RAL {p['ral']} — {p['weight']} кг" for p in powders]
    text = "Текущий список порошка:\n" + "\n".join(lines) + "\n\nЧто дальше?"

    await state.set_state(None)
    await message.answer(text, reply_markup=powder_more_kb())


@dp.callback_query(F.data == "powder_more")
async def powder_add_more(call: CallbackQuery, state: FSMContext):
    await state.set_state(CloseShift.powder_ral)
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await call.message.answer("Введи следующий RAL:", reply_markup=cancel_kb())
    await call.answer()


@dp.callback_query(F.data == "powder_done")
async def powder_finish(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    powders = data.get("powders", [])

    if not powders:
        await call.answer("Добавь хотя бы один цвет!", show_alert=True)
        return

    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    # Переходим к этапу с деталями
    await state.set_state(None)
    await call.message.answer(
        "🔩 Хочешь добавить названия покрашенных деталей и их количество?\n"
        "(по желанию)",
        reply_markup=details_ask_kb(),
    )
    await call.answer()


# --- ДЕТАЛИ ---
@dp.callback_query(F.data == "details_skip")
async def details_skip(call: CallbackQuery, state: FSMContext):
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await call.answer()
    await finalize_shift(call.message, call.from_user.id, state)


@dp.callback_query(F.data == "details_more")
async def details_more(call: CallbackQuery, state: FSMContext):
    await state.set_state(CloseShift.details_name)
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await call.message.answer(
        "Введи название детали (например, «Кронштейн А»):",
        reply_markup=cancel_kb(),
    )
    await call.answer()


@dp.message(CloseShift.details_name)
async def details_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("⚠️ Название не может быть пустым:")
        return
    await state.update_data(current_detail_name=name)
    await state.set_state(CloseShift.details_count)
    await message.answer(f"Сколько штук «{name}»?")


@dp.message(CloseShift.details_count)
async def details_count(message: Message, state: FSMContext):
    count_str = message.text.strip()
    if not count_str.isdigit() or int(count_str) <= 0:
        await message.answer("⚠️ Введи целое положительное число (например, 5):")
        return

    data = await state.get_data()
    name = data["current_detail_name"]
    details = data.get("details", [])
    details.append({"name": name, "count": int(count_str)})
    await state.update_data(details=details)

    lines = [f"• {d['name']} — {d['count']} шт." for d in details]
    text = "Текущий список деталей:\n" + "\n".join(lines) + "\n\nЧто дальше?"

    await state.set_state(None)
    await message.answer(text, reply_markup=details_more_kb())


@dp.callback_query(F.data == "details_done")
async def details_done(call: CallbackQuery, state: FSMContext):
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await call.answer()
    await finalize_shift(call.message, call.from_user.id, state)


# --- ФИНАЛИЗАЦИЯ СМЕНЫ ---
async def finalize_shift(message: Message, user_id: int, state: FSMContext):
    data = await state.get_data()
    incidents = data.get("incidents", "нет")
    powders = data.get("powders", [])
    details = data.get("details", [])

    powder_text = "\n".join([f"  • RAL {p['ral']} — {p['weight']} кг" for p in powders]) \
                  or "  — нет данных —"

    if details:
        details_text = "\n".join([f"  • {d['name']} — {d['count']} шт." for d in details])
    else:
        details_text = "  — не указано —"

    db.close_shift(user_id, incidents, powder_text, details_text)
    row = db.get_last_closed_shift(user_id)

    await state.clear()

    if row:
        text = (
            "✅ <b>Смена закрыта</b>\n\n"
            f"👤 ФИО: {row[0]}\n"
            f"📅 Дата: {row[1]}\n"
            f"🕐 Тип: {row[2]}\n"
            f"📝 Замечания при открытии: {row[3]}\n"
            f"⚠️ Происшествия: {row[4]}\n\n"
            f"🎨 <b>Порошок:</b>\n{row[5]}\n\n"
            f"🔩 <b>Покрашенные детали:</b>\n{row[6]}\n\n"
            f"🕓 Открыта: {row[7]}\n"
            f"🕓 Закрыта: {row[8]}"
        )
    else:
        text = "✅ Смена закрыта, но данные не найдены."

    await message.answer(text, reply_markup=main_menu())


# ================== ВЕБ-СЕРВЕР ДЛЯ RENDER ==================
async def health(request):
    return web.Response(text="OK")


async def start_web():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")


# ================== ЗАПУСК ==================
async def main():
    db.init_db()
    await start_web()
    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
