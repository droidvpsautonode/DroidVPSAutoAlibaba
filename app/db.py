"""
Database module.
SQLite database for storing accounts, region cache, and action logs.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional

from app.config import Config


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DB_PATH
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        """Initialize database tables."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_name TEXT NOT NULL UNIQUE,
                    access_key_id TEXT NOT NULL,
                    access_key_secret_encrypted TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS region_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    region_id TEXT NOT NULL,
                    region_name TEXT NOT NULL,
                    instance_count INTEGER DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                    UNIQUE(account_id, region_id)
                );

                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                    telegram_user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    account_name TEXT DEFAULT '',
                    region_id TEXT DEFAULT '',
                    instance_id TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    error_message TEXT DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_logs_timestamp 
                    ON action_logs(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_region_cache_account 
                    ON region_cache(account_id);
            """)
            conn.commit()
        finally:
            conn.close()

    # ==================== ACCOUNTS ====================

    def add_account(
        self,
        account_name: str,
        access_key_id: str,
        access_key_secret_encrypted: str,
        notes: str = ""
    ) -> int:
        """Add a new Alibaba Cloud account. Returns account ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO accounts 
                   (account_name, access_key_id, access_key_secret_encrypted, notes)
                   VALUES (?, ?, ?, ?)""",
                (account_name, access_key_id, access_key_secret_encrypted, notes)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_accounts(self) -> list[dict]:
        """Get all accounts (without decrypted secrets)."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT id, account_name, access_key_id, 
                   access_key_secret_encrypted, notes, created_at
                   FROM accounts ORDER BY created_at DESC"""
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_account_by_id(self, account_id: int) -> Optional[dict]:
        """Get a single account by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT id, account_name, access_key_id,
                   access_key_secret_encrypted, notes, created_at
                   FROM accounts WHERE id = ?""",
                (account_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_account_by_name(self, account_name: str) -> Optional[dict]:
        """Get a single account by name."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT id, account_name, access_key_id,
                   access_key_secret_encrypted, notes, created_at
                   FROM accounts WHERE account_name = ?""",
                (account_name,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_account(self, account_id: int) -> bool:
        """Delete an account by ID. Returns True if deleted."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM accounts WHERE id = ?", (account_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def account_exists(self, account_name: str) -> bool:
        """Check if account name already exists."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT 1 FROM accounts WHERE account_name = ?",
                (account_name,)
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    # ==================== REGION CACHE ====================

    def set_region_cache(
        self,
        account_id: int,
        regions: list[dict]
    ):
        """
        Update region cache for an account.
        regions: list of {"region_id": str, "region_name": str, "instance_count": int}
        """
        conn = self._get_conn()
        try:
            # Clear old cache for this account
            conn.execute(
                "DELETE FROM region_cache WHERE account_id = ?",
                (account_id,)
            )
            # Insert new cache
            for region in regions:
                conn.execute(
                    """INSERT INTO region_cache 
                       (account_id, region_id, region_name, instance_count, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        account_id,
                        region["region_id"],
                        region["region_name"],
                        region.get("instance_count", 0),
                        datetime.utcnow().isoformat()
                    )
                )
            conn.commit()
        finally:
            conn.close()

    def get_region_cache(self, account_id: int) -> list[dict]:
        """Get cached regions for an account (only those with instances)."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT region_id, region_name, instance_count, updated_at
                   FROM region_cache 
                   WHERE account_id = ? AND instance_count > 0
                   ORDER BY region_name""",
                (account_id,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_region_cache_updated_at(self, account_id: int) -> Optional[str]:
        """Get last update time for region cache."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT MAX(updated_at) as last_update
                   FROM region_cache WHERE account_id = ?""",
                (account_id,)
            ).fetchone()
            return row["last_update"] if row else None
        finally:
            conn.close()

    # ==================== ACTION LOGS ====================

    def add_log(
        self,
        telegram_user_id: int,
        action: str,
        account_name: str = "",
        region_id: str = "",
        instance_id: str = "",
        status: str = "success",
        error_message: str = ""
    ) -> int:
        """Add action log entry. Returns log ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO action_logs 
                   (telegram_user_id, action, account_name, region_id, 
                    instance_id, status, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    telegram_user_id, action, account_name,
                    region_id, instance_id, status, error_message
                )
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_logs(self, limit: int = 20) -> list[dict]:
        """Get recent action logs."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT id, timestamp, telegram_user_id, action,
                   account_name, region_id, instance_id, status, error_message
                   FROM action_logs
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()


# Singleton instance
db = Database()
