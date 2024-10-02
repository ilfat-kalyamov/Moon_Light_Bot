from config import set_server, bot

set_server()

import commands

def start_bot():
    bot.infinity_polling()