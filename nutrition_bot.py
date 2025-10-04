import os
import random
import logging
from fpdf import FPDF, XPos, YPos
from openai import OpenAI
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton


BOT_TOKEN = "7856566481:AAEwZLalSnVXEF9R7PaKi7NU8Ekb_fgLAbg"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)


user_data = {}


def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton('📝 Ввести данные'),          
        KeyboardButton('👤 Личный кабинет'),
        KeyboardButton('🍎 Умный план (ИИ)'),
        KeyboardButton('🎲 Локальный план'),
        KeyboardButton('💡 Советы от ИИ'),
        KeyboardButton('📄 PDF-план'),
        KeyboardButton('🔄 Сбросить данные')
    )
    return keyboard

def create_goal_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('🎯 Похудение'))
    kb.add(KeyboardButton('💪 Набор массы'))
    kb.add(KeyboardButton('⚖️ Поддержание'))
    kb.add(KeyboardButton('🏃‍♂️ Спорт'))
    return kb

def create_activity_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('💺 Сидячий образ'))
    kb.add(KeyboardButton('🚶‍♂️ Легкая активность'))
    kb.add(KeyboardButton('🏋️‍♂️ Умеренные тренировки'))
    kb.add(KeyboardButton('🔥 Высокая активность'))
    return kb


def calculate_bmi(weight, height):
    return round(weight / ((height / 100) ** 2), 1)

def get_bmi_status(bmi):
    if bmi < 18.5: return "недостаточный вес"
    elif bmi <= 24.9: return "норма"
    elif bmi <= 29.9: return "избыток"
    else: return "ожирение"

def calculate_calories(weight, height, age, gender, goal, activity):
    bmr = 10 * weight + 6.25 * height - 5 * age + (5 if gender == "мужской" else -161)
    activity_mult = {"сидячий": 1.2, "легкая": 1.375, "умеренная": 1.55, "высокая": 1.725}
    goal_mult = {"похудение": 0.85, "поддержание": 1.0, "набор массы": 1.15, "спорт": 1.1}
    return int(bmr * activity_mult.get(activity, 1.375) * goal_mult.get(goal, 1.0))

def calculate_bju(calories, goal, weight):
    ratios = {
        "похудение": (0.35, 0.25, 0.40),
        "набор массы": (0.30, 0.25, 0.45),
        "спорт": (0.33, 0.22, 0.45),
        "поддержание": (0.25, 0.25, 0.50)
    }
    p, f, c = ratios.get(goal, ratios["поддержание"])
    return int(calories * p / 4), int(calories * f / 9), int(calories * c / 4)


LOCAL_PLANS = {
    "похудение": [
        "🥗 Завтрак: Овсянка с ягодами (280 ккал)\n🍏 Перекус: Яблоко + миндаль (200 ккал)\n🍲 Обед: Курица с гречкой (400 ккал)\n🥒 Перекус: Йогурт (120 ккал)\n🐟 Ужин: Рыба с овощами (350 ккал)",
        "🥣 Завтрак: Творог с льняным семенем (250 ккал)\n🍌 Перекус: Груша (80 ккал)\n🍛 Обед: Суп с фрикадельками (380 ккал)\n🥜 Перекус: Горсть орехов (150 ккал)\n🥩 Ужин: Индейка с брокколи (320 ккал)",
        "🍳 Завтрак: Яичница с шпинатом (300 ккал)\n🥒 Перекус: Огурцы + хумус (180 ккал)\n🍲 Обед: Салат с тунцом (420 ккал)\n🥛 Перекус: Кефир (100 ккал)\n🐟 Ужин: Кальмары с лимоном (300 ккал)",
        "🥞 Завтрак: Белковые блинчики (260 ккал)\n🍓 Перекус: Клубника (70 ккал)\n🍲 Обед: Овощной суп с курицей (370 ккал)\n🥜 Перекус: Тыквенные семечки (130 ккал)\n🥦 Ужин: Запечённая брокколи с тофу (290 ккал)",
        "🥑 Завтрак: Авокадо с яйцом (310 ккал)\n🥕 Перекус: Морковь с гуакамоле (160 ккал)\n🍲 Обед: Лёгкий овощной суп (330 ккал)\n🥛 Перекус: Ряженка (110 ккал)\n🐟 Ужин: Запечённый лосось (340 ккал)",
        "🥣 Завтрак: Гречка на воде (240 ккал)\n🍎 Перекус: Яблоко (95 ккал)\n🍲 Обед: Свекольник с яйцом (360 ккал)\n🥜 Перекус: Миндаль (140 ккал)\n🥩 Ужин: Говядина на пару (310 ккал)",
        "🍳 Завтрак: Омлет с помидорами (290 ккал)\n🥒 Перекус: Огурец (30 ккал)\n🍲 Обед: Суп-пюре из брокколи (350 ккал)\n🥛 Перекус: Йогурт без сахара (100 ккал)\n🐟 Ужин: Камбала с лимоном (280 ккал)",
        "🥣 Завтрак: Киноа с ягодами (270 ккал)\n🍌 Перекус: Банан (105 ккал)\n🍲 Обед: Салат с индейкой (390 ккал)\n🥜 Перекус: Грецкие орехи (150 ккал)\n🥩 Ужин: Куриные котлеты на пару (300 ккал)",
        "🥗 Завтрак: Салат с авокадо и яйцом (320 ккал)\n🍏 Перекус: Груша (80 ккал)\n🍲 Обед: Овощной рагу (340 ккал)\n🥛 Перекус: Кефир 1% (90 ккал)\n🐟 Ужин: Треска с овощами (290 ккал)",
        "🥣 Завтрак: Овсянка на воде с корицей (250 ккал)\n🍓 Перекус: Малина (60 ккал)\n🍲 Обед: Суп с чечевицей (370 ккал)\n🥜 Перекус: Семечки подсолнуха (130 ккал)\n🥩 Ужин: Кролик с овощами (310 ккал)",
        "🍳 Завтрак: Яичница с грибами (300 ккал)\n🥒 Перекус: Сельдерей с арахисовой пастой (170 ккал)\n🍲 Обед: Суп с курицей и вермишелью (380 ккал)\n🥛 Перекус: Творог 5% (120 ккал)\n🐟 Ужин: Форель на гриле (330 ккал)",
        "🥣 Завтрак: Пшённая каша с тыквой (260 ккал)\n🍎 Перекус: Яблоко с корицей (110 ккал)\n🍲 Обед: Суп-харчо (360 ккал)\n🥜 Перекус: Кешью (140 ккал)\n🥩 Ужин: Индейка с кабачками (300 ккал)"
    ],
    "набор массы": [
        "🥞 Завтрак: Блинчики с арахисовой пастой (600 ккал)\n🥜 Перекус: Орехи + сухофрукты (300 ккал)\n🍗 Обед: Макароны с курицей (700 ккал)\n🥛 Перекус: Протеиновый коктейль (350 ккал)\n🍖 Ужин: Свинина с картофелем (650 ккал)",
        "🥣 Завтрак: Овсянка с бананом и мёдом (550 ккал)\n🍌 Перекус: Банан + йогурт (280 ккал)\n🍛 Обед: Рис с говядиной (720 ккал)\n🥜 Перекус: Арахис (200 ккал)\n🥩 Ужин: Курица с киноа (600 ккал)",
        "🍳 Завтрак: Яичница с авокадо и тостом (580 ккал)\n🥜 Перекус: Протеиновый батончик (250 ккал)\n🍲 Обед: Паста с фаршем и сыром (750 ккал)\n🥛 Перекус: Молоко с овсянкой (300 ккал)\n🥩 Ужин: Стейк с картофельным пюре (680 ккал)",
        "🥞 Завтрак: Оладьи с кленовым сиропом (620 ккал)\n🥜 Перекус: Смесь орехов (280 ккал)\n🍗 Обед: Гречка с курицей и соусом (710 ккал)\n🥛 Перекус: Кефир с бананом (290 ккал)\n🍖 Ужин: Свинина с гречкой (640 ккал)",
        "🥣 Завтрак: Мюсли с молоком и фруктами (570 ккал)\n🍌 Перекус: Банан + арахисовая паста (310 ккал)\n🍛 Обед: Плов с говядиной (730 ккал)\n🥜 Перекус: Гранола (260 ккал)\n🥩 Ужин: Рыба с картофелем фри (620 ккал)",
        "🍳 Завтрак: Омлет с сыром и ветчиной (600 ккал)\n🥜 Перекус: Протеиновый коктейль (340 ккал)\n🍲 Обед: Лазанья мясная (760 ккал)\n🥛 Перекус: Йогурт с мёдом (270 ккал)\n🥩 Ужин: Курица с рисом и овощами (630 ккал)",
        "🥞 Завтрак: Французские тосты с ягодами (590 ккал)\n🥜 Перекус: Орехи и сухофрукты (290 ккал)\n🍗 Обед: Макароны с фрикадельками (740 ккал)\n🥛 Перекус: Молочный коктейль (320 ккал)\n🍖 Ужин: Говядина с картофелем (660 ккал)",
        "🥣 Завтрак: Овсянка с орехами и сухофруктами (560 ккал)\n🍌 Перекус: Банан + творог (300 ккал)\n🍛 Обед: Рис с курицей и овощами (700 ккал)\n🥜 Перекус: Арахис (210 ккал)\n🥩 Ужин: Свинина с овощами (610 ккал)",
        "🍳 Завтрак: Яичница с беконом и тостом (610 ккал)\n🥜 Перекус: Протеиновый батончик (260 ккал)\n🍲 Обед: Суп с клёцками и мясом (720 ккал)\n🥛 Перекус: Кефир с овсянкой (280 ккал)\n🥩 Ужин: Курица с картофелем (640 ккал)",
        "🥞 Завтрак: Блины с творогом и сметаной (630 ккал)\n🥜 Перекус: Смесь орехов (300 ккал)\n🍗 Обед: Гречка с говядиной (750 ккал)\n🥛 Перекус: Молоко с бананом (310 ккал)\n🍖 Ужин: Свинина с овощами (620 ккал)",
        "🥣 Завтрак: Киноа с орехами и фруктами (580 ккал)\n🍌 Перекус: Банан + йогурт (290 ккал)\n🍛 Обед: Паста с курицей и сливочным соусом (730 ккал)\n🥜 Перекус: Гранола (270 ккал)\n🥩 Ужин: Рыба с картофелем (600 ккал)",
        "🍳 Завтрак: Омлет с овощами и сыром (590 ккал)\n🥜 Перекус: Протеиновый коктейль (330 ккал)\n🍲 Обед: Плов с курицей (740 ккал)\n🥛 Перекус: Творог с мёдом (300 ккал)\n🥩 Ужин: Говядина с гречкой (650 ккал)"
    ],
    "поддержание": [
        "🍳 Завтрак: Яичница с авокадо (400 ккал)\n🍌 Перекус: Банан (120 ккал)\n🍲 Обед: Индейка с овощами (500 ккал)\n🥜 Перекус: Протеиновый батончик (200 ккал)\n🐟 Ужин: Лосось с салатом (480 ккал)",
        "🥣 Завтрак: Овсянка с фруктами (380 ккал)\n🍎 Перекус: Яблоко (95 ккал)\n🍛 Обед: Суп с курицей (420 ккал)\n🥜 Перекус: Горсть орехов (180 ккал)\n🥩 Ужин: Рыба с овощами (400 ккал)",
        "🥞 Завтрак: Блинчики с ягодами (420 ккал)\n🍌 Перекус: Йогурт с мёдом (220 ккал)\n🍲 Обед: Гречка с курицей (480 ккал)\n🥜 Перекус: Фруктовый салат (160 ккал)\n🐟 Ужин: Кальмары с овощами (410 ккал)",
        "🍳 Завтрак: Омлет с овощами (390 ккал)\n🍇 Перекус: Виноград (100 ккал)\n🍛 Обед: Рис с индейкой (470 ккал)\n🥜 Перекус: Творог с ягодами (200 ккал)\n🥩 Ужин: Говядина с брокколи (450 ккал)",
        "🥣 Завтрак: Творог с фруктами (370 ккал)\n🍐 Перекус: Груша (100 ккал)\n🍲 Обед: Суп-пюре из тыквы (410 ккал)\n🥜 Перекус: Миндаль (170 ккал)\n🐟 Ужин: Форель с овощами (430 ккал)",
        "🥞 Завтрак: Оладьи с яблоком (400 ккал)\n🍓 Перекус: Клубника (80 ккал)\n🍛 Обед: Паста с овощами (460 ккал)\n🥜 Перекус: Кефир (150 ккал)\n🥩 Ужин: Курица с киноа (440 ккал)",
        "🍳 Завтрак: Яичница с помидорами (380 ккал)\n🍊 Перекус: Апельсин (85 ккал)\n🍲 Обед: Суп с фрикадельками (430 ккал)\n🥜 Перекус: Йогурт (190 ккал)\n🐟 Ужин: Треска с овощами (420 ккал)",
        "🥣 Завтрак: Гречка с яйцом (390 ккал)\n🍌 Перекус: Банан (110 ккал)\n🍛 Обед: Салат с тунцом (450 ккал)\n🥜 Перекус: Орехи (180 ккал)\n🥩 Ужин: Индейка с овощами (460 ккал)",
        "🥞 Завтрак: Блины с мёдом (410 ккал)\n🍎 Перекус: Яблоко (95 ккал)\n🍲 Обед: Овощной суп с курицей (420 ккал)\n🥜 Перекус: Творог (200 ккал)\n🐟 Ужин: Лосось с салатом (470 ккал)",
        "🍳 Завтрак: Омлет с авокадо (400 ккал)\n🍇 Перекус: Виноград (100 ккал)\n🍛 Обед: Рис с рыбой (440 ккал)\n🥜 Перекус: Кефир с ягодами (180 ккал)\n🥩 Ужин: Говядина с овощами (450 ккал)",
        "🥣 Завтрак: Овсянка с орехами (390 ккал)\n🍐 Перекус: Груша (100 ккал)\n🍲 Обед: Суп с чечевицей (430 ккал)\n🥜 Перекус: Йогурт (190 ккал)\n🐟 Ужин: Камбала с овощами (410 ккал)",
        "🥞 Завтрак: Французские тосты (420 ккал)\n🍓 Перекус: Малина (70 ккал)\n🍛 Обед: Паста с курицей (460 ккал)\n🥜 Перекус: Творог с мёдом (210 ккал)\n🥩 Ужин: Курица с брокколи (440 ккал)"
    ],
    "спорт": [
        "🥣 Завтрак: Гречка с яйцом (420 ккал)\n🍌 Перекус: Банан + орехи (250 ккал)\n🍗 Обед: Курица с рисом (650 ккал)\n🥛 Перекус: Творог с мёдом (300 ккал)\n🥩 Ужин: Говядина с овощами (580 ккал)",
        "🍳 Завтрак: Омлет с овощами и авокадо (440 ккал)\n🥜 Перекус: Протеиновый коктейль (320 ккал)\n🍲 Обед: Рис с лососем (670 ккал)\n🥛 Перекус: Кефир с бананом (280 ккал)\n🐟 Ужин: Тунец с овощами (520 ккал)",
        "🥞 Завтрак: Блинчики с творогом (460 ккал)\n🍌 Перекус: Банан (120 ккал)\n🍛 Обед: Макароны с говядиной (690 ккал)\n🥛 Перекус: Протеиновый батончик (260 ккал)\n🥩 Ужин: Курица с киноа (560 ккал)",
        "🥣 Завтрак: Овсянка с яйцом и орехами (430 ккал)\n🥜 Перекус: Арахисовая паста с яблоком (270 ккал)\n🍲 Обед: Плов с курицей (660 ккал)\n🥛 Перекус: Творог с ягодами (290 ккал)\n🐟 Ужин: Форель с овощами (530 ккал)",
        "🍳 Завтрак: Яичница с беконом (450 ккал)\n🍌 Перекус: Банан + йогурт (240 ккал)\n🍛 Обед: Гречка с говядиной (680 ккал)\n🥛 Перекус: Молоко с овсянкой (300 ккал)\n🥩 Ужин: Индейка с овощами (540 ккал)",
        "🥞 Завтрак: Оладьи с бананом (440 ккал)\n🥜 Перекус: Смесь орехов (260 ккал)\n🍲 Обед: Рис с курицей и овощами (650 ккал)\n🥛 Перекус: Кефир с мёдом (270 ккал)\n🐟 Ужин: Кальмары с овощами (510 ккал)",
        "🥣 Завтрак: Киноа с яйцом и авокадо (420 ккал)\n🍌 Перекус: Банан (120 ккал)\n🍛 Обед: Паста с фаршем (670 ккал)\n🥛 Перекус: Протеиновый коктейль (310 ккал)\n🥩 Ужин: Говядина с брокколи (550 ккал)",
        "🍳 Завтрак: Омлет с сыром и помидорами (430 ккал)\n🥜 Перекус: Творог с мёдом (280 ккал)\n🍲 Обед: Суп с клёцками и мясом (640 ккал)\n🥛 Перекус: Йогурт с бананом (250 ккал)\n🐟 Ужин: Лосось с овощами (520 ккал)",
        "🥞 Завтрак: Блины с арахисовой пастой (450 ккал)\n🍌 Перекус: Банан + орехи (250 ккал)\n🍛 Обед: Рис с индейкой (660 ккал)\n🥛 Перекус: Кефир с овсянкой (290 ккал)\n🥩 Ужин: Курица с овощами (530 ккал)",
        "🥣 Завтрак: Овсянка с бананом и мёдом (410 ккал)\n🥜 Перекус: Арахис (240 ккал)\n🍲 Обед: Гречка с курицей (650 ккал)\n🥛 Перекус: Творог с ягодами (280 ккал)\n🐟 Ужин: Треска с овощами (500 ккал)",
        "🍳 Завтрак: Яичница с авокадо и тостом (440 ккал)\n🍌 Перекус: Банан (120 ккал)\n🍛 Обед: Плов с говядиной (680 ккал)\n🥛 Перекус: Протеиновый батончик (260 ккал)\n🥩 Ужин: Говядина с овощами (540 ккал)",
        "🥞 Завтрак: Французские тосты с ягодами (430 ккал)\n🥜 Перекус: Смесь орехов (250 ккал)\n🍲 Обед: Макароны с курицей (660 ккал)\n🥛 Перекус: Кефир с мёдом (270 ккал)\n🐟 Ужин: Форель с овощами (510 ккал)"
    ]
}


LOCAL_TIPS = {
    "похудение": [
        "Пейте стакан воды за 30 минут до еды",
        "Исключите сахар и сладкие напитки",
        "Ужинайте за 3 часа до сна",
        "Ешьте медленно — мозгу нужно 20 минут, чтобы почувствовать сытость",
        "Добавьте в рацион клетчатку: овсянка, овощи, яблоки",
        "Готовьте дома — это контролирует калории",
        "Спите 7–8 часов — недосып повышает аппетит",
        "Не пропускайте завтрак",
        "Замените белый хлеб на цельнозерновой",
        "Используйте маленькие тарелки",
        "Ведите пищевой дневник",
        "Ходите пешком минимум 8000 шагов в день"
    ],
    "набор массы": [
        "Ешьте каждые 2.5–3 часа",
        "Увеличьте калорийность за счёт орехов, авокадо, оливкового масла",
        "Пейте калорийные коктейли между приёмами пищи",
        "Не забывайте про углеводы — они дают энергию для роста",
        "Спите минимум 8 часов — мышцы растут во сне",
        "Тренируйтесь с отягощениями 3–4 раза в неделю",
        "Ешьте белок после тренировки",
        "Не бойтесь жиров — они нужны для гормонов",
        "Используйте протеиновые добавки при нехватке белка",
        "Пейте достаточно воды — обезвоживание снижает анаболизм"
    ],
    "спорт": [
        "За 2 часа до тренировки — углеводы + немного белка",
        "Сразу после — быстрые углеводы + белок",
        "Пейте воду каждые 15–20 минут во время нагрузки",
        "Восполняйте электролиты при интенсивных тренировках",
        "Углеводное окно длится 45 минут после тренировки",
        "Белок распределяйте равномерно в течение дня",
        "Не тренируйтесь на голодный желудок",
        "Следите за восстановлением — без отдыха нет роста"
    ],
    "поддержание": [
        "Соблюдайте режим питания — ешьте в одно и то же время",
        "Разнообразьте рацион — минимум 30 продуктов в неделю",
        "Пейте 1.5–2 литра воды ежедневно",
        "Готовьте на пару, запекайте, тушите — избегайте жарки",
        "Ешьте овощи при каждом приёме пищи",
        "Контролируйте размер порций",
        "Позволяйте себе 1–2 «cheat meal» в неделю",
        "Регулярно взвешивайтесь — но не чаще раза в неделю"
    ]
}


def get_ai_response(prompt):
    try:
        completion = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenRouter error: {e}")
        return None


def generate_pdf(user_id):
    if user_id not in user_data:
        return None
    data = user_data[user_id]
    bmi = calculate_bmi(data['weight'], data['height'])
    calories = calculate_calories(data['weight'], data['height'], data['age'],
                                  data['gender'], data['goal'], data['activity'])
    p, f, c = calculate_bju(calories, data['goal'], data['weight'])
    plan = random.choice(LOCAL_PLANS.get(data['goal'], ["План не найден"]))

    pdf = FPDF()
    pdf.add_page()
    try:
        
        pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf')
        pdf.set_font('DejaVu', '', 12)
    except:
        
        pdf.set_font('Helvetica', '', 12)

    
    pdf.set_font('', 'B', 16)
    pdf.cell(0, 10, 'План питания от Нутрициолога', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(10)

    pdf.set_font('', 'B', 12)
    pdf.cell(0, 8, f"Пользователь ID: {user_id}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, f"Цель: {data['goal']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, f"Калории: {calories} ккал | Б: {p}г | Ж: {f}г | У: {c}г", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    pdf.set_font('', 'B', 12)
    pdf.cell(0, 8, 'План на день:', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('', '', 12)
    for line in plan.split('\n'):
        pdf.cell(0, 8, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    filename = f"plan_{user_id}.pdf"
    pdf.output(filename)
    return filename


@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "🍏 Добро пожаловать в *Умного Нутрициолога*!\n\nВыберите действие:", 
                     parse_mode="Markdown", reply_markup=create_main_keyboard())

@bot.message_handler(func=lambda m: m.text == '📝 Ввести данные')
def start_data_input(m):
    user_data[m.chat.id] = {}
    msg = bot.send_message(m.chat.id, "Введите возраст (лет):")
    bot.register_next_step_handler(msg, process_age)

def process_age(m):
    try:
        age = int(m.text)
        if 10 <= age <= 100:
            user_data[m.chat.id]['age'] = age
            msg = bot.send_message(m.chat.id, "Вес (кг):")
            bot.register_next_step_handler(msg, process_weight)
        else:
            raise ValueError
    except:
        bot.send_message(m.chat.id, "Введите число от 10 до 100")
        start_data_input(m)

def process_weight(m):
    try:
        weight = float(m.text)
        if 30 <= weight <= 200:
            user_data[m.chat.id]['weight'] = weight
            msg = bot.send_message(m.chat.id, "Рост (см):")
            bot.register_next_step_handler(msg, process_height)
        else:
            raise ValueError
    except:
        bot.send_message(m.chat.id, "Введите число от 30 до 200")
        start_data_input(m)

def process_height(m):
    try:
        height = float(m.text)
        if 100 <= height <= 250:
            user_data[m.chat.id]['height'] = height
            kb = ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add(KeyboardButton('Мужской'), KeyboardButton('Женский'))
            msg = bot.send_message(m.chat.id, "Пол:", reply_markup=kb)
            bot.register_next_step_handler(msg, process_gender)
        else:
            raise ValueError
    except:
        bot.send_message(m.chat.id, "Введите число от 100 до 250")
        start_data_input(m)

def process_gender(m):
    user_data[m.chat.id]['gender'] = 'мужской' if 'муж' in m.text.lower() else 'женский'
    msg = bot.send_message(m.chat.id, "Уровень активности:", reply_markup=create_activity_keyboard())
    bot.register_next_step_handler(msg, process_activity)

def process_activity(m):
    act_map = {'сидячий': 'сидячий', 'легкая': 'легкая', 'умеренные': 'умеренная', 'высокая': 'высокая'}
    key = next((k for k in act_map if k in m.text.lower()), 'умеренная')
    user_data[m.chat.id]['activity'] = act_map[key]
    msg = bot.send_message(m.chat.id, "Ваша цель:", reply_markup=create_goal_keyboard())
    bot.register_next_step_handler(msg, process_goal)

def process_goal(m):
    goal_map = {'похудение': 'похудение', 'набор': 'набор массы', 'поддержание': 'поддержание', 'спорт': 'спорт'}
    key = next((k for k in goal_map if k in m.text.lower()), 'поддержание')
    user_data[m.chat.id]['goal'] = goal_map[key]
    bot.send_message(m.chat.id, "✅ Данные сохранены!", reply_markup=create_main_keyboard())


@bot.message_handler(func=lambda m: m.text == '👤 Личный кабинет')
def personal_cabinet(m):
    if m.chat.id not in user_data:
        bot.send_message(m.chat.id, "❌ Сначала введите данные")
        return
    data = user_data[m.chat.id]
    bmi = calculate_bmi(data['weight'], data['height'])
    calories = calculate_calories(data['weight'], data['height'], data['age'],
                                  data['gender'], data['goal'], data['activity'])
    p, f, c = calculate_bju(calories, data['goal'], data['weight'])
    status = get_bmi_status(bmi)

    text = f"""👤 *ЛИЧНЫЙ КАБИНЕТ*

📊 *Основное:*
• Возраст: {data['age']} лет
• Вес: {data['weight']} кг
• Рост: {data['height']} см
• Пол: {data['gender']}
• Активность: {data['activity']}
• Цель: {data['goal']}

📈 *Расчёты:*
• ИМТ: {bmi} ({status})
• Калории: {calories} ккал/день
• Белки: {p} г
• Жиры: {f} г
• Углеводы: {c} г

💬 Используйте меню для получения планов и советов!"""

    bot.send_message(m.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == '🍎 Умный план (ИИ)')
def ai_plan(m):
    if m.chat.id not in user_data:
        bot.send_message(m.chat.id, "❌ Сначала введите данные")
        return
    bot.send_chat_action(m.chat.id, 'typing')
    data = user_data[m.chat.id]
    calories = calculate_calories(data['weight'], data['height'], data['age'],
                                  data['gender'], data['goal'], data['activity'])
    p, f, c = calculate_bju(calories, data['goal'], data['weight'])
    prompt = f"Составь план питания на день для {data['age']} лет, {data['weight']} кг, цель: {data['goal']}. Нужно {calories} ккал, {p}г белка. Только список на русском с эмодзи."
    ai = get_ai_response(prompt)
    if ai:
        bot.send_message(m.chat.id, f"✨ *План от ИИ:*\n\n{ai}", parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ ИИ недоступен. Используйте локальный план.")


@bot.message_handler(func=lambda m: m.text == '🎲 Локальный план')
def local_plan(m):
    if m.chat.id not in user_data:
        bot.send_message(m.chat.id, "❌ Сначала введите данные")
        return
    goal = user_data[m.chat.id]['goal']
    plan = random.choice(LOCAL_PLANS.get(goal, ["План не найден"]))
    bot.send_message(m.chat.id, f"🎲 *Локальный план (цель: {goal}):*\n\n{plan}", parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == '💡 Советы от ИИ')
def ai_tips(m):
    if m.chat.id not in user_data:
        bot.send_message(m.chat.id, "❌ Сначала введите данные")
        return
    bot.send_chat_action(m.chat.id, 'typing')
    goal = user_data[m.chat.id]['goal']
    prompt = f"Дай 5 практических советов по питанию для цели '{goal}'. Кратко, на русском, без вводных фраз."
    ai = get_ai_response(prompt)
    if ai:
        bot.send_message(m.chat.id, f"💡 *Советы от ИИ:*\n\n{ai}", parse_mode="Markdown")
    else:
        tips = random.sample(LOCAL_TIPS.get(goal, LOCAL_TIPS["поддержание"]), min(5, len(LOCAL_TIPS.get(goal, []))))
        text = "💡 *Локальные советы:*\n\n" + "\n".join(f"• {t}" for t in tips)
        bot.send_message(m.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == '📄 PDF-план')
def pdf_plan(m):
    if m.chat.id not in user_data:
        bot.send_message(m.chat.id, "❌ Сначала введите данные")
        return
    bot.send_chat_action(m.chat.id, 'upload_document')
    try:
        filename = generate_pdf(m.chat.id)
        with open(filename, 'rb') as f:
            bot.send_document(m.chat.id, f, caption="📄 Ваш персональный план!")
        os.remove(filename)
    except Exception as e:
        bot.send_message(m.chat.id, "❌ Ошибка генерации PDF")


@bot.message_handler(func=lambda m: m.text == '🔄 Сбросить данные')
def reset(m):
    user_data.pop(m.chat.id, None)
    bot.send_message(m.chat.id, "✅ Данные сброшены", reply_markup=create_main_keyboard())


if __name__ == "__main__":
    print("🚀 Запущен: Умный Нутрициолог PRO")
    print("🔑 Убедитесь, что OPENROUTER_API_KEY задан")
    bot.infinity_polling()
