#!/usr/bin/env python3
"""
TITAN BOT V3 — PART 2: MANAGERS (Roast, Attack, Voice) [ULTIMATE EDITION]
"""

import json
import random
import asyncio
import time
import os
import hashlib
import logging
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from config import Config
from database import db

logger = logging.getLogger(__name__)

# ==========================================
# 0. ENUMS & DATA CLASSES (Type Safety)
# ==========================================

class AttackMode(Enum):
    NORMAL = "normal"
    BURST = "burst"
    ZERO_DELAY = "zero_delay"
    HYPERBURST = "hyperburst"
    ULTRABURST = "ultraburst"
    SMART = "smart"
    ADAPTIVE = "adaptive"
    RANDOM = "random"
    
    @classmethod
    def list_modes(cls) -> List[str]:
        return [mode.value for mode in cls]

@dataclass
class AttackSession:
    """Attack session data container"""
    chat_id: int
    target: str
    mode: AttackMode = AttackMode.NORMAL
    speed: float = 0.3
    roasts_sent: int = 0
    start_time: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    consecutive_errors: int = 0
    is_active: bool = True

# ==========================================
# 1. ROAST MANAGER (Enhanced)
# ==========================================

DEFAULT_ROASTS = [
    "မင်းက ခွေးကောင်ကြီးပဲ",
    "ဘာလဲဟဲ့ လူပျက်ကြီး",
    "စောက်ရူးသား",
    "မအေလိုးမသား",
    "ဖာသည်မသား",
    "ရိုက်ထားမနားနဲ့",
    "မင်းအမေလိုးပြီ",
    "ဟေ့ကုလား၀က်သားစားပြ",
    "ဆင်းရဲသား",
    "တဲအိမ်နဲ့ဆို",
    "ဖာသယ်မလား",
    "လိုးပေးမယ်",
    "ခုန်ကိုက်တာလားဟ",
]

class RoastManager:
    def __init__(self):
        self._roasts: List[str] = []
        self._cache: List[str] = []
        self._last_reload: float = 0
        self._cache_ttl: int = 300  # 5 minutes
        self.load()
    
    def load(self) -> None:
        """Load roasts with caching"""
        try:
            if os.path.exists(Config.ROASTS_FILE):
                with open(Config.ROASTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._roasts = data
                    else:
                        self._roasts = DEFAULT_ROASTS.copy()
            else:
                self._roasts = DEFAULT_ROASTS.copy()
                self.save()
            self._update_cache()
        except Exception as e:
            logger.error(f"Roast load error: {e}")
            self._roasts = DEFAULT_ROASTS.copy()
    
    def _update_cache(self) -> None:
        """Update internal cache"""
        self._cache = self._roasts.copy()
        self._last_reload = time.time()
    
    def save(self) -> None:
        try:
            with open(Config.ROASTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._roasts, f, ensure_ascii=False, indent=2)
            self._update_cache()
        except Exception as e:
            logger.error(f"Roast save error: {e}")
    
    def get_random(self) -> str:
        """Get random roast with cache fallback"""
        if self._cache and (time.time() - self._last_reload) < self._cache_ttl:
            return random.choice(self._cache) if self._cache else "Get rekt!"
        self._update_cache()
        return random.choice(self._cache) if self._cache else "Get rekt!"
    
    def get_all(self) -> List[str]:
        return self._roasts.copy()
    
    def add(self, text: str) -> bool:
        if text and text not in self._roasts:
            self._roasts.append(text)
            self.save()
            return True
        return False
    
    def remove(self, index: int) -> Optional[str]:
        if 0 <= index < len(self._roasts):
            removed = self._roasts.pop(index)
            self.save()
            return removed
        return None
    
    def count(self) -> int:
        return len(self._roasts)
    
    def get_random_multiple(self, count: int = 3) -> List[str]:
        """Get multiple random roasts"""
        if not self._cache:
            return ["Get rekt!"]
        return random.sample(self._cache, min(count, len(self._cache)))

roast_manager = RoastManager()

# ==========================================
# 2. ATTACK MANAGER (FULLY ENHANCED)
# ==========================================

class AttackManager:
    def __init__(self):
        self._sessions: Dict[int, AttackSession] = {}
        self._tasks: Dict[int, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._stats = {
            "total_attacks": 0,
            "total_roasts_sent": 0,
            "active_attacks": 0
        }
    
    def get_session(self, chat_id: int) -> Optional[AttackSession]:
        return self._sessions.get(chat_id)
    
    def is_active(self, chat_id: int) -> bool:
        return chat_id in self._tasks and not self._tasks[chat_id].done()
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "active_attacks": len(self._tasks),
            "sessions": len(self._sessions)
        }
    
    async def start(
        self, 
        context, 
        chat_id: int, 
        target: str, 
        mode: str = "normal",
        speed: float = 0.3,
        on_message_sent: Optional[Callable] = None
    ) -> bool:
        """Start attack with enhanced control"""
        async with self._lock:
            # Stop existing if any
            if self.is_active(chat_id):
                await self.stop(chat_id)
            
            # Create session
            session = AttackSession(
                chat_id=chat_id,
                target=target,
                mode=AttackMode(mode) if mode in AttackMode.list_modes() else AttackMode.NORMAL,
                speed=max(0.01, min(2.0, speed))
            )
            self._sessions[chat_id] = session
            self._stats["total_attacks"] += 1
        
        async def attack_loop():
            try:
                while session.is_active:
                    try:
                        current_mode = session.mode
                        roasts = roast_manager.get_random_multiple(1)
                        roast = roasts[0] if roasts else "Get rekt!"
                        
                        # Mode-specific behavior
                        if current_mode == AttackMode.BURST:
                            for _ in range(10):
                                await context.bot.send_message(
                                    chat_id=chat_id, 
                                    text=f"{target} {roast_manager.get_random()}"
                                )
                                session.roasts_sent += 1
                                await asyncio.sleep(0.1)
                            await asyncio.sleep(1.0)
                        
                        elif current_mode == AttackMode.ZERO_DELAY:
                            await context.bot.send_message(
                                chat_id=chat_id, 
                                text=f"{target} {roast}"
                            )
                            session.roasts_sent += 1
                            await asyncio.sleep(0.01)
                        
                        elif current_mode == AttackMode.HYPERBURST:
                            for _ in range(25):
                                await context.bot.send_message(
                                    chat_id=chat_id, 
                                    text=f"{target} {roast_manager.get_random()}"
                                )
                                session.roasts_sent += 1
                                await asyncio.sleep(0.08)
                            await asyncio.sleep(3.0)
                        
                        elif current_mode == AttackMode.ULTRABURST:
                            for _ in range(15):
                                await context.bot.send_message(
                                    chat_id=chat_id, 
                                    text=f"{target} {roast_manager.get_random()}"
                                )
                                session.roasts_sent += 1
                                await asyncio.sleep(0.06)
                            await asyncio.sleep(2.0)
                        
                        elif current_mode == AttackMode.SMART:
                            current_speed = max(0.05, session.speed * 0.8) if session.roasts_sent > 20 else max(0.1, session.speed * 0.9) if session.roasts_sent > 10 else session.speed
                            await context.bot.send_message(
                                chat_id=chat_id, 
                                text=f"{target} {roast}"
                            )
                            session.roasts_sent += 1
                            await asyncio.sleep(current_speed)
                        
                        elif current_mode == AttackMode.ADAPTIVE:
                            if session.roasts_sent > 30:
                                current_speed = max(0.05, session.speed * 0.7)
                            elif session.roasts_sent > 20:
                                current_speed = max(0.1, session.speed * 0.85)
                            elif session.roasts_sent > 10:
                                current_speed = max(0.2, session.speed * 0.95)
                            else:
                                current_speed = session.speed
                            await context.bot.send_message(
                                chat_id=chat_id, 
                                text=f"{target} {roast}"
                            )
                            session.roasts_sent += 1
                            await asyncio.sleep(current_speed)
                        
                        elif current_mode == AttackMode.RANDOM:
                            await context.bot.send_message(
                                chat_id=chat_id, 
                                text=f"{target} {roast}"
                            )
                            session.roasts_sent += 1
                            await asyncio.sleep(random.uniform(0.05, 1.0))
                        
                        else:  # NORMAL & fallback
                            await context.bot.send_message(
                                chat_id=chat_id, 
                                text=f"{target} {roast}"
                            )
                            session.roasts_sent += 1
                            await asyncio.sleep(session.speed)
                        
                        session.last_active = time.time()
                        session.consecutive_errors = 0
                        
                        if on_message_sent:
                            await on_message_sent(session)
                        
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        session.consecutive_errors += 1
                        logger.error(f"Attack error in {chat_id}: {e}")
                        if session.consecutive_errors >= 5:
                            logger.warning(f"Stopping attack in {chat_id} due to too many errors")
                            break
                        await asyncio.sleep(2)
            
            except asyncio.CancelledError:
                pass
            finally:
                # Cleanup
                duration = time.time() - session.start_time
                await asyncio.to_thread(
                    db.log_attack,
                    chat_id, target, 0, session.roasts_sent, 
                    duration, session.speed, session.mode.value
                )
                self._stats["total_roasts_sent"] += session.roasts_sent
                self._sessions.pop(chat_id, None)
                self._tasks.pop(chat_id, None)
                self._stats["active_attacks"] = len(self._tasks)
        
        task = asyncio.create_task(attack_loop())
        self._tasks[chat_id] = task
        self._stats["active_attacks"] = len(self._tasks)
        return True
    
    async def stop(self, chat_id: int) -> bool:
        if self.is_active(chat_id):
            self._tasks[chat_id].cancel()
            if chat_id in self._sessions:
                self._sessions[chat_id].is_active = False
            return True
        return False
    
    async def stop_all(self) -> int:
        """Stop all active attacks"""
        count = 0
        for chat_id in list(self._tasks.keys()):
            if await self.stop(chat_id):
                count += 1
        return count
    
    def set_speed(self, chat_id: int, speed: float) -> bool:
        session = self.get_session(chat_id)
        if session:
            session.speed = max(0.01, min(2.0, speed))
            return True
        return False
    
    def set_mode(self, chat_id: int, mode: str) -> bool:
        if mode in AttackMode.list_modes():
            session = self.get_session(chat_id)
            if session:
                session.mode = AttackMode(mode)
                return True
        return False
    
    def get_active_chats(self) -> List[int]:
        return list(self._tasks.keys())

attack_manager = AttackManager()

# ==========================================
# 3. VOICE MANAGER (Enhanced)
# ==========================================

class VoiceManager:
    def __init__(self):
        self.voice_dir = os.path.join(Config.DATA_DIR, "voices")
        os.makedirs(self.voice_dir, exist_ok=True)
        self._cache: Dict[str, str] = {}
        self._max_cache_size = 100
    
    def get_voice_file(self, roast_text: str) -> str:
        text_hash = hashlib.md5(roast_text.encode("utf-8")).hexdigest()
        return os.path.join(self.voice_dir, f"{text_hash}.mp3")
    
    def voice_exists(self, roast_text: str) -> bool:
        return os.path.exists(self.get_voice_file(roast_text))
    
    def save_voice(self, roast_text: str, audio_data: bytes) -> str:
        voice_file = self.get_voice_file(roast_text)
        try:
            with open(voice_file, "wb") as f:
                f.write(audio_data)
            self._cache[roast_text] = voice_file
            if len(self._cache) > self._max_cache_size:
                # Remove oldest entries
                keys = list(self._cache.keys())
                for key in keys[:20]:
                    self._cache.pop(key, None)
        except Exception as e:
            logger.error(f"Failed to save voice file: {e}")
        return voice_file
    
    def get_random_voice(self) -> Optional[str]:
        try:
            files = [f for f in os.listdir(self.voice_dir) if f.endswith(".mp3")]
            if files:
                return os.path.join(self.voice_dir, random.choice(files))
        except Exception as e:
            logger.error(f"Error reading voices dir: {e}")
        return None
    
    def get_voice_count(self) -> int:
        try:
            return len([f for f in os.listdir(self.voice_dir) if f.endswith(".mp3")])
        except:
            return 0
    
    def clear_voices(self) -> int:
        """Clear all voice files and return count removed"""
        count = 0
        try:
            for f in os.listdir(self.voice_dir):
                if f.endswith(".mp3"):
                    os.remove(os.path.join(self.voice_dir, f))
                    count += 1
            self._cache.clear()
        except Exception as e:
            logger.error(f"Failed to clear voices: {e}")
        return count

voice_manager = VoiceManager()

print("Part 2 (ULTIMATE EDITION) Loaded Successfully!")
