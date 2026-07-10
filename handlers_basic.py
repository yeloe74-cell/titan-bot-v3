#!/usr/bin/env python3
"""
TITAN BOT V3 — PART 3: BASIC HANDLERS (DEVELOPER EDITION)
Clean Code | No Emoji | Production Ready
"""

import time
import asyncio
import logging
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import Config
from database import db
from auth import Auth
from roast_manager import roast_manager
from attack_manager import attack_manager, AttackMode

logger = logging.getLogger(__name__)

# ==========================================
# 1. BASIC COMMANDS
# ==========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await asyncio.to_thread(db.add_user, user.id, user.username, user.first_name)
    
    help_text = (
        "TITAN BOT V3 — ULTIMATE EDITION\n"
        "===============================\n\n"
        "COMMANDS:\n"
        "/help — Show all commands\n"
        "/attack [target] — Start attack\n"
        "/stop — Stop attack\n"
        "/speed [value] — Set speed\n"
        "/roast [target] — Roast user\n"
        "/roast list — List roasts\n"
        "/roast add [text] — Add roast\n"
        "/roast remove [n] — Remove roast\n"
        "/stats — Bot statistics\n"
        "/ping — Check bot speed\n"
        "/about — About this bot"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    message = await update.message.reply_text("Pong!")
    elapsed = (time.time() - start_time) * 1000
    await message.edit_text(f"Pong! {elapsed:.2f}ms", parse_mode=ParseMode.MARKDOWN)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = await asyncio.to_thread(db.get_total_users)
    admin_list = Config.get_admins()
    
    await update.message.reply_text(
        f"TITAN BOT V3\n"
        f"Version: {Config.VERSION}\n"
        f"Users: {total_users}\n"
        f"Roasts: {roast_manager.count()}\n"
        f"Admins: {len(admin_list)}",
        parse_mode=ParseMode.MARKDOWN
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not Auth.is_admin(user_id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    
    attack_stats = await asyncio.to_thread(db.get_attack_stats)
    total_users = await asyncio.to_thread(db.get_total_users)
    active_users = await asyncio.to_thread(db.get_active_users, 24)
    admin_list = Config.get_admins()
    
    total_attacks = attack_stats.get('total_attacks', 0) if attack_stats else 0
    total_roasts = attack_stats.get('total_roasts', 0) if attack_stats else 0
    
    await update.message.reply_text(
        f"BOT STATISTICS\n"
        f"==============\n\n"
        f"USERS:\n"
        f"  Total: {total_users}\n"
        f"  Active (24h): {active_users}\n\n"
        f"ATTACKS:\n"
        f"  Total: {total_attacks}\n"
        f"  Roasts Sent: {total_roasts}\n\n"
        f"ADMINS: {len(admin_list)}",
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================================
# 2. ATTACK COMMANDS
# ==========================================

async def attack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not Auth.is_admin(user_id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    
    chat_id = update.effective_chat.id
    target = None
    target_id = None
    mode = "normal"
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target = target_user.username or target_user.first_name
        target_id = target_user.id
        if context.args:
            mode = context.args[0].lower()
    elif context.args:
        target = context.args[0]
        if len(context.args) > 1:
            mode = context.args[1].lower()
    
    if not target:
        await update.message.reply_text("Error: Target not found.")
        return
    
    mode_map = {
        "zero": "zero_delay",
        "hyper": "hyperburst",
        "ultra": "ultraburst"
    }
    mode = mode_map.get(mode, mode)
    
    if mode not in AttackMode.list_modes():
        mode = "normal"
    
    await attack_manager.start(
        context=context,
        chat_id=chat_id,
        target=target,
        mode=mode
    )
    
    session = attack_manager.get_session(chat_id)
    speed = session.speed if session else 0.3
    
    await update.message.reply_text(
        f"Attack started on {target}\n"
        f"Mode: {mode}\n"
        f"Speed: {speed}s\n"
        f"Stop: /stop",
        parse_mode=ParseMode.MARKDOWN
    )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not Auth.is_admin(user_id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    
    chat_id = update.effective_chat.id
    if await attack_manager.stop(chat_id):
        await update.message.reply_text("Attack stopped.")
    else:
        await update.message.reply_text("No active attack in this chat.")

async def speed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not Auth.is_admin(user_id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /speed [value]")
        return
    
    try:
        speed = float(context.args[0])
        chat_id = update.effective_chat.id
        
        if attack_manager.set_speed(chat_id, speed):
            await update.message.reply_text(f"Speed set to {speed}s")
        else:
            await update.message.reply_text("Start an attack first before setting speed.")
    except ValueError:
        await update.message.reply_text("Invalid speed. Please use a number (e.g., 0.5).")

async def attack_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not Auth.is_admin(user_id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    
    chat_id = update.effective_chat.id
    session = attack_manager.get_session(chat_id)
    
    if not session:
        await update.message.reply_text("No active attack in this chat.")
        return
    
    await update.message.reply_text(
        f"ATTACK STATUS\n"
        f"=============\n"
        f"Target: {session.target}\n"
        f"Mode: {session.mode.value}\n"
        f"Speed: {session.speed}s\n"
        f"Roasts Sent: {session.roasts_sent}\n"
        f"Active: {session.is_active}\n"
        f"Duration: {int(time.time() - session.start_time)}s",
        parse_mode=ParseMode.MARKDOWN
    )

async def attack_modes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not Auth.is_admin(user_id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    
    modes = AttackMode.list_modes()
    text = "AVAILABLE ATTACK MODES:\n\n"
    for mode in modes:
        text += f"  - {mode}\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 3. ROAST COMMANDS
# ==========================================

async def roast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not Auth.is_admin(user_id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text(
            "Usage:\n"
            "/roast [target]\n"
            "/roast list\n"
            "/roast add [text]\n"
            "/roast remove [number]"
        )
        return
    
    # Roast list
    if context.args and context.args[0].lower() == "list":
        roasts = roast_manager.get_all()
        if not roasts:
            await update.message.reply_text("No roasts configured.")
            return
        
        text = "ROAST LIST:\n\n"
        for i, roast in enumerate(roasts, 1):
            text += f"{i}. {roast}\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Roast add
    if context.args and context.args[0].lower() == "add":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /roast add [text]")
            return
        
        new_roast = " ".join(context.args[1:])
        if roast_manager.add(new_roast):
            await update.message.reply_text(f"Added: {new_roast}")
        else:
            await update.message.reply_text("Already exists or invalid text.")
        return
    
    # Roast remove
    if context.args and context.args[0].lower() == "remove":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /roast remove [number]")
            return
        
        try:
            index = int(context.args[1]) - 1
            removed = roast_manager.remove(index)
            if removed:
                await update.message.reply_text(f"Removed: {removed}")
            else:
                await update.message.reply_text("Invalid number.")
        except ValueError:
            await update.message.reply_text("Please provide a valid number.")
        return
    
    # Roast target
    target = "User"
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target = target_user.username or target_user.first_name
        if context.args:
            target += " " + " ".join(context.args)
    elif context.args:
        target = " ".join(context.args)
    
    roast_text = roast_manager.get_random()
    
    try:
        await asyncio.to_thread(
            db._execute,
            "INSERT INTO roast_history (user_id, target, roast) VALUES (?, ?, ?)",
            (user_id, target, roast_text)
        )
    except Exception as e:
        logger.warning(f"Could not log roast: {e}")
    
    await update.message.reply_text(f"{target}\n\n{roast_text}")

async def roast_count_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not Auth.is_admin(user_id):
        await update.message.reply_text("Access denied. Admin only.")
        return
    
    count = roast_manager.count()
    await update.message.reply_text(f"Total roasts: {count}", parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 4. REGISTER HANDLERS
# ==========================================

def register_handlers(app):
    """Register all command handlers"""
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    app.add_handler(CommandHandler("attack", attack_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("speed", speed_command))
    app.add_handler(CommandHandler("attackstatus", attack_status_command))
    app.add_handler(CommandHandler("attackmodes", attack_modes_command))
    
    app.add_handler(CommandHandler("roast", roast_command))
    app.add_handler(CommandHandler("roastcount", roast_count_command))
    
    logger.info("All handlers registered successfully.")

print("Part 3 (Developer Edition) loaded successfully.")
