#!/usr/bin/env python3
"""
Demo Data Seed Script for Triumph OS CRM

Creates realistic demo data for all entities:
- 10 Accounts (General Contractors)
- 15-20 Contacts
- 10 Opportunities across multiple stages
- Tasks (completed + pending)
- Activities (calls, emails, meetings, site visits)

All demo data is prefixed with "Demo - " for easy identification.

Usage:
    python -m app.demo.seed_demo_data
"""

import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.models.account import Account
from app.models.contact import Contact
from app.models.opportunity import Opportunity
from app.models.task import Task
from app.models.activity import Activity


# Demo prefix for easy identification
DEMO_PREFIX = "Demo - "


def today() -> date:
    return date.today()


def days_ago(n: int) -> date:
    return today() - timedelta(days=n)


def days_from_now(n: int) -> date:
    return today() + timedelta(days=n)


def datetime_ago(days: int, hours: int = 0) -> datetime:
    return datetime.now() - timedelta(days=days, hours=hours)


# =============================================================================
# DEMO ACCOUNTS (10 General Contractors)
# =============================================================================
DEMO_ACCOUNTS = [
    {
        "name": "Demo - Turner Construction",
        "industry": "Construction",
        "website": "https://turnerconstruction.com",
        "phone": "(512) 555-0100",
        "address": "100 Congress Ave",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "notes": "Large national GC, focus on commercial projects. Key decision maker is Mike Chen."
    },
    {
        "name": "Demo - McCarthy Building",
        "industry": "Construction",
        "website": "https://mccarthy.com",
        "phone": "(512) 555-0101",
        "address": "200 E 6th St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "notes": "Healthcare and education specialist. Good payment terms."
    },
    {
        "name": "Demo - DPR Construction",
        "industry": "Construction",
        "website": "https://dpr.com",
        "phone": "(512) 555-0102",
        "address": "300 Lavaca St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "notes": "Tech-forward builder. Data center and tech campus expertise."
    },
    {
        "name": "Demo - Hensel Phelps",
        "industry": "Construction",
        "website": "https://henselphelps.com",
        "phone": "(512) 555-0103",
        "address": "400 Guadalupe St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "notes": "Government and institutional focus. Strict compliance requirements."
    },
    {
        "name": "Demo - Skanska USA",
        "industry": "Construction",
        "website": "https://usa.skanska.com",
        "phone": "(512) 555-0104",
        "address": "500 W 5th St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "notes": "International presence. Sustainability-focused projects."
    },
    {
        "name": "Demo - Brasfield & Gorrie",
        "industry": "Construction",
        "website": "https://brasfieldgorrie.com",
        "phone": "(512) 555-0105",
        "address": "600 San Jacinto Blvd",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "notes": "Southeast regional strength. Growing Texas presence."
    },
    {
        "name": "Demo - Austin Commercial",
        "industry": "Construction",
        "website": "https://austincommercial.com",
        "phone": "(512) 555-0106",
        "address": "700 Colorado St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "notes": "Local Austin GC. Strong relationships with city permitting."
    },
    {
        "name": "Demo - Harvey Builders",
        "industry": "Construction",
        "website": "https://harveybuilders.com",
        "phone": "(512) 555-0107",
        "address": "800 Trinity St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "notes": "Texas-based, retail and mixed-use specialist."
    },
    {
        "name": "Demo - Balfour Beatty",
        "industry": "Construction",
        "website": "https://balfourbeattyus.com",
        "phone": "(512) 555-0108",
        "address": "900 Red River St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "notes": "UK-based, infrastructure and education focus."
    },
    {
        "name": "Demo - Whiting-Turner",
        "industry": "Construction",
        "website": "https://whiting-turner.com",
        "phone": "(512) 555-0109",
        "address": "1000 E Cesar Chavez St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78702",
        "notes": "Diversified portfolio. Quick turnaround on bid requests."
    },
]


# =============================================================================
# DEMO CONTACTS (linked to accounts by index)
# =============================================================================
DEMO_CONTACTS = [
    # Turner Construction (0)
    {"account_idx": 0, "first_name": "Mike", "last_name": "Chen", "title": "Senior Project Manager", "email": "mchen@demo-turner.com", "phone": "(512) 555-1001", "mobile": "(512) 555-1002", "is_primary": True, "last_contacted": days_ago(3), "next_followup": days_from_now(2)},
    {"account_idx": 0, "first_name": "Sarah", "last_name": "Williams", "title": "Estimator", "email": "swilliams@demo-turner.com", "phone": "(512) 555-1003", "is_primary": False, "last_contacted": days_ago(10)},

    # McCarthy Building (1)
    {"account_idx": 1, "first_name": "Jennifer", "last_name": "Martinez", "title": "Project Director", "email": "jmartinez@demo-mccarthy.com", "phone": "(512) 555-1010", "mobile": "(512) 555-1011", "is_primary": True, "last_contacted": days_ago(5), "next_followup": days_from_now(5)},
    {"account_idx": 1, "first_name": "Tom", "last_name": "Anderson", "title": "Chief Estimator", "email": "tanderson@demo-mccarthy.com", "phone": "(512) 555-1012", "is_primary": False, "last_contacted": days_ago(14)},

    # DPR Construction (2)
    {"account_idx": 2, "first_name": "David", "last_name": "Kim", "title": "Vice President", "email": "dkim@demo-dpr.com", "phone": "(512) 555-1020", "mobile": "(512) 555-1021", "is_primary": True, "last_contacted": days_ago(1), "next_followup": days_from_now(3)},

    # Hensel Phelps (3)
    {"account_idx": 3, "first_name": "Lisa", "last_name": "Thompson", "title": "Senior Estimator", "email": "lthompson@demo-hensel.com", "phone": "(512) 555-1030", "is_primary": True, "last_contacted": days_ago(7), "next_followup": days_ago(2)},  # Overdue followup
    {"account_idx": 3, "first_name": "Robert", "last_name": "Garcia", "title": "Project Manager", "email": "rgarcia@demo-hensel.com", "phone": "(512) 555-1031", "is_primary": False},

    # Skanska USA (4)
    {"account_idx": 4, "first_name": "Amanda", "last_name": "Brown", "title": "Preconstruction Manager", "email": "abrown@demo-skanska.com", "phone": "(512) 555-1040", "mobile": "(512) 555-1041", "is_primary": True, "last_contacted": days_ago(2)},

    # Brasfield & Gorrie (5)
    {"account_idx": 5, "first_name": "Chris", "last_name": "Davis", "title": "Project Executive", "email": "cdavis@demo-brasfield.com", "phone": "(512) 555-1050", "is_primary": True, "last_contacted": days_ago(21)},

    # Austin Commercial (6)
    {"account_idx": 6, "first_name": "Maria", "last_name": "Rodriguez", "title": "Owner", "email": "mrodriguez@demo-austincomm.com", "phone": "(512) 555-1060", "mobile": "(512) 555-1061", "is_primary": True, "last_contacted": days_ago(4), "next_followup": days_from_now(1)},
    {"account_idx": 6, "first_name": "James", "last_name": "Wilson", "title": "Estimator", "email": "jwilson@demo-austincomm.com", "phone": "(512) 555-1062", "is_primary": False},

    # Harvey Builders (7)
    {"account_idx": 7, "first_name": "Kevin", "last_name": "Lee", "title": "Chief Estimator", "email": "klee@demo-harvey.com", "phone": "(512) 555-1070", "is_primary": True, "last_contacted": days_ago(30)},

    # Balfour Beatty (8)
    {"account_idx": 8, "first_name": "Patricia", "last_name": "Moore", "title": "Regional Director", "email": "pmoore@demo-balfour.com", "phone": "(512) 555-1080", "mobile": "(512) 555-1081", "is_primary": True, "last_contacted": days_ago(8), "next_followup": days_from_now(7)},
    {"account_idx": 8, "first_name": "Steven", "last_name": "Taylor", "title": "Estimating Manager", "email": "staylor@demo-balfour.com", "phone": "(512) 555-1082", "is_primary": False, "last_contacted": days_ago(15)},

    # Whiting-Turner (9)
    {"account_idx": 9, "first_name": "Nancy", "last_name": "Jackson", "title": "VP of Preconstruction", "email": "njackson@demo-whiting.com", "phone": "(512) 555-1090", "mobile": "(512) 555-1091", "is_primary": True, "last_contacted": today(), "next_followup": days_from_now(4)},
]


# =============================================================================
# DEMO OPPORTUNITIES (10 across various stages)
# =============================================================================
DEMO_OPPORTUNITIES = [
    # Prospecting stage (2)
    {
        "account_idx": 0,
        "contact_idx": 0,
        "name": "Demo - Domain Tower Data Center",
        "description": "New 50,000 SF data center facility in the Domain area. Low-voltage infrastructure including structured cabling, fiber backbone, and security systems.",
        "stage": "Prospecting",
        "lv_value": Decimal("450000"),
        "hdd_value": Decimal("75000"),
        "bid_date": days_from_now(21),
        "source": "Referral",
        "last_contacted": days_ago(3),
        "next_followup": days_from_now(2),
        "notes": "Initial meeting went well. Mike mentioned they're also looking at Mueller location. Need to follow up on site visit.",
        "project_type": "Data Center",
        "stalled_reason": None,
    },
    {
        "account_idx": 5,
        "contact_idx": 8,
        "name": "Demo - Lakeline Mall Renovation",
        "description": "Retail renovation project. Fire alarm, access control, and PA system upgrades.",
        "stage": "Prospecting",
        "lv_value": Decimal("125000"),
        "bid_date": days_from_now(35),
        "source": "Cold Call",
        "last_contacted": days_ago(21),
        "notes": "Cold outreach. Chris seemed interested but busy. Try again next week.",
        "project_type": "Retail",
        "stalled_reason": "Waiting on drawings",
    },

    # Proposal stage (2)
    {
        "account_idx": 1,
        "contact_idx": 2,
        "name": "Demo - Dell Children's Hospital Wing",
        "description": "New pediatric wing addition. Nurse call, RTLS, access control, and structured cabling throughout.",
        "stage": "Proposal",
        "lv_value": Decimal("680000"),
        "hdd_value": Decimal("45000"),
        "bid_date": days_from_now(14),
        "source": "Repeat Customer",
        "last_contacted": days_ago(5),
        "next_followup": days_from_now(5),
        "notes": "Jennifer requesting detailed breakdown by floor. Need to coordinate with nurse call vendor.",
        "project_type": "Healthcare",
        "stalled_reason": None,
    },
    {
        "account_idx": 2,
        "contact_idx": 4,
        "name": "Demo - Tesla Gigafactory Expansion",
        "description": "Phase 2 expansion of manufacturing facility. Industrial networking, CCTV, and intercom systems.",
        "stage": "Proposal",
        "lv_value": Decimal("920000"),
        "hdd_value": Decimal("180000"),
        "bid_date": days_from_now(7),
        "source": "Referral",
        "last_contacted": days_ago(1),
        "next_followup": days_from_now(3),
        "notes": "High priority. David needs proposal by EOW. Coordinate with industrial automation team.",
        "project_type": "Manufacturing",
        "stalled_reason": None,
    },

    # Bid Sent stage (2)
    {
        "account_idx": 3,
        "contact_idx": 5,
        "name": "Demo - Austin ISD Elementary School",
        "description": "New K-5 elementary school. Full low-voltage package: data, voice, PA, clock, CCTV.",
        "stage": "Bid Sent",
        "lv_value": Decimal("340000"),
        "bid_date": days_ago(3),
        "source": "Website",
        "last_contacted": days_ago(7),
        "next_followup": days_ago(2),  # Overdue
        "notes": "Bid submitted. Waiting on results. Lisa mentioned decision expected this week.",
        "project_type": "Education",
        "stalled_reason": "Waiting on bid results",
    },
    {
        "account_idx": 6,
        "contact_idx": 9,
        "name": "Demo - Downtown Office Tower TI",
        "description": "Tenant improvement for tech company. Open office cabling, AV systems, conference rooms.",
        "stage": "Bid Sent",
        "lv_value": Decimal("185000"),
        "bid_date": days_ago(7),
        "source": "Repeat Customer",
        "last_contacted": days_ago(4),
        "next_followup": days_from_now(1),
        "notes": "Maria said we're competitive. Final decision pending tenant approval.",
        "project_type": "Commercial",
        "stalled_reason": "Waiting on GC",
    },

    # Negotiation stage (2)
    {
        "account_idx": 4,
        "contact_idx": 7,
        "name": "Demo - UT Austin Research Building",
        "description": "New research facility with lab infrastructure. Clean room cabling, BMS integration, specialized grounding.",
        "stage": "Negotiation",
        "lv_value": Decimal("520000"),
        "hdd_value": Decimal("65000"),
        "bid_date": days_ago(14),
        "close_date": days_from_now(10),
        "source": "Referral",
        "last_contacted": days_ago(2),
        "notes": "Down to us and one competitor. Amanda pushing for 5% reduction. Reviewing scope options.",
        "project_type": "Education",
        "stalled_reason": "Budget unclear",
    },
    {
        "account_idx": 8,
        "contact_idx": 12,
        "name": "Demo - Round Rock ISD High School",
        "description": "New high school campus. Comprehensive LV package including athletic facilities.",
        "stage": "Negotiation",
        "lv_value": Decimal("780000"),
        "hdd_value": Decimal("120000"),
        "bid_date": days_ago(21),
        "close_date": days_from_now(5),
        "source": "Website",
        "last_contacted": days_ago(8),
        "next_followup": days_from_now(7),
        "notes": "Patricia confirming final scope. Bond requirements being finalized. Strong position.",
        "project_type": "Education",
        "stalled_reason": None,
    },

    # Won (1)
    {
        "account_idx": 9,
        "contact_idx": 14,
        "name": "Demo - Google Austin Campus Building C",
        "description": "New office building in Google Austin campus. Enterprise networking, AV, and security.",
        "stage": "Won",
        "lv_value": Decimal("1250000"),
        "hdd_value": Decimal("200000"),
        "bid_date": days_ago(45),
        "close_date": days_ago(30),
        "source": "Referral",
        "last_contacted": today(),
        "notes": "Contract signed! Kickoff meeting scheduled. Great win for the team.",
        "project_type": "Commercial",
        "stalled_reason": None,
    },

    # Lost (1)
    {
        "account_idx": 7,
        "contact_idx": 11,
        "name": "Demo - HEB Distribution Center",
        "description": "Warehouse automation and security systems for new distribution facility.",
        "stage": "Lost",
        "lv_value": Decimal("380000"),
        "bid_date": days_ago(30),
        "close_date": days_ago(20),
        "source": "Cold Call",
        "last_contacted": days_ago(30),
        "notes": "Lost to competitor on price. Kevin said they went with lowest bidder. Follow up in 6 months for next project.",
        "project_type": "Industrial",
        "stalled_reason": None,
    },
]


# =============================================================================
# DEMO TASKS (mix of completed and pending, various priorities)
# =============================================================================
DEMO_TASKS = [
    # Tasks for Domain Tower Data Center (opp 0)
    {"opp_idx": 0, "title": "Demo - Schedule site visit with Mike", "description": "Coordinate with Turner PM for site walkthrough", "due_date": days_from_now(3), "priority": "High", "status": "Open"},
    {"opp_idx": 0, "title": "Demo - Get fiber pricing from CommScope", "description": "Need OM4 and single-mode pricing for data center", "due_date": days_from_now(5), "priority": "Medium", "status": "Open"},
    {"opp_idx": 0, "title": "Demo - Review bid documents", "description": "Initial review of drawings and specs", "due_date": days_ago(2), "priority": "High", "status": "Complete", "completed_at": datetime_ago(1)},

    # Tasks for Dell Children's Hospital (opp 2)
    {"opp_idx": 2, "title": "Demo - Nurse call vendor coordination", "description": "Meeting with Rauland rep for pricing", "due_date": days_from_now(2), "priority": "High", "status": "Open"},
    {"opp_idx": 2, "title": "Demo - Floor-by-floor breakdown", "description": "Jennifer needs detailed estimate per floor", "due_date": days_from_now(7), "priority": "Medium", "status": "Open"},
    {"opp_idx": 2, "title": "Demo - RTLS system research", "description": "Compare Versus and CenTrak options", "due_date": days_ago(5), "priority": "Medium", "status": "Complete", "completed_at": datetime_ago(3)},

    # Tasks for Tesla Gigafactory (opp 3)
    {"opp_idx": 3, "title": "Demo - Industrial networking proposal", "description": "Finalize Cisco IE switch configuration", "due_date": days_from_now(1), "priority": "Urgent", "status": "Open"},
    {"opp_idx": 3, "title": "Demo - CCTV camera count verification", "description": "Review drawings for camera locations", "due_date": days_from_now(3), "priority": "High", "status": "Open"},

    # Tasks for Austin ISD Elementary (opp 4)
    {"opp_idx": 4, "title": "Demo - Follow up on bid results", "description": "Call Lisa for status update", "due_date": days_ago(1), "priority": "High", "status": "Open"},  # Overdue

    # Tasks for UT Research Building (opp 6)
    {"opp_idx": 6, "title": "Demo - Value engineering options", "description": "Prepare 3 scope reduction alternatives", "due_date": days_from_now(4), "priority": "High", "status": "Open"},
    {"opp_idx": 6, "title": "Demo - Clean room cabling specs", "description": "Research plenum-rated options", "due_date": days_ago(7), "priority": "Medium", "status": "Complete", "completed_at": datetime_ago(5)},

    # Tasks for Google Campus (opp 8) - Won project
    {"opp_idx": 8, "title": "Demo - Kickoff meeting prep", "description": "Prepare project schedule and team assignments", "due_date": days_from_now(2), "priority": "High", "status": "Open"},
    {"opp_idx": 8, "title": "Demo - Submittals preparation", "description": "Start compiling product submittals", "due_date": days_from_now(14), "priority": "Medium", "status": "Open"},
    {"opp_idx": 8, "title": "Demo - Contract review complete", "description": "Legal review of subcontract", "due_date": days_ago(10), "priority": "Urgent", "status": "Complete", "completed_at": datetime_ago(8)},

    # General tasks (not linked to opportunities)
    {"opp_idx": None, "title": "Demo - Update insurance certificates", "description": "Annual renewal due", "due_date": days_from_now(10), "priority": "Medium", "status": "Open"},
    {"opp_idx": None, "title": "Demo - Safety training renewal", "description": "OSHA 30 refresher", "due_date": days_from_now(30), "priority": "Low", "status": "Open"},
]


# =============================================================================
# DEMO ACTIVITIES (calls, emails, meetings, site visits)
# =============================================================================
DEMO_ACTIVITIES = [
    # Activities for Domain Tower Data Center (opp 0)
    {"opp_idx": 0, "contact_idx": 0, "activity_type": "call", "subject": "Demo - Initial project discussion", "description": "Discussed scope and timeline. Mike mentioned urgency due to tenant move-in date.", "activity_date": datetime_ago(3)},
    {"opp_idx": 0, "contact_idx": 1, "activity_type": "email", "subject": "Demo - Sent preliminary pricing", "description": "Emailed ROM estimate to Sarah for internal review.", "activity_date": datetime_ago(2)},

    # Activities for Dell Children's Hospital (opp 2)
    {"opp_idx": 2, "contact_idx": 2, "activity_type": "meeting", "subject": "Demo - Preconstruction kickoff", "description": "Met with Jennifer and team. Walked through bid documents. Good opportunity.", "activity_date": datetime_ago(5)},
    {"opp_idx": 2, "contact_idx": 3, "activity_type": "call", "subject": "Demo - Takeoff clarification", "description": "Called Tom to clarify cable tray routing questions.", "activity_date": datetime_ago(14)},
    {"opp_idx": 2, "contact_idx": 2, "activity_type": "email", "subject": "Demo - RFI response received", "description": "Jennifer sent clarification on nurse call integration points.", "activity_date": datetime_ago(8)},

    # Activities for Tesla Gigafactory (opp 3)
    {"opp_idx": 3, "contact_idx": 4, "activity_type": "site_visit", "subject": "Demo - Manufacturing floor walkthrough", "description": "Site visit with David. Identified additional conduit requirements in production area.", "activity_date": datetime_ago(1)},
    {"opp_idx": 3, "contact_idx": 4, "activity_type": "call", "subject": "Demo - Proposal timeline discussion", "description": "David confirmed EOW deadline. Will expedite.", "activity_date": datetime_ago(3)},

    # Activities for Austin ISD Elementary (opp 4)
    {"opp_idx": 4, "contact_idx": 5, "activity_type": "email", "subject": "Demo - Bid submission confirmation", "description": "Submitted bid via BuildingConnected. Lisa acknowledged receipt.", "activity_date": datetime_ago(7)},
    {"opp_idx": 4, "contact_idx": 5, "activity_type": "call", "subject": "Demo - Pre-bid clarification", "description": "Called Lisa about PA system zone requirements.", "activity_date": datetime_ago(10)},

    # Activities for Downtown Office Tower (opp 5)
    {"opp_idx": 5, "contact_idx": 9, "activity_type": "meeting", "subject": "Demo - Final scope review", "description": "Met with Maria to finalize AV scope. Added 2 additional conference rooms.", "activity_date": datetime_ago(4)},
    {"opp_idx": 5, "contact_idx": 10, "activity_type": "email", "subject": "Demo - Revised proposal sent", "description": "Sent updated proposal with additional conference room AV.", "activity_date": datetime_ago(3)},

    # Activities for UT Research Building (opp 6)
    {"opp_idx": 6, "contact_idx": 7, "activity_type": "meeting", "subject": "Demo - Negotiation meeting", "description": "Discussed value engineering options with Amanda. She's pushing for 5% reduction.", "activity_date": datetime_ago(2)},
    {"opp_idx": 6, "contact_idx": 7, "activity_type": "call", "subject": "Demo - Budget discussion", "description": "Amanda mentioned university budget constraints. Need creative solutions.", "activity_date": datetime_ago(5)},

    # Activities for Round Rock ISD (opp 7)
    {"opp_idx": 7, "contact_idx": 12, "activity_type": "call", "subject": "Demo - Scope confirmation call", "description": "Patricia confirming athletic facility requirements. Added stadium speakers.", "activity_date": datetime_ago(8)},
    {"opp_idx": 7, "contact_idx": 13, "activity_type": "email", "subject": "Demo - Bond documentation sent", "description": "Sent performance bond quote to Steven.", "activity_date": datetime_ago(12)},

    # Activities for Google Campus (opp 8) - Won
    {"opp_idx": 8, "contact_idx": 14, "activity_type": "meeting", "subject": "Demo - Contract signing", "description": "Signed subcontract with Nancy. Project officially awarded!", "activity_date": datetime_ago(30)},
    {"opp_idx": 8, "contact_idx": 14, "activity_type": "call", "subject": "Demo - Kickoff scheduling", "description": "Scheduled kickoff meeting for next week.", "activity_date": datetime_ago(0)},
    {"opp_idx": 8, "contact_idx": 14, "activity_type": "email", "subject": "Demo - Insurance certificate sent", "description": "Sent updated COI per contract requirements.", "activity_date": datetime_ago(25)},

    # Activities for HEB Distribution (opp 9) - Lost
    {"opp_idx": 9, "contact_idx": 11, "activity_type": "call", "subject": "Demo - Award notification", "description": "Kevin called to inform us we lost. Competitor was 15% lower. Thanked us for bidding.", "activity_date": datetime_ago(20)},
    {"opp_idx": 9, "contact_idx": 11, "activity_type": "email", "subject": "Demo - Thank you follow-up", "description": "Sent thank you email. Requested feedback and asked to stay on bid list.", "activity_date": datetime_ago(19)},
]


def seed_demo_data():
    """Create all demo data in the database."""
    db = SessionLocal()

    try:
        # Check if demo data already exists
        existing = db.query(Account).filter(Account.name.like("Demo - %")).first()
        if existing:
            print("Demo data already exists. Run remove_demo_data.py first to clean up.")
            return False

        print("Creating demo data...")

        # Create accounts
        print("  Creating 10 demo accounts...")
        accounts: List[Account] = []
        for acct_data in DEMO_ACCOUNTS:
            account = Account(**acct_data)
            db.add(account)
            accounts.append(account)
        db.flush()  # Get IDs

        # Create contacts
        print(f"  Creating {len(DEMO_CONTACTS)} demo contacts...")
        contacts: List[Contact] = []
        for contact_data in DEMO_CONTACTS:
            data = contact_data.copy()
            account_idx = data.pop("account_idx")
            data["account_id"] = accounts[account_idx].id
            contact = Contact(**data)
            db.add(contact)
            contacts.append(contact)
        db.flush()  # Get IDs

        # Create opportunities
        print(f"  Creating {len(DEMO_OPPORTUNITIES)} demo opportunities...")
        opportunities: List[Opportunity] = []
        for opp_data in DEMO_OPPORTUNITIES:
            data = opp_data.copy()
            account_idx = data.pop("account_idx")
            contact_idx = data.pop("contact_idx")
            data["account_id"] = accounts[account_idx].id
            data["primary_contact_id"] = contacts[contact_idx].id
            opp = Opportunity(**data)
            db.add(opp)
            opportunities.append(opp)
        db.flush()  # Get IDs

        # Create tasks
        print(f"  Creating {len(DEMO_TASKS)} demo tasks...")
        for task_data in DEMO_TASKS:
            data = task_data.copy()
            opp_idx = data.pop("opp_idx")
            if opp_idx is not None:
                data["opportunity_id"] = opportunities[opp_idx].id
            task = Task(**data)
            db.add(task)

        # Create activities
        print(f"  Creating {len(DEMO_ACTIVITIES)} demo activities...")
        for activity_data in DEMO_ACTIVITIES:
            data = activity_data.copy()
            opp_idx = data.pop("opp_idx")
            contact_idx = data.pop("contact_idx")
            data["opportunity_id"] = opportunities[opp_idx].id
            data["contact_id"] = contacts[contact_idx].id
            activity = Activity(**data)
            db.add(activity)

        db.commit()

        print("\nDemo data created successfully!")
        print(f"  - {len(accounts)} Accounts")
        print(f"  - {len(contacts)} Contacts")
        print(f"  - {len(opportunities)} Opportunities")
        print(f"  - {len(DEMO_TASKS)} Tasks")
        print(f"  - {len(DEMO_ACTIVITIES)} Activities")
        print("\nAll demo data is prefixed with 'Demo - ' for easy identification.")
        return True

    except Exception as e:
        db.rollback()
        print(f"Error creating demo data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
