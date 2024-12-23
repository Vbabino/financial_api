# import datetime
from datetime import datetime, timedelta
from .forms import TransactionsForm
from rest_framework.generics import ListAPIView  # type: ignore
from rest_framework.views import APIView  # type: ignore
from rest_framework.reverse import reverse  # type: ignore
import statistics as st
from django.shortcuts import render, HttpResponse  # type: ignore
from rest_framework.decorators import api_view  # type: ignore
from rest_framework.response import Response  # type: ignore
from .models import Transactions  # type: ignore
from .serializer import TransactionsSerializer  # type: ignore
from drf_yasg.utils import swagger_auto_schema  # type: ignore
from drf_yasg import openapi  # type: ignore
from django.db.models import Sum, Count  # type: ignore
from django.db import models  # type: ignore
from django.contrib import messages


# Create your views here.


# Retrieves all transactions for a specific account, ordered by date.
class TransactionsByAccount(ListAPIView):
    serializer_class = TransactionsSerializer

    @swagger_auto_schema(
        operation_description="Retrieve a paginated list of transactions for a specific account, ordered by date",
        manual_parameters=[
            openapi.Parameter(
                "account_id",
                openapi.IN_PATH,
                description="Account ID (e.g.: AC00225)",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={200: "List of transactions for the specified account"},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        account_id = self.kwargs["account_id"]
        return Transactions.objects.filter(AccountID=account_id).order_by(
            "TransactionDate"
        )


class SuspiciousTransactions(ListAPIView):
    serializer_class = TransactionsSerializer

    """
    Fraud Detection Rules:

    1. High Deviation from Average Spending: Flag a transaction as fraud if the amount exceeds 2 standard deviations from the accounts's average spending.

    2. Unusual locations: Flag a transaction as suspicious if it occurs in a Location that is not among the top 3 most frequent locations for the account

    3. Excessive Login Attempts: Flag as fraud if more than 3 login attempts.

    """

    @swagger_auto_schema(
        operation_description="Returns transactions flagged as suspicious based on anomalies like high amounts, unusual locations, or excessive login attempts.",
        manual_parameters=[
            openapi.Parameter(
                "account_id",
                openapi.IN_PATH,
                description="Account ID (e.g.: AC00441)",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={200: "List of suspicious transactions for the specified account"},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        account_id = self.kwargs["account_id"]

        # Get all transactions for the account
        transactions = Transactions.objects.filter(AccountID=account_id)

        # Initialize empty querysets for suspicious transactions
        high_deviation = Transactions.objects.none()

        # High Deviation from Average Spending
        amounts = list(transactions.values_list("TransactionAmount", flat=True))

        if len(amounts) > 1:  # Ensure there are enough transactions to calculate stdev
            avg_amount = st.mean(amounts)
            std_dev = st.stdev(amounts)
            threshold = avg_amount + 2 * std_dev
            high_deviation = transactions.filter(TransactionAmount__gt=threshold)

        # Unusual Locations
        location_counts = (
            transactions.values("Location")
            .annotate(count=models.Count("Location"))
            .order_by("-count")
        )
        top_3_locations = [
            loc["Location"] for loc in location_counts[:3] if loc["count"] >= 2
        ]

        """
        Check for unusual transaction locations:
        If there are 3 or fewer unique locations and each has only 1 transaction,
        consider all locations as normal. Otherwise, mark transactions from locations
        outside the top 3 most frequent as unusual."""

        if len(location_counts) <= 3 and all(
            loc["count"] == 1 for loc in location_counts
        ):
            unusual_locations = Transactions.objects.none()  # No unusual locations
        elif all(loc["count"] == 1 for loc in location_counts):
            unusual_locations = Transactions.objects.none()  # No unusual locations
        else:
            unusual_locations = transactions.exclude(Location__in=top_3_locations)

        # Excessive Login Attempts
        excessive_login_attempts = transactions.filter(LoginAttempts__gt=3)

        # Combine all suspicious transactions

        return high_deviation | unusual_locations | excessive_login_attempts


# Provides a summary of total transactions, total amounts, and counts for a specific merchant
class TransactionsSummaryByMerchant(ListAPIView):
    serializer_class = TransactionsSerializer

    @swagger_auto_schema(
        operation_description="Provides a summary of total transactions, total amounts, and counts for a specific merchant",
        manual_parameters=[
            openapi.Parameter(
                "merchant_id",
                openapi.IN_PATH,
                description="Merchant Name (e.g.: M065)",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={200: "Summary of transactions for the specified merchant"},
    )
    def get(self, request, merchant_id, *args, **kwargs):
        # Filter transactions for the given merchant
        transactions = Transactions.objects.filter(MerchantID=merchant_id)

        # Perform aggregation for the summary
        summary = transactions.aggregate(
            total_amount=Sum("TransactionAmount"),
            total_transactions=Count("TransactionID"),
        )

        # Add the merchant ID to the summary
        summary["merchant_id"] = merchant_id

        return Response(summary)


# Add a new transaction
class AddTransaction(APIView):

    @swagger_auto_schema(
        operation_description="Creates a new transaction with validations.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "AccountID": openapi.Schema(type=openapi.TYPE_STRING),
                "TransactionDate": openapi.Schema(type=openapi.TYPE_STRING),
                "TransactionAmount": openapi.Schema(type=openapi.TYPE_NUMBER),
                "TransactionType": openapi.Schema(type=openapi.TYPE_STRING),
                "TransactionDuration": openapi.Schema(type=openapi.TYPE_INTEGER),
                "CustomerAge": openapi.Schema(type=openapi.TYPE_INTEGER),
                "CustomerOccupation": openapi.Schema(type=openapi.TYPE_STRING),
                "AccountBalance": openapi.Schema(type=openapi.TYPE_NUMBER),
                "MerchantID": openapi.Schema(type=openapi.TYPE_STRING),
                "Channel": openapi.Schema(type=openapi.TYPE_STRING),
                "DeviceID": openapi.Schema(type=openapi.TYPE_STRING),
                "Location": openapi.Schema(type=openapi.TYPE_STRING),
                "LoginAttempts": openapi.Schema(type=openapi.TYPE_INTEGER),
                "IPAddress": openapi.Schema(type=openapi.TYPE_STRING),
                "PreviousTransactionDate": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: "Transaction added successfully"},
    )
    def post(self, request):
        serializer = TransactionsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Transaction added successfully"})
        return Response(serializer.errors, status=400)


# Provides spending insights for a specific account, including totals by transaction type, most-used merchant, location, and channel
class SpendingInsightsView(ListAPIView):
    serializer_class = TransactionsSerializer

    @swagger_auto_schema(
        operation_description="Provides spending insights for a specific account, including totals by transaction type, most-used merchant, location, and channel.",
        manual_parameters=[
            openapi.Parameter(
                "account_id",
                openapi.IN_PATH,
                description="Account ID for which to retrieve spending insights (e.g.: AC00225).",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={200: "Spending insights for the specified account"},
    )
    def get(self, request, account_id, *args, **kwargs):

        try:
            # Filter transactions for the given account
            transactions = Transactions.objects.filter(AccountID=account_id)

            # Total spending by transaction type
            spending_by_type = transactions.values("TransactionType").annotate(
                total_amount=Sum("TransactionAmount"),
                transaction_count=Count("TransactionID"),
            )

            # Most used merchant
            merchant_counts = transactions.values("MerchantID").annotate(
                count=Count("TransactionID")
            )
            most_used_merchant = merchant_counts.order_by("-count").first()

            # Check if all merchants are used once
            if most_used_merchant and all(
                merchant["count"] == 1 for merchant in merchant_counts
            ):
                most_used_merchant = {"message": "All merchants are used once"}

            # Most used channel
            channel_counts = transactions.values("Channel").annotate(
                count=Count("TransactionID")
            )
            most_used_channel = channel_counts.order_by("-count").first()

            # check if all channels are used once
            if most_used_channel and all(
                channel["count"] == 1 for channel in channel_counts
            ):
                most_used_channel = {"message": "All channels are used once"}

            # Most used location
            location_counts = transactions.values("Location").annotate(
                count=Count("TransactionID")
            )
            most_used_location = location_counts.order_by("-count").first()

            # check if all locations are used once
            if most_used_location and all(
                location["count"] == 1 for location in location_counts
            ):
                most_used_location = {"message": "All locations are used once"}

            # Build the response
            response = {
                "account_id": account_id,
                "spending_by_type": list(spending_by_type),
                "most_used_merchant": most_used_merchant,
                "most_used_channel": most_used_channel,
                "most_used_location": most_used_location,
            }

            return Response(response)

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"}, status=500
            )


class HighFrequencyAccountsView(APIView):

    @swagger_auto_schema(
        operation_description="Identifies accounts with unusually high transaction frequency within a defined period.",
        manual_parameters=[
            openapi.Parameter(
                "days",
                openapi.IN_QUERY,
                description="Number of days to analyze transaction frequency. Default is 1000 since the transactions of the data set occured in 2023.",
                type=openapi.TYPE_INTEGER,
                required=False,
            )
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "period_days": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "high_frequency_accounts": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "AccountID": openapi.Schema(type=openapi.TYPE_STRING),
                                "transaction_count": openapi.Schema(
                                    type=openapi.TYPE_INTEGER
                                ),
                            },
                        ),
                    ),
                },
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        # Get the period from query parameters (default: last 7 days)
        period = int(request.query_params.get("days", 1000))

        # Calculate the start date for filtering
        start_date = datetime.now() - timedelta(days=period)

        # Filter transactions within the defined period
        high_frequency_accounts = (
            Transactions.objects.filter(TransactionDate__gte=start_date)
            .values("AccountID")
            .annotate(transaction_count=Count("TransactionID"))
            .filter(transaction_count__gt=10)  # Threshold for high frequency
            .order_by("-transaction_count")
        )

        # Format the response
        results = [
            {
                "AccountID": account["AccountID"],
                "transaction_count": account["transaction_count"],
            }
            for account in high_frequency_accounts
        ]

        return Response(
            {
                "period_days": period,
                "high_frequency_accounts": results,
            }
        )
