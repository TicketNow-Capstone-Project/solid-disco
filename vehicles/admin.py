from django.contrib import admin
from .models import Driver, Vehicle, Wallet, Deposit
from django.utils.html import format_html

# Inline for Deposit model
class DepositInline(admin.TabularInline):
    model = Deposit
    extra = 0
    readonly_fields = ('reference_number', 'amount', 'payment_method', 'status', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'balance_display', 'currency', 'status', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = (
        'vehicle__license_plate',
        'vehicle__vehicle_name',
        'vehicle__assigned_driver__first_name',
        'vehicle__assigned_driver__last_name',
    )
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20
    inlines = [DepositInline]  # Add this line to see deposits in wallet admin
    
    def balance_display(self, obj):
        return f"{obj.balance:,.2f} {obj.currency}"
    balance_display.short_description = 'Balance'

# Keep the other admin classes the same as above...
@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('driver_id', 'first_name', 'last_name', 'license_number', 'city_municipality', 'province')
    search_fields = ('first_name', 'last_name', 'license_number', 'driver_id')
    list_per_page = 20

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_name', 'license_plate', 'vehicle_type', 'assigned_driver', 'qr_code_display')
    list_filter = ('vehicle_type', 'ownership_type')
    search_fields = (
        'license_plate', 
        'vehicle_name',
        'assigned_driver__first_name',
        'assigned_driver__last_name',
        'vehicle_type',
    )
    readonly_fields = ('qr_code_preview',)
    exclude = ('qr_code',)
    list_per_page = 20

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

    
@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'wallet_display', 'amount_display', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = (
        'reference_number',
        'wallet__vehicle__license_plate',
        'wallet__vehicle__vehicle_name',
        'payment_method',
    )
    readonly_fields = ('reference_number', 'created_at')  # ✅ removed updated_at
    list_per_page = 20
    
    def wallet_display(self, obj):
        return f"{obj.wallet.vehicle.assigned_driver} - {obj.wallet.vehicle.license_plate}"
    wallet_display.short_description = 'Wallet (Driver - Plate)'
    
    def amount_display(self, obj):
        return f"{obj.amount:,.2f} {obj.wallet.currency}"
    amount_display.short_description = 'Amount'
