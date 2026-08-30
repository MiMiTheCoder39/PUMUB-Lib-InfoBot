"""
services/memory_service.py
--------------------------
Handles persistent conversation memory and sliding-window context.
"""

from models.db import mysql
from flask import current_app
from typing import List, Dict, Any, Optional

class MemoryService:
    @staticmethod
    def save_message(user_id: int, role: str, content: str) -> Optional[int]:
        """Save a message to the chat history and return its ID."""
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO chat_history (user_id, role, content) VALUES (%s, %s, %s)",
            (user_id, role, content)
        )
        mysql.connection.commit()
        history_id = cur.lastrowid
        cur.close()
        return history_id

    @staticmethod
    def get_recent_history(user_id: int, limit: int = 8) -> List[Dict[str, str]]:
        """Fetch recent messages for context."""
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT role, content FROM chat_history WHERE user_id = %s "
            "ORDER BY timestamp DESC LIMIT %s",
            (user_id, limit)
        )
        rows = cur.fetchall()
        cur.close()
        
        # Reverse to get chronological order
        history = [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
        return history

    @staticmethod
    def clear_history(user_id: int):
        """Clear conversation for a user."""
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM chat_history WHERE user_id = %s", (user_id,))
        mysql.connection.commit()
        cur.close()

    @staticmethod
    def get_formatted_history(user_id: int, limit: int = 6) -> str:
        """Format history for LLM injection."""
        history = MemoryService.get_recent_history(user_id, limit)
        if not history:
            return ""
            
        formatted = "Previous Conversation:\n"
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            formatted += f"{role_label}: {msg['content']}\n"
        return formatted
