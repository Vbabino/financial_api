from django.utils import timezone
from datetime import timedelta
from transactions_app.models import *


def create_test_data():
    account = Accounts.objects.create(AccountID="AC00128")
    merchant = Merchants.objects.create(MerchantID="M015")
    device = Devices.objects.create(DeviceID="D000051")
    base_data = {
        "AccountID": account,
        "TransactionDate": timezone.now(),
        "TransactionAmount": 100.50,
        "TransactionType": "Credit",
        "TransactionDuration": 120,
        "Location": "New York",
        "LoginAttempts": 1,
        "IPAddress": "192.168.1.1",
        "MerchantID": merchant,
        "Channel": "ATM",
        "DeviceID": device,
        "CustomerAge": 30,
        "CustomerOccupation": "Engineer",
        "AccountBalance": 4900,
        "PreviousTransactionDate": "2023-01-01 12:00:00",
    }
    transaction = Transactions.objects.create(**base_data)
    return account, merchant, device, transaction



def create_transactions(
    account, 
    merchant, 
    device, 
    transaction_amount=100.50, 
    num_transactions=15, 
    time_gap="minutes",
    transaction_type="Credit",
    transaction_duration=120,
    location="New York",
    login_attempts=1,
    ip_address="192.168.1.1",
    channel="ATM",
    customer_age=30,
    customer_occupation="Engineer",
    account_balance=4900
):
    """
    Helper function to create transactions for an account.

    Args:
        account (Accounts): The account instance
        merchant (Merchants): The merchant instance
        device (Devices): The device instance
        transaction_amount (float): Amount for transaction
        num_transactions (int): Number of transactions to create
        time_gap (str): Time gap between transactions ("minutes" or "days")
        transaction_type (str): Type of transaction
        transaction_duration (int): Duration in minutes
        location (str): Transaction location
        login_attempts (int): Number of login attempts
        ip_address (str): IP address
        channel (str): Transaction channel 
        customer_age (int): Age of customer
        customer_occupation (str): Customer occupation
        account_balance (float): Account balance
    """
    now = timezone.now()
    
    base_data = {
        "AccountID": account,
        "TransactionAmount": transaction_amount,
        "TransactionType": transaction_type,
        "TransactionDuration": transaction_duration,
        "Location": location,
        "LoginAttempts": login_attempts,
        "IPAddress": ip_address,
        "MerchantID": merchant,
        "Channel": channel,
        "DeviceID": device,
        "CustomerAge": customer_age,
        "CustomerOccupation": customer_occupation,
        "AccountBalance": account_balance,
        "PreviousTransactionDate": now - timedelta(days=1),
    }

    for i in range(num_transactions):
        if time_gap == "minutes":
            base_data["TransactionDate"] = now - timedelta(minutes=i)
        elif time_gap == "days":
            base_data["TransactionDate"] = now - timedelta(days=i)
        elif time_gap == "weeks":
            base_data["TransactionDate"] = now - timedelta(weeks=i)
        Transactions.objects.create(**base_data)
