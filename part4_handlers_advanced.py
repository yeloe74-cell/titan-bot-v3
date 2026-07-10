#!/usr/bin/env python3
"""
TITAN BOT V3 — PART 4: ADVANCED HANDLERS
Enterprise Developer Edition

This module contains advanced command handlers for:
- Admin Management
- Blacklist / Whitelist
- Ghost / Troll Mode
- Broadcast System

Style: Clean Code | Strict Type Hints | Professional Logging
"""

import asyncio
import logging
from functools import wraps
from typing import Optional, List, Dict, Any, Callable, Awaitable

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode

from config import Config
from database import db
from auth import Auth
from data_manager import DataManager

logger = logging.getLogger(__name__)

# ==========================================
# 0. TYPE DEFINITIONS
# ==========================================

HandlerFunc = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]

# ==========================================
# 1. CUSTOM DECORATORS
# ==========================================

def owner_only(func: HandlerFunc) -> HandlerFunc:
    """Restrict command access to bot owner only."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not Auth.is_owner(user_id):
            await update.message.reply_text("Error: Access denied. Owner privileges required.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def admin_only(func: HandlerFunc) -> HandlerFunc:
    """Restrict command access to bot admins only."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not Auth.is_admin(user_id):
            await update.message.reply_text("Error: Access denied. Administrator privileges required.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def log_command(func: HandlerFunc) -> HandlerFunc:
    """Log command usage for system auditing."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        command = update.message.text.split()[0] if update.message and update.message.text else "unknown_command"
        logger.info(f"Execution Audit: {command} invoked by UID:{user.id} (@{user.username or 'NoUser'})")
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

async def resolve_user_id(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    target: str
) -> Optional[int]:
    """
    Resolve user ID from username or ID string safely.
    """
    # If the target is just numbers (an ID)
    if target.lstrip("-").isdigit():
        return int(target)
    
    # If the target is a username (Requires custom DB implementation)
    if target.startswith("@"):
        username = target[1:]
        try:
            user_data = await asyncio.to_thread(db.get_user_by_username, username)
            if user_data and 'id' in user_data:
                return int(user_data['id'])
            else:
                await update.message.reply_text(f"Error: Could not locate user `@{username}` in the database.", parse_mode=ParseMode.MARKDOWN)
        except AttributeError:
            logger.warning("System Warning: db.get_user_by_username method is missing.")
        except Exception as e:
            logger.error(f"Resolution Error (Username): {e}")
            
    return None

async def resolve_target(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE
) -> Optional[int]:
    """Resolve target user ID from reply or command argument."""
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    
    if context.args:
        return await resolve_user_id(update, context, context.args[0])
    
    return None

def format_user_mention(user_id: int, name: str = None) -> str:
    """Format a user mention for Telegram."""
    display_name = name or f"User{user_id}"
    return f"[{display_name}](tg://user?id={user_id})"

# ==========================================
# 3. ADMIN MANAGEMENT
# ==========================================

@log_command
@owner_only
async def adm_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Promote a user to system administrator."""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/adm [user_id or @username]`\n"
            "Example: `/adm 123456789`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    target = context.args[0]
    target_id = await resolve_user_id(update, context, target)
    
    if not target_id: return
    
    if target_id == Config.OWNER_ID:
        await update.message.reply_text("Info: Target is the system owner and already possesses admin rights.")
        return
    
    if target_id in Config.get_admins():
        await update.message.reply_text("Info: Target is already configured as an administrator.")
        return
    
    if Config.save_admin(target_id, add=True):
        await update.message.reply_text(f"Success: Administrator privileges granted to `{target}`.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("Error: Failed to update administrator configuration. See system logs.")

@log_command
@owner_only
async def disadm_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Revoke a user's administrator privileges."""
    if not context.args:
        await update.message.reply_text("Usage: `/disadm [user_id or @username]`", parse_mode=ParseMode.MARKDOWN)
        return
    
    target = context.args[0]
    target_id = await resolve_user_id(update, context, target)
    
    if not target_id: return
    
    if target_id == Config.OWNER_ID:
        await update.message.reply_text("Error: Cannot revoke privileges from the system owner.")
        return
    
    if target_id not in Config.get_admins():
        await update.message.reply_text("Info: Target does not have administrator privileges.")
        return
    
    if Config.save_admin(target_id, add=False):
        await update.message.reply_text(f"Success: Administrator privileges revoked from `{target}`.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("Error: Failed to update administrator configuration. See system logs.")

@log_command
@admin_only
async def admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retrieve the list of current administrators."""
    admins = Config.get_admins()
    if not admins:
        await update.message.reply_text("Info: No administrators currently registered in the system.")
        return
    
    admin_list = []
    for aid in admins:
        try:
            chat = await context.bot.get_chat(aid)
            name = chat.first_name or f"User_{aid}"
            admin_list.append(f"  • {name} (`{aid}`)")
        except Exception:
            admin_list.append(f"  • UID: `{aid}`")
    
    await update.message.reply_text(f"**SYSTEM ADMINISTRATORS:**\n{chr(10).join(admin_list)}", parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 4. BLACKLIST & WHITELIST
# ==========================================

@log_command
@owner_only
async def blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a user to the restricted access list."""
    if not context.args:
        await update.message.reply_text("Usage: `/blacklist [user_id or @username] [reason]`", parse_mode=ParseMode.MARKDOWN)
        return
    
    target = context.args[0]
    target_id = await resolve_user_id(update, context, target)
    if not target_id: return
    
    if Auth.is_blacklisted(target_id):
        await update.message.reply_text("Info: Target is already on the restricted list.")
        return
    
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Administrative restriction"
    await asyncio.to_thread(db.add_blacklist, target_id, reason, update.effective_user.id)
    await update.message.reply_text(f"Action: User `{target}` has been restricted.\nReason: {reason}", parse_mode=ParseMode.MARKDOWN)

@log_command
@owner_only
async def unblacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a user from the restricted access list."""
    if not context.args:
        await update.message.reply_text("Usage: `/unblacklist [user_id or @username]`", parse_mode=ParseMode.MARKDOWN)
        return
    
    target = context.args[0]
    target_id = await resolve_user_id(update, context, target)
    if not target_id: return
    
    if not Auth.is_blacklisted(target_id):
        await update.message.reply_text("Info: Target is not currently restricted.")
        return
    
    await asyncio.to_thread(db.remove_blacklist, target_id)
    await update.message.reply_text(f"Success: Target removed from the restricted list: `{target}`", parse_mode=ParseMode.MARKDOWN)

@log_command
@admin_only
async def blacklist_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retrieve the list of restricted users."""
    blacklist = await asyncio.to_thread(db.get_blacklist)
    if not blacklist:
        await update.message.reply_text("Info: The restricted list is currently empty.")
        return
    
    text = "**RESTRICTED USERS (BLACKLIST):**\n\n"
    for entry in blacklist:
        text += f"  • UID: `{entry['id']}`\n    Reason: {entry['reason']}\n\n"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@log_command
@owner_only
async def whitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a user to the trusted access list."""
    if not context.args:
        await update.message.reply_text("Usage: `/whitelist [user_id or @username]`", parse_mode=ParseMode.MARKDOWN)
        return
    
    target = context.args[0]
    target_id = await resolve_user_id(update, context, target)
    if not target_id: return
    
    if Auth.is_whitelisted(target_id):
        await update.message.reply_text("Info: Target is already on the trusted list.")
        return
    
    await asyncio.to_thread(db.add_whitelist, target_id, update.effective_user.id)
    await update.message.reply_text(f"Success: Target added to the trusted list: `{target}`", parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 5. GHOST & TROLL SYSTEMS
# ==========================================

@log_command
@admin_only
async def ghost_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Activate ghost mode operations for a target."""
    chat_id = update.effective_chat.id
    target_id = await resolve_target(update, context)
    
    if not target_id:
        await update.message.reply_text("Usage: `/ghost [user_id or @username]` or reply to target.", parse_mode=ParseMode.MARKDOWN)
        return
    
    if await asyncio.to_thread(db.is_ghosted, chat_id, target_id):
        await update.message.reply_text("Info: Ghost mode is already active for this target.")
        return
    
    await asyncio.to_thread(db.add_ghost, chat_id, target_id, update.effective_user.id)
    await update.message.reply_text("Status: Ghost mode activated.")

@log_command
@admin_only
async def unghost_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deactivate ghost mode operations for a target."""
    chat_id = update.effective_chat.id
    target_id = await resolve_target(update, context)
    
    if not target_id:
        await update.message.reply_text("Usage: `/unghost [user_id or @username]` or reply to target.", parse_mode=ParseMode.MARKDOWN)
        return
    
    if not await asyncio.to_thread(db.is_ghosted, chat_id, target_id):
        await update.message.reply_text("Info: Ghost mode is not currently active for this target.")
        return
    
    await asyncio.to_thread(db.remove_ghost, chat_id, target_id)
    await update.message.reply_text("Status: Ghost mode deactivated.")

@log_command
@admin_only
async def troll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Activate troll mode operations for a target."""
    chat_id = update.effective_chat.id
    target_id = await resolve_target(update, context)
    
    if not target_id:
        await update.message.reply_text("Usage: `/troll [user_id or @username]` or reply to target.", parse_mode=ParseMode.MARKDOWN)
        return
    
    if await asyncio.to_thread(db.is_trolled, chat_id, target_id):
        await update.message.reply_text("Info: Troll mode is already active for this target.")
        return
    
    await asyncio.to_thread(db.add_troll, chat_id, target_id, update.effective_user.id)
    await update.message.reply_text("Status: Troll mode activated.")

@log_command
@admin_only
async def untroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deactivate troll mode operations for a target."""
    chat_id = update.effective_chat.id
    target_id = await resolve_target(update, context)
    
    if not target_id:
        await update.message.reply_text("Usage: `/untroll [user_id or @username]` or reply to target.", parse_mode=ParseMode.MARKDOWN)
        return
    
    if not await asyncio.to_thread(db.is_trolled, chat_id, target_id):
        await update.message.reply_text("Info: Troll mode is not currently active for this target.")
        return
    
    await asyncio.to_thread(db.remove_troll, chat_id, target_id)
    await update.message.reply_text("Status: Troll mode deactivated.")

# ==========================================
# 6. BROADCAST SYSTEM
# ==========================================

@log_command
@owner_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute a system-wide message broadcast."""
    if not update.message.reply_to_message and not context.args:
        await update.message.reply_text(
            "Usage: `/broadcast [message]`\n"
            "Or reply to a message with `/broadcast`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    message = None
    if update.message.reply_to_message:
        if update.message.reply_to_message.text:
            message = update.message.reply_to_message.text
        else:
            await update.message.reply_text("Error: Invalid operation. Reply to a valid text message.")
            return
    else:
        message = " ".join(context.args)
    
    if not message:
        await update.message.reply_text("Error: Broadcast payload is empty.")
        return
    
    try:
        rows = await asyncio.to_thread(
            db.execute,
            "SELECT DISTINCT chat_id FROM attack_history",
            fetchall=True
        )
    except Exception as e:
        logger.error(f"Database Query Error (Broadcast): {e}")
        await update.message.reply_text("Error: Database transaction failed during broadcast initialization.")
        return
    
    if not rows:
        await update.message.reply_text("Info: No eligible chat records found for broadcasting.")
        return
    
    chat_ids = [row['chat_id'] for row in rows]
    total_chats = len(chat_ids)
    
    progress_msg = await update.message.reply_text(f"Processing: Initializing broadcast to `{total_chats}` chats...", parse_mode=ParseMode.MARKDOWN)
    
    sent_count = 0
    failed_count = 0
    
    for chat_id in chat_ids:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            sent_count += 1
            await asyncio.sleep(0.1)  # FloodWait mitigation
        except Exception as e:
            logger.debug(f"Broadcast dispatch failed for chat {chat_id}: {e}")
            failed_count += 1
        
        # Telemetry update
        if (sent_count + failed_count) % 50 == 0:
            await progress_msg.edit_text(
                f"**Processing Broadcast...**\n"
                f"Progress: `{sent_count + failed_count}/{total_chats}`\n"
                f"Success: `{sent_count}` | Failed: `{failed_count}`",
                parse_mode=ParseMode.MARKDOWN
            )
    
    await progress_msg.edit_text(
        f"**BROADCAST OPERATION COMPLETE:**\n"
        f"Success: `{sent_count}`\n"
        f"Failed: `{failed_count}`\n"
        f"Total Processed: `{total_chats}`",
        parse_mode=ParseMode.MARKDOWN
    )

@log_command
@owner_only
async def broadcast_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retrieve telemetry for potential broadcast targets."""
    try:
        row = await asyncio.to_thread(
            db.execute,
            "SELECT COUNT(DISTINCT chat_id) as count FROM attack_history",
            fetchone=True
        )
        total_chats = row['count'] if row else 0
        await update.message.reply_text(f"Statistics: Total eligible chats for broadcast: `{total_chats}`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Telemetry Fetch Error: {e}")
        await update.message.reply_text("Error: Failed to retrieve broadcast telemetry.")

# ==========================================
# 7. REGISTRATION
# ==========================================

def register_handlers(app) -> None:
    """Register all advanced handlers to the main application core."""
    # Admin System
    app.add_handler(CommandHandler("adm", adm_command))
    app.add_handler(CommandHandler("disadm", disadm_command))
    app.add_handler(CommandHandler("admins", admins_command))
    
    # Access Control List (ACL)
    app.add_handler(CommandHandler("blacklist", blacklist_command))
    app.add_handler(CommandHandler("unblacklist", unblacklist_command))
    app.add_handler(CommandHandler("blacklistlist", blacklist_list_command))
    app.add_handler(CommandHandler("whitelist", whitelist_command))
    
    # Interference Modules
    app.add_handler(CommandHandler("ghost", ghost_command))
    app.add_handler(CommandHandler("unghost", unghost_command))
    app.add_handler(CommandHandler("troll", troll_command))
    app.add_handler(CommandHandler("untroll", untroll_command))
    
    # Communications
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("broadcaststats", broadcast_stats_command))
    
    logger.info("System Initialization: Advanced handlers registered successfully.")

if __name__ == "__main__":
    print("Module Loaded: Part 4 (Enterprise Developer Edition).")

