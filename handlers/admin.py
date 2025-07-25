from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message

ADMIN_IDS = [6694989403]  # 👈 твой Telegram ID

router = Router()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ У тебя нет доступа к админ-панели.")
        return

    await message.answer("👑 Добро пожаловать в админ-панель!\nВыберите действие:\n\n1. Добавить фразы\n2. Посмотреть пользователей\n(и так далее...)")
