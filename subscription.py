from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

CHANNEL_USERNAME = "@gixefa"


async def check_subscription(bot, user_id):

    try:

        member = await bot.get_chat_member(
            CHANNEL_USERNAME,
            user_id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except:
        return False


def subscribe_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Open Channel",
                    url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Check Subscription",
                    callback_data="check_sub"
                )
            ]
        ]
    )
