from django.contrib import admin
from .models import TerminalQueue, TerminalFeeBalance

admin.site.register(TerminalQueue)
admin.site.register(TerminalFeeBalance)
