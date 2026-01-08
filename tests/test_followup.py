"""
Unit tests for follow-up calculation service.

Tests the rules:
1. Stage = Prospecting => next_followup = last_contacted + 14 days
2. Stage = Bid Sent => next_followup = last_contacted + 14 days
3. If bid date has passed and status not Won/Lost => next_followup = today + 2 business days
"""

import pytest
from datetime import date, timedelta
from app.services.followup import (
    calculate_next_followup,
    add_business_days,
    should_recalculate_followup,
    get_followup_status,
)


class TestAddBusinessDays:
    """Tests for add_business_days function."""
    
    def test_add_business_days_weekday_start(self):
        """Adding business days starting from Monday."""
        # Monday Jan 15, 2024
        start = date(2024, 1, 15)
        result = add_business_days(start, 2)
        # Should be Wednesday Jan 17, 2024
        assert result == date(2024, 1, 17)
    
    def test_add_business_days_spans_weekend(self):
        """Adding business days that span a weekend."""
        # Thursday Jan 18, 2024
        start = date(2024, 1, 18)
        result = add_business_days(start, 2)
        # Friday + skip weekend + Monday = Monday Jan 22, 2024
        assert result == date(2024, 1, 22)
    
    def test_add_business_days_from_friday(self):
        """Adding business days starting from Friday."""
        # Friday Jan 19, 2024
        start = date(2024, 1, 19)
        result = add_business_days(start, 1)
        # Should be Monday Jan 22, 2024
        assert result == date(2024, 1, 22)
    
    def test_add_business_days_from_saturday(self):
        """Adding business days starting from Saturday."""
        # Saturday Jan 20, 2024
        start = date(2024, 1, 20)
        result = add_business_days(start, 1)
        # Should be Monday Jan 22, 2024
        assert result == date(2024, 1, 22)
    
    def test_add_zero_business_days(self):
        """Adding zero business days returns same date."""
        start = date(2024, 1, 15)
        result = add_business_days(start, 0)
        assert result == start


class TestCalculateNextFollowup:
    """Tests for calculate_next_followup function."""
    
    def test_prospecting_stage_with_last_contacted(self):
        """Prospecting stage should add 14 days to last_contacted."""
        today = date(2024, 1, 15)
        last_contacted = date(2024, 1, 10)
        
        result = calculate_next_followup(
            stage='Prospecting',
            last_contacted=last_contacted,
            bid_date=None,
            today=today
        )
        
        assert result == date(2024, 1, 24)  # Jan 10 + 14 days
    
    def test_prospecting_stage_without_last_contacted(self):
        """Prospecting without last_contacted uses today."""
        today = date(2024, 1, 15)
        
        result = calculate_next_followup(
            stage='Prospecting',
            last_contacted=None,
            bid_date=None,
            today=today
        )
        
        assert result == date(2024, 1, 29)  # Today + 14 days
    
    def test_bid_sent_stage(self):
        """Bid Sent stage should add 14 days to last_contacted."""
        today = date(2024, 1, 15)
        last_contacted = date(2024, 1, 10)
        
        result = calculate_next_followup(
            stage='Bid Sent',
            last_contacted=last_contacted,
            bid_date=date(2024, 2, 1),
            today=today
        )
        
        assert result == date(2024, 1, 24)  # Jan 10 + 14 days
    
    def test_past_bid_date_not_won_lost(self):
        """Past bid date should trigger urgent follow-up (2 business days)."""
        today = date(2024, 1, 15)  # Monday
        last_contacted = date(2024, 1, 10)
        bid_date = date(2024, 1, 12)  # Already passed
        
        result = calculate_next_followup(
            stage='Bid Sent',
            last_contacted=last_contacted,
            bid_date=bid_date,
            today=today
        )
        
        # Should be today + 2 business days = Wednesday Jan 17
        assert result == date(2024, 1, 17)
    
    def test_past_bid_date_on_friday(self):
        """Past bid date on Friday should skip weekend."""
        today = date(2024, 1, 19)  # Friday
        bid_date = date(2024, 1, 18)  # Thursday, already passed
        
        result = calculate_next_followup(
            stage='Proposal',
            last_contacted=date(2024, 1, 10),
            bid_date=bid_date,
            today=today
        )
        
        # Friday + 2 business days = Tuesday Jan 23
        assert result == date(2024, 1, 23)
    
    def test_won_stage_no_followup(self):
        """Won stage should return None (no follow-up needed)."""
        result = calculate_next_followup(
            stage='Won',
            last_contacted=date(2024, 1, 10),
            bid_date=date(2024, 1, 5),  # Past bid date
            today=date(2024, 1, 15)
        )
        
        assert result is None
    
    def test_lost_stage_no_followup(self):
        """Lost stage should return None."""
        result = calculate_next_followup(
            stage='Lost',
            last_contacted=date(2024, 1, 10),
            bid_date=date(2024, 1, 5),
            today=date(2024, 1, 15)
        )
        
        assert result is None
    
    def test_negotiation_stage_future_bid_date(self):
        """Non-special stage with future bid date returns None."""
        today = date(2024, 1, 15)
        bid_date = date(2024, 2, 1)  # Future
        
        result = calculate_next_followup(
            stage='Negotiation',
            last_contacted=date(2024, 1, 10),
            bid_date=bid_date,
            today=today
        )
        
        # Negotiation isn't Prospecting or Bid Sent, so no auto follow-up
        assert result is None
    
    def test_past_bid_date_takes_priority(self):
        """Past bid date rule takes priority over stage rules."""
        today = date(2024, 1, 15)  # Monday
        last_contacted = date(2024, 1, 1)  # Would give Jan 15 for Prospecting
        bid_date = date(2024, 1, 10)  # Past
        
        result = calculate_next_followup(
            stage='Prospecting',
            last_contacted=last_contacted,
            bid_date=bid_date,
            today=today
        )
        
        # Past bid date rule: today + 2 business days = Jan 17
        assert result == date(2024, 1, 17)


class TestShouldRecalculateFollowup:
    """Tests for should_recalculate_followup function."""
    
    def test_stage_change_triggers_recalculation(self):
        """Changing stage should trigger recalculation."""
        result = should_recalculate_followup(
            old_stage='Prospecting',
            new_stage='Proposal',
            old_last_contacted=date(2024, 1, 10),
            new_last_contacted=date(2024, 1, 10),
            old_bid_date=None,
            new_bid_date=None
        )
        assert result is True
    
    def test_last_contacted_change_triggers_recalculation(self):
        """Changing last_contacted should trigger recalculation."""
        result = should_recalculate_followup(
            old_stage='Prospecting',
            new_stage='Prospecting',
            old_last_contacted=date(2024, 1, 10),
            new_last_contacted=date(2024, 1, 15),
            old_bid_date=None,
            new_bid_date=None
        )
        assert result is True
    
    def test_bid_date_change_triggers_recalculation(self):
        """Changing bid_date should trigger recalculation."""
        result = should_recalculate_followup(
            old_stage='Bid Sent',
            new_stage='Bid Sent',
            old_last_contacted=date(2024, 1, 10),
            new_last_contacted=date(2024, 1, 10),
            old_bid_date=date(2024, 2, 1),
            new_bid_date=date(2024, 2, 15)
        )
        assert result is True
    
    def test_no_change_no_recalculation(self):
        """No changes should not trigger recalculation."""
        result = should_recalculate_followup(
            old_stage='Prospecting',
            new_stage='Prospecting',
            old_last_contacted=date(2024, 1, 10),
            new_last_contacted=date(2024, 1, 10),
            old_bid_date=None,
            new_bid_date=None
        )
        assert result is False


class TestGetFollowupStatus:
    """Tests for get_followup_status function."""
    
    def test_overdue_status(self):
        """Past follow-up date should be overdue."""
        today = date(2024, 1, 15)
        next_followup = date(2024, 1, 10)  # 5 days ago
        
        result = get_followup_status(next_followup, today)
        
        assert result['status'] == 'overdue'
        assert result['days_until'] == -5
        assert 'danger' in result['css_class']
    
    def test_due_today_status(self):
        """Follow-up today should be due_today."""
        today = date(2024, 1, 15)
        next_followup = date(2024, 1, 15)
        
        result = get_followup_status(next_followup, today)
        
        assert result['status'] == 'due_today'
        assert result['days_until'] == 0
        assert 'warning' in result['css_class']
    
    def test_upcoming_soon_status(self):
        """Follow-up in 1-3 days should be upcoming with info class."""
        today = date(2024, 1, 15)
        next_followup = date(2024, 1, 17)  # 2 days
        
        result = get_followup_status(next_followup, today)
        
        assert result['status'] == 'upcoming'
        assert result['days_until'] == 2
        assert 'info' in result['css_class']
    
    def test_upcoming_later_status(self):
        """Follow-up more than 3 days out should be upcoming with no special class."""
        today = date(2024, 1, 15)
        next_followup = date(2024, 1, 25)  # 10 days
        
        result = get_followup_status(next_followup, today)
        
        assert result['status'] == 'upcoming'
        assert result['days_until'] == 10
        assert result['css_class'] == ''
    
    def test_no_followup_status(self):
        """No follow-up date should return none status."""
        result = get_followup_status(None)
        
        assert result['status'] == 'none'
        assert result['days_until'] is None
