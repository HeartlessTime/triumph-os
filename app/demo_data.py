"""Demo data for fallback when database is unavailable."""

from datetime import datetime, date, timedelta
from decimal import Decimal
from app.models import Account, Contact, Opportunity, Activity, Task


def get_demo_accounts():
    """Return list of demo Account objects (not saved to DB)."""
    accounts = []

    # Account 1: Construction company
    acc1 = Account()
    acc1.id = 1
    acc1.name = "Sunbelt Construction Partners"
    acc1.industry = "Construction"
    acc1.website = "www.sunbeltconstruction.example"
    acc1.phone = "(555) 234-5678"
    acc1.address = "1250 Commerce Drive"
    acc1.city = "Phoenix"
    acc1.state = "AZ"
    acc1.zip_code = "85001"
    acc1.notes = "Major GC in Southwest region. Active bidder on commercial projects."
    acc1.created_at = datetime.utcnow() - timedelta(days=180)
    accounts.append(acc1)

    # Account 2: Real estate developer
    acc2 = Account()
    acc2.id = 2
    acc2.name = "Metro Real Estate Development"
    acc2.industry = "Real Estate"
    acc2.website = "www.metroredevelopment.example"
    acc2.phone = "(555) 876-5432"
    acc2.address = "500 Tower Boulevard, Suite 1200"
    acc2.city = "Dallas"
    acc2.state = "TX"
    acc2.zip_code = "75201"
    acc2.notes = "Multi-family and mixed-use developer. Repeat customer."
    acc2.created_at = datetime.utcnow() - timedelta(days=365)
    accounts.append(acc2)

    # Account 3: Healthcare facility
    acc3 = Account()
    acc3.id = 3
    acc3.name = "Regional Medical Center"
    acc3.industry = "Healthcare"
    acc3.phone = "(555) 321-9876"
    acc3.address = "2400 Medical Park Way"
    acc3.city = "Austin"
    acc3.state = "TX"
    acc3.zip_code = "78701"
    acc3.notes = "Planning major expansion. Key decision maker is CFO."
    acc3.created_at = datetime.utcnow() - timedelta(days=90)
    accounts.append(acc3)

    # Account 4: Education
    acc4 = Account()
    acc4.id = 4
    acc4.name = "Valley School District"
    acc4.industry = "Education"
    acc4.phone = "(555) 555-0100"
    acc4.address = "1800 Education Lane"
    acc4.city = "Mesa"
    acc4.state = "AZ"
    acc4.zip_code = "85201"
    acc4.notes = "Public bid process. Bond funding approved for new campus."
    acc4.created_at = datetime.utcnow() - timedelta(days=120)
    accounts.append(acc4)

    # Account 5: Manufacturing
    acc5 = Account()
    acc5.id = 5
    acc5.name = "TechFab Industries"
    acc5.industry = "Manufacturing"
    acc5.website = "www.techfabindustries.example"
    acc5.phone = "(555) 444-3210"
    acc5.address = "3500 Industrial Parkway"
    acc5.city = "San Antonio"
    acc5.state = "TX"
    acc5.zip_code = "78219"
    acc5.notes = "Expanding facility. Price sensitive."
    acc5.created_at = datetime.utcnow() - timedelta(days=60)
    accounts.append(acc5)

    return accounts


def get_demo_contacts():
    """Return list of demo Contact objects (not saved to DB)."""
    contacts = []

    # Contacts for Sunbelt Construction
    c1 = Contact()
    c1.id = 1
    c1.account_id = 1
    c1.first_name = "Michael"
    c1.last_name = "Rodriguez"
    c1.title = "Project Manager"
    c1.email = "mrodriguez@sunbelt.example"
    c1.phone = "(555) 234-5678"
    c1.mobile = "(555) 234-5679"
    c1.is_primary = True
    c1.notes = "Very responsive. Prefers email."
    contacts.append(c1)

    c2 = Contact()
    c2.id = 2
    c2.account_id = 1
    c2.first_name = "Sarah"
    c2.last_name = "Thompson"
    c2.title = "VP of Operations"
    c2.email = "sthompson@sunbelt.example"
    c2.phone = "(555) 234-5680"
    c2.is_primary = False
    contacts.append(c2)

    # Contact for Metro Real Estate
    c3 = Contact()
    c3.id = 3
    c3.account_id = 2
    c3.first_name = "David"
    c3.last_name = "Chen"
    c3.title = "Development Director"
    c3.email = "dchen@metroredevelopment.example"
    c3.phone = "(555) 876-5432"
    c3.mobile = "(555) 876-5433"
    c3.is_primary = True
    c3.notes = "Decision maker. Schedule calls in advance."
    contacts.append(c3)

    # Contact for Regional Medical
    c4 = Contact()
    c4.id = 4
    c4.account_id = 3
    c4.first_name = "Jennifer"
    c4.last_name = "Martinez"
    c4.title = "Facilities Manager"
    c4.email = "jmartinez@regionalmedical.example"
    c4.phone = "(555) 321-9876"
    c4.is_primary = True
    contacts.append(c4)

    # Contact for Valley School District
    c5 = Contact()
    c5.id = 5
    c5.account_id = 4
    c5.first_name = "Robert"
    c5.last_name = "Johnson"
    c5.title = "Director of Facilities"
    c5.email = "rjohnson@valleyschools.example"
    c5.phone = "(555) 555-0100"
    c5.is_primary = True
    c5.notes = "Public bid process. Must follow formal procedures."
    contacts.append(c5)

    # Contact for TechFab
    c6 = Contact()
    c6.id = 6
    c6.account_id = 5
    c6.first_name = "Lisa"
    c6.last_name = "Anderson"
    c6.title = "Plant Manager"
    c6.email = "landerson@techfab.example"
    c6.phone = "(555) 444-3210"
    c6.mobile = "(555) 444-3211"
    c6.is_primary = True
    contacts.append(c6)

    return contacts


def get_demo_opportunities():
    """Return list of demo Opportunity objects (not saved to DB)."""
    opportunities = []
    today = date.today()

    # Opp 1: High-value commercial project
    o1 = Opportunity()
    o1.id = 1
    o1.account_id = 1
    o1.name = "Sunbelt - Downtown Office Tower"
    o1.description = "12-story office building, full low-voltage package including fire alarm, access control, CCTV, and structured cabling"
    o1.stage = "Proposal"
    o1.probability = 60
    o1.bid_date = today + timedelta(days=14)
    o1.close_date = None
    o1.last_contacted = today - timedelta(days=3)
    o1.next_followup = today + timedelta(days=7)
    o1.bid_type = "Public"
    o1.submission_method = "Electronic"
    o1.bid_time = None
    o1.bid_form_required = True
    o1.bond_required = True
    o1.prevailing_wage = "Yes"
    o1.project_type = "Commercial Office"
    o1.rebid = False
    o1.lv_value = Decimal("485000.00")
    o1.hdd_value = Decimal("0.00")
    o1.owner_id = 1
    o1.assigned_estimator_id = 1
    o1.estimating_status = "In Progress"
    o1.estimating_checklist = [
        {"item": "Review bid documents", "done": True},
        {"item": "Site visit scheduled", "done": True},
        {"item": "Takeoff complete", "done": True},
        {"item": "Vendor quotes received", "done": False},
        {"item": "Labor estimate complete", "done": False},
        {"item": "Management review", "done": False},
    ]
    o1.primary_contact_id = 1
    o1.source = "Repeat Customer"
    o1.notes = (
        "GC is pre-qualified. Strong relationship. Competitive bid with 3 other subs."
    )
    o1.created_at = datetime.utcnow() - timedelta(days=45)
    o1.primary_account_id = 1
    o1.related_contact_ids = [1, 2]
    o1.quick_links = ["https://triumph.example/bids/sunbelt-downtown"]
    o1.end_user_account_id = 3
    opportunities.append(o1)

    # Opp 2: Multi-family project
    o2 = Opportunity()
    o2.id = 2
    o2.account_id = 2
    o2.name = "Metro - Riverside Apartments Phase 2"
    o2.description = (
        "250-unit apartment complex, access control and CCTV for common areas"
    )
    o2.stage = "Bid Sent"
    o2.probability = 75
    o2.bid_date = today + timedelta(days=7)
    o2.lv_value = Decimal("125000.00")
    o2.hdd_value = Decimal("0.00")
    o2.owner_id = 1
    o2.assigned_estimator_id = 1
    o2.estimating_status = "Complete"
    o2.primary_contact_id = 3
    o2.source = "Repeat Customer"
    o2.last_contacted = today - timedelta(days=1)
    o2.next_followup = today + timedelta(days=3)
    o2.notes = "Phase 1 completed successfully. Repeat customer discount applied."
    o2.created_at = datetime.utcnow() - timedelta(days=30)
    o2.primary_account_id = 2
    o2.related_contact_ids = [3]
    o2.quick_links = ["https://triumph.example/bids/metro-riverside"]
    opportunities.append(o2)

    # Opp 3: Healthcare expansion - needs follow-up
    o3 = Opportunity()
    o3.id = 3
    o3.account_id = 3
    o3.name = "Regional Medical - Emergency Dept Expansion"
    o3.description = (
        "New emergency department wing, nurse call, fire alarm, access control"
    )
    o3.stage = "Proposal"
    o3.probability = 40
    o3.bid_date = today + timedelta(days=60)
    o3.lv_value = Decimal("320000.00")
    o3.hdd_value = Decimal("0.00")
    o3.owner_id = 1
    o3.assigned_estimator_id = 1
    o3.estimating_status = "Not Started"
    o3.primary_contact_id = 4
    o3.source = "Referral"
    o3.last_contacted = today - timedelta(days=15)
    o3.next_followup = today - timedelta(days=5)  # Overdue!
    o3.notes = "Waiting on drawings. Follow up needed on timeline."
    o3.created_at = datetime.utcnow() - timedelta(days=20)
    o3.primary_account_id = 3
    o3.related_contact_ids = [4]
    o3.quick_links = ["https://triumph.example/bids/regional-medical"]
    opportunities.append(o3)

    # Opp 4: School project with HDD
    o4 = Opportunity()
    o4.id = 4
    o4.account_id = 4
    o4.name = "Valley Schools - New High School Campus"
    o4.description = "New construction, full technology package plus underground fiber optic backbone between buildings"
    o4.stage = "Bid Sent"
    o4.probability = 60
    o4.bid_date = today + timedelta(days=45)
    o4.lv_value = Decimal("650000.00")
    o4.hdd_value = Decimal("85000.00")
    o4.owner_id = 1
    o4.assigned_estimator_id = 1
    o4.estimating_status = "In Progress"
    o4.primary_contact_id = 5
    o4.source = "Advertisement"
    o4.last_contacted = today - timedelta(days=7)
    o4.next_followup = today + timedelta(days=2)
    o4.bid_type = "Public"
    o4.bid_form_required = True
    o4.bond_required = True
    o4.prevailing_wage = "Yes"
    o4.project_type = "Education"
    o4.notes = "Public bid. Bond funded. Site visit scheduled for next week."
    o4.created_at = datetime.utcnow() - timedelta(days=35)
    o4.primary_account_id = 4
    o4.related_contact_ids = [5]
    o4.quick_links = ["https://triumph.example/bids/valley-school"]
    opportunities.append(o4)

    # Opp 5: Manufacturing facility - prospecting
    o5 = Opportunity()
    o5.id = 5
    o5.account_id = 5
    o5.name = "TechFab - Warehouse Expansion"
    o5.description = "50,000 sq ft warehouse addition, basic security and fire alarm"
    o5.stage = "Prospecting"
    o5.probability = 10
    o5.bid_date = None
    o5.lv_value = Decimal("95000.00")
    o5.hdd_value = Decimal("0.00")
    o5.owner_id = 1
    o5.assigned_estimator_id = 1
    o5.estimating_status = "Not Started"
    o5.primary_contact_id = 6
    o5.source = "Cold Call"
    o5.last_contacted = today - timedelta(days=10)
    o5.next_followup = today + timedelta(days=1)
    o5.notes = "Initial contact made. Waiting for drawings and timeline."
    o5.created_at = datetime.utcnow() - timedelta(days=12)
    o5.primary_account_id = 5
    o5.related_contact_ids = [6]
    o5.quick_links = []
    opportunities.append(o5)

    # Opp 6: Recently won project
    o6 = Opportunity()
    o6.id = 6
    o6.account_id = 1
    o6.name = "Sunbelt - Retail Plaza Phase 1"
    o6.description = "Strip mall development, security and low-voltage systems"
    o6.stage = "Won"
    o6.probability = 100
    o6.bid_date = today - timedelta(days=20)
    o6.close_date = today - timedelta(days=15)
    o6.lv_value = Decimal("180000.00")
    o6.hdd_value = Decimal("0.00")
    o6.owner_id = 1
    o6.assigned_estimator_id = 1
    o6.estimating_status = "Complete"
    o6.primary_contact_id = 1
    o6.source = "Repeat Customer"
    o6.last_contacted = today - timedelta(days=15)
    o6.notes = "Won at $180k. Project kickoff scheduled for next month."
    o6.created_at = datetime.utcnow() - timedelta(days=60)
    o6.primary_account_id = 1
    o6.related_contact_ids = [1]
    o6.quick_links = ["https://triumph.example/bids/sunbelt-retail-plaza"]
    opportunities.append(o6)

    return opportunities


def get_demo_activities():
    """Return list of demo Activity objects (not saved to DB)."""
    activities = []
    today = date.today()

    # Recent activities
    a1 = Activity()
    a1.id = 1
    a1.account_id = 1
    a1.opportunity_id = 1
    a1.contact_id = 1
    a1.activity_type = "Call"
    a1.subject = "Discussed bid schedule and submittal requirements"
    a1.notes = (
        "Michael confirmed bid deadline is firm. Requested value engineering options."
    )
    a1.activity_date = today - timedelta(days=3)
    a1.duration = 30
    a1.created_by_id = 1
    activities.append(a1)

    a2 = Activity()
    a2.id = 2
    a2.account_id = 2
    a2.opportunity_id = 2
    a2.contact_id = 3
    a2.activity_type = "Email"
    a2.subject = "Bid submission confirmation"
    a2.notes = "Sent final bid via portal. David acknowledged receipt."
    a2.activity_date = today - timedelta(days=1)
    a2.created_by_id = 1
    activities.append(a2)

    a3 = Activity()
    a3.id = 3
    a3.account_id = 1
    a3.opportunity_id = 1
    a3.activity_type = "Meeting"
    a3.subject = "Pre-bid site walk"
    a3.notes = (
        "Attended mandatory site walk. Took photos. Identified MEP coordination issues."
    )
    a3.activity_date = today - timedelta(days=10)
    a3.duration = 120
    a3.created_by_id = 1
    activities.append(a3)

    a4 = Activity()
    a4.id = 4
    a4.account_id = 4
    a4.opportunity_id = 4
    a4.contact_id = 5
    a4.activity_type = "Call"
    a4.subject = "Initial project discussion"
    a4.notes = (
        "Robert provided project overview. Bid documents to be released next week."
    )
    a4.activity_date = today - timedelta(days=7)
    a4.duration = 45
    a4.created_by_id = 1
    activities.append(a4)

    return activities


def get_demo_tasks():
    """Return list of demo Task objects (not saved to DB)."""
    tasks = []
    today = date.today()

    # Upcoming tasks
    t1 = Task()
    t1.id = 1
    t1.opportunity_id = 1
    t1.title = "Request fire alarm quotes from vendors"
    t1.description = "Get quotes from Johnson Controls and Simplex for FA system"
    t1.status = "Open"
    t1.priority = "High"
    t1.due_date = today + timedelta(days=3)
    t1.assigned_to_id = 1
    t1.created_by_id = 1
    tasks.append(t1)

    t2 = Task()
    t2.id = 2
    t2.opportunity_id = 1
    t2.title = "Complete labor estimate for cabling"
    t2.description = "Calculate man-hours for structured cabling installation"
    t2.status = "Open"
    t2.priority = "High"
    t2.due_date = today + timedelta(days=5)
    t2.assigned_to_id = 1
    t2.created_by_id = 1
    tasks.append(t2)

    t3 = Task()
    t3.id = 3
    t3.opportunity_id = 3
    t3.title = "Follow up with Jennifer on drawings"
    t3.description = "Check if updated MEP drawings are available"
    t3.status = "Open"
    t3.priority = "Medium"
    t3.due_date = today + timedelta(days=1)
    t3.assigned_to_id = 1
    t3.created_by_id = 1
    tasks.append(t3)

    t4 = Task()
    t4.id = 4
    t4.opportunity_id = 4
    t4.title = "Schedule site visit for Valley Schools project"
    t4.description = "Coordinate with Robert for site access next week"
    t4.status = "Open"
    t4.priority = "Medium"
    t4.due_date = today + timedelta(days=2)
    t4.assigned_to_id = 1
    t4.created_by_id = 1
    tasks.append(t4)

    t5 = Task()
    t5.id = 5
    t5.opportunity_id = 2
    t5.title = "Prepare bid presentation"
    t5.description = "Create PowerPoint for bid review meeting"
    t5.status = "Complete"
    t5.priority = "High"
    t5.due_date = today - timedelta(days=2)
    t5.completed_date = today - timedelta(days=3)
    t5.assigned_to_id = 1
    t5.created_by_id = 1
    tasks.append(t5)

    return tasks


# Store demo data in memory
_demo_accounts = None
_demo_contacts = None
_demo_opportunities = None
_demo_activities = None
_demo_tasks = None


def init_demo_data():
    """Initialize demo data (call once on startup)."""
    global \
        _demo_accounts, \
        _demo_contacts, \
        _demo_opportunities, \
        _demo_activities, \
        _demo_tasks
    _demo_accounts = get_demo_accounts()
    _demo_contacts = get_demo_contacts()
    _demo_opportunities = get_demo_opportunities()
    _demo_activities = get_demo_activities()
    _demo_tasks = get_demo_tasks()


def get_all_demo_accounts():
    """Get all demo accounts."""
    if _demo_accounts is None:
        init_demo_data()
    return _demo_accounts


def get_all_demo_contacts():
    """Get all demo contacts."""
    if _demo_contacts is None:
        init_demo_data()
    return _demo_contacts


def get_all_demo_opportunities():
    """Get all demo opportunities."""
    if _demo_opportunities is None:
        init_demo_data()
    return _demo_opportunities


def get_all_demo_activities():
    """Get all demo activities."""
    if _demo_activities is None:
        init_demo_data()
    return _demo_activities


def get_all_demo_tasks():
    """Get all demo tasks."""
    if _demo_tasks is None:
        init_demo_data()
    return _demo_tasks


# Demo mode CRUD helpers - for persistent in-memory data during presentations
def get_next_id(entity_list):
    """Get the next available ID for an entity."""
    if not entity_list:
        return 1
    return max(item.id for item in entity_list) + 1


def add_demo_account(account):
    """Add a new account to demo data (persists during session)."""
    if _demo_accounts is None:
        init_demo_data()
    if account.id is None:
        account.id = get_next_id(_demo_accounts)
    _demo_accounts.append(account)
    return account


def update_demo_account(account_id, **updates):
    """Update an account in demo data."""
    if _demo_accounts is None:
        init_demo_data()
    for acc in _demo_accounts:
        if acc.id == account_id:
            for key, value in updates.items():
                setattr(acc, key, value)
            acc.updated_at = datetime.utcnow()
            return acc
    return None


def delete_demo_account(account_id):
    """Delete an account from demo data."""
    global _demo_accounts, _demo_contacts
    if _demo_accounts is None:
        init_demo_data()
    _demo_accounts = [acc for acc in _demo_accounts if acc.id != account_id]
    # Also remove contacts for this account
    _demo_contacts = [c for c in _demo_contacts if c.account_id != account_id]
    return True


def add_demo_contact(contact):
    """Add a new contact to demo data (persists during session)."""
    if _demo_contacts is None:
        init_demo_data()
    if contact.id is None:
        contact.id = get_next_id(_demo_contacts)
    _demo_contacts.append(contact)
    return contact


def update_demo_contact(contact_id, **updates):
    """Update a contact in demo data."""
    if _demo_contacts is None:
        init_demo_data()
    for contact in _demo_contacts:
        if contact.id == contact_id:
            for key, value in updates.items():
                setattr(contact, key, value)
            contact.updated_at = datetime.utcnow()
            return contact
    return None


def delete_demo_contact(contact_id):
    """Delete a contact from demo data."""
    global _demo_contacts
    if _demo_contacts is None:
        init_demo_data()
    _demo_contacts = [c for c in _demo_contacts if c.id != contact_id]
    return True


def add_demo_opportunity(opportunity):
    """Add a new opportunity to demo data (persists during session)."""
    if _demo_opportunities is None:
        init_demo_data()
    if opportunity.id is None:
        opportunity.id = get_next_id(_demo_opportunities)
    _demo_opportunities.append(opportunity)
    return opportunity


def update_demo_opportunity(opportunity_id, **updates):
    """Update an opportunity in demo data."""
    if _demo_opportunities is None:
        init_demo_data()
    for opp in _demo_opportunities:
        if opp.id == opportunity_id:
            for key, value in updates.items():
                setattr(opp, key, value)
            opp.updated_at = datetime.utcnow()
            return opp
    return None


def delete_demo_opportunity(opportunity_id):
    """Delete an opportunity from demo data."""
    global _demo_opportunities
    if _demo_opportunities is None:
        init_demo_data()
    _demo_opportunities = [o for o in _demo_opportunities if o.id != opportunity_id]
    return True
