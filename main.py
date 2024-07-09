import json
import os
import re
import shutil

import requests
import telebot
from bs4 import BeautifulSoup
from PIL import Image
from telebot.types import InputFile

bot = telebot.TeleBot(os.environ['BOT_API'])

def bot_edit_message(bot_message, text):
    bot_text = bot_message.text + '\n' + text
    return bot.edit_message_text(chat_id=bot_message.chat.id, message_id=bot_message.message_id, text=bot_text)

def bot_edit_numbers(bot_message, number):
    bot_text = bot_message.text
    old = str(number-1) + '/'
    new = str(number) + '/'
    bot_text = new.join(bot_text.rsplit(old, 1))
    return bot.edit_message_text(chat_id = bot_message.chat.id, message_id=bot_message.message_id, text=bot_text)

def parser(message, bot_message):
    url = message.text
    response = requests.get(url)

    if response.status_code == 200:
        new_text = bot_edit_message(bot_message, 'Получен ответ от сервера.')
    else:
        new_text = bot_edit_message(bot_message, f'ОШИБКА: Не удалось получить ответ от сервера: {response.status_code}')
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    scripts = soup.find_all('script')
    title = soup.title.string
    new_text = bot_edit_message(new_text, f'Тайтл: {title}')

    if len(scripts) < 14:
        new_text = bot_edit_message(new_text, f'ОШИБКА: Не найдено необходимое количество скриптов на сайте. Найдено скриптов: {len(scripts)}')
        return

    script_14 = scripts[13].string
    if not script_14:
        new_text = bot_edit_message(new_text, 'ОШИБКА: Скрипт 14 пуст или не содержит текста.')
        return

    chapter_pattern = re.search(r'const local_text_epi\s*=\s*\'(?:Vol\.\d+\s*)?Ch\.(\d+\.\d+|\d+)\';', script_14)
    if chapter_pattern:
        chapter = chapter_pattern.group(1)
    else:
        new_text = bot_edit_message(new_text, 'ОШИБКА: неизвестная глава.')
        return
    new_text = bot_edit_message(new_text, f'Номер главы: {chapter}')

    img_https_pattern = re.search(r'const imgHttps\s*=\s*(\[[^\]]*\])', script_14)
    if not img_https_pattern:
        new_text = bot_edit_message(new_text, 'ОШИБКА: Не удалось обнаружить массив изображений.')
        return
    img_https_array = json.loads(img_https_pattern.group(1))
    new_text = bot_edit_message(new_text, f'Найдено {len(img_https_array)} изображений.')
    return new_text, chapter, img_https_array

def dir_maker(chapter, bot_message):
    uniq_path = str(bot_message.chat.id)
    os.makedirs(uniq_path, exist_ok=True)
    parent_folder = os.path.join(uniq_path, f'Глава_{chapter}')
    new_text = bot_edit_message(bot_message, f'Создаю папку: Глава_{chapter}')
    webp_folder = os.path.join(parent_folder, 'webp')
    os.makedirs(webp_folder, exist_ok=True)
    new_text = bot_edit_message(new_text, f'Создаю папку для загрузки изображений: Глава_{chapter}/webp')
    return new_text, parent_folder, webp_folder

def download_images(img_urls, folder_name, bot_message):
    new_text = bot_edit_message(bot_message, f'Начинаю загрузку изображений: 0/{len(img_urls)}')
    for idx, img_url in enumerate(img_urls, 1):
        response = requests.get(img_url)
        if response.status_code == 200:
            img_filename = os.path.join(folder_name, f'{idx}.webp')
            with open(img_filename, 'wb') as img_file:
                img_file.write(response.content)
            new_text = bot_edit_numbers(new_text, idx)
        else:
            new_text = bot_edit_message(new_text, f'ОШИБКА: не удалось получить изображение из: {img_url}')
            return
    new_text = bot_edit_message(new_text, 'Все изображения загружены.')
    return new_text

def convert_webp_to_png(src_folder, dst_folder, bot_message, size):
    new_text = bot_edit_message(bot_message, f'Начинаю конвертацию изображений в png. 0/{size}')
    os.makedirs(dst_folder, exist_ok=True)
    n = 0
    for filename in os.listdir(src_folder):
        n += 1
        if filename.endswith(".webp"):
            webp_image = Image.open(os.path.join(src_folder, filename))
            png_image = webp_image.convert("RGBA")
            png_image.save(os.path.join(dst_folder, filename.replace(".webp", ".png")))
            new_text = bot_edit_numbers(new_text, n)
        else:
            new_text = bot_edit_message(new_text, f'ОШИБКА: не удалось конвертировать изображение {filename}')
    new_text = bot_edit_message(new_text, 'Все изображения конвертированы.')
    return new_text

def create_and_send_archive(user_id, chapter, bot_message):
    new_text = bot_edit_message(bot_message, 'Создаю архив.')
    uniq_path = str(bot_message.chat.id)
    os.makedirs(uniq_path, exist_ok=True)
    parent_folder = os.path.join(uniq_path, f'Глава_{chapter}')
    shutil.make_archive(parent_folder, format='zip', root_dir=parent_folder)
    new_text = bot_edit_message(new_text, 'Архив создан. Отправляю.')
    try:
        bot.send_document(chat_id=user_id, document=InputFile(f'{parent_folder}.zip'), reply_to_message_id=new_text.message_id)
    except Exception as e:
        new_text = bot_edit_message(new_text, f'ОШИБКА: Не удалось отправить файл из-за ошибки со стороны Телеграмм, попытайтесь снова: {e}')
    os.remove(f'{parent_folder}.zip')
    return new_text

def send_message_to_admin(message):
    output = f"Выполнено действие в чате: {message.from_user.id}\nОт пользователя: {message.from_user.username}\nСообщение: {message.text}"
    bot.send_message(os.environ['ADMIN_ID'], output)

@bot.message_handler(commands=['help', 'start'])
def start_command(message):
    bot.send_message(message.from_user.id, "Привет, я бот для скачивания глав манги в помощь команде Moon Light team. Отправь мне ссылку на главу и я отправлю тебе в ответ архив. Ссылка пока что работает только для сайта mto.to. Ссылка должна вести на главу в режиме All pages. То есть без части ссылки /1 на конце.\n\nПрошу любые сообщения с ошибками отправлять ему @for_what_or")

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    send_message_to_admin(message)
    bot_message = bot.send_message(message.from_user.id, 'Начинаю процесс.', reply_to_message_id=message.message_id)
    bot_message, ch, img_urls = parser(message, bot_message)
    bot_message, parent_folder, webp_folder = dir_maker(ch, bot_message)
    bot_message = download_images(img_urls, webp_folder, bot_message)
    bot_message = convert_webp_to_png(webp_folder, os.path.join(parent_folder, 'png'), bot_message, len(img_urls))
    shutil.rmtree(webp_folder)
    bot_message = create_and_send_archive(message.from_user.id, ch, bot_message)
    shutil.rmtree(str(bot_message.chat.id))
    bot_edit_message(bot_message, 'Готово.')
    return
bot.infinity_polling()