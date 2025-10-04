import requests
import nest_asyncio
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler
from telegram.ext import ConversationHandler

# Стадии диалога
FROM, AMOUNT, TO = range(3)

TOKEN = "Token"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет, я бот Мороза!")

async def convert_button_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("USD", callback_data="USD"),
         InlineKeyboardButton("EUR", callback_data="EUR")],
        [InlineKeyboardButton("PLN", callback_data="PLN"),
         InlineKeyboardButton("CAD", callback_data="CAD")],
        [InlineKeyboardButton("UAH", callback_data="UAH")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Выберите валюту, **из которой** хотите перевести:", reply_markup=reply_markup)
    return FROM

async def from_currency_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["from_currency"] = query.data
    await query.edit_message_text(f"Валюта источника: {query.data}\nВведите сумму:")

    return AMOUNT

async def amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Введите число.")
        return AMOUNT

    context.user_data["amount"] = amount

    keyboard = [
        [InlineKeyboardButton("USD", callback_data="USD"),
         InlineKeyboardButton("EUR", callback_data="EUR")],
        [InlineKeyboardButton("PLN", callback_data="PLN"),
         InlineKeyboardButton("CAD", callback_data="CAD")],
        [InlineKeyboardButton("UAH", callback_data="UAH")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Выберите валюту, **в которую** хотите перевести:", reply_markup=reply_markup)
    return TO

async def to_currency_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    from_currency = context.user_data["from_currency"]
    to_currency = query.data
    amount = context.user_data["amount"]

    if from_currency not in RATES or to_currency not in RATES:
        await query.edit_message_text("Неизвестная валюта.")
        return ConversationHandler.END

    uah = amount * RATES[from_currency]
    result = uah / RATES[to_currency]

    await query.edit_message_text(
        f"{amount} {from_currency} = {round(result, 2)} {to_currency}\n"
        f"(курс: {round(RATES[from_currency], 2)} → {round(RATES[to_currency], 2)})"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

from telegram.ext import ConversationHandler, MessageHandler, filters

async def new_conversion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("USD", callback_data="USD"),
         InlineKeyboardButton("EUR", callback_data="EUR")],
        [InlineKeyboardButton("PLN", callback_data="PLN"),
         InlineKeyboardButton("CAD", callback_data="CAD")],
        [InlineKeyboardButton("UAH", callback_data="UAH")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Выберите валюту, **из которой** хотите перевести:", reply_markup=reply_markup)
    return FROM

async def repeat_conversion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = context.user_data.get("last_conversion")

    if not data:
        await query.edit_message_text("Нет последней операции для повтора.")
        return

    from_currency = data["from"]
    to_currency = data["to"]
    amount = data["amount"]

    if from_currency not in RATES or to_currency not in RATES:
        await query.edit_message_text("Одна из валют устарела или удалена.")
        return

    uah = amount * RATES[from_currency]
    result = uah / RATES[to_currency]

    await query.edit_message_text(
        f"🔁 Повтор:\n"
        f"{amount} {from_currency} = {round(result, 2)} {to_currency}\n"
        f"(курс: {round(RATES[from_currency], 2)} → {round(RATES[to_currency], 2)})"
    )

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("convert_button", convert_button_start)],
    states={
        FROM: [CallbackQueryHandler(from_currency_chosen)],
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_received)],
        TO: [
            CallbackQueryHandler(to_currency_chosen),
            CallbackQueryHandler(new_conversion, pattern="^new_convert$"),  # ✅ перемещено сюда
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

async def to_currency_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    from_currency = context.user_data["from_currency"]
    to_currency = query.data
    amount = context.user_data["amount"]

    if from_currency not in RATES or to_currency not in RATES:
        await query.edit_message_text("Неизвестная валюта.")
        return ConversationHandler.END

    uah = amount * RATES[from_currency]
    result = uah / RATES[to_currency]

    # Сохраняем данные для повторной конверсии
    context.user_data["last_conversion"] = {
        "from": from_currency,
        "to": to_currency,
        "amount": amount
    }

    # Кнопки: Повторить / Новая
    keyboard = [
        [InlineKeyboardButton("🔁 Повторить", callback_data="repeat")],
        [InlineKeyboardButton("🆕 Новая конвертация", callback_data="new_convert")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"{amount} {from_currency} = {round(result, 2)} {to_currency}\n"
        f"(курс: {round(RATES[from_currency], 2)} → {round(RATES[to_currency], 2)})",
        reply_markup=reply_markup
    )
    return ConversationHandler.END


async def choose_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("USD", callback_data='USD'),
            InlineKeyboardButton("EUR", callback_data='EUR'),
        ],
        [
            InlineKeyboardButton("PLN", callback_data='PLN'),
            InlineKeyboardButton("AUD", callback_data='AUD'),
        ],
        [
            InlineKeyboardButton("CAD", callback_data='CAD'),
            InlineKeyboardButton("UAH", callback_data='UAH'),
        ],
        [
            InlineKeyboardButton("THB", callback_data='THB'),
            InlineKeyboardButton("AZN", callback_data='AZN'),
        ],
        
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите валюту:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Обязательный ответ Telegram API

    selected_currency = query.data

    # Загружаем курсы
    url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"
    response = requests.get(url)
    data = response.json()

    # Ищем нужную валюту
    rate = None
    for item in data:
        if item["cc"] == selected_currency:
            rate = item["rate"]
            break

    if rate:
        await query.edit_message_text(f"Курс {selected_currency}: {rate} ₴")
    else:
        await query.edit_message_text("Валюта не найдена.")


async def currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"
    response = requests.get(url)
    data = response.json()

    target_currencies = {
        "USD": "Долар США",
        "EUR": "Євро",
        "AUD": "Австралійський долар",
        "PLN": "Злотий",
        "CAD": "Канадський долар",
        "AZN": "Азербайджанський манат",
        "DZD": "Алжирський динар",
        "THB": "Бат",
        "BGN": "Болгарський лев"
        }
    
    result = "📊 Курси валют НБУ:\n\n"


    for code in target_currencies:
        if code in RATES:
            name = target_currencies[code]
            rate = RATES[code]
            result += f"{name} ({code}): {rate} ₴\n"

    await update.message.reply_text(result)

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Формат: /convert <сумма> <из> <в>")
        return

    try:
        amount = float(args[0])
        from_currency = args[1].upper()
        to_currency = args[2].upper()
    except:
        await update.message.reply_text("Неверный формат.")
        return

    if from_currency not in RATES or to_currency not in RATES:
        await update.message.reply_text("Неизвестная валюта.")
        return

    uah = amount * RATES[from_currency]
    result = uah / RATES[to_currency]

    await update.message.reply_text(
        f"{amount} {from_currency} = {round(result, 2)} {to_currency} "
        f"(курс: {round(RATES[from_currency], 2)} → {round(RATES[to_currency], 2)})"
)
    
RATES = {"UAH": 1.0}

async def update_rates_daily():
    global RATES  # указываем, что хотим изменить глобальную переменную

    while True:  # бесконечный цикл — выполняется в фоне
        try:
            print("🔄 Обновляю курсы валют...")
            response = requests.get("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json")
            data = response.json()

            # Обновляем словарь RATES
            RATES = {"UAH": 1.0}  # сбрасываем и добавляем гривну
            for item in data:
                RATES[item["cc"]] = item["rate"]

            print("✅ Курсы успешно обновлены.")

        except Exception as e:
            print("❌ Ошибка при обновлении курсов:", e)

        await asyncio.sleep(86400)  # ждать 86400 секунд = 1 день

app = ApplicationBuilder().token(TOKEN).build()

async def main():
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("currency", currency))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(CommandHandler("choose", choose_currency))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(repeat_conversion, pattern="^repeat$"))
    app.add_handler(CallbackQueryHandler(new_conversion, pattern="^new_convert$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    

    asyncio.create_task(update_rates_daily())

    await app.run_polling()

nest_asyncio.apply()

asyncio.get_event_loop().run_until_complete(main())