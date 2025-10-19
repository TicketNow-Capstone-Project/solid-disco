from django.db import models
from django.utils import timezone
from accounts.models import CustomUser


class Profit(models.Model):
    recorded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profits_recorded'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)
    date_recorded = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date_recorded']
        verbose_name = "Profit Record"
        verbose_name_plural = "Profit Records"

    def __str__(self):
        return f"₱{self.amount} - {self.date_recorded.strftime('%Y-%m-%d %H:%M:%S')}"
