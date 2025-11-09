import os
import logging
import csv
import random
from collections import defaultdict, deque
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token='7978111291:AAHZ1V52UmvK7QcEOE5IcXbB2MEHbDgYMdM')
dp = Dispatcher()

# Глобальные переменные для хранения состояния пользователей
user_states = {}
user_progress = {}

# Загрузка словаря из CSV
def load_vocabulary():
    vocabulary = defaultdict(list)
    try:
        with open('vocab.csv', 'r', encoding='utf-8') as file:
            # Читаем первую строку для определения структуры
            first_line = file.readline().strip()
            logger.info(f"First line: {first_line}")
            
            # Проверяем разделитель
            if '|' in first_line:
                delimiter = '|'
                logger.info("Using | as delimiter")
            elif ',' in first_line:
                delimiter = ','
                logger.info("Using , as delimiter")
            else:
                delimiter = '\t'
                logger.info("Using tab as delimiter")
            
            # Возвращаемся к началу файла
            file.seek(0)
            
            # Читаем CSV
            reader = csv.reader(file, delimiter=delimiter)
            headers = next(reader)
            logger.info(f"Headers: {headers}")
            
            # Нормализуем заголовки
            headers = [header.strip().lower() for header in headers]
            logger.info(f"Normalized headers: {headers}")
            
            # Определяем индексы колонок
            unit_idx = None
            word_idx = None
            transcription_idx = None
            definition_idx = None
            russian_idx = None
            uzbek_idx = None
            
            for i, header in enumerate(headers):
                if 'unit' in header:
                    unit_idx = i
                elif 'word' in header:
                    word_idx = i
                elif 'transcription' in header:
                    transcription_idx = i
                elif 'definition' in header:
                    definition_idx = i
                elif 'russian' in header:
                    russian_idx = i
                elif 'uzbek' in header:
                    uzbek_idx = i
            
            logger.info(f"Column indices - Unit: {unit_idx}, Word: {word_idx}")
            
            if unit_idx is None or word_idx is None:
                logger.error("Required columns (unit, word) not found!")
                return vocabulary
            
            # Читаем данные
            for row_num, row in enumerate(reader, 2):
                if len(row) <= max(unit_idx, word_idx):
                    continue
                
                unit = row[unit_idx].strip()
                word = row[word_idx].strip()
                
                if not unit or not word:
                    continue
                
                word_data = {
                    'word': word,
                    'transcription': row[transcription_idx].strip() if transcription_idx is not None and transcription_idx < len(row) else '',
                    'definition': row[definition_idx].strip() if definition_idx is not None and definition_idx < len(row) else '',
                    'russian': row[russian_idx].strip() if russian_idx is not None and russian_idx < len(row) else '',
                    'uzbek': row[uzbek_idx].strip() if uzbek_idx is not None and uzbek_idx < len(row) else '',
                }
                
                vocabulary[unit].append(word_data)
        
        logger.info(f"Successfully loaded {sum(len(words) for words in vocabulary.values())} words from {len(vocabulary)} units")
        return vocabulary
        
    except Exception as e:
        logger.error(f"Error loading vocabulary: {e}")
        # Тестовые данные
        vocabulary = defaultdict(list)
        test_data = [
            {
                'word': 'bond',
                'transcription': '/bɒnd/',
                'definition': 'a close connection joining two or more people',
                'russian': 'узы, связь',
                'uzbek': 'aloqa, munosabat',
            },
            {
                'word': 'adolescence', 
                'transcription': '/æd.əˈles.əns/',
                'definition': 'the period of time in a persons life when they are developing into an adult',
                'russian': 'юность',
                'uzbek': 'o\'smirlik',
            }
        ]
        vocabulary['UNIT 1'] = test_data
        return vocabulary

vocabulary = load_vocabulary()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {'mode': 'unit_selection'}
    
    builder = InlineKeyboardBuilder()
    
    # Сортируем юниты по номеру
    units = sorted(vocabulary.keys(), key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else float('inf'))
    
    for unit in units:
        builder.button(text=f"{unit} ({len(vocabulary[unit])} words)", callback_data=f"unit_{unit}")
    
    builder.button(text="📊 Progress", callback_data="progress")
    builder.adjust(1)
    
    await message.answer(
        "🇬🇧 Welcome to Vocabulary Bot! 🇺🇿\n"
        "Select a unit to start learning:",
        reply_markup=builder.as_markup()
    )

# Показ выбора режима
async def show_mode_selection(callback: types.CallbackQuery, unit: str):
    user_id = callback.from_user.id
    user_states[user_id] = {'unit': unit, 'mode': 'mode_selection'}
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Practice Mode", callback_data="practice_mode")
    builder.button(text="🃏 Flashcard Mode", callback_data="flashcard_mode")
    builder.button(text="🔄 Reverse Mode", callback_data="reverse_mode")
    builder.button(text="⬅️ Back to Units", callback_data="back_to_units")
    builder.button(text="📊 Progress", callback_data="progress")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"Unit: {unit}\nSelect learning mode:",
        reply_markup=builder.as_markup()
    )

# Показ выбора юнитов
async def show_unit_selection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = {'mode': 'unit_selection'}
    
    builder = InlineKeyboardBuilder()
    
    # Сортируем юниты по номеру
    units = sorted(vocabulary.keys(), key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else float('inf'))
    
    for unit in units:
        builder.button(text=f"{unit} ({len(vocabulary[unit])} words)", callback_data=f"unit_{unit}")
    
    builder.button(text="📊 Progress", callback_data="progress")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "Select a unit to start learning:",
        reply_markup=builder.as_markup()
    )
# Режим изучения слов (Practice Mode)
async def start_practice_mode(callback: types.CallbackQuery, user_id: int):
    unit = user_states[user_id]['unit']
    user_states[user_id] = {
        'mode': 'practice',
        'unit': unit,
        'current_index': 0
    }
    
    await show_practice_word(callback, user_id)

async def show_practice_word(callback: types.CallbackQuery, user_id: int):
    state = user_states[user_id]
    unit = state['unit']
    index = state['current_index']
    words = vocabulary[unit]
    word_data = words[index]
    
    message = (
        f"<b>{word_data['word']}</b> {word_data['transcription']}\n"
        f"{word_data['definition']}\n"
        f"🇷🇺 {word_data['russian']}\n"
        f"🇺🇿 {word_data['uzbek']}\n"
        f"\nWord {index + 1} of {len(words)}"
    )
    
    builder = InlineKeyboardBuilder()
    
    if index > 0:
        builder.button(text="⬅️ Previous", callback_data="practice_prev")
    
    if index < len(words) - 1:
        builder.button(text="Next ➡️", callback_data="practice_next")
    
    builder.button(text="⬅️ Back to Modes", callback_data="back_to_modes")
    builder.adjust(2)  # По 2 кнопки в строке для Previous/Next
    
    await callback.message.edit_text(
        message, 
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

# Режим флеш-карточек (Flashcard Mode)
async def start_flashcard_mode(callback: types.CallbackQuery, user_id: int):
    unit = user_states[user_id]['unit']
    words = vocabulary[unit].copy()
    random.shuffle(words)
    
    user_states[user_id] = {
        'mode': 'flashcard',
        'unit': unit,
        'words': words,
        'current_index': 0,
        'unknown_words': deque(),
        'completed_words': set()
    }
    
    await show_flashcard_word(callback, user_id)

async def show_flashcard_word(callback: types.CallbackQuery, user_id: int):
    state = user_states[user_id]
    words = state['words']
    index = state['current_index']
    
    if index >= len(words):
        if state['unknown_words']:
            next_word = state['unknown_words'].popleft()
            words.append(next_word)
            state['current_index'] = len(words) - 1
        else:
            await flashcard_session_complete(callback, user_id)
            return
    
    word_data = words[state['current_index']]
    
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Don't know", callback_data="flashcard_dont_know")
    builder.button(text="👁️ Show", callback_data="flashcard_show")
    builder.button(text="✅ Know", callback_data="flashcard_know")
    builder.button(text="⬅️ Back to Modes", callback_data="back_to_modes")
    builder.adjust(2, 1, 1)  # 2 кнопки в первой строке, по 1 в остальных
    
    await callback.message.edit_text(
        f"<b>{word_data['word']}</b>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

async def flashcard_show(callback: types.CallbackQuery, user_id: int):
    state = user_states[user_id]
    word_data = state['words'][state['current_index']]
    
    message = (
        f"<b>{word_data['word']}</b> {word_data['transcription']}\n"
        f"{word_data['definition']}\n"
        f"🇷🇺 {word_data['russian']}\n"
        f"🇺🇿 {word_data['uzbek']}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Don't know", callback_data="flashcard_dont_know")
    builder.button(text="✅ Know", callback_data="flashcard_know")
    builder.button(text="⬅️ Back to Modes", callback_data="back_to_modes")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(
        message,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

# Режим обратного ввода (Reverse Mode)
async def start_reverse_mode(callback: types.CallbackQuery, user_id: int):
    unit = user_states[user_id]['unit']
    words = vocabulary[unit].copy()
    random.shuffle(words)
    
    user_states[user_id] = {
        'mode': 'reverse',
        'unit': unit,
        'words': words,
        'current_index': 0,
        'waiting_for_answer': True
    }
    
    await show_reverse_question(callback, user_id)

async def show_reverse_question(callback: types.CallbackQuery, user_id: int):
    state = user_states[user_id]
    word_data = state['words'][state['current_index']]
    
    message = (
        f"<b>What word corresponds to this definition?</b>\n\n"
        f"{word_data['definition']}\n"
        f"🇷🇺 {word_data['russian']}\n"
        f"🇺🇿 {word_data['uzbek']}\n\n"
        f"Please type your answer:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Back to Modes", callback_data="back_to_modes")
    
    await callback.message.edit_text(
        message,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )
    
    state['waiting_for_answer'] = True

# Обработка текстовых сообщений (для Reverse Mode)
@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in user_states:
        await message.answer("Please use /start to begin")
        return
    
    state = user_states[user_id]
    
    if state['mode'] == 'reverse' and state.get('waiting_for_answer', False):
        user_answer = message.text.strip().lower()
        correct_word = state['words'][state['current_index']]['word'].lower()
        
        if user_answer == correct_word:
            response = "✅ Correct! Well done!"
            builder = InlineKeyboardBuilder()
            builder.button(text="Next Word ➡️", callback_data="reverse_next")
            builder.button(text="⬅️ Back to Modes", callback_data="back_to_modes")
        else:
            word_data = state['words'][state['current_index']]
            response = (
                f"❌ Incorrect. The right answer is:\n\n"
                f"<b>{word_data['word']}</b> {word_data['transcription']}\n"
                f"{word_data['definition']}\n"
                f"🇷🇺 {word_data['russian']}\n"
                f"🇺🇿 {word_data['uzbek']}"
            )
            builder = InlineKeyboardBuilder()
            builder.button(text="Next Word ➡️", callback_data="reverse_next")
            builder.button(text="⬅️ Back to Modes", callback_data="back_to_modes")
        
        await message.answer(
            response,
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML
        )
        state['waiting_for_answer'] = False

# Показ прогресса
async def show_progress(callback: types.CallbackQuery, user_id: int):
    if user_id not in user_progress or not user_progress[user_id]:
        message = "📊 You haven't started learning any words yet.\nSelect a unit and start learning!"
    else:
        message = "📊 Your Progress:\n\n"
        total_known = 0
        total_words = 0
        
        for unit, progress in user_progress[user_id].items():
            unit_words = len(vocabulary[unit])
            known_words = len(progress['known'])
            total_known += known_words
            total_words += unit_words
            
            percentage = (known_words / unit_words) * 100 if unit_words > 0 else 0
            message += f"<b>{unit}</b>: {known_words}/{unit_words} ({percentage:.1f}%)\n"
        
        overall_percentage = (total_known / total_words) * 100 if total_words > 0 else 0
        message += f"\n<b>Overall Progress</b>: {total_known}/{total_words} ({overall_percentage:.1f}%)"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Back", callback_data="back_to_units")
    
    await callback.message.edit_text(
        message,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

# Обработка всех callback запросов
@dp.callback_query(F.data.startswith("unit_"))
async def handle_unit_selection(callback: types.CallbackQuery):
    unit = callback.data[5:]
    await show_mode_selection(callback, unit)

@dp.callback_query(F.data == "progress")
async def handle_progress(callback: types.CallbackQuery):
    await show_progress(callback, callback.from_user.id)

@dp.callback_query(F.data == "practice_mode")
async def handle_practice_mode(callback: types.CallbackQuery):
    await start_practice_mode(callback, callback.from_user.id)

@dp.callback_query(F.data == "flashcard_mode")
async def handle_flashcard_mode(callback: types.CallbackQuery):
    await start_flashcard_mode(callback, callback.from_user.id)

@dp.callback_query(F.data == "reverse_mode")
async def handle_reverse_mode(callback: types.CallbackQuery):
    await start_reverse_mode(callback, callback.from_user.id)

@dp.callback_query(F.data == "back_to_units")
async def handle_back_to_units(callback: types.CallbackQuery):
    await show_unit_selection(callback)

@dp.callback_query(F.data == "back_to_modes")
async def handle_back_to_modes(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    unit = user_states[user_id]['unit']
    await show_mode_selection(callback, unit)

@dp.callback_query(F.data == "practice_next")
async def handle_practice_next(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id]['current_index'] += 1
    await show_practice_word(callback, user_id)

@dp.callback_query(F.data == "practice_prev")
async def handle_practice_prev(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id]['current_index'] -= 1
    await show_practice_word(callback, user_id)

@dp.callback_query(F.data == "flashcard_dont_know")
async def handle_flashcard_dont_know(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = user_states[user_id]
    current_word = state['words'][state['current_index']]
    
    if len(state['unknown_words']) < 5:
        state['unknown_words'].append(current_word)
    else:
        state['unknown_words'].rotate(-1)
        state['unknown_words'][-1] = current_word
    
    state['current_index'] += 1
    await show_flashcard_word(callback, user_id)

@dp.callback_query(F.data == "flashcard_show")
async def handle_flashcard_show(callback: types.CallbackQuery):
    await flashcard_show(callback, callback.from_user.id)

@dp.callback_query(F.data == "flashcard_know")
async def handle_flashcard_know(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = user_states[user_id]
    state['completed_words'].add(state['words'][state['current_index']]['word'])
    state['current_index'] += 1
    await show_flashcard_word(callback, user_id)

@dp.callback_query(F.data == "reverse_next")
async def handle_reverse_next(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = user_states[user_id]
    state['current_index'] += 1
    
    if state['current_index'] >= len(state['words']):
        await reverse_session_complete(callback, user_id)
    else:
        await show_reverse_question(callback, user_id)

async def flashcard_session_complete(callback: types.CallbackQuery, user_id: int):
    state = user_states[user_id]
    unit = state['unit']
    total_words = len(vocabulary[unit])
    known_words = len(state['completed_words'])
    
    if user_id not in user_progress:
        user_progress[user_id] = {}
    if unit not in user_progress[user_id]:
        user_progress[user_id][unit] = {'known': set(), 'unknown': set()}
    
    user_progress[user_id][unit]['known'].update(state['completed_words'])
    
    message = (
        f"🎉 Flashcard session complete!\n"
        f"Unit: {unit}\n"
        f"Words known: {known_words}/{total_words}\n"
        f"Progress: {known_words/total_words*100:.1f}%"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Repeat Session", callback_data="flashcard_mode")
    builder.button(text="⬅️ Back to Modes", callback_data="back_to_modes")
    builder.button(text="📊 View Progress", callback_data="progress")
    builder.adjust(1)
    
    await callback.message.edit_text(message, reply_markup=builder.as_markup())

async def reverse_session_complete(callback: types.CallbackQuery, user_id: int):
    state = user_states[user_id]
    unit = state['unit']
    total_words = len(vocabulary[unit])
    
    message = (
        f"🎉 Reverse mode session complete!\n"
        f"Unit: {unit}\n"
        f"Words practiced: {total_words}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Repeat Session", callback_data="reverse_mode")
    builder.button(text="⬅️ Back to Modes", callback_data="back_to_modes")
    builder.button(text="📊 View Progress", callback_data="progress")
    builder.adjust(1)
    
    await callback.message.edit_text(message, reply_markup=builder.as_markup())

# Запуск бота
async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)


import asyncio
import sys

if __name__ == '__main__':
    # Для корректного завершения работы
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped gracefully")
    except Exception as e:
        print(f"Bot crashed with error: {e}")
