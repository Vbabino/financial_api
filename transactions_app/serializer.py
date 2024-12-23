import datetime
from decimal import Decimal
from django.utils.timezone import now
from rest_framework import serializers
from .models import *
from django.core.validators import RegexValidator


class TransactionsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transactions
        exclude = ["TransactionID"]

    # Validators for the fields in the Transactions model:

    # AccountID: Must be in the format ACXXXXX (e.g., AC00128).
    AccountID = serializers.CharField(
        validators=[
            RegexValidator(
                regex=r"^AC\d{5}$",
                message="AccountID must be in the format ACXXXXX (e.g., AC00128).",
                code="invalid_account_id",
            )
        ],
        error_messages={
            
            "required": "AccountID is required.",
            "blank": "AccountID cannot be blank.",
        },
    )

    # MerchantID: Must be in the format MXXX (e.g., M001).
    MerchantID = serializers.CharField(
        validators=[
            RegexValidator(
                regex=r"^M\d{3}$",
                message="MerchantID must be in the format MXXX (e.g., M001).",
                code="invalid_merchant_id",
            )
        ],
        error_messages={
            "required": "MerchantID is required.",
            "blank": "MerchantID cannot be blank.",
        },
    )

    # DeviceID: Must be in the format DXXXXXX (e.g., D000128).
    DeviceID = serializers.CharField(
        validators=[
            RegexValidator(
                regex=r"^D\d{6}$",
                message="DeviceID must be in the format DXXXXXX (e.g., D000128).",
                code="invalid_device_id",
            )
        ],
        error_messages={
            "required": "DeviceID is required.",
            "blank": "DeviceID cannot be blank.",
        },
    )

    Channel = serializers.ChoiceField(
        choices=[("ATM", "ATM"), ("Online", "Online"), ("Branch", "Branch")],
        error_messages={
            "invalid_choice": "Channel must be one of: ATM, Online, or Branch.",
        },
    )

    TransactionType = serializers.ChoiceField(
        choices=[("Credit", "Credit"), ("Debit", "Debit")],
        error_messages={
            "invalid_choice": "TransactionType must be one of: Credit, Debit.",
        },
    )

    def validate_AccountID(self, value):
        # Check if the AccountID exists in the database
        try:
            return Accounts.objects.get(AccountID=value)
        except Accounts.DoesNotExist:
            raise serializers.ValidationError("Invalid AccountID. Account does not exist.")
    
    def validate_MerchantID(self, value):
        # Check if the MerchantID exists in the database
        try:
            return Merchants.objects.get(MerchantID=value)
        except Merchants.DoesNotExist:
            raise serializers.ValidationError("Invalid MerchantID. Merchant does not exist.")
    
    def validate_DeviceID(self, value):
        # Check if the DeviceID exists in the database
        try:
            return Devices.objects.get(DeviceID=value)
        except Devices.DoesNotExist:
            raise serializers.ValidationError("Invalid DeviceID. Device does not exist.")

    # Make sure the TransactionDate is not in the future
    def validate_TransactionDate(self, value):
        if value > now():  # Compare with the current datetime
            raise serializers.ValidationError(
                "Transaction date must not be in the future."
            )
        return value

    # Make sure PreviousTransactionDate is not in the future
    def validate_PreviousTransactionDate(self, value):
        if value > now():  # Compare with the current datetime
            raise serializers.ValidationError(
                "Previous transaction date must not be in the future."
            )
        return value

    # Make sure the Location is not empty
    def validate_Location(self, value):
        if not value:
            raise serializers.ValidationError("Location must not be empty.")
        return value
