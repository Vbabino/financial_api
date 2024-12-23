from django.forms import inlineformset_factory
from django import forms
from .models import *


class TransactionsForm(forms.ModelForm):
    class Meta:
        model = Transactions
        fields = "__all__"
        exclude = ["TransactionID"]
        widgets = {
            "TransactionDate": forms.DateInput(attrs={"type": "date"}),
            "PreviousTransactionDate": forms.DateInput(attrs={"type": "date"}),
        }
