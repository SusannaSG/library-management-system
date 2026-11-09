from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from library.models import Book, Loan, Member

BOOKS = [
    ("Python Crash Course", "Eric Matthes", "9781593279288", "Programming", 3),
    ("Automate the Boring Stuff with Python", "Al Sweigart", "9781593279929", "Programming", 2),
    ("Clean Code", "Robert C. Martin", "9780132350884", "Programming", 2),
    ("Introduction to Algorithms", "Thomas H. Cormen", "9780262046305", "Computer Science", 1),
    ("Database System Concepts", "Abraham Silberschatz", "9780078022159", "Computer Science", 2),
    ("Hands-On Machine Learning", "Aurelien Geron", "9781492032649", "Data Science", 2),
    ("The Pragmatic Programmer", "Andrew Hunt", "9780135957059", "Programming", 1),
    ("Wings of Fire", "A. P. J. Abdul Kalam", "9788173711466", "Biography", 3),
    ("The Alchemist", "Paulo Coelho", "9780062315007", "Fiction", 2),
    ("Atomic Habits", "James Clear", "9780735211292", "Self Help", 2),
]

MEMBERS = [
    ("Asha Patil", "asha@example.com"),
    ("Ravi Kumar", "ravi@example.com"),
    ("Meena Rao", "meena@example.com"),
    ("Imran Sheikh", "imran@example.com"),
]


class Command(BaseCommand):
    help = "Load demo books, members and loans, plus a librarian login (librarian / library12345)."

    def handle(self, *args, **options):
        User = get_user_model()
        staff, _ = User.objects.get_or_create(
            username="librarian", defaults={"is_staff": True, "is_superuser": True}
        )
        staff.set_password("library12345")
        staff.save()

        for title, author, isbn, category, copies in BOOKS:
            Book.objects.get_or_create(
                isbn=isbn,
                defaults={"title": title, "author": author, "category": category, "total_copies": copies},
            )
        for name, email in MEMBERS:
            Member.objects.get_or_create(email=email, defaults={"name": name})

        if not Loan.objects.exists():
            today = timezone.localdate()
            asha, ravi, meena = (Member.objects.get(email=e) for e in
                                 ("asha@example.com", "ravi@example.com", "meena@example.com"))
            crash = Book.objects.get(isbn="9781593279288")
            clean = Book.objects.get(isbn="9780132350884")
            alchemist = Book.objects.get(isbn="9780062315007")
            # An overdue loan, a normal loan and a returned loan (late, with a fine)
            Loan.objects.create(book=clean, member=ravi, issued_on=today - timedelta(days=20),
                                due_on=today - timedelta(days=6))
            Loan.objects.create(book=crash, member=asha, issued_on=today - timedelta(days=3),
                                due_on=today + timedelta(days=11))
            Loan.objects.create(book=alchemist, member=meena, issued_on=today - timedelta(days=25),
                                due_on=today - timedelta(days=11),
                                returned_on=today - timedelta(days=8), fine=15)

        self.stdout.write(self.style.SUCCESS("Demo data loaded. Login: librarian / library12345"))
