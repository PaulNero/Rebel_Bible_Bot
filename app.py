import asyncio
import logging
import csv
import os
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import re

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
LINK = os.getenv("LINK")

CSV_FILE = "REBEL_BIBLE_BOT.csv"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class Survey(StatesGroup):
    name = State()
    price = State()
    brands = State()
    city = State()
    contact = State()

def get_brands_keyboard(selected_brands):
    keyboard = []
    brands = ["Reuzel", "Lock Stock", "Morgan’s", "REBEL", "Dream Catcher", "Boy's Toys", "KONDOR", "NishMan",
              "White Cosmetics", "London Grooming"]
    for brand in brands:
        text = f"☑️ {brand}" if brand in selected_brands else brand
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"brand_{brand}")])
    if selected_brands:
        keyboard.append([InlineKeyboardButton(text="❌ Отменить выбор", callback_data="cancel_brand")])
        keyboard.append([InlineKeyboardButton(text="✅ Завершить выбор", callback_data="finish_brands")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

price_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Дешевле 800 руб."), KeyboardButton(text="800–1000 руб.")],
        [KeyboardButton(text="1000–1400 руб."), KeyboardButton(text="1400–2000 руб.")],
        [KeyboardButton(text="2000–3000 руб."), KeyboardButton(text="Свыше 3000 руб.")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    await message.answer("Привет! Чтобы получить бесплатный гайд, пройди опрос. Это займет 20 секунд. \nКак тебя зовут?🙂")
    await state.set_state(Survey.name)

@dp.message(Survey.name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not re.match(r"^[A-Za-zА-Яа-я\s-]+$", name):
        await message.answer("Пожалуйста, введи корректное имя (только буквы, пробелы или дефис).")
        return
    await state.update_data(name=name, username=message.from_user.username)
    await message.answer(f"Кайф! {name} очень приятно 🤗 Сколько сейчас по твоему прайсу стоит услуга «мужская стрижка»?",
                         reply_markup=price_keyboard)
    await state.set_state(Survey.price)

@dp.message(Survey.price)
async def process_price(message: types.Message, state: FSMContext):
    if message.text not in ["Дешевле 800 руб.", "800–1000 руб.", "1000–1400 руб.", "1400–2000 руб.", "2000–3000 руб.",
                            "Свыше 3000 руб."]:
        await message.answer("Пожалуйста, выбери вариант из списка. \n\nЕсли клавиатура недоступна, нажмите на иконку 🎛 справа от строки ввода.")
        return
    await state.update_data(price=message.text)
    await message.answer("Норм-норм)) А на каких брендах косметики работаешь? (можно выбрать несколько вариантов)",
                         reply_markup=get_brands_keyboard([]))

    await state.set_state(Survey.brands)

@dp.callback_query(Survey.brands)
async def process_brand(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_brands = data.get("brands", [])

    if callback.data.startswith("brand_"):
        brand = callback.data.replace("brand_", "")
        if brand in selected_brands:
            selected_brands.remove(brand)
        else:
            selected_brands.append(brand)
        await state.update_data(brands=selected_brands)
    elif callback.data == "cancel_brand" and selected_brands:
        selected_brands.clear()
        await state.update_data(brands=selected_brands)
    elif callback.data == "finish_brands":
        await callback.message.delete_reply_markup()
        await callback.message.answer("Отлично! В каком городе ты живешь и работаешь?")
        await state.set_state(Survey.city)
        return
    await callback.message.edit_reply_markup(reply_markup=get_brands_keyboard(selected_brands))
    await callback.answer()

@dp.message(Survey.city)
async def process_city(message: types.Message, state: FSMContext):
    city = message.text.strip()
    if not re.match(r"^[A-Za-zА-Яа-я\s-]+$", city):
        await message.answer("Пожалуйста, введи корректное название города (только буквы, пробелы или дефис).")
        return
    await state.update_data(city=city)
    await message.answer(
        "Крутяк!👏 Остался последний шаг и гайд твой! Напиши ник своего аккаунта в Instagram (например, ahuennyi_barber).")
    await state.set_state(Survey.contact)

@dp.message(Survey.contact)
async def process_contact(message: types.Message, state: FSMContext):
    contact = message.text.strip()
    # Маска для никнейма Instagram: буквы, цифры, точки, подчеркивания, длина 1-30 символов
    if not re.match(r"^[a-zA-Z0-9._]{1,30}$", contact):
        await message.answer("Пожалуйста, введи корректный ник Instagram (до 30 символов, только буквы, цифры, точки или подчеркивания).")
        return
    await state.update_data(contact=contact)
    data = await state.get_data()

    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["№", "Имя", "Город", "Username", "Цена", "Бренды", "Instagram"])
        row_num = sum(1 for _ in open(CSV_FILE)) if file_exists else 1
        row_num = max(row_num, 0)
        writer.writerow(
            [row_num, data.get("name"), data.get("city"), data.get("username"), data.get("price"),
             ", ".join(data.get("brands", [])), data.get("contact")])

    survey_text = (f"📋 Новая анкета!\n\n"
                   f"👤 Имя: {data.get('name')}\n"
                   f"🏙 Город: {data.get('city')}\n"
                   f"🔗 Username: @{data.get('username')}\n"
                   f"💰 Цена: {data.get('price')}\n"
                   f"💄 Бренды: {', '.join(data.get('brands', []))}\n"
                   f"📸 Instagram: https://www.instagram.com/{data.get('contact')}")
    await bot.send_message(CHANNEL_ID, survey_text)

    await bot.send_document(CHANNEL_ID, types.FSInputFile(CSV_FILE))

    await message.answer(
        f"Респект! Спасибо за твое время и интерес, забирай гайд! {LINK} \nИ да, знай, что я жду, когда о тебе узнают ВСЕ!))")
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())