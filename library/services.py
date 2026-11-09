"""The library's business rules. Views and the API both call these functions,
so the rules are written once and tested directly."""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    LOAN_DAYS,
    MAX_ACTIVE_LOANS,
    Book,
    Loan,
    Member,
    calculate_fine,
)


class LibraryError(Exception):
    """Raised when a library rule stops an action (shown to the user as a message)."""


@transaction.atomic
def issue_book(book, member):
    """Lend a book to a member, after checking the rules."""
    # Lock the book row so two librarians cannot issue the last copy at once.
    book = Book.objects.select_for_update().get(pk=book.pk)

    if book.available_copies < 1:
        raise LibraryError(f'No copies of "{book.title}" are available right now.')

    active = member.loans.filter(returned_on__isnull=True).count()
    if active >= MAX_ACTIVE_LOANS:
        raise LibraryError(
            f"{member.name} already has {MAX_ACTIVE_LOANS} books. Return one first."
        )

    today = timezone.localdate()
    return Loan.objects.create(
        book=book,
        member=member,
        issued_on=today,
        due_on=today + timedelta(days=LOAN_DAYS),
    )


@transaction.atomic
def return_book(loan):
    """Mark a loan as returned and work out any late fine."""
    loan = Loan.objects.select_for_update().get(pk=loan.pk)
    if loan.returned_on is not None:
        raise LibraryError("This book has already been returned.")

    loan.returned_on = timezone.localdate()
    loan.fine = calculate_fine(loan.due_on, loan.returned_on)
    loan.save()
    return loan


def library_stats():
    """Numbers for the dashboard and the stats API."""
    today = timezone.localdate()
    active = Loan.objects.filter(returned_on__isnull=True)
    # Sum() adds up the fine column in the database; it is None when there are no rows.
    fines = Loan.objects.aggregate(total=Sum("fine"))["total"] or Decimal(0)
    return {
        "total_books": Book.objects.count(),
        "total_members": Member.objects.count(),
        "active_loans": active.count(),
        "overdue_loans": active.filter(due_on__lt=today).count(),
        "fines_collected": str(fines),
    }
