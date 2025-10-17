from django.contrib import admin
from .models import Driver, Vehicle
from django.utils.html import format_html

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('driver_id', 'first_name', 'last_name', 'license_number', 'city_municipality', 'province')
    search_fields = ('first_name', 'last_name', 'license_number', 'driver_id')


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_name', 'license_plate', 'vehicle_type', 'assigned_driver', 'qr_code_display')
    list_filter = ('vehicle_type',)
    search_fields = (
                    'license_plate', 
                    'vehicle_name',
                    'assigned_driver__first_name',
                    'assigned_driver__last_name',
                    'vehicle_type',
)

    readonly_fields = ('qr_code_preview',)  # 👈 preview only

    exclude = ('qr_code',)  # 👈 hides the upload field

    def qr_code_display(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="100" height="100" />', obj.qr_code.url)
        return "No QR Code"
    qr_code_display.short_description = "QR Code"

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="150" height="150" />', obj.qr_code.url)
        return "QR code will be generated after saving."
    qr_code_preview.short_description = "QR Code Preview"
