# import datetime
from datetime import datetime, timedelta
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.reverse import reverse
import statistics as st
from django.shortcuts import render, HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Transactions
from .serializer import TransactionsSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Sum, Count
from django.db import models


# Create your views here.


class TransactionsByAccount(ListAPIView):
    """
    Endpoint to retrieve a paginated list of transactions for a specific account, ordered by date.

    This view handles GET requests to fetch transactions associated with a given account ID.
    The transactions are ordered by their transaction date.

    Attributes:
        serializer_class (TransactionsSerializer): The serializer class used for serializing the transactions data.

    Methods:
        get(request, *args, **kwargs):
            Handles GET requests to retrieve the list of transactions for the specified account.

        get_queryset():
            Retrieves the queryset of transactions filtered by the provided account ID and ordered by transaction date.
    """

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
        return (
            Transactions.objects.filter(AccountID=account_id)
            .select_related("AccountID", "MerchantID", "DeviceID")
            .order_by("TransactionDate")
        )


class SuspiciousTransactions(ListAPIView):
    serializer_class = TransactionsSerializer

    """
    Endpoint to identify suspicious transactions based on high deviations from average spending, unusual locations, and excessive login attempts. 
    
    Fraud Detection Rules:

    1. High Deviation from Average Spending: Flag a transaction as fraud if the amount exceeds 2 standard deviations from the account's average spending.

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
        transactions = Transactions.objects.filter(AccountID=account_id).select_related(
            "AccountID", "MerchantID", "DeviceID"
        )

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
        location_counts = list(
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


class TransactionsSummaryByMerchant(ListAPIView):
    """
    Provides a summary of total transactions, total amounts, and counts for a specific merchant.

    This endpoint filters transactions for a given merchant and performs aggregation to return a summary
    including the total amount of transactions and the total number of transactions for that merchant.

    Attributes:
        serializer_class (TransactionsSerializer): The serializer class used for the transactions.

    Methods:
        get(request, merchant_id, *args, **kwargs):
            Handles GET requests to provide the summary of transactions for the specified merchant.
            Parameters:
                request (Request): The HTTP request object.
                merchant_id (str): The ID of the merchant for which the summary is to be provided.
            Returns:
                Response: A response object containing the summary of transactions.
    """

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


class AddTransaction(APIView):
    """
    Endpoint to create a new transaction with validations.

    This endpoint allows the creation of a new transaction by accepting various transaction-related
    details in the request body. The request body must include the following fields:

    - AccountID (str): The ID of the account.
    - TransactionDate (str): The date of the transaction.
    - TransactionAmount (float): The amount of the transaction.
    - TransactionType (str): The type of the transaction.
    - TransactionDuration (int): The duration of the transaction.
    - CustomerAge (int): The age of the customer.
    - CustomerOccupation (str): The occupation of the customer.
    - AccountBalance (float): The balance of the account.
    - MerchantID (str): The ID of the merchant.
    - Channel (str): The channel through which the transaction was made.
    - DeviceID (str): The ID of the device used for the transaction.
    - Location (str): The location of the transaction.
    - LoginAttempts (int): The number of login attempts.
    - IPAddress (str): The IP address from which the transaction was made.
    - PreviousTransactionDate (str): The date of the previous transaction.

    Responses:
        200: Transaction added successfully.
        400: Bad request with validation errors.
    """

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


class SpendingInsightsView(ListAPIView):
    """
    Provides spending insights for a specific account, including totals by transaction type, most-used merchant, location, and channel.

    Attributes:
        serializer_class (class): The serializer class used for transactions.

    Methods:
        get(request, account_id, *args, **kwargs):
            Retrieves spending insights for the specified account.

            Parameters:
                request (HttpRequest): The request object.
                account_id (str): The account ID for which to retrieve spending insights.

            Returns:
                Response: A response object containing spending insights or an error message.
    """

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
            # merchant_counts = transactions.values("MerchantID").annotate(
            #     count=Count("TransactionID")
            # )
            # most_used_merchant = merchant_counts.order_by("-count").first()

            # # Check if all merchants are used once
            # if most_used_merchant and all(
            #     merchant["count"] == 1 for merchant in merchant_counts
            # ):
            #     most_used_merchant = {"message": "All merchants are used once"}

            merchant_counts = list(
                transactions.values("MerchantID")
                .annotate(count=Count("TransactionID"))
                .order_by("-count")
            )

            most_used_merchant = merchant_counts[0] if merchant_counts else None

            if most_used_merchant and all(m["count"] == 1 for m in merchant_counts):
                most_used_merchant = {"message": "All merchants are used once"}

            # Most used channel
            channel_counts = list(
                transactions.values("Channel")
                .annotate(count=Count("TransactionID"))
                .order_by("-count")
            )

            most_used_channel = channel_counts[0] if channel_counts else None

            # check if all channels are used once
            if most_used_channel and all(
                channel["count"] == 1 for channel in channel_counts
            ):
                most_used_channel = {"message": "All channels are used once"}

            # Most used location
            location_counts = list(
                transactions.values("Location")
                .annotate(count=Count("TransactionID"))
                .order_by("-count")
            )
            most_used_location = location_counts[0] if location_counts else None

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
    """
    Identifies accounts with unusually high transaction frequency within a defined period.

    This endpoint allows users to identify accounts that have a high number of transactions
    within a specified number of days. By default, it analyzes the last 1000 days of transactions.

    Query Parameters:
    - days (int, optional): Number of days to analyze transaction frequency. Default is 1000.

    Responses:
    - 200 OK: A JSON object containing:
        - period_days (int): The number o days analyzed.
        - high_frequency_accounts (list): A list of accounts with high transaction frequency,
          each containing:
            - AccountID (str): The ID of the account.
            - transaction_count (int): The number of transactions for the account within the period.

    Example:
    GET /api/high-frequency-accounts?days=30
    """

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
        # Get the period from query parameters (default: last 1000 days)
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
