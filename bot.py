from config import set_server, bot

set_server()

from commands import *

bot.infinity_polling()