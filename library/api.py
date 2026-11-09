from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from . import services
from .models import Book, Loan, Member
from .serializers import BookSerializer, IssueSerializer, LoanSerializer, MemberSerializer


class BookViewSet(viewsets.ModelViewSet):
    """Anyone can read books; only logged-in staff can add, edit or delete.
    Search with /api/books/?search=python (matches title, author, category, ISBN)."""

    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [SearchFilter]
    search_fields = ["title", "author", "category", "isbn"]


class MemberViewSet(viewsets.ModelViewSet):
    """Member details are private, so every request must be logged in."""

    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["name", "email"]


class LoanViewSet(viewsets.ReadOnlyModelViewSet):
    """Loans are created and closed only through issue/ and return/ so the
    library rules are always applied."""

    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        loans = Loan.objects.select_related("book", "member")
        state = self.request.query_params.get("status")  # active | returned | overdue
        if state == "active":
            loans = loans.filter(returned_on__isnull=True)
        elif state == "returned":
            loans = loans.filter(returned_on__isnull=False)
        elif state == "overdue":
            loans = loans.filter(returned_on__isnull=True, due_on__lt=timezone.localdate())
        return loans

    @action(detail=False, methods=["post"])
    def issue(self, request):
        data = IssueSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            loan = services.issue_book(data.validated_data["book"], data.validated_data["member"])
        except services.LibraryError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(LoanSerializer(loan).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="return")
    def return_loan(self, request, pk=None):
        loan = self.get_object()
        try:
            loan = services.return_book(loan)
        except services.LibraryError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(LoanSerializer(loan).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stats(request):
    return Response(services.library_stats())
