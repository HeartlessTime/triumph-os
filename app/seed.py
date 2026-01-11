"""
Seed data for RevenueOS development and testing.

Run with: python -m app.seed
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from app.database import SessionLocal, engine, Base
from app.models import (
    Account,
    Contact,
    ScopePackage,
    Opportunity,
    OpportunityScope,
    Estimate,
    EstimateLineItem,
    Activity,
    Task,
    Vendor,
    User,
)
from app.services.followup import calculate_next_followup
from app.services.estimate import recalculate_estimate


def seed_database():
    """Seed the database with sample data."""
    db = SessionLocal()
    # Ensure tables exist (useful for SQLite dev when migrations haven't been run)
    Base.metadata.create_all(bind=engine)

    try:
        print("Seeding database...")

        # Create Users (needed for owner/estimator assignment)
        print("  Creating users...")
        users = [
            User(
                email="garrett@triumph.com",
                password_hash="placeholder",
                full_name="Garrett Garcia",
                role="Admin",
                is_active=True,
            ),
            User(
                email="sales@triumph.com",
                password_hash="placeholder",
                full_name="Sarah Sales",
                role="Sales",
                is_active=True,
            ),
            User(
                email="estimator@triumph.com",
                password_hash="placeholder",
                full_name="Eric Estimator",
                role="Estimator",
                is_active=True,
            ),
        ]
        db.add_all(users)
        db.flush()

        # Create Low-Voltage Scope Packages (replace generic scopes for LV contractors)
        print("  Creating low-voltage scope packages...")
        lv_scopes = [
            "Horizontal Cabling (Copper)",
            "Backbone Cabling (Fiber/Copper)",
            "Site / Campus Fiber",
            "IDF / MDF Closet Buildout",
            "Security / Access Control",
            "Cameras / Surveillance",
            "Wireless / Access Points",
            "AV / Paging / Intercom",
            "Other",
        ]
        scopes = []
        for i, name in enumerate(lv_scopes, start=1):
            scopes.append(ScopePackage(name=name, description=None, sort_order=i))
        db.add_all(scopes)
        db.flush()

        # Create Vendors
        print("  Creating vendors...")
        vendors = [
            Vendor(
                name="ABC Electrical Supply",
                contact_name="John Smith",
                email="john@abcelectric.com",
                phone="555-111-2222",
                specialty="Electrical",
            ),
            Vendor(
                name="Quality Plumbing Co",
                contact_name="Jane Doe",
                email="jane@qualityplumb.com",
                phone="555-222-3333",
                specialty="Plumbing",
            ),
            Vendor(
                name="Steel Masters Inc",
                contact_name="Bob Steel",
                email="bob@steelmasters.com",
                phone="555-333-4444",
                specialty="Steel",
            ),
            Vendor(
                name="Concrete Solutions",
                contact_name="Mary Mason",
                email="mary@concretesol.com",
                phone="555-444-5555",
                specialty="Concrete",
            ),
        ]
        db.add_all(vendors)
        db.flush()

        # Create Accounts
        print("  Creating accounts...")
        accounts = [
            Account(
                name="Acme Corporation",
                industry="Manufacturing",
                website="https://acme.example.com",
                phone="555-100-1000",
                address="100 Industrial Way",
                city="Austin",
                state="TX",
                zip_code="78701",
            ),
            Account(
                name="TechStart Inc",
                industry="Technology",
                website="https://techstart.example.com",
                phone="555-200-2000",
                address="200 Innovation Blvd",
                city="Austin",
                state="TX",
                zip_code="78702",
            ),
            Account(
                name="City Hospital",
                industry="Healthcare",
                website="https://cityhospital.example.com",
                phone="555-300-3000",
                address="300 Medical Center Dr",
                city="Round Rock",
                state="TX",
                zip_code="78664",
            ),
            Account(
                name="Summit Schools District",
                industry="Education",
                phone="555-400-4000",
                address="400 Education Lane",
                city="Cedar Park",
                state="TX",
                zip_code="78613",
            ),
        ]
        db.add_all(accounts)
        db.flush()

        # Create Contacts
        print("  Creating contacts...")
        contacts = [
            # Acme contacts
            Contact(
                account_id=accounts[0].id,
                first_name="Robert",
                last_name="Johnson",
                title="Facilities Director",
                email="rjohnson@acme.example.com",
                phone="555-100-1001",
                is_primary=True,
            ),
            Contact(
                account_id=accounts[0].id,
                first_name="Lisa",
                last_name="Williams",
                title="Project Manager",
                email="lwilliams@acme.example.com",
                phone="555-100-1002",
            ),
            # TechStart contacts
            Contact(
                account_id=accounts[1].id,
                first_name="David",
                last_name="Chen",
                title="CEO",
                email="dchen@techstart.example.com",
                phone="555-200-2001",
                is_primary=True,
            ),
            Contact(
                account_id=accounts[1].id,
                first_name="Emily",
                last_name="Park",
                title="Operations Manager",
                email="epark@techstart.example.com",
                phone="555-200-2002",
            ),
            # Hospital contacts
            Contact(
                account_id=accounts[2].id,
                first_name="Dr. James",
                last_name="Wilson",
                title="Chief Administrator",
                email="jwilson@cityhospital.example.com",
                phone="555-300-3001",
                is_primary=True,
            ),
            # School contacts
            Contact(
                account_id=accounts[3].id,
                first_name="Patricia",
                last_name="Davis",
                title="Superintendent",
                email="pdavis@summit.example.com",
                phone="555-400-4001",
                is_primary=True,
            ),
        ]
        db.add_all(contacts)
        db.flush()

        # Create Opportunities
        print("  Creating opportunities...")
        today = date.today()

        opps = [
            # Acme - Prospecting
            Opportunity(
                account_id=accounts[0].id,
                name="Warehouse Expansion Phase 1",
                description="Expand existing warehouse by 50,000 sq ft including new loading docks",
                stage="Prospecting",
                lv_value=Decimal("850000"),
                hdd_value=None,
                bid_date=today + timedelta(days=45),
                primary_contact_id=contacts[0].id,
                source="Referral",
                last_contacted=today - timedelta(days=3),
                estimating_status="Not Started",
                estimating_checklist=Opportunity.DEFAULT_CHECKLIST.copy(),
            ),
            # TechStart - Bid Sent
            Opportunity(
                account_id=accounts[1].id,
                name="Office Renovation",
                description="Complete renovation of 3rd floor office space including new HVAC",
                stage="Bid Sent",
                lv_value=Decimal("425000"),
                hdd_value=None,
                bid_date=today + timedelta(days=7),
                primary_contact_id=contacts[2].id,
                source="Website",
                last_contacted=today - timedelta(days=1),
                estimating_status="Complete",
                estimating_checklist=[
                    {"item": "Review bid documents", "done": True},
                    {"item": "Site visit scheduled", "done": True},
                    {"item": "Takeoff complete", "done": True},
                    {"item": "Vendor quotes received", "done": True},
                    {"item": "Labor estimate complete", "done": True},
                    {"item": "Management review", "done": True},
                ],
            ),
            # Hospital - Negotiation
            Opportunity(
                account_id=accounts[2].id,
                name="Emergency Room Expansion",
                description="Add 10 new emergency bays with full medical infrastructure",
                stage="Negotiation",
                lv_value=Decimal("2150000"),
                hdd_value=None,
                bid_date=today - timedelta(days=5),
                primary_contact_id=contacts[4].id,
                source="Repeat Customer",
                last_contacted=today,
                estimating_status="Complete",
                estimating_checklist=[
                    {"item": "Review bid documents", "done": True},
                    {"item": "Site visit scheduled", "done": True},
                    {"item": "Takeoff complete", "done": True},
                    {"item": "Vendor quotes received", "done": True},
                    {"item": "Labor estimate complete", "done": True},
                    {"item": "Management review", "done": True},
                ],
            ),
            # School - Proposal
            Opportunity(
                account_id=accounts[3].id,
                name="New Gymnasium Construction",
                description="Build new 25,000 sq ft gymnasium with locker rooms",
                stage="Proposal",
                lv_value=Decimal("1800000"),
                hdd_value=None,
                bid_date=today + timedelta(days=21),
                primary_contact_id=contacts[5].id,
                source="Cold Call",
                last_contacted=today - timedelta(days=7),
                estimating_status="In Progress",
                estimating_checklist=[
                    {"item": "Review bid documents", "done": True},
                    {"item": "Site visit scheduled", "done": True},
                    {"item": "Takeoff complete", "done": True},
                    {"item": "Vendor quotes received", "done": False},
                    {"item": "Labor estimate complete", "done": False},
                    {"item": "Management review", "done": False},
                ],
            ),
            # Won opportunity
            Opportunity(
                account_id=accounts[0].id,
                name="Parking Lot Expansion",
                description="Add 100 parking spaces with lighting",
                stage="Won",
                lv_value=Decimal("175000"),
                hdd_value=None,
                bid_date=today - timedelta(days=30),
                close_date=today - timedelta(days=15),
                primary_contact_id=contacts[0].id,
                source="Repeat Customer",
                last_contacted=today - timedelta(days=15),
                estimating_status="Complete",
                estimating_checklist=[
                    {"item": "Review bid documents", "done": True},
                    {"item": "Site visit scheduled", "done": True},
                    {"item": "Takeoff complete", "done": True},
                    {"item": "Vendor quotes received", "done": True},
                    {"item": "Labor estimate complete", "done": True},
                    {"item": "Management review", "done": True},
                ],
            ),
        ]

        # Calculate next_followup for each opportunity
        for opp in opps:
            opp.next_followup = calculate_next_followup(
                stage=opp.stage,
                last_contacted=opp.last_contacted,
                bid_date=opp.bid_date,
                today=today,
            )

        db.add_all(opps)
        db.flush()

        # Add scope packages to opportunities
        print("  Adding scope packages to opportunities...")
        scope_links = [
            OpportunityScope(opportunity_id=opps[0].id, scope_package_id=scopes[0].id),
            OpportunityScope(opportunity_id=opps[0].id, scope_package_id=scopes[4].id),
            OpportunityScope(opportunity_id=opps[0].id, scope_package_id=scopes[5].id),
            OpportunityScope(opportunity_id=opps[1].id, scope_package_id=scopes[1].id),
            OpportunityScope(opportunity_id=opps[1].id, scope_package_id=scopes[3].id),
            OpportunityScope(opportunity_id=opps[1].id, scope_package_id=scopes[6].id),
            OpportunityScope(opportunity_id=opps[2].id, scope_package_id=scopes[0].id),
            OpportunityScope(opportunity_id=opps[2].id, scope_package_id=scopes[1].id),
            OpportunityScope(opportunity_id=opps[2].id, scope_package_id=scopes[2].id),
            OpportunityScope(opportunity_id=opps[2].id, scope_package_id=scopes[3].id),
            OpportunityScope(opportunity_id=opps[3].id, scope_package_id=scopes[0].id),
            OpportunityScope(opportunity_id=opps[3].id, scope_package_id=scopes[4].id),
            OpportunityScope(opportunity_id=opps[3].id, scope_package_id=scopes[5].id),
            OpportunityScope(opportunity_id=opps[4].id, scope_package_id=scopes[4].id),
        ]
        db.add_all(scope_links)
        db.flush()

        # Create Estimates
        print("  Creating estimates...")
        estimates = [
            # TechStart Office Renovation - 2 versions
            Estimate(
                opportunity_id=opps[1].id,
                version=1,
                name="Initial Estimate",
                status="Revised",
                margin_percent=Decimal("20"),
            ),
            Estimate(
                opportunity_id=opps[1].id,
                version=2,
                name="Final Bid",
                status="Sent",
                margin_percent=Decimal("22"),
            ),
            # Hospital ER Expansion
            Estimate(
                opportunity_id=opps[2].id,
                version=1,
                name="Full Scope",
                status="Approved",
                margin_percent=Decimal("18"),
            ),
        ]
        db.add_all(estimates)
        db.flush()

        # Create Line Items
        print("  Creating estimate line items...")
        line_items = [
            # TechStart v1
            EstimateLineItem(
                estimate_id=estimates[0].id,
                line_type="labor",
                description="Demolition crew",
                quantity=Decimal("120"),
                unit="hour",
                unit_cost=Decimal("65"),
                sort_order=1,
            ),
            EstimateLineItem(
                estimate_id=estimates[0].id,
                line_type="labor",
                description="Electrical installation",
                quantity=Decimal("200"),
                unit="hour",
                unit_cost=Decimal("85"),
                sort_order=2,
            ),
            EstimateLineItem(
                estimate_id=estimates[0].id,
                line_type="labor",
                description="HVAC installation",
                quantity=Decimal("160"),
                unit="hour",
                unit_cost=Decimal("90"),
                sort_order=3,
            ),
            EstimateLineItem(
                estimate_id=estimates[0].id,
                line_type="material",
                description="Electrical materials",
                quantity=Decimal("1"),
                unit="lot",
                unit_cost=Decimal("45000"),
                sort_order=4,
            ),
            EstimateLineItem(
                estimate_id=estimates[0].id,
                line_type="material",
                description="HVAC units and ductwork",
                quantity=Decimal("1"),
                unit="lot",
                unit_cost=Decimal("75000"),
                sort_order=5,
            ),
            # TechStart v2 (adjusted)
            EstimateLineItem(
                estimate_id=estimates[1].id,
                line_type="labor",
                description="Demolition crew",
                quantity=Decimal("100"),
                unit="hour",
                unit_cost=Decimal("65"),
                sort_order=1,
            ),
            EstimateLineItem(
                estimate_id=estimates[1].id,
                line_type="labor",
                description="Electrical installation",
                quantity=Decimal("180"),
                unit="hour",
                unit_cost=Decimal("85"),
                sort_order=2,
            ),
            EstimateLineItem(
                estimate_id=estimates[1].id,
                line_type="labor",
                description="HVAC installation",
                quantity=Decimal("140"),
                unit="hour",
                unit_cost=Decimal("90"),
                sort_order=3,
            ),
            EstimateLineItem(
                estimate_id=estimates[1].id,
                line_type="labor",
                description="Drywall and finishing",
                quantity=Decimal("240"),
                unit="hour",
                unit_cost=Decimal("55"),
                sort_order=4,
            ),
            EstimateLineItem(
                estimate_id=estimates[1].id,
                line_type="material",
                description="Electrical materials",
                quantity=Decimal("1"),
                unit="lot",
                unit_cost=Decimal("42000"),
                sort_order=5,
            ),
            EstimateLineItem(
                estimate_id=estimates[1].id,
                line_type="material",
                description="HVAC units and ductwork",
                quantity=Decimal("1"),
                unit="lot",
                unit_cost=Decimal("72000"),
                sort_order=6,
            ),
            EstimateLineItem(
                estimate_id=estimates[1].id,
                line_type="material",
                description="Drywall and paint",
                quantity=Decimal("15000"),
                unit="sf",
                unit_cost=Decimal("4.50"),
                sort_order=7,
            ),
            # Hospital
            EstimateLineItem(
                estimate_id=estimates[2].id,
                line_type="labor",
                description="General construction",
                quantity=Decimal("2000"),
                unit="hour",
                unit_cost=Decimal("75"),
                sort_order=1,
            ),
            EstimateLineItem(
                estimate_id=estimates[2].id,
                line_type="labor",
                description="Electrical",
                quantity=Decimal("800"),
                unit="hour",
                unit_cost=Decimal("90"),
                sort_order=2,
            ),
            EstimateLineItem(
                estimate_id=estimates[2].id,
                line_type="labor",
                description="Plumbing",
                quantity=Decimal("600"),
                unit="hour",
                unit_cost=Decimal("85"),
                sort_order=3,
            ),
            EstimateLineItem(
                estimate_id=estimates[2].id,
                line_type="labor",
                description="Medical gas systems",
                quantity=Decimal("400"),
                unit="hour",
                unit_cost=Decimal("110"),
                sort_order=4,
            ),
            EstimateLineItem(
                estimate_id=estimates[2].id,
                line_type="material",
                description="Construction materials",
                quantity=Decimal("1"),
                unit="lot",
                unit_cost=Decimal("450000"),
                sort_order=5,
            ),
            EstimateLineItem(
                estimate_id=estimates[2].id,
                line_type="material",
                description="Electrical systems",
                quantity=Decimal("1"),
                unit="lot",
                unit_cost=Decimal("180000"),
                sort_order=6,
            ),
            EstimateLineItem(
                estimate_id=estimates[2].id,
                line_type="material",
                description="Medical equipment infrastructure",
                quantity=Decimal("1"),
                unit="lot",
                unit_cost=Decimal("320000"),
                sort_order=7,
            ),
        ]
        db.add_all(line_items)
        db.flush()

        # Recalculate estimate totals
        for est in estimates:
            recalculate_estimate(est)

        # Create Activities
        print("  Creating activities...")
        activities = [
            Activity(
                opportunity_id=opps[0].id,
                activity_type="call",
                subject="Initial discovery call",
                description="Discussed project scope and timeline",
                activity_date=datetime.now() - timedelta(days=3),
                contact_id=contacts[0].id,
            ),
            Activity(
                opportunity_id=opps[1].id,
                activity_type="meeting",
                subject="Site walkthrough",
                description="Toured the 3rd floor with Emily",
                activity_date=datetime.now() - timedelta(days=10),
                contact_id=contacts[3].id,
            ),
            Activity(
                opportunity_id=opps[1].id,
                activity_type="email",
                subject="Sent proposal",
                description="Emailed final proposal v2",
                activity_date=datetime.now() - timedelta(days=1),
                contact_id=contacts[2].id,
            ),
            Activity(
                opportunity_id=opps[2].id,
                activity_type="meeting",
                subject="Contract negotiation",
                description="Discussed final terms with Dr. Wilson",
                activity_date=datetime.now(),
                contact_id=contacts[4].id,
            ),
            Activity(
                opportunity_id=opps[3].id,
                activity_type="site_visit",
                subject="Site survey",
                description="Completed site measurements and soil analysis",
                activity_date=datetime.now() - timedelta(days=5),
                contact_id=contacts[5].id,
            ),
        ]
        db.add_all(activities)
        db.flush()

        # Create Tasks
        print("  Creating tasks...")
        tasks = [
            Task(
                opportunity_id=opps[0].id,
                title="Schedule site visit",
                description="Coordinate with facilities for site access",
                due_date=today + timedelta(days=3),
                priority="High",
            ),
            Task(
                opportunity_id=opps[0].id,
                title="Request drawings",
                description="Get existing building drawings from Acme",
                due_date=today + timedelta(days=5),
                priority="Medium",
            ),
            Task(
                opportunity_id=opps[1].id,
                title="Follow up on proposal",
                description="Check if they have questions on v2",
                due_date=today + timedelta(days=2),
                priority="High",
            ),
            Task(
                opportunity_id=opps[2].id,
                title="Finalize contract",
                description="Send final contract for signature",
                due_date=today + timedelta(days=1),
                priority="Urgent",
            ),
            Task(
                opportunity_id=opps[3].id,
                title="Get steel quotes",
                description="Request quotes from 3 steel vendors",
                due_date=today + timedelta(days=7),
                priority="Medium",
            ),
        ]
        db.add_all(tasks)

        db.commit()
        print("Database seeding complete.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
