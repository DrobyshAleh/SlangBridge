from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇵🇱 Учим польский")],
            [KeyboardButton(text="📘 О нас")],
            [KeyboardButton(text="💬 Форум")],
            [KeyboardButton(text="📢 Объявления")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return kb
