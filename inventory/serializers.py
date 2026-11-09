from rest_framework import serializers
from .models import Product, Customer, SalesOrder, SalesOrderItem

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "product_code", "name", "category", "price", "stock_quantity", "is_active"]
        read_only_fields = ["stock_quantity"]
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "email", "mobile", "city", "is_active"]
class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)
class OrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(min_value=1)
    order_date = serializers.DateField()
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=20)
    items = OrderItemInputSerializer(many=True, allow_empty=False)
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.product_code", read_only=True)
    class Meta:
        model = SalesOrderItem
        fields = ["id", "product", "product_code", "product_name", "quantity", "rate", "amount"]
class OrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = SalesOrder
        fields = ["id", "order_number", "customer", "customer_name", "order_date", "status",
                  "discount_percentage", "subtotal", "discount_amount", "grand_total", "items", "created_by"]
