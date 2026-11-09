from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from . import services
from .models import FINE_PER_DAY, LOAN_DAYS, MAX_ACTIVE_LOANS, Book, Loan, Member

User = get_user_model()


class LibraryTestCase(TestCase):
    """Common setup: a few books, two members and a librarian login."""

    def setUp(self):
        self.python = Book.objects.create(
            title="Python Basics", author="A. Writer", isbn="1111111111111",
            category="Programming", total_copies=2,
        )
        self.novel = Book.objects.create(
            title="Night Train", author="B. Author", isbn="2222222222222",
            category="Fiction", total_copies=1,
        )
        self.asha = Member.objects.create(name="Asha", email="asha@example.com")
        self.ravi = Member.objects.create(name="Ravi", email="ravi@example.com")
        self.staff = User.objects.create_user("librarian", password="pass12345")


class FineTests(TestCase):
    def test_returned_on_due_date_has_no_fine(self):
        day = timezone.localdate()
        self.assertEqual(services.calculate_fine(day, day), 0)

    def test_returned_early_has_no_fine(self):
        day = timezone.localdate()
        self.assertEqual(services.calculate_fine(day, day - timedelta(days=3)), 0)

    def test_late_return_charges_per_day(self):
        day = timezone.localdate()
        late = day + timedelta(days=4)
        self.assertEqual(services.calculate_fine(day, late), Decimal(4 * FINE_PER_DAY))


class IssueBookTests(LibraryTestCase):
    def test_issue_sets_due_date_14_days_out(self):
        loan = services.issue_book(self.python, self.asha)
        self.assertEqual(loan.due_on, timezone.localdate() + timedelta(days=LOAN_DAYS))
        self.assertIsNone(loan.returned_on)

    def test_available_copies_drop_when_issued(self):
        self.assertEqual(self.python.available_copies, 2)
        services.issue_book(self.python, self.asha)
        self.assertEqual(self.python.available_copies, 1)

    def test_cannot_issue_when_no_copies_left(self):
        services.issue_book(self.novel, self.asha)  # the only copy
        with self.assertRaises(services.LibraryError):
            services.issue_book(self.novel, self.ravi)

    def test_member_limit_is_enforced(self):
        for i in range(MAX_ACTIVE_LOANS):
            book = Book.objects.create(
                title=f"Book {i}", author="X", isbn=f"90000000000{i:02d}",
                category="Misc", total_copies=1,
            )
            services.issue_book(book, self.asha)
        with self.assertRaises(services.LibraryError):
            services.issue_book(self.python, self.asha)

    def test_returning_a_book_frees_a_slot_for_the_member(self):
        loans = []
        for i in range(MAX_ACTIVE_LOANS):
            book = Book.objects.create(
                title=f"Book {i}", author="X", isbn=f"80000000000{i:02d}",
                category="Misc", total_copies=1,
            )
            loans.append(services.issue_book(book, self.asha))
        services.return_book(loans[0])
        services.issue_book(self.python, self.asha)  # now allowed


class ReturnBookTests(LibraryTestCase):
    def test_on_time_return_has_no_fine(self):
        loan = services.issue_book(self.python, self.asha)
        loan = services.return_book(loan)
        self.assertEqual(loan.returned_on, timezone.localdate())
        self.assertEqual(loan.fine, 0)

    def test_late_return_gets_fine(self):
        loan = Loan.objects.create(
            book=self.python, member=self.asha,
            issued_on=timezone.localdate() - timedelta(days=20),
            due_on=timezone.localdate() - timedelta(days=6),
        )
        loan = services.return_book(loan)
        self.assertEqual(loan.fine, Decimal(6 * FINE_PER_DAY))

    def test_cannot_return_twice(self):
        loan = services.issue_book(self.python, self.asha)
        services.return_book(loan)
        with self.assertRaises(services.LibraryError):
            services.return_book(loan)

    def test_returned_copy_becomes_available_again(self):
        loan = services.issue_book(self.novel, self.asha)
        services.return_book(loan)
        self.assertEqual(self.novel.available_copies, 1)


class StatsTests(LibraryTestCase):
    def test_stats_count_overdue_and_fines(self):
        today = timezone.localdate()
        Loan.objects.create(book=self.python, member=self.asha,
                            issued_on=today - timedelta(days=20), due_on=today - timedelta(days=6))
        Loan.objects.create(book=self.novel, member=self.ravi,
                            issued_on=today - timedelta(days=30), due_on=today - timedelta(days=16),
                            returned_on=today - timedelta(days=14), fine=10)
        stats = services.library_stats()
        self.assertEqual(stats["total_books"], 2)
        self.assertEqual(stats["total_members"], 2)
        self.assertEqual(stats["active_loans"], 1)
        self.assertEqual(stats["overdue_loans"], 1)
        self.assertEqual(Decimal(stats["fines_collected"]), Decimal(10))


class BookApiTests(LibraryTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_anyone_can_list_books(self):
        res = self.client.get("/api/books/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 2)

    def test_search_matches_title_author_and_category(self):
        self.assertEqual(len(self.client.get("/api/books/?search=python").json()), 1)
        self.assertEqual(len(self.client.get("/api/books/?search=Author").json()), 1)
        self.assertEqual(len(self.client.get("/api/books/?search=Fiction").json()), 1)
        self.assertEqual(self.client.get("/api/books/?search=zzz").json(), [])

    def test_book_shows_available_copies(self):
        services.issue_book(self.python, self.asha)
        data = self.client.get(f"/api/books/{self.python.pk}/").json()
        self.assertEqual(data["available_copies"], 1)

    def test_anonymous_cannot_create_book(self):
        res = self.client.post("/api/books/", {
            "title": "T", "author": "A", "isbn": "3333333333333",
            "category": "C", "total_copies": 1}, format="json")
        self.assertIn(res.status_code, (401, 403))

    def test_staff_can_create_book(self):
        self.client.force_authenticate(self.staff)
        res = self.client.post("/api/books/", {
            "title": "T", "author": "A", "isbn": "3333333333333",
            "category": "C", "total_copies": 1}, format="json")
        self.assertEqual(res.status_code, 201)

    def test_duplicate_isbn_is_rejected(self):
        self.client.force_authenticate(self.staff)
        res = self.client.post("/api/books/", {
            "title": "Copy", "author": "A", "isbn": self.python.isbn,
            "category": "C", "total_copies": 1}, format="json")
        self.assertEqual(res.status_code, 400)


class LoanApiTests(LibraryTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(self.staff)

    def test_members_are_private(self):
        anon = APIClient()
        self.assertIn(anon.get("/api/members/").status_code, (401, 403))
        self.assertEqual(len(self.client.get("/api/members/").json()), 2)

    def test_issue_then_return_flow(self):
        issue = self.client.post("/api/loans/issue/",
                                 {"book": self.python.pk, "member": self.asha.pk}, format="json")
        self.assertEqual(issue.status_code, 201)
        loan_id = issue.json()["id"]
        ret = self.client.post(f"/api/loans/{loan_id}/return/")
        self.assertEqual(ret.status_code, 200)
        self.assertIsNotNone(ret.json()["returned_on"])

    def test_issue_with_no_copies_returns_409(self):
        services.issue_book(self.novel, self.asha)
        res = self.client.post("/api/loans/issue/",
                               {"book": self.novel.pk, "member": self.ravi.pk}, format="json")
        self.assertEqual(res.status_code, 409)
        self.assertIn("error", res.json())

    def test_issue_with_unknown_book_returns_400(self):
        res = self.client.post("/api/loans/issue/",
                               {"book": 9999, "member": self.asha.pk}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_double_return_returns_409(self):
        loan = services.issue_book(self.python, self.asha)
        self.client.post(f"/api/loans/{loan.pk}/return/")
        res = self.client.post(f"/api/loans/{loan.pk}/return/")
        self.assertEqual(res.status_code, 409)

    def test_status_filters(self):
        today = timezone.localdate()
        Loan.objects.create(book=self.python, member=self.asha,
                            issued_on=today - timedelta(days=20), due_on=today - timedelta(days=6))
        services.issue_book(self.novel, self.ravi)
        self.assertEqual(len(self.client.get("/api/loans/?status=active").json()), 2)
        self.assertEqual(len(self.client.get("/api/loans/?status=overdue").json()), 1)
        self.assertEqual(len(self.client.get("/api/loans/?status=returned").json()), 0)

    def test_loans_cannot_be_created_directly(self):
        res = self.client.post("/api/loans/", {"book": self.python.pk, "member": self.asha.pk},
                               format="json")
        self.assertEqual(res.status_code, 405)

    def test_stats_endpoint(self):
        res = self.client.get("/api/stats/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total_books"], 2)


class WebPageTests(LibraryTestCase):
    def test_pages_require_login(self):
        for name in ("dashboard", "books", "loans", "issue"):
            res = self.client.get(reverse(name))
            self.assertEqual(res.status_code, 302, name)
            self.assertIn("/accounts/login/", res["Location"])

    def test_login_page_loads(self):
        self.assertContains(self.client.get("/accounts/login/"), "Librarian login")

    def test_dashboard_loads_after_login(self):
        self.client.login(username="librarian", password="pass12345")
        res = self.client.get(reverse("dashboard"))
        self.assertContains(res, "Dashboard")

    def test_book_search_page(self):
        self.client.login(username="librarian", password="pass12345")
        res = self.client.get(reverse("books"), {"q": "night"})
        self.assertContains(res, "Night Train")
        self.assertNotContains(res, "Python Basics")

    def test_issue_form_creates_loan(self):
        self.client.login(username="librarian", password="pass12345")
        res = self.client.post(reverse("issue"), {"member": self.asha.pk, "book": self.python.pk})
        self.assertRedirects(res, reverse("loans"))
        self.assertEqual(Loan.objects.count(), 1)

    def test_issue_form_shows_rule_error(self):
        services.issue_book(self.novel, self.asha)
        self.client.login(username="librarian", password="pass12345")
        res = self.client.post(reverse("issue"), {"member": self.ravi.pk, "book": self.novel.pk})
        self.assertContains(res, "No copies")
        self.assertEqual(Loan.objects.count(), 1)

    def test_return_requires_post(self):
        loan = services.issue_book(self.python, self.asha)
        self.client.login(username="librarian", password="pass12345")
        self.assertEqual(self.client.get(reverse("return", args=[loan.pk])).status_code, 405)

    def test_return_button_marks_returned(self):
        loan = services.issue_book(self.python, self.asha)
        self.client.login(username="librarian", password="pass12345")
        self.client.post(reverse("return", args=[loan.pk]))
        loan.refresh_from_db()
        self.assertIsNotNone(loan.returned_on)
