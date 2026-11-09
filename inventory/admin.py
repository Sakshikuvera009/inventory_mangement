from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Customer, Product, SalesOrder, SalesOrderItem, StockMovement
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Application role", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Application role", {"fields": ("role",)}),)
admin.site.register([Customer, Product, SalesOrder, SalesOrderItem, StockMovement])
