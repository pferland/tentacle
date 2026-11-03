#    Tentacle V4 - The Automated TV Show Tracker, Downloader & Media Organizer
#    Copyright (C) 2010-2026
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Cryptographic manager for credentials encryption at rest."""

from __future__ import annotations

import os
import stat
from cryptography.fernet import Fernet, InvalidToken

DEFAULT_KEY_FILE = "tentacle.key"
ENCRYPTED_PREFIX = "enc:"


class CryptoManager:
    """Handles encryption and decryption of sensitive secrets (API keys, passwords)."""

    def __init__(self, key_path: str = DEFAULT_KEY_FILE) -> None:
        self.key_path = os.path.abspath(key_path)
        self._fernet: Fernet = self._load_or_generate_key()

    def _load_or_generate_key(self) -> Fernet:
        """Load encryption key from app path, or generate a new 256-bit key."""
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                key = f.read().strip()
        else:
            key = Fernet.generate_key()
            # Write with owner-only read/write permissions (0600)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            mode = stat.S_IRUSR | stat.S_IWUSR  # 0o600
            fd = os.open(self.key_path, flags, mode)
            with open(fd, "wb") as f:
                f.write(key)

        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt sensitive string, prefixing with 'enc:'."""
        if not plaintext:
            return ""
        if plaintext.startswith(ENCRYPTED_PREFIX):
            return plaintext  # already encrypted
        encrypted_bytes = self._fernet.encrypt(plaintext.encode("utf-8"))
        return f"{ENCRYPTED_PREFIX}{encrypted_bytes.decode('utf-8')}"

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt string if prefixed with 'enc:', or return as-is for plaintext."""
        if not ciphertext:
            return ""
        if not ciphertext.startswith(ENCRYPTED_PREFIX):
            return ciphertext  # legacy plaintext fallback
        token = ciphertext[len(ENCRYPTED_PREFIX) :].encode("utf-8")
        try:
            decrypted_bytes = self._fernet.decrypt(token)
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            return ""  # Invalid key or corrupted data
