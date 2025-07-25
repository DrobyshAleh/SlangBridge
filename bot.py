import logging
import asyncio
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

from lang import texts  # Тексты на разных языках, нужно иметь этот модуль

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not API_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

if not ADMIN_ID or not ADMIN_ID.isdigit():
    raise ValueError("ADMIN_ID не найден или не является числом в переменных окружения")

ADMIN_ID = int(ADMIN_ID)

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# Хранение языка пользователя (по user_id)
user_lang: dict[int, str] = {}

# Списки для хранения постов в памяти (в проде надо заменить на базу)
proposed_posts: list[dict] = []
published_posts: list[dict] = []


class PostForm(StatesGroup):
    waiting_for_text = State()
    waiting_for_images = State()


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts[lang]["learn_polish"])],
            [KeyboardButton(text=texts[lang]["about"])],
            [KeyboardButton(text=texts[lang]["announcements"])],
            [KeyboardButton(text=texts[lang]["forum_menu"])],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def forum_menu(lang: str, is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text=texts[lang]["propose_post"])],
        [KeyboardButton(text=texts[lang]["forum_show"])],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text=texts[lang]["view_pending"])])
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} вызвал /start")
    lang_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang:ru")],
        [InlineKeyboardButton(text="Polski 🇵🇱", callback_data="lang:pl")]
    ])
    await message.answer("Привет! Выберите язык / Wybierz język:", reply_markup=lang_keyboard)


@dp.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = callback.data.split(":")[1]
    user_lang[callback.from_user.id] = lang
    logging.info(f"User {callback.from_user.id} выбрал язык {lang}")
    text = texts[lang]["menu_title"]
    keyboard = main_menu(lang)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(text, reply_markup=keyboard)


@dp.message()
async def menu_handler(message: Message, state: FSMContext):
    lang = user_lang.get(message.from_user.id, "ru")
    text = message.text

    # Если пользователь в процессе создания поста — игнорируем остальные кнопки
    current_state = await state.get_state()
    if current_state is not None:
        # Игнорируем остальные команды, чтобы не слететь из FSM
        return

    if text == texts[lang]["learn_polish"]:
        await message.answer(texts[lang].get("learn_polish_text", "Тут будет обучение польскому."))

    elif text == texts[lang]["about"]:
        await message.answer(texts[lang].get("about_text", "Информация о нас."))

    elif text == texts[lang]["announcements"]:
        await message.answer(texts[lang].get("announcements_text", "Здесь объявления."))

    elif text == texts[lang]["forum_menu"]:
        is_admin = message.from_user.id == ADMIN_ID
        keyboard = forum_menu(lang, is_admin)
        await message.answer(texts[lang]["forum_text"], reply_markup=keyboard)

    elif text == texts[lang]["propose_post"]:
        await message.answer(texts[lang]["enter_post"])
        await state.set_state(PostForm.waiting_for_text)

    elif text == texts[lang]["forum_show"]:
        if not published_posts:
            await message.answer(texts[lang]["no_posts"])
            return
        for post in published_posts:
            if post["images"]:
                media = [types.InputMediaPhoto(media=img) for img in post["images"]]
                await bot.send_media_group(message.from_user.id, media)
            await bot.send_message(message.from_user.id, post["text"])

    elif text == texts[lang]["view_pending"] and message.from_user.id == ADMIN_ID:
        if not proposed_posts:
            await message.answer(texts[lang]["no_pending_posts"])
            return
        for idx, post in enumerate(proposed_posts.copy()):
            media_group = [types.InputMediaPhoto(media=img_id) for img_id in post["images"]]
            if media_group:
                await bot.send_media_group(message.from_user.id, media=media_group)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=texts[lang]["approve"], callback_data=f"approve:{idx}"),
                InlineKeyboardButton(text=texts[lang]["reject"], callback_data=f"reject:{idx}")
            ]])
            await bot.send_message(message.from_user.id, post["text"], reply_markup=keyboard)


@dp.message(PostForm.waiting_for_text)
async def receive_post_text(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Пожалуйста, введите текст поста.")
        return
    await state.update_data(post_text=message.text.strip(), images=[])
    await message.answer("Теперь пришлите изображения (до 10 штук). Когда закончите — отправьте команду /done.\nЕсли не хотите добавлять фото, просто отправьте /done.")
    await state.set_state(PostForm.waiting_for_images)


@dp.message(PostForm.waiting_for_images, F.photo)
async def receive_post_images(message: Message, state: FSMContext):
    data = await state.get_data()
    images = data.get("images", [])
    if len(images) >= 10:
        await message.answer("Можно загрузить не более 10 изображений.")
        return
    file_id = message.photo[-1].file_id
    images.append(file_id)
    await state.update_data(images=images)
    await message.answer(f"Изображение {len(images)} принято.")


@dp.message(PostForm.waiting_for_images, Command("done"))
async def finish_post(message: Message, state: FSMContext):
    data = await state.get_data()
    text = data.get("post_text", "")
    images = data.get("images", [])
    if not text.strip():
        await message.answer("Текст поста не может быть пустым.")
        return
    proposed_posts.append({"user_id": message.from_user.id, "text": text, "images": images})
    await message.answer("Спасибо! Ваш пост отправлен на модерацию.")
    await state.clear()
    lang = user_lang.get(message.from_user.id, "ru")
    await message.answer(texts[lang]["menu_title"], reply_markup=main_menu(lang))


@dp.message(Command("done"))
async def done_out_of_context(message: Message):
    # Если команда /done вне FSM
    await message.answer("Вы пока не создаёте пост. Используйте кнопку 'Предложить пост' для начала.")


@dp.callback_query(F.data.startswith("approve:"))
async def approve_post(callback: CallbackQuery):
    await callback.answer()
    lang = user_lang.get(callback.from_user.id, "ru")
    idx = int(callback.data.split(":")[1])
    if 0 <= idx < len(proposed_posts):
        post = proposed_posts.pop(idx)
        published_posts.append(post)

        # Отправляем пост в канал/чат с постами (можно заменить на свой ID канала)
        # Пример: await bot.send_message(YOUR_CHANNEL_ID, post["text"], ...)

        if post["images"]:
            media_group = [types.InputMediaPhoto(media=img) for img in post["images"]]
            await bot.send_media_group(callback.from_user.id, media=media_group)
        await bot.send_message(callback.from_user.id, f"✅ {texts[lang]['approved_post']}")

        try:
            await bot.send_message(post["user_id"], texts[lang]["your_post_approved"])
        except Exception as e:
            logging.warning(f"Не удалось отправить сообщение пользователю: {e}")
    else:
        await callback.answer("Пост не найден.", show_alert=True)


@dp.callback_query(F.data.startswith("reject:"))
async def reject_post(callback: CallbackQuery):
    await callback.answer()
    lang = user_lang.get(callback.from_user.id, "ru")
    idx = int(callback.data.split(":")[1])
    if 0 <= idx < len(proposed_posts):
        post = proposed_posts.pop(idx)
        await callback.message.answer(texts[lang]["rejected_post"])
        try:
            await bot.send_message(post["user_id"], texts[lang]["your_post_rejected"])
        except Exception as e:
            logging.warning(f"Не удалось отправить сообщение пользователю: {e}")
    else:
        await callback.answer("Пост не найден.", show_alert=True)


@dp.callback_query(F.data == "forum_show")
async def forum_show(callback: CallbackQuery):
    await callback.answer()
    lang = user_lang.get(callback.from_user.id, "ru")
    if not published_posts:
        await callback.message.answer(texts[lang]["no_posts"])
        return
    for post in published_posts:
        if post["images"]:
            media = [types.InputMediaPhoto(media=img) for img in post["images"]]
            await bot.send_media_group(callback.from_user.id, media)
        await bot.send_message(callback.from_user.id, post["text"])


async def main():
    logging.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
