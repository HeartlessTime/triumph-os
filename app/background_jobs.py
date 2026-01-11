"""
Background job scheduler for periodic tasks.

EMAIL SYNC FEATURE REMOVED - This entire module is disabled for MVP.
APScheduler dependency removed to keep the app lightweight.

To re-enable email sync in the future:
1. Install apscheduler: pip install apscheduler
2. Uncomment the code below
3. Re-enable email_sync_router in app/routes/__init__.py and app/main.py
4. Set EMAIL_SYNC_ENABLED=true in environment
"""

import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# EMAIL SYNC DISABLED - All APScheduler code commented out for MVP
# =============================================================================

# import os
# from datetime import datetime, timedelta
# from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.triggers.interval import IntervalTrigger
#
# from app.database import SessionLocal
# from app.email_integration import get_email_integration
# from app.models import User
#
#
# class BackgroundJobScheduler:
#     """Manages background jobs for the application."""
#
#     def __init__(self):
#         self.scheduler = BackgroundScheduler()
#         self.email_sync_enabled = (
#             os.getenv("EMAIL_SYNC_ENABLED", "false").lower() == "true"
#         )
#
#     def start(self):
#         """Start the background job scheduler."""
#         if not self.scheduler.running:
#             # Add email sync job if enabled
#             if self.email_sync_enabled:
#                 # Run every 15 minutes
#                 self.scheduler.add_job(
#                     func=sync_emails_job,
#                     trigger=IntervalTrigger(minutes=15),
#                     id="email_sync_job",
#                     name="Sync emails and create activities",
#                     replace_existing=True,
#                 )
#                 logger.info("Email sync job scheduled to run every 15 minutes")
#
#             self.scheduler.start()
#             logger.info("Background job scheduler started")
#
#     def stop(self):
#         """Stop the background job scheduler."""
#         if self.scheduler.running:
#             self.scheduler.shutdown()
#             logger.info("Background job scheduler stopped")
#
#     def run_email_sync_now(self):
#         """Manually trigger email sync job."""
#         sync_emails_job()
#
#
# def sync_emails_job():
#     """
#     Background job to sync emails and create activities.
#     Runs periodically to keep activities up to date.
#     """
#     logger.info("Starting email sync job...")
#
#     db = SessionLocal()
#     try:
#         # Get the primary user (assuming first user is the owner)
#         user = db.query(User).filter(User.is_admin == True).first()
#         if not user:
#             logger.warning("No admin user found for email sync")
#             return
#
#         # Get Gmail integration
#         email_integration = get_email_integration(db, provider="gmail")
#
#         if not email_integration:
#             logger.warning(
#                 "Email integration not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD env vars."
#             )
#             return
#
#         # Sync emails from last 24 hours
#         since_date = datetime.utcnow() - timedelta(hours=24)
#         stats = email_integration.sync_emails(since_date=since_date, user_id=user.id)
#
#         logger.info(f"Email sync completed: {stats}")
#
#         if stats["errors"]:
#             for error in stats["errors"]:
#                 logger.error(f"Email sync error: {error}")
#
#     except Exception as e:
#         logger.error(f"Email sync job failed: {str(e)}")
#
#     finally:
#         db.close()
#
#
# # Global scheduler instance
# scheduler = BackgroundJobScheduler()


# =============================================================================
# STUB: Provide a no-op scheduler for any code that might import it
# =============================================================================

class DisabledScheduler:
    """Stub scheduler that does nothing. Email sync is disabled for MVP."""

    def __init__(self):
        self.scheduler = None

    def start(self):
        logger.info("Background jobs disabled for MVP - scheduler not started")

    def stop(self):
        pass

    def run_email_sync_now(self):
        logger.warning("Email sync is disabled for MVP")


# Export stub scheduler so imports don't break
scheduler = DisabledScheduler()
