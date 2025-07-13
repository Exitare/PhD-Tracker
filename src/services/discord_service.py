import threading
import requests
import os
import logging

logger = logging.getLogger(__name__)

class DiscordService:

    @staticmethod
    def _send_async(webhook_url: str, data: dict):
        try:
            response = requests.post(webhook_url, json=data, timeout=5)
            if response.status_code != 204:
                logger.warning(f"Discord message failed: {response.status_code} {response.text}")
        except Exception as e:
            logger.exception(f"Error sending Discord message: {e}")

    @staticmethod
    def send_message(content: str) -> bool:
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            logger.warning("Discord webhook URL is not set.")
            return False

        data = {
            "content": content,
            "username": "PhD Assistant",
        }

        threading.Thread(
            target=DiscordService._send_async,
            args=(webhook_url, data),
            daemon=True
        ).start()

        return True