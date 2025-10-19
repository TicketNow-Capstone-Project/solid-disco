from django.shortcuts import render
from .models import Profit

def profit_report_view(request):
    profits = Profit.objects.all()
    total = sum(p.amount for p in profits)
    context = {
        'profits': profits,
        'total': total,
    }
    return render(request, 'reports/profit_report.html', context)
