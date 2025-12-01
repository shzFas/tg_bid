from aiogram import Bot
import os

def get_bot_by_sender(sender: str) -> Bot:
    """
    sender = 'request' или 'spec'
    """
    if sender == 'spec':
        return Bot(token=os.getenv("SPEC_BOT_TOKEN"))
    return Bot(token=os.getenv("REQUEST_BOT_TOKEN"))
