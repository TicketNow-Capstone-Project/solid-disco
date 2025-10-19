from django.db import models
from terminal.models import TerminalQueue

class Trip(models.Model):
    # ✅ Use string reference to avoid circular import issues
    queue_entry = models.ForeignKey(
        'terminal.TerminalQueue',   # <-- references TerminalQueue model in terminal app
        on_delete=models.CASCADE,
        related_name='trips',
        null=True,
        blank=True
    )
    
    departure_time = models.DateTimeField()
    status = models.CharField(max_length=50, default='Scheduled')

    def __str__(self):
        queue_info = f" for {self.queue_entry}" if self.queue_entry else ""
        return f"Trip{queue_info} at {self.departure_time.strftime('%Y-%m-%d %H:%M')}"