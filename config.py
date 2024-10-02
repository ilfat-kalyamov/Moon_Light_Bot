import os
import telebot
from telebot import apihelper
from dotenv import load_dotenv

load_dotenv(override=True)

bot_api = os.getenv("BOT_API")

admin_id = os.getenv("ADMIN_ID")

bot = telebot.TeleBot(bot_api)

def set_server():
    server_mode = os.getenv("SERVER_MODE")
    if server_mode == 'local':
        apihelper.API_URL = 'http://0.0.0.0:8081/bot{0}/{1}'
        apihelper.FILE_URL = 'http://0.0.0.0:8081'