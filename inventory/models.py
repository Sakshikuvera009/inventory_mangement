from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        SALES = "SALES", "Sales User"
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.SALES)

    @property
    def is_admin_user(self):
        return self.is_superuser or self.role == self.Role.ADMIN

class Customer(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"]), models.Index(fields=["mobile"])]
    def __str__(self): return self.name

class Product(models.Model):
    product_code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["product_code"]), models.Index(fields=["category", "is_active"])]
    def __str__(self): return f"{self.product_code} - {self.name}"

class SalesOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
    order_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    order_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(20)])
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales_orders")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["order_date", "status"]), models.Index(fields=["customer", "status"])]
    def __str__(self): return self.order_number

class SalesOrderItem(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["sales_order", "product"], name="unique_product_per_order")]

class StockMovement(models.Model):
    class Type(models.TextChoices):
        OPENING = "OPENING", "Opening Stock"
        IN = "IN", "Stock In"
        OUT = "OUT", "Stock Out"
        SALE = "SALE", "Sale"
        SALE_RETURN = "SALE_RETURN", "Sale Return"
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=Type.choices)
    quantity_change = models.IntegerField()
    sales_order = models.ForeignKey(SalesOrder, null=True, blank=True, on_delete=models.PROTECT, related_name="stock_movements")
    reason = models.CharField(max_length=255)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "created_at"])]
