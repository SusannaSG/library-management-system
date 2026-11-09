from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services
from .forms import IssueForm
from .models import Book, Loan


@login_required
def dashboard(request):
    overdue = Loan.objects.select_related("book", "member").filter(
        returned_on__isnull=True, due_on__lt=timezone.localdate()
    )
    return render(request, "library/dashboard.html", {
        "stats": services.library_stats(),
        "overdue": overdue,
    })


@login_required
def book_list(request):
    query = request.GET.get("q", "").strip()
    books = Book.objects.all()
    if query:
        books = books.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
            | Q(category__icontains=query) | Q(isbn__icontains=query)
        )
    return render(request, "library/books.html", {"books": books, "query": query})


@login_required
def loan_list(request):
    loans = Loan.objects.select_related("book", "member")
    show = request.GET.get("show", "active")
    if show == "active":
        loans = loans.filter(returned_on__isnull=True)
    return render(request, "library/loans.html", {"loans": loans, "show": show})


@login_required
def issue_book(request):
    form = IssueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            loan = services.issue_book(form.cleaned_data["book"], form.cleaned_data["member"])
        except services.LibraryError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request, f'Issued "{loan.book.title}" to {loan.member.name}. Due {loan.due_on:%d %b %Y}.'
            )
            return redirect("loans")
    return render(request, "library/issue.html", {"form": form})


@login_required
@require_POST
def return_loan(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    try:
        loan = services.return_book(loan)
    except services.LibraryError as exc:
        messages.error(request, str(exc))
    else:
        if loan.fine:
            messages.warning(request, f'Returned "{loan.book.title}". Late fine: Rs. {loan.fine}.')
        else:
            messages.success(request, f'Returned "{loan.book.title}". No fine.')
    return redirect("loans")
