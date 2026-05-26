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
# state appear
# subs cheker
# lekso
# osintgram

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
from subscription import (
    check_subscription,
    subscribe_keyboard
)

# =========================
# НАСТРОЙКИ
# =========================
TOKEN = "8986544001:AAFiZVfBPZpwGn4TK-Wv9vpHaBh7G8N65pY"

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

        "timeout": 10,
        "info": "⏳ Runtime: 10 seconds",
    },

    "project": {
        "name": "School Project",
        "file": "scripts/snoserprivate.py",

        "needs_password": True,

        "needs_choice": True,
        "needs_username": True,
        "needs_id": True,
        "needs_chat": True,
        "needs_violation": True,
        "needs_reason": True,

        "timeout": 120,
        "info": "⏳ Runtime: 2 minutes",
    },

    "osint": {
        "name": "OSINTGRAM",
        "file": "scripts/osintgram/main.py",

        # Передаём username аргументом
        "needs_username": True,

        "timeout": 30,
        "info": "⏳ Runtime: 30 seconds",
    }
}

# =========================
# BOT INIT
# =========================
bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())
# Текущий активный процесс
ACTIVE_PROCESS = False

# =========================
# STATES
# =========================
class RunScriptState(StatesGroup):
    choosing_script = State()

    waiting_password = State()
    waiting_phone = State()

    waiting_choice = State()
    waiting_username = State()
    waiting_id = State()
    waiting_chat = State()
    waiting_violation = State()
    waiting_reason = State()

# =========================
# KEYBOARDS
# =========================
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Launch Project")],
        [KeyboardButton(text="ℹ️ Help")],
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
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Launch", callback_data="confirm_run"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="cancel"),
            ]
        ]
    )

def reason_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📨 Spam", callback_data="reason_1"),
                InlineKeyboardButton(text="🕵️ Doxxing", callback_data="reason_2"),
            ],
            [
                InlineKeyboardButton(text="🤬 Insults", callback_data="reason_3"),
                InlineKeyboardButton(text="💊 Drugs", callback_data="reason_4"),
            ],
            [
                InlineKeyboardButton(text="🔞 Porn", callback_data="reason_12"),
                InlineKeyboardButton(text="☠️ Terrorism", callback_data="reason_15"),
            ]
        ]
    )
    
# =========================
# HELPERS
# =========================
def run_external_script(script_path: str, *inputs, timeout=10):

    from pathlib import Path
    import subprocess
    import sys
    import re

    path = Path(script_path)

    # Проверка файла
    if not path.exists():
        return "❌ Script not found.", "", None

    process = None

    try:

        process = subprocess.Popen(
            [sys.executable, str(path), *inputs],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Ждём результат
        stdout, stderr = process.communicate(
            input="info\nfollowers\nfollowings\nexit\n",
            timeout=timeout
        )
        
        # =========================
        # CLEAN OUTPUT
        # =========================

        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

        stdout = ansi_escape.sub('', stdout)
        stderr = ansi_escape.sub('', stderr)

        cleaned_lines = []

        skip_words = [
            "Version",
            "Developed by",
            "Type 'list'",
            "Type 'FILE'",
            "Type 'JSON'",
            "Run a command:",
            "HikerAPI",
            "[HD PROFILE PIC]",
            "Username (Full Name)",
            "default is disabled",
            "_____",
            "\\_____",
            "/_____/",
            "@@",
        ]

        for line in stdout.splitlines():

            line = line.strip()

            # Пустые строки
            if not line:
                continue

            # FILE / JSON help
            if line.startswith("Type 'FILE"):
                continue

            if line.startswith("Type 'JSON"):
                continue

            # Help/banner мусор
            if any(word in line for word in skip_words):
                continue

            # ASCII мусор
            if (
                "██" in line
                or "══" in line
                or "___" in line
                or "\\__" in line
            ):
                continue

            # Красивый вывод followers/followings
            if line.startswith("|"):

                parts = [x.strip() for x in line.split("|") if x.strip()]

                if len(parts) >= 3:

                    username = parts[1]
                    fullname = parts[2]

                    # Пропускаем заголовок таблицы
                    if username.lower() == "username":
                        continue

                    if not fullname:
                        fullname = "No Name"

                    line = f"• @{username} ({fullname})"

                else:
                    continue

            # Убираем линии таблиц
            if line.startswith("+"):
                continue

            # Убираем огромные ссылки
            if "http" in line and len(line) > 80:
                continue

            cleaned_lines.append(line)

        stdout = "\n".join(cleaned_lines)

        # =========================
        # ОШИБКА
        # =========================
        if stderr:

            return (
                "❌ Script finished with an error.",
                stderr[:3000],
                process
            )

        # =========================
        # УСПЕХ
        # =========================
        return (
            "✅ Script executed successfully.",
            stdout[:3000],
            process
        )

    except subprocess.TimeoutExpired:

        # Если завис или бесконечный цикл
        if process:
            process.kill()

        return (
            f"✅ Script ran successfully for {timeout} sec and was terminated.",
            "",
            process
        )

    except Exception as e:

        # Ошибка запуска
        if process and process.poll() is None:
            process.kill()

        return (
            "❌ Launch error.",
            str(e),
            process
        )

    finally:

        # Гарантированное завершение
        if process and process.poll() is None:
            process.kill()
            
# =========================
# START
# =========================
@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):

    # Сброс состояния
    await state.clear()

    # Проверка подписки
    is_subscribed = await check_subscription(
        bot,
        message.from_user.id
    )

    # Если не подписан
    if not is_subscribed:

        await message.answer(
            "🔒 Access denied.\n\n"
            "To continue using this bot,\n"
            "please subscribe to our channel.",
            reply_markup=subscribe_keyboard()
        )

        return

    # Если подписан
    await message.answer(
        "Hello Stranger.\n"
        "No questions. Just be yourself.",
        reply_markup=main_keyboard,
    )
# ===== CHECK SUBSCRIPTION ====
@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery):

    is_subscribed = await check_subscription(
        bot,
        callback.from_user.id
    )

    # Не подписан
    if not is_subscribed:

        await callback.answer(
            "❌ Subscription not found.",
            show_alert=True
        )

        return

    # Подписан
    await callback.message.edit_text(
        "✅ Subscription confirmed."
    )

    await callback.message.answer(
        "Welcome!",
        reply_markup=main_keyboard
    )

    await callback.answer()
    
# =========================
# MAIN MENU
# =========================
@dp.message(F.text == "🚀 Launch Project")
async def show_scripts(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RunScriptState.choosing_script)
    await message.answer(
        "📌 Choose a script to launch:",
        reply_markup=scripts_inline_keyboard(),
    )


@dp.message(F.text == "ℹ️ Help")
async def help_handler(message: Message, state: FSMContext):

    # Сброс состояния
    await state.clear()

    await message.answer(
        "ℹ️ <b>Information</b>\n\n"
        "This bot is designed to launch "
        "connected Python scripts.\n\n"

        "🚀 To get started, press "
        "«Launch Project».\n\n"

        "🔐 <b>Don’t know the password?</b>\n"
        "Contact the administrator.",
        parse_mode="HTML"
    )


# =========================
# SCRIPT SELECTION
# =========================
@dp.callback_query(F.data.startswith("script_"))
async def script_selected(callback: CallbackQuery, state: FSMContext):
    script_key = callback.data.replace("script_", "")

    if script_key not in SCRIPTS:
        await callback.answer("Script not found", show_alert=True)
        return

    script = SCRIPTS[script_key]

    await state.update_data(script_key=script_key)

    # Если нужен пароль
    if script.get("needs_password"):
        await state.set_state(RunScriptState.waiting_password)

        await callback.message.edit_text(
            f"🔐 Selected: {script['name']}\n"
            f"{script.get('info', '')}\n\n"
            "Enter password:"
        )

    # Если нужен номер
    elif script.get("needs_phone"):
        await state.set_state(RunScriptState.waiting_phone)

        await callback.message.edit_text(
            f"📱 Selected: {script['name']}\nEnter phone number:"
        )

    # Если нужен выбор меню
    elif script.get("needs_choice"):
        await state.set_state(RunScriptState.waiting_choice)

        await callback.message.edit_text(
            "📋 Choose a section:",
            reply_markup=menu_keyboard()
        )

    # Если нужен username
    elif script.get("needs_username"):

        await state.set_state(RunScriptState.waiting_username)

        await callback.message.edit_text(
            f"👤 Selected: {script['name']}\n\n"
            "Enter Instagram username:"
        )

    else:
        await callback.message.edit_text(
            f"⚡ Selected: {script['name']}\nReady to launch.",
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

    # Если нужен номер
    if script.get("needs_phone"):
        await state.set_state(RunScriptState.waiting_phone)

        await message.answer(
            "📱 Now enter a phone number:"
        )

    # Если нужен выбор меню
    elif script.get("needs_choice"):
        await state.set_state(RunScriptState.waiting_choice)

        await message.answer(
            "📋 Choose a section:",
            reply_markup=menu_keyboard()
        )

    else:
        await message.answer(
            "✅ Data received.",
            reply_markup=confirm_keyboard(),
        )

# =========================
# PHONE INPUT
# =========================
@dp.message(RunScriptState.waiting_phone)
async def phone_input(message: Message, state: FSMContext):
    # Очищаем номер от пробелов, +, скобок, тире
    raw_phone = message.text

    cleaned_phone = (
        raw_phone.replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    # Проверка: только цифры
    if not cleaned_phone.isdigit():
        await message.answer("⚠️ Enter the phone number using digits only (you can include +, the bot will clean it).")
        return

    # Сохраняем уже очищенный номер
    await state.update_data(phone=cleaned_phone)

    await message.answer(
        f"📱 Phone number accepted: {cleaned_phone}\n🚀 Everything is ready!",
        reply_markup=confirm_keyboard(),
    )

def menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Accounts", callback_data="menu_1"),
                InlineKeyboardButton(text="📢 Channels", callback_data="menu_2"),
            ],
            [
                InlineKeyboardButton(text="🤖 Bots", callback_data="menu_3"),
                InlineKeyboardButton(text="💬 Chats", callback_data="menu_4"),
            ]
        ]
    )


@dp.callback_query(F.data.startswith("menu_"))
async def menu_selected(callback: CallbackQuery, state: FSMContext):

    choice = callback.data.replace("menu_", "")

    await state.update_data(choice=choice)

    # =========================
    # ACCOUNTS
    # =========================
    if choice == "1":

        await state.set_state(RunScriptState.waiting_username)

        await callback.message.edit_text(
            "👤 Enter Telegram username:"
        )

    # =========================
    # CHANNELS
    # =========================
    elif choice == "2":

        await state.set_state(RunScriptState.waiting_chat)

        await callback.message.edit_text(
            "📢 Send channel link:"
        )

    # =========================
    # BOTS
    # =========================
    elif choice == "3":

        await state.set_state(RunScriptState.waiting_username)

        await callback.message.edit_text(
            "🤖 Enter bot username:"
        )

    # =========================
    # CHATS
    # =========================
    elif choice == "4":

        await state.set_state(RunScriptState.waiting_chat)

        await callback.message.edit_text(
            "💬 Send chat link:"
        )

    await callback.answer()


@dp.message(RunScriptState.waiting_username)
async def username_input(message: Message, state: FSMContext):

    await state.update_data(username=message.text)

    data = await state.get_data()

    choice = data.get("choice")

    # =========================
    # OSINT
    # =========================
    if data.get("script_key") == "osint":

        await message.answer(
            "✅ Username received.",
            reply_markup=confirm_keyboard(),
        )

        return

    # =========================
    # BOTS
    # =========================
    if choice == "3":

        await message.answer(
            "✅ Bot username received.",
            reply_markup=confirm_keyboard(),
        )

        return

    # =========================
    # ACCOUNTS
    # =========================
    await state.set_state(RunScriptState.waiting_id)

    await message.answer(
        "🆔 Enter Telegram ID:"
    )


@dp.message(RunScriptState.waiting_id)
async def id_input(message: Message, state: FSMContext):

    await state.update_data(user_id=message.text)

    data = await state.get_data()

    reason = data.get("reason")

    # 18 19 20 21
    if reason in ["18", "19", "20", "21"]:

        await message.answer(
            "✅ Data received.",
            reply_markup=confirm_keyboard(),
        )

        return

    await state.set_state(RunScriptState.waiting_chat)

    await message.answer(
        "💬 Send chat/message link:"
    )

@dp.message(RunScriptState.waiting_chat)
async def chat_input(message: Message, state: FSMContext):

    await state.update_data(chat=message.text)

    data = await state.get_data()

    choice = data.get("choice")

    # =========================
    # CHANNELS
    # =========================
    if choice == "2":

        await state.set_state(RunScriptState.waiting_violation)

        await message.answer(
            "⚠️ Send violation link:"
        )

        return

    # =========================
    # CHATS
    # =========================
    if choice == "4":

        reason = data.get("reason")

        # chat option 6
        if reason == "6":

            await state.set_state(RunScriptState.waiting_violation)

            await message.answer(
                "⚠️ Send violation link:"
            )

            return

        await message.answer(
            "✅ Data received.",
            reply_markup=confirm_keyboard(),
        )

        return

    # =========================
    # ACCOUNTS
    # =========================
    await state.set_state(RunScriptState.waiting_violation)

    await message.answer(
        "⚠️ Send violation link:"
    )


@dp.message(RunScriptState.waiting_violation)
async def violation_input(message: Message, state: FSMContext):

    await state.update_data(violation=message.text)

    data = await state.get_data()
    script = SCRIPTS[data["script_key"]]

    # Если нужен reason
    if script.get("needs_reason"):

        await state.set_state(RunScriptState.waiting_reason)

        await message.answer(
            "⚠️ Select a reason:",
            reply_markup=reason_keyboard()
        )

    else:

        await message.answer(
            "✅ All data received.",
            reply_markup=confirm_keyboard(),
        )

@dp.callback_query(F.data.startswith("reason_"))
async def reason_selected(callback: CallbackQuery, state: FSMContext):

    reason = callback.data.replace("reason_", "")

    # Сохраняем номер причины
    await state.update_data(reason=reason)

    await callback.message.edit_text(
        "✅ Reason selected."
    )

    await callback.message.answer(
        "🚀 Everything is ready to launch.",
        reply_markup=confirm_keyboard()
    )

    await callback.answer()
    
# =========================
# RUN SCRIPT
# =========================
@dp.callback_query(F.data == "confirm_run")
async def confirm_run(callback: CallbackQuery, state: FSMContext):

    global ACTIVE_PROCESS

    # Если уже выполняется процесс
    if ACTIVE_PROCESS:
        await callback.answer(
            "⛔ This script is already running. Wait for it to stop and relaunch.",
            show_alert=True
        )
        return

    # Блокируем новые запуски
    ACTIVE_PROCESS = True

    data = await state.get_data()

    # Если state уже очищен
    if "script_key" not in data:

        await callback.answer(
            "⚠️ Session expired. Please start again.",
            show_alert=True
        )

        return

    script = SCRIPTS[data["script_key"]]

    # Собираем input()
    inputs = []

    if data.get("password"):
        inputs.append(data["password"])

    if data.get("phone"):
        inputs.append(data["phone"])

    if data.get("choice"):
        inputs.append(data["choice"])

    if data.get("reason"):
        inputs.append(data["reason"])

    if data.get("username"):
        inputs.append(data["username"])

    if data.get("user_id"):
        inputs.append(data["user_id"])

    if data.get("chat"):
        inputs.append(data["chat"])

    if data.get("violation"):
        inputs.append(data["violation"])

    status_message = await callback.message.edit_text(
        f"⏳ Script started.\n"
        f"⏱ Auto-stop in {script['timeout']} sec."
    )

    try:

        stdout, stderr, process = await asyncio.to_thread(
            run_external_script,
            script["file"],
            *inputs,
            timeout=script["timeout"]
        )

        text = stdout if stdout else "✅ Script finished."

        # Ограничиваем длину ошибок
        if stderr:

            short_error = stderr[:3500]

            text += f"\n\n⚠️ {short_error}"

    # Если ошибка была длинной
            if len(stderr) > 3500:
                text += "\n\n... error truncated ..."

        await status_message.edit_text(
            text,
            reply_markup=None
        )

    except Exception as e:

        await callback.message.answer(
            f"❌ Launch error:\n{e}"
        )

    finally:
        # Разрешаем запуск снова
        ACTIVE_PROCESS = False

    await state.clear()
    await callback.answer()
    
# =========================
# CANCEL
# =========================
@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text("❌ Action canceled.")
    await callback.message.answer(
        "🏠 Returning to the menu.",
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
