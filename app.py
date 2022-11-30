# -*- coding: utf-8 -*

import os
import logging
import uuid

from dotenv import load_dotenv
from redis import Redis
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup

load_dotenv()

logging.basicConfig(level=logging.INFO)

redis = Redis(host='redis', port=6379)

API_TOKEN = os.getenv('API_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
CHANNEL_ID = os.getenv('CHANNEL_ID')

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Photo(StatesGroup):
  id = State()
  caption = State()

class Deletion(StatesGroup):
  id = State()

async def check_user(user_id):
  user_in_chat = await bot.get_chat_member(CHAT_ID, user_id)
  if (user_in_chat.status == 'left'):
    return False
  else:
    return True

async def get_meta():
  chat = await bot.get_chat(CHAT_ID)
  channel = await bot.get_chat(CHANNEL_ID)
  meta = dict()
  meta['chat_title'] = chat.title
  meta['chat_username'] = chat.username
  meta['channel_title'] = channel.title
  meta['channel_username'] = channel.username

  return meta

global_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
global_menu.add('Добавить фотографию')
global_menu.add('Удалить фотографию')
global_menu.add('Правила')
cancel_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
cancel_menu.add('Отмена')

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
  meta = await get_meta()
  await message.reply(f'Привет!\nЯ бот канала "{meta["channel_title"]}".\nПеред публикацией ознакомтесь с правилами.\nДля публикации фотографии воспользуйтесь меню.\nПубликация доступна только участникам чата "{meta["chat_title"]}"', reply_markup=global_menu)

@dp.message_handler(content_types=['text'])
async def handle_command(message: types.Message):
  meta = await get_meta()
  is_user_in_chat = await check_user(message.from_user.id)
  if (is_user_in_chat == False):
    text = f'Публикация фотографий в галерею доступна только участникам чата <a href="https://t.me/{meta["chat_username"]}">{meta["chat_title"]}</a>'
    await message.answer(parse_mode='html',text=text)
    return
  if (message.text == 'Добавить фотографию'):
    await Photo.id.set()
    await message.reply('Отправьте фотографию (не как файл)', reply_markup=cancel_menu)
  elif (message.text == 'Удалить фотографию'):
    await Deletion.id.set()
    await message.reply('Введите код для удаления:', reply_markup=cancel_menu)
  elif (message.text == 'Правила'):
    await message.reply(f'Публикация доступна только участникам группы "{meta["chat_title"]}"\n\nТребования к фото:\n1. Допускается публикация фотографий/сканов аналоговых отпечатков выполненных по классическому серебряно-желатиновому процессу либо в любой альтернативной технике.\n2. Допускается публикация сканов фотопленки в случае, если скан представляет собой завершенную работу и распространяется автором в цифровом виде.\n3. Допускается публикация фотографии/сканов отпечатков выполненных в альтернативных техниках с цифровых негативов.\n4. В случае публикации фотографии отпечатка, непосредственно отпечаток должен занимать не менее 95% площади кадра. Перспективные искажения должны быть сведены к минимуму.\n5. Запрещена публикация репортажных фотографий, а также фотографий не имеющих художественной ценности(например тестовых снимков).\n6. Запрещена публикация цифровых фотографий.\n7. Запрещена публикация любой рекламны, спама, оскорблений, политических призывов и материалов, нарушающих законодательство Российской Федерации.\n\nТребования к подписи:\n1. Необходимо добавить к фотографии небольшое описание с используемым оборудованием, пленкой, техникой печати, а также любыми другими сведениями касательно выкладываемой работы, которым Вы считаете нужными поделиться.\n2. Автор будет добавлен в описание автоматически.\n3. В описании запрещено упоминать любые лаборатории, даже если вы там проявляли и/или сканировали фотографию.\n4. В описании запрещена публикация любой рекламны, спама, оскорблений, политических призывов и материалов, нарушающих законодательство Российской Федерации.\n\nВ случае нарушения данных правил, Ваша фотография будет удалена.\nВ случае систематического нарушения правил, Вы будете исключены из чата.', reply_markup=global_menu)
  else:
    await message.reply(f'Для публикации фотографии воспользуйтесь меню.', reply_markup=global_menu)

@dp.message_handler(Text(equals='Отмена', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
  current_state = await state.get_state()
  if current_state is None:
    return
  logging.info('Cancelling state %r', current_state)
  await state.finish()
  await message.reply(f'Добро пожаловат! Для публикации фотографии воспользуйтесь меню.', reply_markup=global_menu)

async def post_photo(message, photo_id, caption):
  caption_with_author=f'{caption}\nАвтор: <a href="tg://user?id={message.from_user.id}">{message.from_user.mention}</a>'
  res = await bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, parse_mode='html', caption=caption_with_author)
  uid = int(uuid.uuid4())
  message_id = int(res.message_id)
  try:
    redis.set(uid, message_id)
  except:
    await message.answer(f'Что-то пошло не так! Попробуте перезагрузить бота и попробовать снова!', reply_markup=global_menu)
    return
  await message.answer(f'Фотография успешно опубликована!')
  await message.answer(f'Код для удаления:')
  await message.answer(f'{uid}', reply_markup=global_menu)

@dp.message_handler(state=Deletion.id, content_types=['text'])
async def delete_photo(message: types.Message, state: FSMContext):
  uid = int(message.text)
  try:
    id = int(redis.get(uid))
    logging.info(id)
  except:
    await message.answer(f'Не удалось найти фотографию с соответсвующим кодом!', reply_markup=global_menu)
    await state.finish()
    return
  try:
    res = await bot.delete_message(chat_id=CHANNEL_ID, message_id=id)
    redis.delete(uid)
    await message.answer(f'Фотография успешно удалена', reply_markup=global_menu)
    await state.finish()
  except:
    await message.answer(f'Не удалось удалить фотографию!', reply_markup=global_menu)
    await state.finish()

@dp.message_handler(state=Photo.id, content_types=['photo'])
async def handle_photo(message: types.Message, state: FSMContext):
  photo_id=message.photo[-1].file_id
  caption=message.caption
  if (caption != None):
    await post_photo(message, photo_id, caption)
    await state.finish()
  else:
    async with state.proxy() as data:
      data['id'] = photo_id
    await Photo.next()
    await message.reply("Добавьте описание:", reply_markup=cancel_menu)

@dp.message_handler(state=Photo.caption)
async def handle_caption(message: types.Message, state: FSMContext):
  caption = message.text
  async with state.proxy() as data:
    data['caption'] = caption
    await post_photo(message=message, photo_id=data['id'], caption=data['caption'])
  await state.finish() 

@dp.message_handler(content_types=['audio', 'document', 'game', 'sticker', 'video', 'video_note', 'voice', 'contact', 'location', 'venue', 'poll', 'dice'], state='*')
async def catch_wrong_files(message: types.Message, state: FSMContext):
  await state.finish() 
  await message.answer(f'Данный тип файла недоступен для публикации!\nДля публикации фотографии воспользуйтесь меню.', reply_markup=global_menu)

@dp.message_handler(content_types=['photo'])
async def handle_single_photo(message: types.Message):
  await message.reply(f'Для публикации фотографии воспользуйтесь меню.', reply_markup=global_menu)

if __name__ == '__main__':
  executor.start_polling(dp, skip_updates=True)
