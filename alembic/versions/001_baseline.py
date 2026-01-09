"""baseline schema - all tables

Revision ID: 001_baseline
Revises:
Create Date: 2026-01-09
"""
from alembic import op
import sqlalchemy as sa

revision = '001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Accounts table
    op.create_table('accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('zip_code', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_accounts_name', 'accounts', ['name'])

    # Contacts table
    op.create_table('contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('title', sa.String(100), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('mobile', sa.String(50), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contacts_account_id', 'contacts', ['account_id'])
    op.create_index('ix_contacts_email', 'contacts', ['email'])

    # Scope Packages table
    op.create_table('scope_packages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Opportunities table
    op.create_table('opportunities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stage', sa.String(50), nullable=False, server_default='Prospecting'),
        sa.Column('probability', sa.Integer(), nullable=True),
        sa.Column('bid_date', sa.Date(), nullable=True),
        sa.Column('close_date', sa.Date(), nullable=True),
        sa.Column('last_contacted', sa.Date(), nullable=True),
        sa.Column('next_followup', sa.Date(), nullable=True),
        sa.Column('estimating_status', sa.String(50), nullable=False, server_default='Not Started'),
        sa.Column('estimating_checklist', sa.JSON(), nullable=True),
        sa.Column('primary_contact_id', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('bid_type', sa.String(50), nullable=True),
        sa.Column('submission_method', sa.String(50), nullable=True),
        sa.Column('bid_time', sa.Time(), nullable=True),
        sa.Column('bid_form_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('bond_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('prevailing_wage', sa.String(20), nullable=True),
        sa.Column('known_risks', sa.Text(), nullable=True),
        sa.Column('project_type', sa.String(50), nullable=True),
        sa.Column('rebid', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('lv_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('hdd_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('gcs', sa.JSON(), nullable=True),
        sa.Column('related_contact_ids', sa.JSON(), nullable=True),
        sa.Column('quick_links', sa.JSON(), nullable=True),
        sa.Column('end_user_account_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['primary_contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['end_user_account_id'], ['accounts.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_opportunities_account_id', 'opportunities', ['account_id'])
    op.create_index('ix_opportunities_stage', 'opportunities', ['stage'])
    op.create_index('ix_opportunities_bid_date', 'opportunities', ['bid_date'])
    op.create_index('ix_opportunities_next_followup', 'opportunities', ['next_followup'])

    # Opportunity-Scope junction table
    op.create_table('opportunity_scopes',
        sa.Column('opportunity_id', sa.Integer(), nullable=False),
        sa.Column('scope_package_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scope_package_id'], ['scope_packages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('opportunity_id', 'scope_package_id')
    )

    # Estimates table
    op.create_table('estimates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('opportunity_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='Draft'),
        sa.Column('labor_total', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('material_total', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('subtotal', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('margin_percent', sa.Numeric(5, 2), nullable=False, server_default='20'),
        sa.Column('margin_amount', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('total', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('opportunity_id', 'version', name='uq_estimate_version')
    )
    op.create_index('ix_estimates_opportunity_id', 'estimates', ['opportunity_id'])

    # Estimate Line Items table
    op.create_table('estimate_line_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('estimate_id', sa.Integer(), nullable=False),
        sa.Column('line_type', sa.String(50), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('quantity', sa.Numeric(15, 4), nullable=False, server_default='1'),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('unit_cost', sa.Numeric(15, 4), nullable=False, server_default='0'),
        sa.Column('total', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['estimate_id'], ['estimates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_estimate_line_items_estimate_id', 'estimate_line_items', ['estimate_id'])

    # Activities table
    op.create_table('activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('opportunity_id', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.String(50), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('activity_date', sa.DateTime(), nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_activities_opportunity_id', 'activities', ['opportunity_id'])
    op.create_index('ix_activities_activity_date', 'activities', ['activity_date'])

    # Tasks table
    op.create_table('tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('opportunity_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('priority', sa.String(20), nullable=False, server_default='Medium'),
        sa.Column('status', sa.String(20), nullable=False, server_default='Open'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tasks_opportunity_id', 'tasks', ['opportunity_id'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])
    op.create_index('ix_tasks_due_date', 'tasks', ['due_date'])

    # Documents table
    op.create_table('documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('opportunity_id', sa.Integer(), nullable=True),
        sa.Column('estimate_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('document_type', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['estimate_id'], ['estimates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_documents_opportunity_id', 'documents', ['opportunity_id'])

    # Vendors table
    op.create_table('vendors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('contact_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('specialty', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Vendor Quote Requests table
    op.create_table('vendor_quote_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('opportunity_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='Pending'),
        sa.Column('sent_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('received_date', sa.Date(), nullable=True),
        sa.Column('quote_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vendor_quote_requests_opportunity_id', 'vendor_quote_requests', ['opportunity_id'])

    # Meeting Briefs table
    op.create_table('meeting_briefs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('brief_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_meeting_briefs_account_id', 'meeting_briefs', ['account_id'])


def downgrade():
    op.drop_index('ix_meeting_briefs_account_id', table_name='meeting_briefs')
    op.drop_table('meeting_briefs')
    op.drop_index('ix_vendor_quote_requests_opportunity_id', table_name='vendor_quote_requests')
    op.drop_table('vendor_quote_requests')
    op.drop_table('vendors')
    op.drop_index('ix_documents_opportunity_id', table_name='documents')
    op.drop_table('documents')
    op.drop_index('ix_tasks_due_date', table_name='tasks')
    op.drop_index('ix_tasks_status', table_name='tasks')
    op.drop_index('ix_tasks_opportunity_id', table_name='tasks')
    op.drop_table('tasks')
    op.drop_index('ix_activities_activity_date', table_name='activities')
    op.drop_index('ix_activities_opportunity_id', table_name='activities')
    op.drop_table('activities')
    op.drop_index('ix_estimate_line_items_estimate_id', table_name='estimate_line_items')
    op.drop_table('estimate_line_items')
    op.drop_index('ix_estimates_opportunity_id', table_name='estimates')
    op.drop_table('estimates')
    op.drop_table('opportunity_scopes')
    op.drop_index('ix_opportunities_next_followup', table_name='opportunities')
    op.drop_index('ix_opportunities_bid_date', table_name='opportunities')
    op.drop_index('ix_opportunities_stage', table_name='opportunities')
    op.drop_index('ix_opportunities_account_id', table_name='opportunities')
    op.drop_table('opportunities')
    op.drop_table('scope_packages')
    op.drop_index('ix_contacts_email', table_name='contacts')
    op.drop_index('ix_contacts_account_id', table_name='contacts')
    op.drop_table('contacts')
    op.drop_index('ix_accounts_name', table_name='accounts')
    op.drop_table('accounts')
