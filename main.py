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

        # Время работы
        "timeout": 10,
        "info": "⏳ Время работы: 10 секунд",
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

        # Время работы
        "timeout": 120,
        "info": "⏳ Время работы: 2 минуты",
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
        [KeyboardButton(text="🚀 Запустить проект")],
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

def reason_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📨 Спам", callback_data="reason_1"),
                InlineKeyboardButton(text="🕵️ Доксинг", callback_data="reason_2"),
            ],
            [
                InlineKeyboardButton(text="🤬 Оскорбления", callback_data="reason_3"),
                InlineKeyboardButton(text="💊 Наркота", callback_data="reason_4"),
            ],
            [
                InlineKeyboardButton(text="🔞 Порно", callback_data="reason_12"),
                InlineKeyboardButton(text="☠️ Терроризм", callback_data="reason_15"),
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
        return "❌ Скрипт не найден.", "", None

    # Формируем input() данные
    input_data = "\n".join(inputs) + "\n"

    process = None

    try:

        # Запуск процесса
        process = subprocess.Popen(
            [sys.executable, str(path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Передаём input() и ждём результат
        stdout, stderr = process.communicate(
            input=input_data,
            timeout=timeout
        )

        # =========================
        # ОЧИСТКА ANSI / ASCII МУСОРА
        # =========================

        # ANSI escape
        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

        stdout = ansi_escape.sub('', stdout)
        stderr = ansi_escape.sub('', stderr)

        # RGB мусор
        stdout = re.sub(r'\[38;2;.*?m', '', stdout)
        stderr = re.sub(r'\[38;2;.*?m', '', stderr)

        # Удаляем огромные ascii-art строки
        cleaned_lines = []

        for line in stdout.splitlines():

            # Пропуск слишком длинных строк
            if len(line) > 300:
                continue

            cleaned_lines.append(line)

        stdout = "\n".join(cleaned_lines)

        # =========================
        # ОШИБКА
        # =========================
        if stderr:

            return (
                "❌ Скрипт завершился с ошибкой.",
                stderr[:3000],
                process
            )

        # =========================
        # УСПЕХ
        # =========================
        return (
            "✅ Скрипт успешно выполнился.",
            stdout[:3000],
            process
        )

    except subprocess.TimeoutExpired:

        # Если завис или бесконечный цикл
        if process:
            process.kill()

        return (
            f"✅ Скрипт успешно отработал {timeout} сек. и был завершён.",
            "",
            process
        )

    except Exception as e:

        # Ошибка запуска
        if process and process.poll() is None:
            process.kill()

        return (
            "❌ Ошибка запуска.",
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
        "🎮 Welcome!",
        reply_markup=main_keyboard
    )

    await callback.answer()
    
# =========================
# MAIN MENU
# =========================
@dp.message(F.text == "🚀 Запустить проект")
async def show_scripts(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RunScriptState.choosing_script)
    await message.answer(
        "📌 Выбери скрипт для запуска:",
        reply_markup=scripts_inline_keyboard(),
    )


@dp.message(F.text == "ℹ️ Помощь")
async def help_handler(message: Message, state: FSMContext):

    # Сброс состояния
    await state.clear()

    await message.answer(
        "ℹ️ <b>Информация</b>\n\n"
        "Бот предназначен для запуска "
        "подключённых Python-скриптов.\n\n"

        "🚀 Для начала работы нажмите "
        "«Запустить проект».\n\n"

        "🔐 <b>Не знаете пароль?</b>\n"
        "Обратитесь к администратору.",
        parse_mode="HTML"
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

    # Если нужен пароль
    if script.get("needs_password"):
        await state.set_state(RunScriptState.waiting_password)

        await callback.message.edit_text(
            f"🔐 Выбран: {script['name']}\n"
            f"{script.get('info', '')}\n\n"
            "Введите пароль:"
        )

    # Если нужен номер
    elif script.get("needs_phone"):
        await state.set_state(RunScriptState.waiting_phone)

        await callback.message.edit_text(
            f"📱 Выбран: {script['name']}\nВведите номер:"
        )

    # Если нужен выбор меню
    elif script.get("needs_choice"):
        await state.set_state(RunScriptState.waiting_choice)

        await callback.message.edit_text(
            "📋 Выберите раздел:",
            reply_markup=menu_keyboard()
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

    # Если нужен номер
    if script.get("needs_phone"):
        await state.set_state(RunScriptState.waiting_phone)

        await message.answer(
            "📱 Теперь введи номер телефона:"
        )

    # Если нужен выбор меню
    elif script.get("needs_choice"):
        await state.set_state(RunScriptState.waiting_choice)

        await message.answer(
            "📋 Выберите раздел:",
            reply_markup=menu_keyboard()
        )

    else:
        await message.answer(
            "✅ Данные получены.",
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
        await message.answer("⚠️ Введите номер только цифрами (можно с +, бот сам очистит).")
        return

    # Сохраняем уже очищенный номер
    await state.update_data(phone=cleaned_phone)

    await message.answer(
        f"📱 Номер принят: {cleaned_phone}\n🚀 Всё готово!",
        reply_markup=confirm_keyboard(),
    )

def menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Аккаунты", callback_data="menu_1"),
                InlineKeyboardButton(text="📢 Каналы", callback_data="menu_2"),
            ],
            [
                InlineKeyboardButton(text="🤖 Боты", callback_data="menu_3"),
                InlineKeyboardButton(text="💬 Чаты", callback_data="menu_4"),
            ]
        ]
    )


@dp.callback_query(F.data.startswith("menu_"))
async def menu_selected(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.replace("menu_", "")

    await state.update_data(choice=choice)

    await state.set_state(RunScriptState.waiting_username)

    await callback.message.edit_text(
        "✅ Раздел выбран.\n\n"
        "👤 Укажите username пользователя Telegram:"
    )

    await callback.answer()


@dp.message(RunScriptState.waiting_username)
async def username_input(message: Message, state: FSMContext):
    await state.update_data(username=message.text)

    await state.set_state(RunScriptState.waiting_id)
    await message.answer(
    "🆔 Укажите Telegram ID пользователя:"
    )


@dp.message(RunScriptState.waiting_id)
async def id_input(message: Message, state: FSMContext):
    await state.update_data(user_id=message.text)

    await state.set_state(RunScriptState.waiting_chat)
    await message.answer(
    "💬 Отправьте ссылку на чат, канал или сообщение:"
    )


@dp.message(RunScriptState.waiting_chat)
async def chat_input(message: Message, state: FSMContext):
    await state.update_data(chat=message.text)

    await state.set_state(RunScriptState.waiting_violation)
    await message.answer(
    "⚠️ Отправьте ссылку на материал или сообщение, связанное с жалобой:"
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
            "⚠️ Выберите причину:",
            reply_markup=reason_keyboard()
        )

    else:

        await message.answer(
            "✅ Все данные получены.",
            reply_markup=confirm_keyboard(),
        )

@dp.callback_query(F.data.startswith("reason_"))
async def reason_selected(callback: CallbackQuery, state: FSMContext):

    reason = callback.data.replace("reason_", "")

    # Сохраняем номер причины
    await state.update_data(reason=reason)

    await callback.message.edit_text(
        "✅ Причина выбрана."
    )

    await callback.message.answer(
        "🚀 Всё готово к запуску.",
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
            "⛔ У вас уже запущен данный скрипт. Дождитесь его остановки и перезапустите.",
            show_alert=True
        )
        return

    # Блокируем новые запуски
    ACTIVE_PROCESS = True

    data = await state.get_data()

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

    await callback.message.edit_text(
        f"⏳ Скрипт запущен.\n"
        f"⏱ Автоостановка через {script['timeout']} сек."
    )

    try:

        stdout, stderr, process = await asyncio.to_thread(
            run_external_script,
            script["file"],
            *inputs,
            timeout=script["timeout"]
        )

        text = stdout if stdout else "✅ Скрипт завершён."

        # Ограничиваем длину ошибок
        if stderr:

            short_error = stderr[:3500]

            text += f"\n\n⚠️ {short_error}"

    # Если ошибка была длинной
            if len(stderr) > 3500:
                text += "\n\n... error truncated ..."

        await callback.message.answer(text)

    except Exception as e:

        await callback.message.answer(
            f"❌ Ошибка запуска:\n{e}"
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
