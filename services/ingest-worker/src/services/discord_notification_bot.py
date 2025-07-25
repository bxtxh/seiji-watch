"""
Discord Notification Bot - Daily notifications for issue review workflow.
Sends scheduled notifications about pending issues at 14:00 JST.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any

import aiohttp
import pytz

from .airtable_issue_manager import AirtableIssueManager

logger = logging.getLogger(__name__)


@dataclass
class DiscordNotificationConfig:
    """Configuration for Discord notifications."""

    webhook_url: str
    channel_id: str | None = None
    notification_time: time = field(default_factory=lambda: time(14, 0))  # 14:00
    timezone: str = "Asia/Tokyo"
    enabled: bool = True
    retry_attempts: int = 3
    retry_delay: float = 60.0  # seconds

    def __post_init__(self):
        if not self.webhook_url:
            raise ValueError("Discord webhook URL is required")


class DiscordNotificationBot:
    """Discord bot for issue review notifications."""

    def __init__(self, config: DiscordNotificationConfig | None = None):
        self.config = config or self._load_config_from_env()
        self.airtable_manager = AirtableIssueManager()
        self.logger = logger

        # Task tracking
        self.notification_task: asyncio.Task | None = None
        self.is_running = False

        # Timezone setup
        self.timezone = pytz.timezone(self.config.timezone)

    def _load_config_from_env(self) -> DiscordNotificationConfig:
        """Load configuration from environment variables."""
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            raise ValueError("DISCORD_WEBHOOK_URL environment variable is required")

        # Parse notification time from environment
        notification_time_str = os.getenv("DISCORD_NOTIFICATION_TIME", "14:00")
        try:
            hour, minute = map(int, notification_time_str.split(":"))
            notification_time = time(hour, minute)
        except ValueError:
            self.logger.warning(
                f"Invalid notification time format: {notification_time_str}, using default 14:00"
            )
            notification_time = time(14, 0)

        return DiscordNotificationConfig(
            webhook_url=webhook_url,
            channel_id=os.getenv("DISCORD_CHANNEL_ID"),
            notification_time=notification_time,
            timezone=os.getenv("DISCORD_TIMEZONE", "Asia/Tokyo"),
            enabled=os.getenv("DISCORD_NOTIFICATIONS_ENABLED", "true").lower()
            == "true",
            retry_attempts=int(os.getenv("DISCORD_RETRY_ATTEMPTS", "3")),
            retry_delay=float(os.getenv("DISCORD_RETRY_DELAY", "60.0")),
        )

    async def start(self):
        """Start the notification scheduler."""
        if self.is_running:
            self.logger.warning("Discord notification bot is already running")
            return

        if not self.config.enabled:
            self.logger.info("Discord notifications are disabled")
            return

        self.is_running = True
        self.notification_task = asyncio.create_task(self._notification_scheduler())

        self.logger.info(
            f"Discord notification bot started - notifications at {self.config.notification_time} {self.config.timezone}"
        )

    async def stop(self):
        """Stop the notification scheduler."""
        if not self.is_running:
            return

        self.is_running = False

        if self.notification_task and not self.notification_task.done():
            self.notification_task.cancel()
            try:
                await self.notification_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Discord notification bot stopped")

    async def _notification_scheduler(self):
        """Main scheduler loop for daily notifications."""
        self.logger.info("Discord notification scheduler started")

        while self.is_running:
            try:
                # Calculate next notification time
                next_notification = self._calculate_next_notification_time()
                current_time = datetime.now(self.timezone)

                wait_seconds = (next_notification - current_time).total_seconds()

                if wait_seconds > 0:
                    self.logger.info(
                        f"Next notification scheduled for {next_notification.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )

                    # Wait until next notification time
                    await asyncio.sleep(wait_seconds)

                # Send notification if still running
                if self.is_running:
                    await self._send_daily_notification()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in notification scheduler: {e}")
                # Wait before retrying to avoid tight error loops
                await asyncio.sleep(300)  # 5 minutes

    def _calculate_next_notification_time(self) -> datetime:
        """Calculate the next notification time."""
        now = datetime.now(self.timezone)

        # Create today's notification time
        today_notification = now.replace(
            hour=self.config.notification_time.hour,
            minute=self.config.notification_time.minute,
            second=0,
            microsecond=0,
        )

        # If today's notification time has passed, schedule for tomorrow
        if now >= today_notification:
            next_notification = today_notification + timedelta(days=1)
        else:
            next_notification = today_notification

        return next_notification

    async def _send_daily_notification(self):
        """Send the daily notification about pending issues."""
        try:
            self.logger.info("Preparing daily Discord notification")

            # Get pending issue count (exclude failed validation)
            pending_count = await self.airtable_manager.count_pending_issues(
                exclude_failed_validation=True
            )

            # Get some statistics for richer notification
            stats = await self.airtable_manager.get_issue_statistics()

            # Create notification message
            message = self._create_notification_message(pending_count, stats)

            # Send notification with retries
            success = await self._send_discord_message(message)

            if success:
                self.logger.info(
                    f"Daily notification sent successfully - {pending_count} pending issues"
                )
            else:
                self.logger.error("Failed to send daily notification after all retries")

        except Exception as e:
            self.logger.error(f"Error sending daily notification: {e}")

    def _create_notification_message(
        self, pending_count: int, stats: dict[str, Any]
    ) -> dict[str, Any]:
        """Create Discord message for notification."""

        # Get current date in JST
        current_date = datetime.now(self.timezone).strftime("%Y年%m月%d日")

        # Choose emoji and message based on pending count
        if pending_count == 0:
            emoji = "✅"
            title = "レビュー完了"
            description = "本日のレビュー待ちイシューはありません。"
            color = 0x00FF00  # Green
        elif pending_count <= 5:
            emoji = "📋"
            title = "レビュー通知"
            description = f"レビュー待ちのイシューが **{pending_count}件** あります。"
            color = 0x3498DB  # Blue
        elif pending_count <= 20:
            emoji = "⚠️"
            title = "レビュー要注意"
            description = f"レビュー待ちのイシューが **{pending_count}件** あります。"
            color = 0xF39C12  # Orange
        else:
            emoji = "🚨"
            title = "レビュー緊急"
            description = (
                f"レビュー待ちのイシューが **{pending_count}件** と多数あります。"
            )
            color = 0xE74C3C  # Red

        # Build embed fields
        fields = []

        if pending_count > 0:
            fields.append(
                {
                    "name": "📝 レビュー待ち",
                    "value": f"{pending_count}件",
                    "inline": True,
                }
            )

        # Add statistics if available
        if stats:
            total_issues = stats.get("total_issues", 0)
            approved_count = stats.get("approved_count", 0)

            fields.extend(
                [
                    {
                        "name": "📊 総イシュー数",
                        "value": f"{total_issues}件",
                        "inline": True,
                    },
                    {
                        "name": "✅ 承認済み",
                        "value": f"{approved_count}件",
                        "inline": True,
                    },
                ]
            )

            if stats.get("average_quality_score", 0) > 0:
                fields.append(
                    {
                        "name": "🎯 平均品質スコア",
                        "value": f"{stats['average_quality_score']:.2f}",
                        "inline": True,
                    }
                )

        # Create the embed message
        embed = {
            "title": f"{emoji} {title}",
            "description": description,
            "color": color,
            "fields": fields,
            "footer": {
                "text": f"Seiji Watch | {current_date}",
                "icon_url": "https://example.com/seiji-watch-icon.png",  # Optional: Add your icon URL
            },
            "timestamp": datetime.now(self.timezone).isoformat(),
        }

        # Add action buttons if there are pending issues
        if pending_count > 0:
            # Note: Discord webhook doesn't support interactive components,
            # but we can include helpful links in the description
            airtable_url = os.getenv(
                "AIRTABLE_REVIEW_URL", "https://airtable.com/your-base-id/your-table-id"
            )
            embed["description"] += f"\n\n👉 [Airtableでレビューする]({airtable_url})"

        # Add next notification info
        next_notification = self._calculate_next_notification_time()
        embed[
            "description"
        ] += f"\n⏰ 次回通知: {next_notification.strftime('%m月%d日 %H:%M')}"

        return {"embeds": [embed]}

    async def _send_discord_message(self, message: dict[str, Any]) -> bool:
        """Send message to Discord webhook with retries."""

        for attempt in range(self.config.retry_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.config.webhook_url,
                        json=message,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 204:  # Discord webhook success
                            return True
                        elif response.status == 429:  # Rate limited
                            retry_after = int(response.headers.get("Retry-After", 60))
                            self.logger.warning(
                                f"Discord rate limited, waiting {retry_after} seconds"
                            )
                            await asyncio.sleep(retry_after)
                        else:
                            response_text = await response.text()
                            self.logger.error(
                                f"Discord webhook failed (attempt {attempt + 1}): {response.status} - {response_text}"
                            )

            except TimeoutError:
                self.logger.error(f"Discord webhook timeout (attempt {attempt + 1})")
            except Exception as e:
                self.logger.error(f"Discord webhook error (attempt {attempt + 1}): {e}")

            # Wait before retry (except on last attempt)
            if attempt < self.config.retry_attempts - 1:
                await asyncio.sleep(self.config.retry_delay)

        return False

    async def send_test_notification(self) -> bool:
        """Send a test notification immediately."""
        try:
            self.logger.info("Sending test Discord notification")

            # Get current stats
            pending_count = await self.airtable_manager.count_pending_issues()
            stats = await self.airtable_manager.get_issue_statistics()

            # Create test message
            message = self._create_notification_message(pending_count, stats)

            # Add test indicator
            if message["embeds"]:
                message["embeds"][0]["title"] = (
                    "🧪 " + message["embeds"][0]["title"] + " (テスト)"
                )
                message["embeds"][0]["description"] = (
                    "これはテスト通知です。\n\n" + message["embeds"][0]["description"]
                )

            # Send message
            success = await self._send_discord_message(message)

            if success:
                self.logger.info("Test notification sent successfully")
            else:
                self.logger.error("Failed to send test notification")

            return success

        except Exception as e:
            self.logger.error(f"Error sending test notification: {e}")
            return False

    async def send_custom_notification(
        self, title: str, message: str, color: int = 0x3498DB
    ) -> bool:
        """Send a custom notification message."""
        try:
            embed = {
                "title": title,
                "description": message,
                "color": color,
                "footer": {
                    "text": "Seiji Watch",
                },
                "timestamp": datetime.now(self.timezone).isoformat(),
            }

            discord_message = {"embeds": [embed]}

            return await self._send_discord_message(discord_message)

        except Exception as e:
            self.logger.error(f"Error sending custom notification: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if Discord webhook is accessible."""
        try:
            # Send a minimal test message
            test_message = {
                "content": "Health check - this message will be deleted",
                "flags": 64,  # Ephemeral flag (though webhooks might not support this)
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url,
                    json=test_message,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 204

        except Exception as e:
            self.logger.error(f"Discord health check failed: {e}")
            return False

    def get_status(self) -> dict[str, Any]:
        """Get current bot status."""
        next_notification = (
            self._calculate_next_notification_time() if self.is_running else None
        )

        return {
            "is_running": self.is_running,
            "enabled": self.config.enabled,
            "notification_time": self.config.notification_time.strftime("%H:%M"),
            "timezone": self.config.timezone,
            "next_notification": (
                next_notification.isoformat() if next_notification else None
            ),
            "webhook_configured": bool(self.config.webhook_url),
            "retry_attempts": self.config.retry_attempts,
            "retry_delay": self.config.retry_delay,
        }


# CLI utility functions for standalone operation
async def main():
    """Main function for standalone operation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python discord_notification_bot.py [start|test|status]")
        return

    command = sys.argv[1].lower()

    try:
        bot = DiscordNotificationBot()

        if command == "start":
            print("Starting Discord notification bot...")
            await bot.start()
            print("Bot started. Press Ctrl+C to stop.")

            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping bot...")
                await bot.stop()
                print("Bot stopped.")

        elif command == "test":
            print("Sending test notification...")
            success = await bot.send_test_notification()
            if success:
                print("✅ Test notification sent successfully")
            else:
                print("❌ Failed to send test notification")

        elif command == "status":
            status = bot.get_status()
            print("Bot Status:")
            for key, value in status.items():
                print(f"  {key}: {value}")

        else:
            print(f"Unknown command: {command}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
