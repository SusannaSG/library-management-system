from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api, views

# The router builds the standard URLs (list, detail, create, update, delete) for us.
router = DefaultRouter()
router.register("books", api.BookViewSet, basename="book")
router.register("members", api.MemberViewSet, basename="member")
router.register("loans", api.LoanViewSet, basename="loan")

urlpatterns = [
    # Web pages
    path("", views.dashboard, name="dashboard"),
    path("books/", views.book_list, name="books"),
    path("loans/", views.loan_list, name="loans"),
    path("loans/issue/", views.issue_book, name="issue"),
    path("loans/<int:pk>/return/", views.return_loan, name="return"),
    # REST API
    path("api/stats/", api.stats, name="api-stats"),
    path("api/", include(router.urls)),
]
