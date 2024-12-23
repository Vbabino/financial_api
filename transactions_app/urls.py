from django.urls import include, path, re_path  # type: ignore
from . import views
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="API Documentation",
        default_version="v1",
        description="""API documentation for Bank transactions Endpoints
                    Python version: 3.12.4
                    Django version: 5.1.4
                    Django Rest Framework version: 3.15.2
                    Pagination size: 5 
                    """,
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    url="https://financial-api-wdns.onrender.com",
)

urlpatterns = [
    path("", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
    path(
        "transactions/<str:account_id>/",
        views.TransactionsByAccount.as_view(),
        name="transactions_by_account",
    ),
    path(
        "flagged_transactions/<str:account_id>/",
        views.SuspiciousTransactions.as_view(),
        name="flagged_transactions",
    ),
    path(
        "merchants/<str:merchant_id>/summary/",
        views.TransactionsSummaryByMerchant.as_view(),
        name="merchant-summary",
    ),
    path("add_transaction/", views.AddTransaction.as_view(), name="add_transaction"),
    path(
        "transactions/spending-insights/<str:account_id>/",
        views.SpendingInsightsView.as_view(),
        name="transaction-spending-insights",
    ),
    path(
        "accounts/high-frequency/",
        views.HighFrequencyAccountsView.as_view(),
        name="high-frequency-accounts",
    ),
]
