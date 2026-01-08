"""
Background job scheduler for periodic tasks.
Uses APScheduler for running background jobs like email sync.
"""
import os
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import SessionLocal
from app.email_integration import get_email_integration
from app.models import User

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackgroundJobScheduler:
    """Manages background jobs for the application."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.email_sync_enabled = os.getenv('EMAIL_SYNC_ENABLED', 'false').lower() == 'true'

    def start(self):
        """Start the background job scheduler."""
        if not self.scheduler.running:
            # Add email sync job if enabled
            if self.email_sync_enabled:
                # Run every 15 minutes
                self.scheduler.add_job(
                    func=sync_emails_job,
                    trigger=IntervalTrigger(minutes=15),
                    id='email_sync_job',
                    name='Sync emails and create activities',
                    replace_existing=True
                )
                logger.info("Email sync job scheduled to run every 15 minutes")

            self.scheduler.start()
            logger.info("Background job scheduler started")

    def stop(self):
        """Stop the background job scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Background job scheduler stopped")

    def run_email_sync_now(self):
        """Manually trigger email sync job."""
        sync_emails_job()


def sync_emails_job():
    """
    Background job to sync emails and create activities.
    Runs periodically to keep activities up to date.
    """
    logger.info("Starting email sync job...")

    db = SessionLocal()
    try:
        # Get the primary user (assuming first user is the owner)
        user = db.query(User).filter(User.is_admin == True).first()
        if not user:
            logger.warning("No admin user found for email sync")
            return

        # Get Gmail integration
        email_integration = get_email_integration(db, provider='gmail')

        if not email_integration:
            logger.warning("Email integration not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD env vars.")
            return

        # Sync emails from last 24 hours
        since_date = datetime.utcnow() - timedelta(hours=24)
        stats = email_integration.sync_emails(since_date=since_date, user_id=user.id)

        logger.info(f"Email sync completed: {stats}")

        if stats['errors']:
            for error in stats['errors']:
                logger.error(f"Email sync error: {error}")

    except Exception as e:
        logger.error(f"Email sync job failed: {str(e)}")

    finally:
        db.close()


# Global scheduler instance
scheduler = BackgroundJobScheduler()
