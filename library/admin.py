from django.contrib import admin

from .models import Book, Loan, Member


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "category", "isbn", "total_copies"]
    search_fields = ["title", "author", "isbn"]
    list_filter = ["category"]


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "joined_on"]
    search_fields = ["name", "email"]


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["book", "member", "issued_on", "due_on", "returned_on", "fine"]
    list_filter = ["returned_on"]
