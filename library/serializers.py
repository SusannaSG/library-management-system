from rest_framework import serializers

from .models import Book, Loan, Member


class BookSerializer(serializers.ModelSerializer):
    available_copies = serializers.IntegerField(read_only=True)

    class Meta:
        model = Book
        fields = ["id", "title", "author", "isbn", "category", "total_copies", "available_copies"]


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ["id", "name", "email", "joined_on"]
        read_only_fields = ["joined_on"]


class LoanSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    member_name = serializers.CharField(source="member.name", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Loan
        fields = [
            "id", "book", "book_title", "member", "member_name",
            "issued_on", "due_on", "returned_on", "fine", "is_overdue",
        ]
        read_only_fields = ["issued_on", "due_on", "returned_on", "fine"]


class IssueSerializer(serializers.Serializer):
    """Validates the body of POST /api/loans/issue/."""

    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    member = serializers.PrimaryKeyRelatedField(queryset=Member.objects.all())
