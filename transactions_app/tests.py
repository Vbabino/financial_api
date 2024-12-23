from datetime import timedelta
from django.test import TestCase
from rest_framework.test import APITestCase
from django.urls import reverse
from .models import *
from rest_framework import status
from django.utils import timezone
from .helpers import *
from django.core.management import call_command


class TransactionsByAccountTests(APITestCase):
    # Tests for TransactionsByAccount endpoint

    @classmethod
    def setUpTestData(cls):
        # Set up test data (accounts and transactions)
        cls.account, cls.merchant, cls.device, cls.transaction1 = create_test_data()

    def test_transactions_by_account_success(self):
        """Test success: Retrieve transactions for a specific account."""

        create_transactions(
            self.account,
            self.merchant,
            self.device,
            num_transactions=1,
            transaction_amount=200.75,
            time_gap="days",
        )

        # Call the endpoint
        url = reverse("transactions_by_account", kwargs={"account_id": "AC00128"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 2
        )  #  Check that the response contains the expected number of transactions
        self.assertEqual(
            float(response.data["results"][0]["TransactionAmount"]), 100.50
        )

    def test_transactions_by_account_no_transactions(self):
        """Test edge case: Account exists but has no transactions."""
        # Create an account without transactions
        Accounts.objects.create(
            AccountID="AC00234",
        )
        url = reverse("transactions_by_account", kwargs={"account_id": "AC00234"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)  # No transactions

    def test_transactions_by_account_invalid_id(self):
        """Test error: Invalid or non-existent account_id."""
        url = reverse("transactions_by_account", kwargs={"account_id": "INVALID"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 0
        )  # Empty result for invalid ID


class AddTransactionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.account = Accounts.objects.create(AccountID="AC00128")
        cls.merchant = Merchants.objects.create(MerchantID="M015")
        cls.device = Devices.objects.create(DeviceID="D000051")

    def get_transaction_data(self, overrides=None):
        """Helper method to create transaction data."""
        data = {
            "AccountID": self.account.AccountID,
            "TransactionDate": "2024-04-11 16:29:14",
            "TransactionAmount": 100.50,
            "TransactionType": "Credit",
            "TransactionDuration": 120,
            "Location": "New York",
            "LoginAttempts": 1,
            "IPAddress": "192.168.1.1",
            "MerchantID": self.merchant.MerchantID,
            "Channel": "ATM",
            "DeviceID": self.device.DeviceID,
            "CustomerAge": 30,
            "CustomerOccupation": "Engineer",
            "AccountBalance": 4900,
            "PreviousTransactionDate": "2023-01-01 12:00:00",
        }
        if overrides:
            data.update(overrides)
        return data

    def test_add_transaction(self):
        """Test success: Add a new transaction."""
        url = reverse("add_transaction")
        data = self.get_transaction_data()
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Transactions.objects.count(), 1)

    def test_invalid_transaction_amount(self):
        """Test edge case: Transaction amount less than 0."""
        url = reverse("add_transaction")
        data = self.get_transaction_data({"TransactionAmount": -100.50})
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_future_dates(self):
        """Test edge case: Transaction date in the future."""
        url = reverse("add_transaction")
        data = self.get_transaction_data(
            {
                "TransactionDate": "2026-04-11 16:29:14",
                "previousTransactionDate": "2026-01-01 12:00:00",
            }
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_maximum_field_length(self):
        """Test edge case: Field length exceeds maximum."""
        url = reverse("add_transaction")
        data = self.get_transaction_data({"Location": "A" * 51})
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_optional_fields(self):
        """Test edge case: Add a new transaction with missing optional fields."""
        url = reverse("add_transaction")
        data = self.get_transaction_data()
        data.pop("Location")
        data.pop("CustomerOccupation")
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_required_fields(self):
        """Test error: Add a new transaction with missing required fields."""
        url = reverse("add_transaction")
        data = self.get_transaction_data()
        data.pop("AccountID")
        data.pop("TransactionType")
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_foreign_key(self):
        """Test error: Add a new transaction with invalid foreign key."""
        url = reverse("add_transaction")
        data = self.get_transaction_data(
            {"AccountID": "INVALID", "MerchantID": "INVALID", "DeviceID": "INVALID"}
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_IP_address(self):
        """Test error: Add a new transaction with invalid IP address."""
        url = reverse("add_transaction")
        data = self.get_transaction_data({"IPAddress": "192.300.1.1"})
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_enum_values(self):
        """Test error: Add a new transaction with invalid enum values."""
        url = reverse("add_transaction")
        data = self.get_transaction_data(
            {"TransactionType": "INVALID", "Channel": "INVALID"}
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date_format(self):
        """Test error: Add a new transaction with invalid date format."""
        url = reverse("add_transaction")
        data = self.get_transaction_data(
            {"TransactionDate": "11-12-2024", "PreviousTransactionDate": "03-08-2023"}
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SuspiciousTransactionsTests(APITestCase):
    # Tests for SuspiciousTransactions endpoint
    @classmethod
    def setUpTestData(cls):
        cls.account, cls.merchant, cls.device, cls.transaction1 = create_test_data()

        create_transactions(
            cls.account,
            cls.merchant,
            cls.device,
            num_transactions=1,
            time_gap="days",
            transaction_amount=150.54,
        )

        create_transactions(
            cls.account,
            cls.merchant,
            cls.device,
            num_transactions=1,
            time_gap="days",
            transaction_amount=30.50,
        )

        create_transactions(
            cls.account,
            cls.merchant,
            cls.device,
            num_transactions=1,
            time_gap="days",
            transaction_amount=145.50,
        )

        create_transactions(
            cls.account,
            cls.merchant,
            cls.device,
            num_transactions=1,
            time_gap="days",
            transaction_amount=250.67,
        )

    def test_exceeding_high_deviation(self):
        """Test success: Retrieve transactions with high deviation."""
        # Add a clear outlier transaction
        create_transactions(
            self.account,
            self.merchant,
            self.device,
            num_transactions=1,
            time_gap="days",
            transaction_amount=50000.50,
        )

        # Call the endpoint
        url = reverse("flagged_transactions", kwargs={"account_id": "AC00128"})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # print(Transactions.objects.values("TransactionAmount"))
        self.assertGreater(
            len(response.data["results"]), 0
        )  # At least one transaction flagged

        # Verify the outlier transaction is flagged
        flagged_transactions = response.data["results"]
        amounts = [float(tx["TransactionAmount"]) for tx in flagged_transactions]
        self.assertIn(50000.50, amounts)  # Ensures the outlier is in the results

    def test_unusual_location(self):
        """Test success: Retrieve transactions with unusual location."""

        # Add a transaction with a different location
        create_transactions(
            self.account,
            self.merchant,
            self.device,
            location="Tokyo",
            num_transactions=1,
        )

        # Call the endpoint
        url = reverse("flagged_transactions", kwargs={"account_id": "AC00128"})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(
            len(response.data["results"]), 0
        )  # At least one transaction flagged

        # Verify the outlier transaction is flagged
        flagged_transactions = response.data["results"]
        locations = [tx["Location"] for tx in flagged_transactions]
        self.assertIn("Tokyo", locations)

    def test_excessive_login_attempts(self):
        """Test success: Retrieve transactions with excessive login attempts."""
        # Add a transaction with excessive login attempts
        create_transactions(self.account, self.merchant, self.device, login_attempts=10)

        # Call the endpoint
        url = reverse("flagged_transactions", kwargs={"account_id": "AC00128"})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_single_transaction(self):
        """Test edge case: Only one transaction in the database.
        The transaction should not be flagged under “high deviation” or "unusual location"
        since standard deviation and top 3 locations cannot be calculated with one value.
        """
        # Create a new account and a single transaction
        account = Accounts.objects.create(AccountID="AC00129")
        merchant = Merchants.objects.create(MerchantID="M016")
        device = Devices.objects.create(DeviceID="D000052")

        create_transactions(account, merchant, device, num_transactions=1)

        # Call the endpoint
        url = reverse("flagged_transactions", kwargs={"account_id": "AC00129"})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that no transaction is flagged under “high deviation”
        self.assertEqual(len(response.data["results"]), 0)

    def test_no_flagged_most_frequent_locations(self):
        """Test edge case: Ensure that when all transactions occur within the top 3 most frequent locations, no transaction is flagged for unusual locations."""

        # Add a transaction with usual location contained in the base data (New York)

        create_transactions(
            self.account,
            self.merchant,
            self.device,
            location="New York",
            num_transactions=1,
        )

        # Call the endpoint
        url = reverse("flagged_transactions", kwargs={"account_id": "AC00128"})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_exact_threshold_for_login_attempts(self):
        """Test edge case: Test with transactions having exactly 3 login attempts. These should not be flagged."""
        # Add a transaction with the exact threshold of login attempts

        create_transactions(self.account, self.merchant, self.device, login_attempts=3)

        # Call the endpoint
        url = reverse("flagged_transactions", kwargs={"account_id": "AC00128"})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 0)

    def test_invalid_account_id(self):
        """Test error: Invalid or non-existent account_id."""
        url = reverse("flagged_transactions", kwargs={"account_id": "INVALID"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)


class HighFrequencyAccountsTests(APITestCase):
    # Tests for HighFrequencyAccounts endpoint
    @classmethod
    def setUpTestData(cls):
        cls.account, cls.merchant, cls.device, cls.transaction1 = create_test_data()

    def test_high_frequency_account_detected(self):
        """Test success: Retrieve high-frequency account."""
        # Create multiple transactions for an account within a short period (e.g., 15 transactions within 1 hour).
        create_transactions(
            self.account, self.merchant, self.device, num_transactions=15
        )

        # Call the endpoint
        url = reverse("high-frequency-accounts")
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["high_frequency_accounts"]), 1)

    def test_multiple_accounts_with_high_frequency(self):
        """Test success: Retrieve multiple accounts with high frequency."""
        # Create two additional accounts
        account1 = Accounts.objects.create(AccountID="AC00129")
        account2 = Accounts.objects.create(AccountID="AC00130")
        merchant = Merchants.objects.create(MerchantID="M016")
        device = Devices.objects.create(DeviceID="D000052")

        # Function to create multiple transactions for an account

        # Create high-frequency transactions for multiple accounts
        create_transactions(
            self.account, merchant, device, num_transactions=20
        )  # First account
        create_transactions(
            account1, merchant, device, num_transactions=25
        )  # Second account
        create_transactions(
            account2, merchant, device, num_transactions=30
        )  # Third account

        # Call the endpoint
        url = reverse("high-frequency-accounts")
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that all three accounts are flagged
        high_frequency_accounts = [
            account["AccountID"] for account in response.data["high_frequency_accounts"]
        ]
        self.assertIn("AC00128", high_frequency_accounts)
        self.assertIn("AC00129", high_frequency_accounts)
        self.assertIn("AC00130", high_frequency_accounts)
        self.assertEqual(len(high_frequency_accounts), 3)

    def test_accounts_with_normal_frequency(self):
        """Test success: Accounts with transactions spread over a larger time range are not flagged."""
        # Create transactions spread over a larger time range
        account1 = Accounts.objects.create(AccountID="AC00130")
        account2 = Accounts.objects.create(AccountID="AC00131")
        merchant = Merchants.objects.create(MerchantID="M017")
        device = Devices.objects.create(DeviceID="D000053")

        create_transactions(
            self.account, merchant, device, time_gap="weeks", num_transactions=5
        )
        create_transactions(
            account1, merchant, device, time_gap="weeks", num_transactions=5
        )
        create_transactions(
            account2, merchant, device, time_gap="weeks", num_transactions=5
        )

        # Call the endpoint
        url = reverse("high-frequency-accounts")
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        high_frequency_accounts = [
            account["AccountID"] for account in response.data["high_frequency_accounts"]
        ]
        self.assertNotIn("AC00130", high_frequency_accounts)  # Should not be flagged
        self.assertNotIn("AC00131", high_frequency_accounts)  # Should not be flagged

    def test_single_account_and_trasaction(self):
        """Test edge case: Only one transaction in the database.
        The transaction should not be flagged under “high frequency” since there is only one transaction.
        """

        # Call the endpoint
        url = reverse("high-frequency-accounts")
        response = self.client.get(url)
        print(response.data)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(
            len(response.data["high_frequency_accounts"]), 0
        )  # Should not be flagged

    def test_exact_threshold_transactions(self):
        """Test edge case: Test with transactions having exactly 10 transactions within 1 hour. These should not be flagged."""
        # Create multiple transactions for an account within a short period (e.g., 10 transactions within 1 hour).
        account = Accounts.objects.create(AccountID="AC00130")
        merchant = Merchants.objects.create(MerchantID="M016")
        device = Devices.objects.create(DeviceID="D000052")

        create_transactions(account, merchant, device, num_transactions=10)

        # Call the endpoint
        url = reverse("high-frequency-accounts")
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["high_frequency_accounts"]), 0)


class TransactionsSummaryByMerchantTests(APITestCase):
    # Tests for TransactionsSummaryByMerchant endpoint
    @classmethod
    def setUpTestData(cls):
        cls.account, cls.merchant, cls.device, cls.transaction1 = create_test_data()

    def test_valid_merchant_id(self):
        """Test success: Retrieve transaction summary for a valid merchant_id."""
        # Create multiple transactions for a merchant
        create_transactions(
            self.account,
            self.merchant,
            self.device,
            num_transactions=20,
            time_gap="days",
        )

        # Call the endpoint
        url = reverse("merchant-summary", kwargs={"merchant_id": "M015"})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("M015", response.data["merchant_id"])

    def test_merchant_with_no_transactions(self):
        """Test success: Merchant with no transactions."""
        # Create a new merchant without transactions
        Merchants.objects.create(MerchantID="M016")

        # Call the endpoint
        url = reverse("merchant-summary", kwargs={"merchant_id": "M016"})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_transactions"], 0)

    def test_merchant_with_single_transaction(self):
        """Test edge case: Merchant with a single transaction."""

        # Call the endpoint
        url = reverse("merchant-summary", kwargs={"merchant_id": "M015"})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_transactions"], 1)

    def test_high_transaction_volume(self):
        """Test success: Verify the endpoint handles the aggregation efficiently and returns the correct totals."""
        # Create a large number of transactions for a single merchant (e.g., 10,000 transactions)
        create_transactions(
            self.account,
            self.merchant,
            self.device,
            transaction_amount=100,
            num_transactions=10000,
            time_gap="days",
        )

        # Call the endpoint
        url = reverse("merchant-summary", kwargs={"merchant_id": "M015"})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_transactions"], 10001)
        self.assertEqual(response.data["total_amount"], 1000100.5)

    def test_invalid_merchant_id(self):
        """Test error: Invalid or non-existent merchant_id."""
        url = reverse("merchant-summary", kwargs={"merchant_id": "INVALID"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_transactions"], 0)

    def test_malformed_merchant_id(self):
        """Test error: Malformed merchant_id."""
        url = reverse("merchant-summary", kwargs={"merchant_id": "M0"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_transactions"], 0)


class SpendingInsightsTests(APITestCase):
    # Tests for SpendingInsights endpoint
    @classmethod
    def setUpTestData(cls):
        cls.account, cls.merchant, cls.device, cls.transaction1 = create_test_data()

        # Add additional transactions to generate insights
        create_transactions(
            cls.account,
            cls.merchant,
            cls.device,
            num_transactions=5,
            transaction_amount=150.50,
            transaction_type="Debit",
            location="New York",
        )
        create_transactions(
            cls.account,
            cls.merchant,
            cls.device,
            num_transactions=3,
            transaction_amount=200.00,
            transaction_type="Credit",
            location="Los Angeles",
        )
        create_transactions(
            cls.account,
            cls.merchant,
            cls.device,
            num_transactions=2,
            transaction_amount=50.75,
            transaction_type="Debit",
            location="Chicago",
        )

    def test_valid_account_id(self):
        """Test success: Retrieve spending insights for a valid account_id."""
        # Call the endpoint
        url = reverse(
            "transaction-spending-insights",
            kwargs={"account_id": self.account.AccountID},
        )
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify spending insights
        self.assertIn("spending_by_type", response.data)
        self.assertIn("most_used_merchant", response.data)
        self.assertIn("most_used_channel", response.data)
        self.assertIn("most_used_location", response.data)

        # Parse spending_by_type list
        spending_by_type = response.data["spending_by_type"]
        debit_data = next(
            (item for item in spending_by_type if item["TransactionType"] == "Debit"),
            None,
        )
        credit_data = next(
            (item for item in spending_by_type if item["TransactionType"] == "Credit"),
            None,
        )

        # Verify spending_by_type
        self.assertIsNotNone(debit_data)
        self.assertEqual(debit_data["total_amount"], 5 * 150.50 + 2 * 50.75)
        self.assertEqual(debit_data["transaction_count"], 7)

        self.assertIsNotNone(credit_data)
        self.assertEqual(credit_data["total_amount"], 3 * 200.00 + 100.50)
        self.assertEqual(credit_data["transaction_count"], 4)

        # Verify most_used values
        self.assertEqual(response.data["most_used_location"]["Location"], "New York")
        self.assertEqual(response.data["most_used_channel"]["Channel"], "ATM")
        self.assertEqual(
            response.data["most_used_merchant"]["MerchantID"], self.merchant.MerchantID
        )

    def test_account_with_single_transaction(self):
        """Test edge case: Account with only one transaction."""
        # Create a new account and a single transaction
        account = Accounts.objects.create(AccountID="AC00129")
        merchant = Merchants.objects.create(MerchantID="M016")
        device = Devices.objects.create(DeviceID="D000052")

        create_transactions(
            account,
            merchant,
            device,
            num_transactions=1,
            transaction_amount=200.75,
            transaction_type="Debit",
            location="San Francisco",
        )

        # Call the endpoint
        url = reverse(
            "transaction-spending-insights", kwargs={"account_id": account.AccountID}
        )
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify spending insights
        self.assertIn("spending_by_type", response.data)
        self.assertIn("most_used_merchant", response.data)
        self.assertIn("most_used_channel", response.data)
        self.assertIn("most_used_location", response.data)

        # Parse spending_by_type list
        spending_by_type = response.data["spending_by_type"]
        debit_data = next(
            (item for item in spending_by_type if item["TransactionType"] == "Debit"),
            None,
        )

        # Verify spending_by_type
        self.assertIsNotNone(debit_data)
        self.assertEqual(debit_data["total_amount"], 200.75)
        self.assertEqual(debit_data["transaction_count"], 1)

        # Verify most_used values
        self.assertEqual(
            response.data["most_used_location"],
            {"message": "All locations are used once"},
        )
        self.assertEqual(
            response.data["most_used_channel"],
            {"message": "All channels are used once"},
        )
        self.assertEqual(
            response.data["most_used_merchant"],
            {"message": "All merchants are used once"},
        )

    def test_account_with_no_transactions(self):
        """Test success: Account with no transactions."""
        # Create a new account without transactions
        account = Accounts.objects.create(AccountID="AC00129")

        # Call the endpoint
        url = reverse(
            "transaction-spending-insights", kwargs={"account_id": account.AccountID}
        )
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify spending insights
        self.assertIn("spending_by_type", response.data)
        self.assertIn("most_used_merchant", response.data)
        self.assertIn("most_used_channel", response.data)
        self.assertIn("most_used_location", response.data)

        # Verify spending_by_type
        self.assertEqual(len(response.data["spending_by_type"]), 0)

        # Verify most_used values
        self.assertIsNone(response.data["most_used_location"])
        self.assertIsNone(response.data["most_used_channel"])
        self.assertIsNone(response.data["most_used_merchant"])

    def test_multiple_transaction_types(self):
        """Test success: Account with transactions of multiple types."""
        # Create a new account and add transactions of different types
        account = Accounts.objects.create(AccountID="AC00130")
        merchant = Merchants.objects.create(MerchantID="M017")
        device = Devices.objects.create(DeviceID="D000053")

        # Create transactions with "Debit" type
        create_transactions(
            account,
            merchant,
            device,
            num_transactions=5,
            transaction_amount=150.00,
            transaction_type="Debit",
            location="New York",
        )

        # Create transactions with "Credit" type
        create_transactions(
            account,
            merchant,
            device,
            num_transactions=3,
            transaction_amount=200.00,
            transaction_type="Credit",
            location="Los Angeles",
        )

        # Call the endpoint
        url = reverse(
            "transaction-spending-insights", kwargs={"account_id": account.AccountID}
        )
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify spending insights
        self.assertIn("spending_by_type", response.data)
        spending_by_type = response.data["spending_by_type"]

        # Parse spending_by_type list
        debit_data = next(
            (item for item in spending_by_type if item["TransactionType"] == "Debit"),
            None,
        )
        credit_data = next(
            (item for item in spending_by_type if item["TransactionType"] == "Credit"),
            None,
        )

        # Verify spending_by_type for Debit
        self.assertIsNotNone(debit_data)
        self.assertEqual(debit_data["total_amount"], 5 * 150.00)
        self.assertEqual(debit_data["transaction_count"], 5)

        # Verify spending_by_type for Credit
        self.assertIsNotNone(credit_data)
        self.assertEqual(credit_data["total_amount"], 3 * 200.00)
        self.assertEqual(credit_data["transaction_count"], 3)

    def test_tied_most_used_values(self):
        """Test edge case: Tied most-used merchant, location, and channel."""
        # Create a new account
        account = Accounts.objects.create(AccountID="AC00131")
        merchant1 = Merchants.objects.create(MerchantID="M018")
        merchant2 = Merchants.objects.create(MerchantID="M019")
        device = Devices.objects.create(DeviceID="D000054")

        # Create transactions tied for most-used merchant
        create_transactions(
            account,
            merchant1,
            device,
            num_transactions=5,
            transaction_amount=100.00,
            transaction_type="Debit",
            location="San Francisco",
            channel="ATM",
        )
        create_transactions(
            account,
            merchant2,
            device,
            num_transactions=5,
            transaction_amount=100.00,
            transaction_type="Debit",
            location="San Francisco",
            channel="ATM",
        )

        # Call the endpoint
        url = reverse(
            "transaction-spending-insights", kwargs={"account_id": account.AccountID}
        )
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify spending insights
        self.assertIn("most_used_merchant", response.data)
        self.assertIn("most_used_location", response.data)
        self.assertIn("most_used_channel", response.data)

        # Check for ties in most-used values
        most_used_merchant = response.data["most_used_merchant"]
        most_used_location = response.data["most_used_location"]
        most_used_channel = response.data["most_used_channel"]

        # Verify tied most-used merchant
        self.assertIn(
            most_used_merchant["MerchantID"], ["M018", "M019"]
        )  # Either merchant1 or merchant2
        self.assertEqual(most_used_merchant["count"], 5)

        # Verify tied most-used location
        self.assertEqual(most_used_location["Location"], "San Francisco")
        self.assertEqual(most_used_location["count"], 10)

        # Verify tied most-used channel
        self.assertEqual(most_used_channel["Channel"], "ATM")
        self.assertEqual(most_used_channel["count"], 10)

    def test_large_number_of_transactions(self):
        """Test success: Handle a large number of transactions for an account efficiently."""
        # Create a new account
        account = Accounts.objects.create(AccountID="AC00132")
        merchant = Merchants.objects.create(MerchantID="M020")
        device = Devices.objects.create(DeviceID="D000055")

        # Generate a large number of transactions (e.g., 10,000)
        create_transactions(
            account,
            merchant,
            device,
            num_transactions=10000,
            transaction_amount=50.00,
            transaction_type="Debit",
            location="New York",
        )

        # Call the endpoint
        url = reverse(
            "transaction-spending-insights", kwargs={"account_id": account.AccountID}
        )
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify spending insights
        self.assertIn("spending_by_type", response.data)
        spending_by_type = response.data["spending_by_type"]

        # Parse spending_by_type list
        debit_data = next(
            (item for item in spending_by_type if item["TransactionType"] == "Debit"),
            None,
        )

        # Verify spending_by_type for Debit
        self.assertIsNotNone(debit_data)
        self.assertEqual(debit_data["total_amount"], 10000 * 50.00)
        self.assertEqual(debit_data["transaction_count"], 10000)

        # Verify the most-used values
        self.assertEqual(response.data["most_used_location"]["Location"], "New York")
        self.assertEqual(response.data["most_used_location"]["count"], 10000)
        self.assertEqual(response.data["most_used_channel"]["Channel"], "ATM")
        self.assertEqual(response.data["most_used_channel"]["count"], 10000)
        self.assertEqual(
            response.data["most_used_merchant"]["MerchantID"], merchant.MerchantID
        )
        self.assertEqual(response.data["most_used_merchant"]["count"], 10000)

    def test_invalid_account_id(self):
        """Test error: Invalid or non-existent account_id."""
        # Call the endpoint with an invalid account_id
        url = reverse("transaction-spending-insights", kwargs={"account_id": "INVALID"})
        response = self.client.get(url)

        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that the response contains empty spending insights
        self.assertEqual(len(response.data["spending_by_type"]), 0)
        self.assertIsNone(response.data["most_used_merchant"])
        self.assertIsNone(response.data["most_used_channel"])
        self.assertIsNone(response.data["most_used_location"])


class SeedDatabaseTests(TestCase):

    def test_seed_database_command(self):
        """
        Test that the populate_db command correctly seeds the database.
        """

        Accounts.objects.all().delete()
        Merchants.objects.all().delete()
        Devices.objects.all().delete()
        Transactions.objects.all().delete()

        # Ensure the database is empty
        self.assertEqual(Accounts.objects.count(), 0)
        self.assertEqual(Merchants.objects.count(), 0)
        self.assertEqual(Devices.objects.count(), 0)
        self.assertEqual(Transactions.objects.count(), 0)

        # Call the custom management command
        try:
            call_command("populate_db")
            print(f"Accounts: {Accounts.objects.count()}")
            print(f"Merchants: {Merchants.objects.count()}")
            print(f"Devices: {Devices.objects.count()}")
            print(f"Transactions: {Transactions.objects.count()}")
        except Exception as e:
            self.fail(f"populate_db command failed with error: {str(e)}")

        # Check that the data has been inserted
        self.assertGreater(Accounts.objects.count(), 0, "No accounts were seeded.")
        self.assertGreater(Merchants.objects.count(), 0, "No merchants were seeded.")
        self.assertGreater(Devices.objects.count(), 0, "No devices were seeded.")
        self.assertGreater(
            Transactions.objects.count(), 0, "No transactions were seeded."
        )

        # Validate one seeded record
        account = Accounts.objects.first()
        self.assertTrue(
            account.AccountID.startswith("AC"), "AccountID format is invalid."
        )
