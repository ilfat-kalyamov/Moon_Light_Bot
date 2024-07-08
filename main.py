import os
import telebot
import shutil
import requests
from bs4 import BeautifulSoup
import re
import json
from telebot.types import InputFile
from PIL import Image

bot = telebot.TeleBot(os.environ['BOT_API'])

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    output = "Выполнено действие с ботом в чате: " + str(message.from_user.id) + ' User: ' + str(message.from_user.username)
    bot.send_message(os.environ['ADMIN_ID'], output)

    if message.text == "/start":
        bot.send_message(message.from_user.id, "Привет, я бот для скачивания глав манги в помощь команде Moon Light team. Отправь мне ссылку на главу и я отправлю тебе в ответ архив. Ссылка пока что работает только для сайта mto.to. Ссылка должна вести на главу в режиме All pages. То есть без части ссылки /1 на конце")
    elif message.text == "/help":
        bot.send_message(message.from_user.id, "Напиши /start")
    else:

        url = message.text
        #url = full_url.rpartition('/')[0]
        print(url)
        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            scripts = soup.find_all('script')

            if len(scripts) >= 14:
                script_14 = scripts[13].string

                if script_14:
                    img_https_pattern = re.search(r'const imgHttps\s*=\s*(\[[^\]]*\])', script_14)

                    if img_https_pattern:
                        img_https_array_str = img_https_pattern.group(1)
                        img_https_array = json.loads(img_https_array_str)
                        output = str(len(img_https_array)) + ' images found. '
                        bot.send_message(message.from_user.id, output)
                        print(len(img_https_array), 'images found.')

                        chapter_pattern = re.search(r'const local_text_epi\s*=\s*\'Ch\.(\d+)\';', script_14)

                        if chapter_pattern:
                            chapter = chapter_pattern.group(1)
                            output = 'Chapter ' + chapter
                            bot.send_message(message.from_user.id, output)
                            print(f'chapter: {chapter}')

                        parent_folder = "Глава_" + chapter
                        folder_name = os.path.join(parent_folder, f'webp')
                        os.makedirs(folder_name, exist_ok=True)
                        output = 'Folder ' + folder_name + ' created successfully. Downloading pages...'
                        bot.send_message(message.from_user.id, output)
                        print(f'Folder "{folder_name}" created successfully')

                        for idx, img_url in enumerate(img_https_array, 1):
                            try:
                                img_response = requests.get(img_url)

                                if img_response.status_code == 200:
                                    img_filename = os.path.join(folder_name, f'{idx}.webp')

                                    # Save the image in PNG format
                                    with open(img_filename, 'wb') as img_file:
                                        img_file.write(img_response.content)
                                    #output = 'Saved ' + img_filename + '.'
                                    #bot.send_message(message.from_user.id, output)
                                    print(f'Saved {img_filename}')
                                else:
                                    output = 'Failed to retrieve image from ' + img_url + '.'
                                    bot.send_message(message.from_user.id, output)
                                    print(f'Failed to retrieve image from {img_url}')
                            except Exception as e:
                                output = 'Error downloading ' + img_url + '.'
                                bot.send_message(message.from_user.id, output)
                                print(f'Error downloading {img_url}: {e}')

                        png_dir = os.path.join(parent_folder, f'png')
                        os.makedirs(png_dir, exist_ok=True)

                        for filename in os.listdir(folder_name):
                            if filename.endswith(".webp"):
                                webp_image = Image.open(os.path.join(folder_name, filename))
                                png_image = webp_image.convert("RGBA")
                                png_image.save(os.path.join(png_dir, filename.replace(".webp", ".png")))
                                
                        print('All images saved to the folder.')
                        output = 'All images saved to the folder.'
                        bot.send_message(message.from_user.id, output)

                        shutil.rmtree(f'Глава_{chapter}/webp')

                        print('Converting started.')
                        output = 'Converting started.'
                        bot.send_message(message.from_user.id, output)
                        shutil.make_archive('Глава_' + chapter, format='zip', root_dir=parent_folder)
                        print('ZIP archive created.')
                        output = 'ZIP archive created. Sending...'
                        bot.send_message(message.from_user.id, output)

                        bot.send_document(message.from_user.id, InputFile(f'Глава_{chapter}.zip'))
                        os.remove(f'Глава_{chapter}.zip')
                        shutil.rmtree(f'Глава_{chapter}')

                    else:
                        output = 'No imgHttps array found in script 14.'
                        bot.send_message(message.from_user.id, output)
                        print('No imgHttps array found in script 14.')
                else:
                    output = 'Script 14 is empty or does not contain text.'
                    bot.send_message(message.from_user.id, output)
                    print('Script 14 is empty or does not contain text.')
            else:
                output = 'Less than 14 script tags found.'
                bot.send_message(message.from_user.id, output)
                #print('Less than 14 script tags found.')
        else:
            output = f'Failed to retrieve data: {response.status_code}'
            bot.send_message(message.from_user.id, output)
            print(f'Failed to retrieve data: {response.status_code}')

bot.infinity_polling()