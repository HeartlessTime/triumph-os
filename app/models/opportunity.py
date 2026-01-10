from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Numeric, ForeignKey, JSON
from sqlalchemy import Boolean, Time
from sqlalchemy.orm import relationship
from app.database import Base


class OpportunityScope(Base):
    """Junction table for Opportunity-ScopePackage many-to-many."""
    __tablename__ = 'opportunity_scopes'

    opportunity_id = Column(Integer, ForeignKey('opportunities.id', ondelete='CASCADE'), primary_key=True)
    scope_package_id = Column(Integer, ForeignKey('scope_packages.id', ondelete='CASCADE'), primary_key=True)

    # Relationships
    opportunity = relationship("Opportunity", back_populates="scope_links")
    scope_package = relationship("ScopePackage", back_populates="opportunities")


class Opportunity(Base):
    __tablename__ = 'opportunities'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    stage = Column(String(50), nullable=False, default='Prospecting', index=True)
    # Make probability optional in DB; keep default for legacy rows
    probability = Column(Integer, nullable=True, default=10)
    # Removed overall GC contract `value` (stored elsewhere); keep lv + hdd split
    bid_date = Column(Date, nullable=True, index=True)
    close_date = Column(Date, nullable=True)
    last_contacted = Column(Date, nullable=True)
    next_followup = Column(Date, nullable=True, index=True)
    # Bid instruction fields
    bid_type = Column(String(50), nullable=True)
    submission_method = Column(String(50), nullable=True)
    bid_time = Column(Time, nullable=True)
    bid_form_required = Column(Boolean, nullable=False, default=False)
    bond_required = Column(Boolean, nullable=False, default=False)
    prevailing_wage = Column(String(20), nullable=True)
    # Project-level fields
    known_risks = Column(Text, nullable=True)
    project_type = Column(String(50), nullable=True)
    rebid = Column(Boolean, nullable=False, default=False)
    # Split values: low-voltage expected value and HDD/underground estimate
    lv_value = Column(Numeric(15, 2), nullable=True)
    hdd_value = Column(Numeric(15, 2), nullable=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    assigned_estimator_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    estimating_status = Column(String(50), nullable=False, default='Not Started')
    estimating_checklist = Column(JSON, nullable=True)
    primary_contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=True)
    source = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    # General contractors bidding on this project (store list of account ids)
    gcs = Column(JSON, nullable=True)
    # Related contact ids (list of contact ids)
    related_contact_ids = Column(JSON, nullable=True)
    # Quick links (list of url strings or objects)
    quick_links = Column(JSON, nullable=True)
    # End-user / owner account (e.g., Austin ISD)
    end_user_account_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    # Stalled reason for tracking why opportunity is not progressing
    stalled_reason = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="opportunities", foreign_keys=[account_id])
    end_user_account = relationship("Account", back_populates="end_user_opportunities", foreign_keys=[end_user_account_id])
    owner = relationship("User", back_populates="owned_opportunities", foreign_keys=[owner_id])
    assigned_estimator = relationship("User", back_populates="assigned_estimates", foreign_keys=[assigned_estimator_id])
    primary_contact = relationship("Contact", back_populates="opportunities")
    scope_links = relationship("OpportunityScope", back_populates="opportunity", cascade="all, delete-orphan")
    estimates = relationship("Estimate", back_populates="opportunity", cascade="all, delete-orphan", order_by="desc(Estimate.version)")
    activities = relationship("Activity", back_populates="opportunity", cascade="all, delete-orphan", order_by="desc(Activity.activity_date)")
    tasks = relationship("Task", back_populates="opportunity", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="opportunity", cascade="all, delete-orphan")
    vendor_quote_requests = relationship("VendorQuoteRequest", back_populates="opportunity", cascade="all, delete-orphan")

    STAGES = [
        ('Prospecting', 10),
        ('Proposal', 40),
        ('Bid Sent', 60),
        ('Negotiation', 80),
        ('Won', 100),
        ('Lost', 0),
    ]

    STAGE_NAMES = [s[0] for s in STAGES]
    STAGE_PROBABILITIES = {s[0]: s[1] for s in STAGES}

    ESTIMATING_STATUSES = [
        'Not Started',
        'In Progress',
        'Review',
        'Complete',
        'On Hold'
    ]

    SOURCES = [
        'Referral',
        'Website',
        'Cold Call',
        'Trade Show',
        'Repeat Customer',
        'Advertisement',
        'Other'
    ]

    STALLED_REASONS = [
        'Waiting on GC',
        'Waiting on bid results',
        'Waiting on drawings',
        'Budget unclear',
        'Internal delay',
    ]

    DEFAULT_CHECKLIST = [
        {'item': 'Review bid documents', 'done': False},
        {'item': 'Site visit scheduled', 'done': False},
        {'item': 'Takeoff complete', 'done': False},
        {'item': 'Vendor quotes received', 'done': False},
        {'item': 'Labor estimate complete', 'done': False},
        {'item': 'Management review', 'done': False},
    ]

    @property
    def scopes(self):
        """Return list of scope packages for this opportunity."""
        return [link.scope_package for link in self.scope_links]

    @property
    def scope_names(self):
        """Return comma-separated list of scope names."""
        return ', '.join(s.name for s in self.scopes)

    @property
    def latest_estimate(self):
        """Return the most recent estimate."""
        if self.estimates:
            return self.estimates[0]
        return None

    @property
    def estimate_count(self):
        return len(self.estimates)

    @property
    def open_tasks(self):
        return [t for t in self.tasks if t.status == 'Open']

    @property
    def completed_tasks(self):
        return [t for t in self.tasks if t.status == 'Complete']

    @property
    def value(self):
        """Total value = LV value + HDD value."""
        return (self.lv_value or Decimal(0)) + (self.hdd_value or Decimal(0))

    @property
    def weighted_value(self):
        """Weighted value disabled — return 0."""
        return Decimal(0)

    @property
    def is_open(self):
        return self.stage not in ['Won', 'Lost']

    @property
    def days_until_bid(self):
        """Return days until bid date, or None if no bid date."""
        if self.bid_date:
            delta = self.bid_date - date.today()
            return delta.days
        return None

    @property
    def is_past_bid_date(self):
        """Check if bid date has passed."""
        if self.bid_date:
            return self.bid_date < date.today()
        return False

    @property
    def checklist_progress(self):
        """Return checklist completion as (completed, total)."""
        if not self.estimating_checklist:
            return (0, 0)
        total = len(self.estimating_checklist)
        done = sum(1 for item in self.estimating_checklist if item.get('done', False))
        return (done, total)

    @property
    def health_score(self):
        """Calculate opportunity health score (0-10).

        Scoring:
        +2 last_contacted within 7 days
        +2 next_followup set
        +2 bid_date set
        +2 primary_contact set
        +2 notes present
        """
        if self.stage in ('Won', 'Lost'):
            return None

        score = 0
        today = date.today()

        # +2 if last_contacted within 7 days
        if self.last_contacted and (today - self.last_contacted).days <= 7:
            score += 2

        # +2 if next_followup is set
        if self.next_followup:
            score += 2

        # +2 if bid_date is set
        if self.bid_date:
            score += 2

        # +2 if primary_contact is set
        if self.primary_contact_id:
            score += 2

        # +2 if notes are present
        if self.notes and self.notes.strip():
            score += 2

        return score

    @property
    def health_score_color(self):
        """Return CSS color class for health score badge."""
        score = self.health_score
        if score is None:
            return None
        if score >= 8:
            return 'success'  # Green
        elif score >= 5:
            return 'warning'  # Yellow
        else:
            return 'danger'   # Red

    def get_default_probability(self):
        """Get default probability for current stage."""
        return self.STAGE_PROBABILITIES.get(self.stage, 10)

    def __repr__(self):
        return f"<Opportunity {self.name}>"
