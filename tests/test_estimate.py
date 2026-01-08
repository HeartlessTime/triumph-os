"""
Unit tests for estimate calculation service.

Tests:
- Line item total calculation (qty × unit_cost)
- Estimate rollup totals (labor, material, subtotal)
- Margin calculation
- Grand total calculation
"""

import pytest
from decimal import Decimal
from app.services.estimate import (
    calculate_line_item_total,
    calculate_estimate_totals,
)


class TestCalculateLineItemTotal:
    """Tests for line item total calculation."""
    
    def test_basic_calculation(self):
        """Basic quantity × unit_cost calculation."""
        result = calculate_line_item_total(
            quantity=Decimal('10'),
            unit_cost=Decimal('25.50')
        )
        assert result == Decimal('255.00')
    
    def test_fractional_quantity(self):
        """Calculation with fractional quantity."""
        result = calculate_line_item_total(
            quantity=Decimal('2.5'),
            unit_cost=Decimal('100')
        )
        assert result == Decimal('250.00')
    
    def test_fractional_cost(self):
        """Calculation with fractional unit cost."""
        result = calculate_line_item_total(
            quantity=Decimal('3'),
            unit_cost=Decimal('33.33')
        )
        assert result == Decimal('99.99')
    
    def test_rounding(self):
        """Result should be rounded to 2 decimal places."""
        result = calculate_line_item_total(
            quantity=Decimal('3'),
            unit_cost=Decimal('33.333')
        )
        # 3 × 33.333 = 99.999, rounded to 100.00
        assert result == Decimal('100.00')
    
    def test_zero_quantity(self):
        """Zero quantity should return zero."""
        result = calculate_line_item_total(
            quantity=Decimal('0'),
            unit_cost=Decimal('100')
        )
        assert result == Decimal('0')
    
    def test_zero_cost(self):
        """Zero cost should return zero."""
        result = calculate_line_item_total(
            quantity=Decimal('10'),
            unit_cost=Decimal('0')
        )
        assert result == Decimal('0')
    
    def test_none_quantity(self):
        """None quantity should return zero."""
        result = calculate_line_item_total(
            quantity=None,
            unit_cost=Decimal('100')
        )
        assert result == Decimal('0')
    
    def test_none_cost(self):
        """None cost should return zero."""
        result = calculate_line_item_total(
            quantity=Decimal('10'),
            unit_cost=None
        )
        assert result == Decimal('0')
    
    def test_large_values(self):
        """Large values should calculate correctly."""
        result = calculate_line_item_total(
            quantity=Decimal('10000'),
            unit_cost=Decimal('999.99')
        )
        assert result == Decimal('9999900.00')


class TestCalculateEstimateTotals:
    """Tests for estimate totals calculation."""
    
    def test_basic_totals(self):
        """Basic totals calculation with labor and materials."""
        labor_items = [
            {'total': Decimal('1000')},
            {'total': Decimal('500')},
        ]
        material_items = [
            {'total': Decimal('2000')},
            {'total': Decimal('1500')},
        ]
        
        result = calculate_estimate_totals(
            labor_items=labor_items,
            material_items=material_items,
            margin_percent=Decimal('20')
        )
        
        assert result['labor_total'] == Decimal('1500.00')
        assert result['material_total'] == Decimal('3500.00')
        assert result['subtotal'] == Decimal('5000.00')
        
        # Margin calculation: total = subtotal / (1 - 0.20) = 5000 / 0.80 = 6250
        assert result['total'] == Decimal('6250.00')
        assert result['margin_amount'] == Decimal('1250.00')
    
    def test_zero_margin(self):
        """Zero margin should return subtotal as total."""
        labor_items = [{'total': Decimal('1000')}]
        material_items = [{'total': Decimal('2000')}]
        
        result = calculate_estimate_totals(
            labor_items=labor_items,
            material_items=material_items,
            margin_percent=Decimal('0')
        )
        
        assert result['subtotal'] == Decimal('3000.00')
        assert result['total'] == Decimal('3000.00')
        assert result['margin_amount'] == Decimal('0.00')
    
    def test_high_margin(self):
        """High margin should calculate correctly."""
        labor_items = [{'total': Decimal('1000')}]
        material_items = []
        
        result = calculate_estimate_totals(
            labor_items=labor_items,
            material_items=material_items,
            margin_percent=Decimal('50')
        )
        
        # total = 1000 / (1 - 0.50) = 1000 / 0.50 = 2000
        assert result['subtotal'] == Decimal('1000.00')
        assert result['total'] == Decimal('2000.00')
        assert result['margin_amount'] == Decimal('1000.00')
    
    def test_empty_labor(self):
        """Empty labor items should give zero labor total."""
        material_items = [{'total': Decimal('1000')}]
        
        result = calculate_estimate_totals(
            labor_items=[],
            material_items=material_items,
            margin_percent=Decimal('20')
        )
        
        assert result['labor_total'] == Decimal('0.00')
        assert result['material_total'] == Decimal('1000.00')
        assert result['subtotal'] == Decimal('1000.00')
    
    def test_empty_materials(self):
        """Empty material items should give zero material total."""
        labor_items = [{'total': Decimal('1000')}]
        
        result = calculate_estimate_totals(
            labor_items=labor_items,
            material_items=[],
            margin_percent=Decimal('20')
        )
        
        assert result['labor_total'] == Decimal('1000.00')
        assert result['material_total'] == Decimal('0.00')
        assert result['subtotal'] == Decimal('1000.00')
    
    def test_both_empty(self):
        """Both empty should give all zeros."""
        result = calculate_estimate_totals(
            labor_items=[],
            material_items=[],
            margin_percent=Decimal('20')
        )
        
        assert result['labor_total'] == Decimal('0.00')
        assert result['material_total'] == Decimal('0.00')
        assert result['subtotal'] == Decimal('0.00')
        assert result['total'] == Decimal('0.00')
        assert result['margin_amount'] == Decimal('0.00')
    
    def test_items_with_none_totals(self):
        """Items with None totals should be treated as zero."""
        labor_items = [
            {'total': Decimal('1000')},
            {'total': None},
        ]
        material_items = [
            {'total': None},
            {'total': Decimal('500')},
        ]
        
        result = calculate_estimate_totals(
            labor_items=labor_items,
            material_items=material_items,
            margin_percent=Decimal('20')
        )
        
        assert result['labor_total'] == Decimal('1000.00')
        assert result['material_total'] == Decimal('500.00')
        assert result['subtotal'] == Decimal('1500.00')
    
    def test_items_with_string_totals(self):
        """Items with string totals should be converted."""
        labor_items = [{'total': '1000.50'}]
        material_items = [{'total': '500.25'}]
        
        result = calculate_estimate_totals(
            labor_items=labor_items,
            material_items=material_items,
            margin_percent=Decimal('20')
        )
        
        assert result['labor_total'] == Decimal('1000.50')
        assert result['material_total'] == Decimal('500.25')
        assert result['subtotal'] == Decimal('1500.75')
    
    def test_margin_15_percent(self):
        """Test 15% margin calculation."""
        labor_items = [{'total': Decimal('850')}]
        material_items = []
        
        result = calculate_estimate_totals(
            labor_items=labor_items,
            material_items=material_items,
            margin_percent=Decimal('15')
        )
        
        # total = 850 / (1 - 0.15) = 850 / 0.85 = 1000
        assert result['subtotal'] == Decimal('850.00')
        assert result['total'] == Decimal('1000.00')
        assert result['margin_amount'] == Decimal('150.00')
    
    def test_margin_25_percent(self):
        """Test 25% margin calculation."""
        labor_items = [{'total': Decimal('750')}]
        material_items = []
        
        result = calculate_estimate_totals(
            labor_items=labor_items,
            material_items=material_items,
            margin_percent=Decimal('25')
        )
        
        # total = 750 / (1 - 0.25) = 750 / 0.75 = 1000
        assert result['subtotal'] == Decimal('750.00')
        assert result['total'] == Decimal('1000.00')
        assert result['margin_amount'] == Decimal('250.00')
    
    def test_complex_estimate(self):
        """Test a complex realistic estimate."""
        labor_items = [
            {'total': Decimal('7800')},   # Demolition
            {'total': Decimal('17000')},  # Electrical
            {'total': Decimal('14400')},  # HVAC
            {'total': Decimal('13200')},  # Drywall
        ]
        material_items = [
            {'total': Decimal('42000')},  # Electrical materials
            {'total': Decimal('72000')},  # HVAC materials
            {'total': Decimal('67500')},  # Drywall materials
        ]
        
        result = calculate_estimate_totals(
            labor_items=labor_items,
            material_items=material_items,
            margin_percent=Decimal('22')
        )
        
        expected_labor = Decimal('52400.00')
        expected_material = Decimal('181500.00')
        expected_subtotal = Decimal('233900.00')
        
        assert result['labor_total'] == expected_labor
        assert result['material_total'] == expected_material
        assert result['subtotal'] == expected_subtotal
        
        # total = 233900 / 0.78 = 299871.79 (rounded)
        expected_total = (expected_subtotal / Decimal('0.78')).quantize(Decimal('0.01'))
        assert result['total'] == expected_total
    
    def test_rounding_consistency(self):
        """Ensure margin_amount + subtotal = total."""
        labor_items = [{'total': Decimal('1234.56')}]
        material_items = [{'total': Decimal('7890.12')}]
        
        result = calculate_estimate_totals(
            labor_items=labor_items,
            material_items=material_items,
            margin_percent=Decimal('18.5')
        )
        
        # Verify that subtotal + margin = total
        calculated_total = result['subtotal'] + result['margin_amount']
        assert abs(calculated_total - result['total']) < Decimal('0.02')  # Allow for rounding
