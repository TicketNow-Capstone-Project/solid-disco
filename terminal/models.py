from django.db import models
from django.conf import settings
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
        plate = getattr(self.vehicle, 'plate_number', None) or getattr(self.vehicle, 'license_plate', None)
        return f"Balance for {plate or self.vehicle.pk}"


class EntryLog(models.Model):
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_INSUFFICIENT = 'insufficient'
    STATUS_INVALID = 'invalid'

    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_INSUFFICIENT, 'Insufficient Balance'),
        (STATUS_INVALID, 'Invalid QR'),
    ]

    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entry_logs'
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='terminal_actions'
    )
    fee_charged = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_FAILED)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    departed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Entry Log"
        verbose_name_plural = "Entry Logs"

    def __str__(self):
        plate = getattr(self.vehicle, 'plate_number', None) or getattr(self.vehicle, 'license_plate', None)
        state = "Active" if self.is_active else "Exited"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {plate or 'Unknown vehicle'} - {self.status} ({state})"


class SystemSettings(models.Model):
    terminal_fee = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    min_deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    entry_cooldown_minutes = models.PositiveIntegerField(default=5)
    departure_duration_minutes = models.PositiveIntegerField(default=30)

    # 🟢 NEW: Seat capacity limits (editable by admin)
    jeepney_max_seats = models.PositiveIntegerField(default=25)
    van_max_seats = models.PositiveIntegerField(default=15)
    bus_max_seats = models.PositiveIntegerField(default=60)

    theme_preference = models.CharField(
        max_length=10,
        choices=[('light', 'Light Mode'), ('dark', 'Dark Mode')],
        default='light'
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"System Settings (Fee: ₱{self.terminal_fee}, "
            f"Min Deposit: ₱{self.min_deposit_amount}, "
            f"Stay: {self.departure_duration_minutes} mins)"
        )

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj
