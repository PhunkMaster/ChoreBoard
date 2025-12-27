"""
Tests for ChoreBoard chore models.
"""
from django.test import TestCase
from decimal import Decimal
from chores.models import Chore, ChoreTemplate


class ChoreModelTests(TestCase):
    """Tests for Chore model."""

    def test_chore_complete_later_default(self):
        """Test that complete_later defaults to False."""
        chore = Chore.objects.create(
            name="Test Chore",
            points=Decimal("10.00")
        )
        self.assertFalse(chore.complete_later)

    def test_chore_complete_later_true(self):
        """Test setting complete_later to True."""
        chore = Chore.objects.create(
            name="Clean Kitchen After Dinner",
            points=Decimal("15.00"),
            complete_later=True
        )
        self.assertTrue(chore.complete_later)

    def test_chore_complete_later_saves_correctly(self):
        """Test that complete_later persists after save."""
        chore = Chore.objects.create(
            name="Test Chore",
            points=Decimal("10.00"),
            complete_later=True
        )
        chore_id = chore.id

        # Retrieve from database
        retrieved_chore = Chore.objects.get(id=chore_id)
        self.assertTrue(retrieved_chore.complete_later)


class ChoreTemplateModelTests(TestCase):
    """Tests for ChoreTemplate model."""

    def test_template_complete_later_default(self):
        """Test that complete_later defaults to False in templates."""
        template = ChoreTemplate.objects.create(
            template_name="Test Template",
            points=Decimal("10.00")
        )
        self.assertFalse(template.complete_later)

    def test_template_complete_later_in_to_chore_dict(self):
        """Test that to_chore_dict includes complete_later field."""
        template = ChoreTemplate.objects.create(
            template_name="Late Chore Template",
            points=Decimal("15.00"),
            complete_later=True
        )
        chore_dict = template.to_chore_dict()
        self.assertIn('complete_later', chore_dict)
        self.assertTrue(chore_dict['complete_later'])
