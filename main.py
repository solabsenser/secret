# bot.py
# Универсальный Telegram-бот для школьного проекта:
# - Красивое меню
# - Reply + Inline кнопки
# - Выбор подключенного скрипта
# - Передача параметров (пароль / номер)
# - Запуск внешнего .py файла через subprocess
#
# Установка:
# pip install aiogram
#
# Структура:
# bot.py
# scripts/
#   TeleSession.py
#   another_script.py

import asyncio
import subprocess
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# =========================
# НАСТРОЙКИ
# =========================
TOKEN = "YOUR_BOT_TOKEN_HERE"

# Список доступных скриптов
# key = callback data
# file = путь к файлу
# needs_password / needs_phone = какие данные спросить
SCRIPTS = {
    "tele": {
        "name": "TeleSession Demo",
        "file": "scripts/TeleSession.py",
        "needs_password": True,
        "needs_phone": True,
    }

# =========================
# BOT INIT
# =========================
bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# =========================
# STATES
# =========================
class RunScriptState(StatesGroup):
    choosing_script = State()
    waiting_password = State()
    waiting_phone = State()


# =========================
# KEYBOARDS
# =========================
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Запустить проект")],
        [KeyboardButton(text="📂 Список скриптов")],
        [KeyboardButton(text="ℹ️ Помощь")],
    ],
    resize_keyboard=True,
)

def scripts_inline_keyboard():
    buttons = []
    for key, script in SCRIPTS.items():
        buttons.append(
            [InlineKeyboardButton(text=f"⚙️ {script['name']}", callback_data=f"script_{key}")]
        )

    buttons.append(
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Запустить", callback_data="confirm_run"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
            ]
        ]
    )


# =========================
# HELPERS
# =========================
async def run_external_script(script_path: str, password: str = "", phone: str = ""):
    """
    Запуск внешнего файла.
    Передаёт данные через stdin (как будто пользователь вводит input()).
    """
    path = Path(script_path)

    if not path.exists():
        return "", f"Файл не найден: {script_path}"

    inputs = []

    if password:
        inputs.append(password)

    if phone:
        inputs.append(phone)

    input_data = "\n".join(inputs) + "\n" if inputs else None

    process = subprocess.Popen(
        [sys.executable, str(path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    stdout, stderr = process.communicate(input=input_data, timeout=60)

    return stdout, stderr


# =========================
# START
# =========================
@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "🎮 Добро пожаловать!\n\n"
        "Этот бот может запускать подключенные Python-скрипты через удобное меню.",
        reply_markup=main_keyboard,
    )


# =========================
# MAIN MENU
# =========================
@dp.message(F.text == "🚀 Запустить проект")
@dp.message(F.text == "📂 Список скриптов")
async def show_scripts(message: Message, state: FSMContext):
    await state.set_state(RunScriptState.choosing_script)

    await message.answer(
        "📌 Выбери скрипт для запуска:",
        reply_markup=scripts_inline_keyboard(),
    )


@dp.message(F.text == "ℹ️ Помощь")
async def help_handler(message: Message):
    await message.answer(
        "🛠 Как подключить свой скрипт:\n\n"
        "1. Помести .py файл в папку scripts/\n"
        "2. Добавь его в словарь SCRIPTS\n"
        "3. Укажи, нужны ли пароль/номер\n\n"
        "После этого бот сможет запускать его через меню."
    )


# =========================
# SCRIPT SELECTION
# =========================
@dp.callback_query(F.data.startswith("script_"))
async def script_selected(callback: CallbackQuery, state: FSMContext):
    script_key = callback.data.replace("script_", "")

    if script_key not in SCRIPTS:
        await callback.answer("Скрипт не найден", show_alert=True)
        return

    script = SCRIPTS[script_key]

    await state.update_data(script_key=script_key)

    if script["needs_password"]:
        await state.set_state(RunScriptState.waiting_password)
        await callback.message.edit_text(
            f"🔐 Выбран: {script['name']}\nВведите пароль:"
        )
    elif script["needs_phone"]:
        await state.set_state(RunScriptState.waiting_phone)
        await callback.message.edit_text(
            f"📱 Выбран: {script['name']}\nВведите номер:"
        )
    else:
        await callback.message.edit_text(
            f"⚡ Выбран: {script['name']}\nГотов к запуску.",
            reply_markup=confirm_keyboard(),
        )

    await callback.answer()


# =========================
# PASSWORD INPUT
# =========================
@dp.message(RunScriptState.waiting_password)
async def password_input(message: Message, state: FSMContext):
    await state.update_data(password=message.text)

    data = await state.get_data()
    script = SCRIPTS[data["script_key"]]

    if script["needs_phone"]:
        await state.set_state(RunScriptState.waiting_phone)
        await message.answer("📱 Теперь введи номер телефона:")
    else:
        await message.answer(
            "✅ Данные получены. Готов к запуску.",
            reply_markup=confirm_keyboard(),
        )


# =========================
# PHONE INPUT
# =========================
@dp.message(RunScriptState.waiting_phone)
async def phone_input(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)

    await message.answer(
        "🚀 Всё готово!",
        reply_markup=confirm_keyboard(),
    )


# =========================
# RUN SCRIPT
# =========================
@dp.callback_query(F.data == "confirm_run")
async def confirm_run(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    script = SCRIPTS[data["script_key"]]

    password = data.get("password", "")
    phone = data.get("phone", "")

    await callback.message.edit_text("⏳ Запускаю скрипт...")

    try:
        stdout, stderr = await asyncio.to_thread(
            run_external_script,
            script["file"],
            password,
            phone,
        )

        result_parts = []

        if stdout:
            result_parts.append(f"📄 OUTPUT:\n{stdout[:3500]}")

        if stderr:
            result_parts.append(f"⚠️ ERRORS:\n{stderr[:3500]}")

        final_text = "\n\n".join(result_parts) if result_parts else "✅ Скрипт завершён без вывода."

        await callback.message.answer(final_text)

    except subprocess.TimeoutExpired:
        await callback.message.answer("⏰ Скрипт выполнялся слишком долго.")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка запуска:\n{e}")

    await state.clear()
    await callback.answer()


# =========================
# CANCEL
# =========================
@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text("❌ Действие отменено.")
    await callback.message.answer(
        "🏠 Возвращаемся в меню.",
        reply_markup=main_keyboard,
    )

    await callback.answer()


# =========================
# MAIN
# =========================
async def main():
    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
