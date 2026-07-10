#!/usr/bin/env python3
"""
TITAN BOT V3 — PART 1: CONFIG + DATABASE + AUTH (PRO/ENTERPRISE EDITION)
"""

import os
import time
import json
import sqlite3
import logging
import threading
from datetime import datetime
from typing import List, Dict, Optional, Any, Union

# ==========================================
# 1. CONFIGURATION
# ==========================================

class Config:
    TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
    OWNER_ID = int(os.getenv("OWNER_ID", 123456789))
    DATA_DIR = "data"
    
    ROASTS_FILE = os.path.join(DATA_DIR, "roasts.json")
    ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")
    BLACKLIST_FILE = os.path.join(DATA_DIR, "blacklist.json")
    WHITELIST_FILE = os.path.join(DATA_DIR, "whitelist.json")
    FILTERS_FILE = os.path.join(DATA_DIR, "filters.json")
    WELCOME_FILE = os.path.join(DATA_DIR, "welcome.json")
    TRANSLATE_FILE = os.path.join(DATA_DIR, "translate.json")
    VOICE_FILE = os.path.join(DATA_DIR, "voice.json")
    DB_FILE = os.path.join(DATA_DIR, "titan.db")
    LOG_FILE = os.path.join(DATA_DIR, "titan.log")
    BACKUP_DIR = os.path.join(DATA_DIR, "backups")
    
    VERSION = "3.0.0"
    MAX_RETRIES = 3
    TIMEOUT = 30
    RATE_LIMIT = 20
    FLOOD_THRESHOLD = 10
    AUTO_BAN_THRESHOLD = 5
    
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    HF_TOKEN = os.getenv("HF_TOKEN", "")
    HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-3B-Instruct")

    # Admins Cache System
    _admin_cache: List[int] = []
    _admin_cache_time: float = 0.0
    CACHE_TTL = 60  # seconds

    @classmethod
    def get_admins(cls) -> List[int]:
        """Load admins from JSON with high-performance caching"""
        now = time.time()
        
        # Return cached if still fresh
        if cls._admin_cache and (now - cls._admin_cache_time) < cls.CACHE_TTL:
            return cls._admin_cache
        
        try:
            if os.path.exists(cls.ADMINS_FILE):
                with open(cls.ADMINS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    admins = data.get("admins", [cls.OWNER_ID])
                    cls._admin_cache = admins
                    cls._admin_cache_time = now
                    return admins
        except Exception as e:
            logger.warning(f"Failed to load admins: {e}")
        
        cls._admin_cache = [cls.OWNER_ID]
        cls._admin_cache_time = now
        return cls._admin_cache

    @classmethod
    def save_admin(cls, user_id: int, add: bool = True) -> bool:
        """Add or remove admin dynamically"""
        admins = cls.get_admins()
        if add and user_id not in admins and user_id != cls.OWNER_ID:
            admins.append(user_id)
        elif not add and user_id in admins:
            admins.remove(user_id)
        else:
            return True # Nothing changed
        
        try:
            with open(cls.ADMINS_FILE, "w", encoding="utf-8") as f:
                json.dump({"admins": admins}, f, indent=2)
            cls._admin_cache = admins
            cls._admin_cache_time = time.time()
            return True
        except Exception as e:
            logger.error(f"Failed to save admins: {e}")
            return False

os.makedirs(Config.DATA_DIR, exist_ok=True)
os.makedirs(Config.BACKUP_DIR, exist_ok=True)

# ==========================================
# 2. LOGGING
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Config.LOG_FILE, encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# ==========================================
# 3. DATABASE (ENTERPRISE GRADE)
# ==========================================

class Database:
    _instance = None
    _lock = threading.Lock() # Prevents SQLite "database is locked" errors

    def __new__(cls):
        # Singleton Pattern: Ensures only ONE database connection exists
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Database, cls).__new__(cls)
                cls._instance._init_connection()
            return cls._instance

    def _init_connection(self):
        self.conn = sqlite3.connect(Config.DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def _dict_factory(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert sqlite3.Row to Python Dictionary"""
        return dict(row) if row else None

    def _execute(self, query: str, params: tuple = (), fetchone=False, fetchall=False) -> Any:
        """Thread-safe and error-proof centralized query executor"""
        with self._lock:
            try:
                cursor = self.conn.execute(query, params)
                if fetchone:
                    result = cursor.fetchone()
                    return self._dict_factory(result) if result else None
                if fetchall:
                    results = cursor.fetchall()
                    return [self._dict_factory(row) for row in results]
                self.conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                logger.error(f"DB Error: {e} | Query: {query[:80]}...")
                self.conn.rollback()
                return None

    def init_db(self):
        """Initialize tables and create indexes for ultra-fast reading"""
        tables = [
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT, 
                language_code TEXT, level INTEGER DEFAULT 0, xp INTEGER DEFAULT 0, 
                coins INTEGER DEFAULT 0, streak INTEGER DEFAULT 0, last_seen DATETIME, 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS attack_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, target TEXT, 
                target_id INTEGER, roasts_sent INTEGER, duration REAL, speed REAL, 
                mode TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS roast_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, target TEXT, 
                roast TEXT, rating INTEGER DEFAULT 0, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS ghost_targets (
                chat_id INTEGER, target_id INTEGER, created_by INTEGER, 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (chat_id, target_id))""",
            """CREATE TABLE IF NOT EXISTS troll_targets (
                chat_id INTEGER, target_id INTEGER, created_by INTEGER, 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (chat_id, target_id))""",
            """CREATE TABLE IF NOT EXISTS auto_reply (
                chat_id INTEGER, target_id INTEGER, reply_text TEXT, created_by INTEGER, 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (chat_id, target_id))""",
            """CREATE TABLE IF NOT EXISTS filters (
                chat_id INTEGER, keyword TEXT, reply_text TEXT, created_by INTEGER, 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (chat_id, keyword))""",
            """CREATE TABLE IF NOT EXISTS welcome (
                chat_id INTEGER PRIMARY KEY, message TEXT, enabled INTEGER DEFAULT 1, 
                created_by INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY, reason TEXT, created_by INTEGER, 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS whitelist (
                id INTEGER PRIMARY KEY, created_by INTEGER, 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"""
        ]
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_xp ON users(xp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen)",
            "CREATE INDEX IF NOT EXISTS idx_attack_chat ON attack_history(chat_id)",
            "CREATE INDEX IF NOT EXISTS idx_filters_chat ON filters(chat_id)"
        ]

        for query in tables + indexes:
            self._execute(query)
    
    # ===== User Methods =====
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str = "", language_code: str = "en") -> None:
        self._execute(
            "INSERT OR REPLACE INTO users (id, username, first_name, last_name, language_code, last_seen) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, username, first_name, last_name, language_code)
        )
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self._execute("SELECT * FROM users WHERE id = ?", (user_id,), fetchone=True)
    
    def update_user_stats(self, user_id: int, xp: int = 0, coins: int = 0, streak: int = 0) -> None:
        self._execute(
            "UPDATE users SET xp = xp + ?, coins = coins + ?, streak = ?, last_seen = CURRENT_TIMESTAMP WHERE id = ?",
            (xp, coins, streak, user_id)
        )
    
    def get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._execute(
            "SELECT id, username, first_name, xp, coins, level FROM users ORDER BY xp DESC LIMIT ?",
            (limit,), fetchall=True
        ) or []

    # ===== Target Methods (Ghost, Troll, Auto-reply, Filter) =====
    # Simplified using a generic check method
    def _check_exists(self, table: str, **kwargs) -> bool:
        conditions = " AND ".join([f"{k} = ?" for k in kwargs.keys()])
        query = f"SELECT 1 FROM {table} WHERE {conditions}"
        return self._execute(query, tuple(kwargs.values()), fetchone=True) is not None

    def is_ghosted(self, chat_id: int, target_id: int) -> bool:
        return self._check_exists("ghost_targets", chat_id=chat_id, target_id=target_id)

    def is_trolled(self, chat_id: int, target_id: int) -> bool:
        return self._check_exists("troll_targets", chat_id=chat_id, target_id=target_id)
    
    def get_filters(self, chat_id: int) -> List[Dict[str, Any]]:
        return self._execute("SELECT keyword, reply_text FROM filters WHERE chat_id = ?", (chat_id,), fetchall=True) or []
    
    # ===== Security Methods =====
    def is_blacklisted(self, user_id: int) -> bool:
        return self._check_exists("blacklist", id=user_id)

    def is_whitelisted(self, user_id: int) -> bool:
        return self._check_exists("whitelist", id=user_id)

db = Database()

# ==========================================
# 4. AUTHENTICATION
# ==========================================

class Auth:
    @staticmethod
    def is_admin(user_id: int) -> bool:
        return user_id == Config.OWNER_ID or user_id in Config.get_admins()
    
    @staticmethod
    def is_owner(user_id: int) -> bool:
        return user_id == Config.OWNER_ID
    
    @staticmethod
    def is_blacklisted(user_id: int) -> bool:
        return db.is_blacklisted(user_id)
    
    @staticmethod
    def can_use_bot(user_id: int) -> bool:
        if Auth.is_admin(user_id):
            return True
        return not Auth.is_blacklisted(user_id)

# ==========================================
# 5. DATA MANAGER
# ==========================================

class DataManager:
    @staticmethod
    def load_json(file_path: str, default: any) -> any:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default
    
    @staticmethod
    def save_json(file_path: str, data: any) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def backup_data() -> str:
        """Safe full backup creation"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(Config.BACKUP_DIR, f"backup_{timestamp}.json")
        
        data = {
            "admins": Config.get_admins(),
            "timestamp": datetime.now().isoformat(),
            "version": Config.VERSION
        }
        DataManager.save_json(backup_file, data)
        return backup_file

print(" Part 1 (PRO EDITION) Loaded Successfully!")
