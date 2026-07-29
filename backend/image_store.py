"""
Image Store — PostgreSQL backend for VoiceAst
Stores captured photos and screenshots as binary (BYTEA) data.

Tables (auto-created on startup):
  captured_images — webcam photos taken via "take a photo and remember this"
  screenshots     — screen captures taken via "take a screenshot and save it"

All text data (labels, descriptions) goes here too so queries are simple.
MongoDB continues to handle command history, memories, and preferences.
"""
from __future__ import annotations

import base64
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config

# ---------------------------------------------------------------------------
# asyncpg — graceful fallback if not installed
# ---------------------------------------------------------------------------
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    print("[WRN] asyncpg not installed. Image store disabled.")
    print("  Install with: pip install asyncpg")

# ---------------------------------------------------------------------------
# SQL Definitions
# ---------------------------------------------------------------------------
_CREATE_CAPTURED_IMAGES = """
CREATE TABLE IF NOT EXISTS captured_images (
    id          SERIAL PRIMARY KEY,
    label       TEXT NOT NULL,
    description TEXT,
    image_data  BYTEA NOT NULL,
    source      TEXT NOT NULL DEFAULT 'webcam',
    taken_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_SCREENSHOTS = """
CREATE TABLE IF NOT EXISTS screenshots (
    id          SERIAL PRIMARY KEY,
    label       TEXT NOT NULL DEFAULT 'untitled',
    description TEXT,
    image_data  BYTEA NOT NULL,
    taken_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_IDX_IMAGES_LABEL      = "CREATE INDEX IF NOT EXISTS idx_images_label      ON captured_images (LOWER(label));"
_CREATE_IDX_SCREENSHOTS_LABEL = "CREATE INDEX IF NOT EXISTS idx_screenshots_label ON screenshots     (LOWER(label));"


class ImageStore:
    """
    Async PostgreSQL store for captured images and screenshots.

    Usage:
        image_store = ImageStore()
        await image_store.connect()
        ...
        await image_store.close()
    """

    def __init__(self):
        self._pool: Optional["asyncpg.Pool"] = None
        self.connected: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self):
        """Open connection pool and create tables if they don't exist."""
        if not ASYNCPG_AVAILABLE:
            print("[X] Image store disabled — asyncpg not installed.")
            return

        try:
            self._pool = await asyncpg.create_pool(
                dsn=config.POSTGRES_URL,
                min_size=1,
                max_size=5,
                command_timeout=10,
            )
            async with self._pool.acquire() as conn:
                await conn.execute(_CREATE_CAPTURED_IMAGES)
                await conn.execute(_CREATE_SCREENSHOTS)
                await conn.execute(_CREATE_IDX_IMAGES_LABEL)
                await conn.execute(_CREATE_IDX_SCREENSHOTS_LABEL)

            self.connected = True
            print("✓ Image Store connected (PostgreSQL)")
        except Exception as e:
            print(f"✗ PostgreSQL connection failed: {e}")
            print("  • Check POSTGRES_URL in your .env")
            print("  • Make sure PostgreSQL is running and the password is correct")
            self.connected = False

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            print("✓ Image Store disconnected (PostgreSQL)")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _b64_to_bytes(image_base64: str) -> bytes:
        """Convert base64 string (with or without data-URL prefix) to raw bytes."""
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]
        return base64.b64decode(image_base64)

    @staticmethod
    def _bytes_to_b64(raw: bytes) -> str:
        return base64.b64encode(raw).decode("utf-8")

    def _check(self) -> bool:
        if not self.connected or not self._pool:
            print("[WRN] Image store not connected — skipping DB operation.")
            return False
        return True

    # ------------------------------------------------------------------
    # Captured Images (webcam photos)
    # ------------------------------------------------------------------

    async def save_image(
        self,
        label: str,
        image_base64: str,
        description: str = "",
        source: str = "webcam",
    ) -> Optional[int]:
        """
        Save a webcam photo to PostgreSQL.

        Args:
            label:         Short human name ("John's desk", "my car").
            image_base64:  Base64-encoded image (JPEG/PNG).
            description:   Optional AI caption.
            source:        'webcam' or 'screenshot'.

        Returns:
            Row ID on success, None on failure.
        """
        if not self._check():
            return None
        try:
            raw = self._b64_to_bytes(image_base64)
            async with self._pool.acquire() as conn:
                row_id = await conn.fetchval(
                    """
                    INSERT INTO captured_images (label, description, image_data, source)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                    """,
                    label.strip(), description.strip(), raw, source,
                )
            print(f"✓ Image saved: '{label}' (id={row_id}, {len(raw)} bytes)")
            return row_id
        except Exception as e:
            print(f"[ERR] save_image: {e}")
            return None

    async def get_image(self, label: str) -> Optional[Dict]:
        """
        Fetch the most recent image whose label matches (case-insensitive).

        Returns dict with keys: id, label, description, image_base64, source, taken_at
        """
        if not self._check():
            return None
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, label, description, image_data, source, taken_at
                    FROM   captured_images
                    WHERE  LOWER(label) LIKE LOWER($1)
                    ORDER  BY taken_at DESC
                    LIMIT  1
                    """,
                    f"%{label.strip()}%",
                )
            if row:
                return {
                    "id":           row["id"],
                    "label":        row["label"],
                    "description":  row["description"],
                    "image_base64": self._bytes_to_b64(bytes(row["image_data"])),
                    "source":       row["source"],
                    "taken_at":     row["taken_at"].isoformat(),
                }
            return None
        except Exception as e:
            print(f"[ERR] get_image: {e}")
            return None

    async def list_images(self, limit: int = 20) -> List[Dict]:
        """Return recent captured images (without raw binary for speed)."""
        if not self._check():
            return []
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, label, description, source, taken_at
                    FROM   captured_images
                    ORDER  BY taken_at DESC
                    LIMIT  $1
                    """,
                    limit,
                )
            return [
                {
                    "id":          r["id"],
                    "label":       r["label"],
                    "description": r["description"],
                    "source":      r["source"],
                    "taken_at":    r["taken_at"].isoformat(),
                }
                for r in rows
            ]
        except Exception as e:
            print(f"[ERR] list_images: {e}")
            return []

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    async def save_screenshot(
        self,
        image_base64: str,
        label: str = "untitled",
        description: str = "",
    ) -> Optional[int]:
        """
        Save a screenshot to PostgreSQL.

        Args:
            image_base64: Base64-encoded PNG screenshot.
            label:        Optional label ("my desktop", "error screen").
            description:  Optional description.

        Returns:
            Row ID on success, None on failure.
        """
        if not self._check():
            return None
        try:
            raw = self._b64_to_bytes(image_base64)
            async with self._pool.acquire() as conn:
                row_id = await conn.fetchval(
                    """
                    INSERT INTO screenshots (label, description, image_data)
                    VALUES ($1, $2, $3)
                    RETURNING id
                    """,
                    label.strip(), description.strip(), raw,
                )
            print(f"✓ Screenshot saved: '{label}' (id={row_id}, {len(raw)} bytes)")
            return row_id
        except Exception as e:
            print(f"[ERR] save_screenshot: {e}")
            return None

    async def get_screenshot(self, label: str = "") -> Optional[Dict]:
        """
        Fetch the most recent screenshot, optionally filtered by label.

        Returns dict with keys: id, label, description, image_base64, taken_at
        """
        if not self._check():
            return None
        try:
            async with self._pool.acquire() as conn:
                if label:
                    row = await conn.fetchrow(
                        """
                        SELECT id, label, description, image_data, taken_at
                        FROM   screenshots
                        WHERE  LOWER(label) LIKE LOWER($1)
                        ORDER  BY taken_at DESC
                        LIMIT  1
                        """,
                        f"%{label.strip()}%",
                    )
                else:
                    row = await conn.fetchrow(
                        """
                        SELECT id, label, description, image_data, taken_at
                        FROM   screenshots
                        ORDER  BY taken_at DESC
                        LIMIT  1
                        """
                    )
            if row:
                return {
                    "id":           row["id"],
                    "label":        row["label"],
                    "description":  row["description"],
                    "image_base64": self._bytes_to_b64(bytes(row["image_data"])),
                    "taken_at":     row["taken_at"].isoformat(),
                }
            return None
        except Exception as e:
            print(f"[ERR] get_screenshot: {e}")
            return None

    async def list_screenshots(self, limit: int = 20) -> List[Dict]:
        """Return recent screenshots (without raw binary for speed)."""
        if not self._check():
            return []
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, label, description, taken_at
                    FROM   screenshots
                    ORDER  BY taken_at DESC
                    LIMIT  $1
                    """,
                    limit,
                )
            return [
                {
                    "id":          r["id"],
                    "label":       r["label"],
                    "description": r["description"],
                    "taken_at":    r["taken_at"].isoformat(),
                }
                for r in rows
            ]
        except Exception as e:
            print(f"[ERR] list_screenshots: {e}")
            return []

    async def get_stats(self) -> Dict:
        """Return quick counts for health check."""
        if not self._check():
            return {"images": 0, "screenshots": 0}
        try:
            async with self._pool.acquire() as conn:
                imgs = await conn.fetchval("SELECT COUNT(*) FROM captured_images")
                ss   = await conn.fetchval("SELECT COUNT(*) FROM screenshots")
            return {"images": imgs, "screenshots": ss}
        except Exception as e:
            print(f"[ERR] get_stats: {e}")
            return {"images": 0, "screenshots": 0}


# Global singleton
image_store = ImageStore()
