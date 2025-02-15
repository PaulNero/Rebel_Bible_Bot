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
import data
import re

TOKEN = data.TOKEN
CHANNEL_ID = data.CHANNEL_ID
CSV_FILE = "REBEL_BIBLE_BOT.csv"

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher()

# Определение состояний
class Survey(StatesGroup):
    price = State()
    brands = State()
    form = State()


# Клавиатура для вопроса о стоимости стрижки
price_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Дешевле 800 руб."), KeyboardButton(text="800–1000 руб.")],
        [KeyboardButton(text="1000–1400 руб."), KeyboardButton(text="1400–2000 руб.")],
        [KeyboardButton(text="2000–3000 руб."), KeyboardButton(text="Свыше 3000 руб.")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


# Функция для обновления клавиатуры с брендами
def get_brands_keyboard(selected_brands):
    keyboard = []
    brands = ["Reuzel", "Lock Stock", "Morgan’s", "REBEL", "NishMan", "Dream Catcher", "Boy's Toys", "KONDOR",
              "White Cosmetics", "Maestro"]
    for brand in brands:
        text = f"✅ {brand}" if brand in selected_brands else brand
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"brand_{brand}")])
    if selected_brands:
        keyboard.append([InlineKeyboardButton(text="❌ Отменить выбор", callback_data="cancel_brand")])
        keyboard.append([InlineKeyboardButton(text="✅ Завершить выбор", callback_data="finish_brands")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    await message.answer("Привет! Чтобы получить бесплатный гайд, пройди опрос. Это займет 20 секунд")
    await message.answer("Стоимость стрижки по твоему прайсу?", reply_markup=price_keyboard)
    await state.set_state(Survey.price)


@dp.message(Survey.price)
async def process_price(message: types.Message, state: FSMContext):
    if message.text not in ["Дешевле 800 руб.", "800–1000 руб.", "1000–1400 руб.", "1400–2000 руб.", "2000–3000 руб.",
                            "Свыше 3000 руб."]:
        await message.answer("Пожалуйста, выбери вариант из списка.")
        return
    await state.update_data(price=message.text)
    await message.answer("На каких брендах косметики работаешь? (Выбери из списка)",
                         reply_markup=get_brands_keyboard([]))
    await state.set_state(Survey.brands)


@dp.callback_query(Survey.brands)
async def process_brand(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_brands = data.get("brands", [])

    if callback.data.startswith("brand_"):
        brand = callback.data.replace("brand_", "")
        if brand in selected_brands:
            selected_brands.remove(brand)  # Удаляет конкретный бренд из списка
        else:
            selected_brands.append(brand)  # Добавляет бренд, если он не был выбран
        await state.update_data(brands=selected_brands)

    elif callback.data == "cancel_brand" and selected_brands:
        selected_brands.pop()
        await state.update_data(brands=selected_brands)

    elif callback.data == "finish_brands":
        await callback.message.delete_reply_markup()  # Скрытие клавиатуры
        await callback.message.answer("Гайд почти твой! Осталось заполнить небольшую анкету.")
        await callback.message.answer("Введите ФИО: ")
        await state.set_state(Survey.form)
        return

    await callback.message.edit_reply_markup(reply_markup=get_brands_keyboard(selected_brands))
    await callback.answer()


@dp.message(Survey.form)
async def process_form(message: types.Message, state: FSMContext):
    data = await state.get_data()
    form_data = data.get("form", [])
    form_data.append(message.text)
    await state.update_data(form=form_data)
    if len(form_data) == 1:
        await message.answer("Введите номер телефона:")

    elif len(form_data) == 2:
        phone_pattern = re.compile(r"^\+\d{10,15}$")
        if not phone_pattern.match(form_data[1]):
            await message.answer("Пожалуйста, введите корректный номер телефона в формате +79111234567")
            form_data.pop()
            return
        await message.answer("Введите ваш аккаунт в Instagram:")

    elif len(form_data) == 3:
        await message.answer("Введите ваш город:")

    else:
        telegram_id = message.from_user.id
        telegram_username = message.from_user.username or "Не указан"
        await state.update_data(contact={
            "ФИО": form_data[0],
            "Телефон": form_data[1],
            "Instagram": form_data[2],
            "Город": form_data[3],
            "Telegram ID": telegram_id,
            "Telegram Username": telegram_username
        })
        await message.answer(f"Спасибо! Вот ссылка на гайд: {data.LINK}")
        file_exists = os.path.isfile(CSV_FILE)
        with open(CSV_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["№", "Ценовой диапазон", "Бренды", "ФИО", "Номер телефона", "Instagram", "Город", "Telegram ID",
                                 "Telegram Username"])
            row_num = sum(1 for _ in open(CSV_FILE)) if file_exists else 0
            writer.writerow(
                [row_num, data['price'], data['brands'], form_data[0], form_data[1], form_data[2], form_data[3], telegram_id,
                 telegram_username])
        await bot.send_document(CHANNEL_ID, types.FSInputFile(CSV_FILE))
        message_text = (f"📌 *Новая заявка!*\n\n"
                        f"*Ценовой диапазон:* {data['price']}\n"
                        f"*Бренды:* {data['brands']}\n"
                        f"*ФИО:* {form_data[0]}\n"
                        f"*Номер телефона:* {form_data[1]}\n"
                        f"*Ссылка на Instagram:* https://instagram.com/{form_data[2]}\n"
                        f"*Город:* {form_data[3]}\n"
                        f"*Telegram ID:* {telegram_id}\n"
                        f"*Telegram Username:* @{telegram_username}")
        await bot.send_message(CHANNEL_ID, message_text, parse_mode="Markdown")
        await state.clear()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
