from decimal import Decimal

from django.db import models
from django.utils import timezone

# Library rules live here so they are easy to find and change.
LOAN_DAYS = 14          # a book can be kept for 14 days
FINE_PER_DAY = 5        # Rs. 5 for every day a book is returned late
MAX_ACTIVE_LOANS = 3    # a member can hold at most 3 books at once


def calculate_fine(due_on, returned_on):
    """Fine = days late x FINE_PER_DAY. Returning on or before the due date is free."""
    days_late = (returned_on - due_on).days
    return Decimal(max(days_late, 0)) * FINE_PER_DAY


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=120)
    isbn = models.CharField(max_length=13, unique=True)
    category = models.CharField(max_length=60)
    total_copies = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} by {self.author}"

    @property
    def available_copies(self):
        """Copies on the shelf = total copies minus copies currently on loan."""
        on_loan = self.loans.filter(returned_on__isnull=True).count()
        return self.total_copies - on_loan


class Member(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    joined_on = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Loan(models.Model):
    """One row each time a member borrows a book. returned_on stays empty
    until the book comes back."""

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="loans")
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="loans")
    issued_on = models.DateField(default=timezone.localdate)
    due_on = models.DateField()
    returned_on = models.DateField(null=True, blank=True)
    fine = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        ordering = ["-issued_on", "-id"]

    def __str__(self):
        return f"{self.book.title} -> {self.member.name}"

    @property
    def is_active(self):
        return self.returned_on is None

    @property
    def is_overdue(self):
        return self.is_active and self.due_on < timezone.localdate()

    @property
    def fine_so_far(self):
        """Fine owed today for a book still out (the final fine once it is returned)."""
        if not self.is_active:
            return self.fine
        return calculate_fine(self.due_on, timezone.localdate())
