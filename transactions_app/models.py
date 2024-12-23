from django.utils import timezone

from django.db import models  # type: ignore
from django.core.validators import MinValueValidator  # type: ignore


# Transactions model
class Transactions(models.Model):
    TransactionID = models.CharField(max_length=10, unique=True, primary_key=True)
    AccountID = models.ForeignKey("Accounts", on_delete=models.CASCADE)
    TransactionAmount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )  # amount cannot be negative
    TransactionDate = models.DateTimeField(default=timezone.now)
    TransactionType = models.CharField(
        max_length=10, choices=[("Credit", "Credit"), ("Debit", "Debit")]
    )
    TransactionDuration = models.IntegerField(
        validators=[MinValueValidator(0)]
    )  # duration cannot be negative
    LoginAttempts = models.IntegerField(
        validators=[MinValueValidator(0)]
    )  # login attempts cannot be negative

    CustomerAge = models.IntegerField(
        validators=[MinValueValidator(0)], default=15
    )  # age cannot be negative
    CustomerOccupation = models.CharField(max_length=50, default="Other")
    AccountBalance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )  # balance cannot be negative
    PreviousTransactionDate = models.DateTimeField(default=timezone.now)
    Location = models.CharField(max_length=50, null=False, blank=False)

    IPAddress = models.GenericIPAddressField(default="0.0.0.0", null=False, blank=False)

    MerchantID = models.ForeignKey("Merchants", on_delete=models.CASCADE)

    Channel = models.CharField(
        max_length=50, choices=[("ATM", "ATM"), ("Online", "Online"), ("Branch", "Branch")]
    )
    DeviceID = models.ForeignKey("Devices", on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.TransactionID:
            last_transaction = Transactions.objects.order_by("-TransactionID").first()
            if last_transaction:
                last_id = int(
                    last_transaction.TransactionID[2:]
                )  # Extract the numeric part
                new_id = f"TX{last_id + 1:06d}"  # Increment and format
            else:
                new_id = "TX000001"  # Start the sequence
            self.TransactionID = new_id
        super().save(*args, **kwargs)


# Accounts model
class Accounts(models.Model):
    AccountID = models.CharField(max_length=10, unique=True, primary_key=True)

    def save(self, *args, **kwargs):
        if not self.AccountID:
            last_account = Accounts.objects.order_by("-AccountID").first()
            if last_account:
                last_id = int(last_account.AccountID[2:])  # Extract the numeric part
                new_id = f"AC{last_id + 1:05d}"  # Increment and format
            else:
                new_id = "AC00001"  # Start the sequence
            self.AccountID = new_id
        super().save(*args, **kwargs)

    def __str__(self):
        return self.AccountID


# Merchant model
class Merchants(models.Model):
    MerchantID = models.CharField(max_length=10, unique=True, primary_key=True)

    def save(self, *args, **kwargs):
        if not self.MerchantID:
            last_merchant = Merchants.objects.order_by("-MerchantID").first()
            if last_merchant:
                last_id = int(last_merchant.MerchantID[1:])  # Extract the numeric part
                new_id = f"M{last_id + 1:03d}"  # Increment and format with four digits
            else:
                new_id = "M001"  # Start the sequence
            self.MerchantID = new_id
        super().save(*args, **kwargs)

    def __str__(self):
        return self.MerchantID


# Device model
class Devices(models.Model):
    DeviceID = models.CharField(max_length=10, unique=True, primary_key=True)

    def save(self, *args, **kwargs):
        if not self.DeviceID:
            last_device = Devices.objects.order_by("-DeviceID").first()
            if last_device:
                last_id = int(last_device.DeviceID[1:])  # Extract the numeric part
                new_id = f"D{last_id + 1:06d}"  # Increment and format with four digits
            else:
                new_id = "D000001"  # Start the sequence
            self.DeviceID = new_id
        super().save(*args, **kwargs)

    def __str__(self):
        return self.DeviceID

