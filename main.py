#!/usr/bin/env python3
"""
TITAN BOT V3 — FINAL INTEGRATION (READY FOR GITHUB)
This module acts as the entry point for the entire bot system.
"""

import os
import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# --- CONFIG & IMPORTS (Fixed names) ---
from config import Config
from database import db
from auth import Auth
from roast_manager import roast_manager
from voice_manager import voice_manager

# Import from handlers_basic.py (Part 3)
from handlers_basic import (
    start_command, help_command, ping_command, 
    about_command, stats_command,
    attack_command, stop_command, speed_command,
    roast_command
)

# Import from part4_handlers_advanced.py (Part 4)
from part4_handlers_advanced import (
    adm_command, disadm_command, admins_command,
    blacklist_command, whitelist_command,
    ghost_command, unghost_command,
    troll_command, stoptroll_command,
    reply_command, unreply_command,
    broadcast_command
)

# Part 5 Extra Handlers (ဒီဖိုင်ထဲမှာတင် ရေးထားတဲ့ function တွေ)
# တကယ်လို့ Part 5 သီးသန့်ဖိုင်ရှိရင် ဒီနေရာကို အစားထိုးပါ
from part5_extra_handlers import (
    filter_command, removefilter_command, filterlist_command,
    welcome_command, welcomeoff_command, translate_command,
    voice_command, ai_command, message_handler, welcome_handler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_handlers(app):
    # Registering all modules
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("attack", attack_command))
    app.add_handler(CommandHandler("adm", adm_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("filter", filter_command))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler))
    
    logger.info("All handlers successfully integrated.")

def main():
    app = Application.builder().token(Config.TOKEN).build()
    register_handlers(app)
    logger.info("Titan Bot V3 started.")
    app.run_polling()

if __name__ == "__main__":
    main()
  
