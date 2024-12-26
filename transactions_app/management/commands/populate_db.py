import os
import pandas as pd
from django.core.management.base import BaseCommand
from transactions_app.models import Accounts, Merchants, Devices, Transactions
from django.utils.timezone import make_aware
from datetime import datetime


class Command(BaseCommand):
    help = "Populate the database with data from the CSV file."

    def handle(self, *args, **kwargs):
        # Define the relative path to the CSV file
        csv_path = os.path.join("data_set", "bank_transactions_data.csv")

        # Read the data from the CSV file
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            self.stderr.write(f"Error reading CSV file: {e}")
            return

        # Populate the Accounts table
        try:
            for account_id in df["AccountID"].unique():
                Accounts.objects.get_or_create(AccountID=account_id)
        except Exception as e:
            self.stderr.write(f"Error inserting accounts: {e}")

        # Populate the Merchants table
        try:
            for merchant_id in df["MerchantID"].unique():
                Merchants.objects.get_or_create(MerchantID=merchant_id)
        except Exception as e:
            self.stderr.write(f"Error inserting merchants: {e}")

        # Populate the Devices table
        try:
            for device_id in df["DeviceID"].unique():
                Devices.objects.get_or_create(DeviceID=device_id)
        except Exception as e:
            self.stderr.write(f"Error inserting devices: {e}")

        # Populate the Transactions table
        for _, row in df.iterrows():
            try:
                Transactions.objects.update_or_create(
                    TransactionID=row["TransactionID"],
                    defaults={
                        "AccountID_id": row["AccountID"],
                        "MerchantID_id": row["MerchantID"],
                        "DeviceID_id": row["DeviceID"],
                        "TransactionAmount": row["TransactionAmount"],
                        "TransactionDate": make_aware(
                            datetime.strptime(
                                row["TransactionDate"], "%Y-%m-%d %H:%M:%S"
                            )
                        ),
                        "TransactionType": row["TransactionType"],
                        "TransactionDuration": row["TransactionDuration"],
                        "LoginAttempts": row["LoginAttempts"],
                        "Channel": row["Channel"],
                        "Location": row["Location"],
                        "IPAddress": row["IPAddress"],
                        "CustomerAge": row["CustomerAge"],
                        "CustomerOccupation": row["CustomerOccupation"],
                        "AccountBalance": row["AccountBalance"],
                        "PreviousTransactionDate": make_aware(
                            datetime.strptime(
                                row["PreviousTransactionDate"], "%Y-%m-%d %H:%M:%S"
                            )
                        ),
                    },
                )
            except Exception as e:
                self.stderr.write(
                    f"Error inserting transaction {row['TransactionID']}: {e}"
                )
