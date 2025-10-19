from django.db import models
from django.core.exceptions import ValidationError


class TerminalFeeBalance(models.Model):
    vehicle = models.OneToOneField(
        'vehicles.Vehicle',
        on_delete=models.CASCADE,
        related_name='fee_balance'
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def clean(self):
        if self.balance < 0:
            raise ValidationError("Balance cannot be negative.")

    def __str__(self):
        return f"Balance for {self.vehicle}"


class TerminalQueue(models.Model):  # ✅ renamed
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.CASCADE,
        related_name='queue_entries'
    )
    entry_time = models.DateTimeField(auto_now_add=True)
    departure_time = models.DateTimeField(null=True, blank=True)
    waiting_time = models.DurationField(default='00:30:00')

    def can_enter_queue(self):
        if hasattr(self.vehicle, 'fee_balance') and self.vehicle.fee_balance.balance <= 0:
            raise ValueError("Insufficient balance.")
        return True

    def __str__(self):
        return f"{self.vehicle.license_plate} Queue Entry"
