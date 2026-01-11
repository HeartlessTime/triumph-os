"""
Email integration module for auto-logging activities from Gmail and Outlook.
Syncs emails with contacts and creates activity records automatically.
"""

import os
import re
from datetime import datetime, timedelta
from typing import Dict, Optional
from email.utils import parsedate_to_datetime
import imaplib
import email
from email.header import decode_header

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Activity, Contact, Opportunity


class EmailIntegration:
    """Base class for email integration."""

    def __init__(self, db: Session):
        self.db = db

    def sync_emails(self, since_date: Optional[datetime] = None) -> Dict:
        """
        Sync emails and create activity records.

        Args:
            since_date: Only sync emails since this date. Defaults to last 7 days.

        Returns:
            Dict with sync stats: {
                'total_emails': int,
                'activities_created': int,
                'errors': List[str]
            }
        """
        raise NotImplementedError("Subclasses must implement sync_emails")

    def match_contact_from_email(self, email_address: str) -> Optional[Contact]:
        """Find contact in database matching email address."""
        if not email_address:
            return None

        # Extract email from "Name <email@domain.com>" format
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", email_address)
        if email_match:
            clean_email = email_match.group(0).lower()
        else:
            clean_email = email_address.lower()

        # Search for contact by email
        contact = (
            self.db.query(Contact).filter(Contact.email.ilike(clean_email)).first()
        )

        return contact

    def find_related_opportunity(
        self, contact: Contact, subject: str, body: str
    ) -> Optional[Opportunity]:
        """
        Find the most relevant opportunity to attach this email to.

        Logic:
        1. Check if subject/body mentions any opportunity name
        2. Find most recent open opportunity for this contact
        3. Return None if no match (user can manually attach later)
        """
        if not contact:
            return None

        # Get opportunities for contact's account
        opportunities = (
            self.db.query(Opportunity)
            .filter(
                and_(
                    Opportunity.account_id == contact.account_id,
                    Opportunity.stage.notin_(["Won", "Lost"]),  # Only open opps
                )
            )
            .order_by(Opportunity.updated_at.desc())
            .all()
        )

        if not opportunities:
            return None

        # Check if opportunity name is mentioned in subject or body
        text = (subject + " " + body).lower()
        for opp in opportunities:
            if opp.name.lower() in text:
                return opp

        # If no explicit mention, return most recent opportunity
        return opportunities[0]

    def create_activity_from_email(
        self,
        opportunity: Optional[Opportunity],
        contact: Optional[Contact],
        subject: str,
        body: str,
        sent_date: datetime,
        created_by_id: int,
    ) -> Optional[Activity]:
        """
        Create an activity record from an email.

        Args:
            opportunity: Opportunity to attach to (can be None)
            contact: Contact the email was with
            subject: Email subject
            body: Email body (truncated for preview)
            sent_date: When email was sent
            created_by_id: User ID who sent/received the email

        Returns:
            Created Activity or None if creation failed
        """
        if not opportunity:
            # Can't create activity without an opportunity
            return None

        # Truncate body for activity description (keep first 500 chars)
        description = body[:500] + "..." if len(body) > 500 else body

        # Check if this activity already exists (avoid duplicates)
        existing = (
            self.db.query(Activity)
            .filter(
                and_(
                    Activity.opportunity_id == opportunity.id,
                    Activity.subject == subject,
                    Activity.activity_date == sent_date,
                    Activity.activity_type == "email",
                )
            )
            .first()
        )

        if existing:
            return existing  # Already logged

        # Create new activity
        activity = Activity(
            opportunity_id=opportunity.id,
            activity_type="email",
            subject=subject,
            description=description,
            activity_date=sent_date,
            contact_id=contact.id if contact else None,
            created_by_id=created_by_id,
        )

        self.db.add(activity)
        self.db.commit()

        # Update last_contacted on opportunity
        if (
            not opportunity.last_contacted
            or sent_date.date() > opportunity.last_contacted
        ):
            opportunity.last_contacted = sent_date.date()
            self.db.commit()

        return activity


class GmailIntegration(EmailIntegration):
    """Gmail integration using IMAP."""

    def __init__(self, db: Session, email_address: str, app_password: str):
        super().__init__(db)
        self.email_address = email_address
        self.app_password = app_password
        self.imap_server = "imap.gmail.com"

    def sync_emails(
        self, since_date: Optional[datetime] = None, user_id: int = None
    ) -> Dict:
        """Sync Gmail emails via IMAP."""
        if since_date is None:
            since_date = datetime.utcnow() - timedelta(days=7)

        stats = {
            "total_emails": 0,
            "activities_created": 0,
            "contacts_matched": 0,
            "opportunities_matched": 0,
            "errors": [],
        }

        try:
            # Connect to Gmail IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.app_password)

            # Search both sent and inbox
            for folder in ["INBOX", "[Gmail]/Sent Mail"]:
                try:
                    mail.select(folder)

                    # Search for emails since date
                    date_str = since_date.strftime("%d-%b-%Y")
                    result, data = mail.search(None, f"(SINCE {date_str})")

                    if result != "OK":
                        continue

                    email_ids = data[0].split()
                    stats["total_emails"] += len(email_ids)

                    # Process each email
                    for email_id in email_ids[-50:]:  # Limit to 50 most recent
                        try:
                            result, msg_data = mail.fetch(email_id, "(RFC822)")
                            if result != "OK":
                                continue

                            raw_email = msg_data[0][1]
                            msg = email.message_from_bytes(raw_email)

                            # Extract email data
                            subject = self._decode_header(msg["Subject"])
                            from_addr = msg["From"]
                            to_addr = msg["To"]
                            date_str = msg["Date"]

                            # Parse date
                            try:
                                sent_date = parsedate_to_datetime(date_str)
                            except:
                                sent_date = datetime.utcnow()

                            # Get body
                            body = self._get_email_body(msg)

                            # Determine contact (sent vs received)
                            if folder == "[Gmail]/Sent Mail":
                                contact_email = to_addr
                            else:
                                contact_email = from_addr

                            # Match contact
                            contact = self.match_contact_from_email(contact_email)
                            if contact:
                                stats["contacts_matched"] += 1

                                # Find related opportunity
                                opportunity = self.find_related_opportunity(
                                    contact, subject, body
                                )
                                if opportunity:
                                    stats["opportunities_matched"] += 1

                                    # Create activity
                                    activity = self.create_activity_from_email(
                                        opportunity=opportunity,
                                        contact=contact,
                                        subject=subject,
                                        body=body,
                                        sent_date=sent_date,
                                        created_by_id=user_id or 1,
                                    )

                                    if activity:
                                        stats["activities_created"] += 1

                        except Exception as e:
                            stats["errors"].append(
                                f"Error processing email {email_id}: {str(e)}"
                            )
                            continue

                except Exception as e:
                    stats["errors"].append(f"Error accessing folder {folder}: {str(e)}")
                    continue

            mail.close()
            mail.logout()

        except Exception as e:
            stats["errors"].append(f"IMAP connection error: {str(e)}")

        return stats

    def _decode_header(self, header_value):
        """Decode email header."""
        if not header_value:
            return ""

        decoded = decode_header(header_value)
        parts = []
        for content, charset in decoded:
            if isinstance(content, bytes):
                parts.append(content.decode(charset or "utf-8", errors="ignore"))
            else:
                parts.append(content)
        return "".join(parts)

    def _get_email_body(self, msg):
        """Extract plain text body from email."""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode(
                            "utf-8", errors="ignore"
                        )
                        break
                    except:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except:
                body = ""

        return body


class OutlookIntegration(EmailIntegration):
    """
    Outlook/Microsoft 365 integration using Microsoft Graph API.
    Requires app registration and OAuth2 setup.
    """

    def __init__(self, db: Session, access_token: str):
        super().__init__(db)
        self.access_token = access_token
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"

    def sync_emails(
        self, since_date: Optional[datetime] = None, user_id: int = None
    ) -> Dict:
        """Sync Outlook emails via Microsoft Graph API."""
        # Note: Requires additional setup with Microsoft Graph API
        # This is a placeholder implementation
        stats = {
            "total_emails": 0,
            "activities_created": 0,
            "errors": ["Outlook integration requires Microsoft Graph API setup"],
        }

        # TODO: Implement Graph API email sync
        # Would use requests library to call:
        # GET https://graph.microsoft.com/v1.0/me/messages
        # with proper OAuth2 authentication

        return stats


def get_email_integration(
    db: Session, provider: str = "gmail"
) -> Optional[EmailIntegration]:
    """
    Factory function to get appropriate email integration.

    Args:
        db: Database session
        provider: 'gmail' or 'outlook'

    Returns:
        EmailIntegration instance or None if not configured
    """
    if provider == "gmail":
        email_addr = os.getenv("GMAIL_ADDRESS")
        app_password = os.getenv("GMAIL_APP_PASSWORD")

        if email_addr and app_password:
            return GmailIntegration(db, email_addr, app_password)

    elif provider == "outlook":
        access_token = os.getenv("OUTLOOK_ACCESS_TOKEN")

        if access_token:
            return OutlookIntegration(db, access_token)

    return None
