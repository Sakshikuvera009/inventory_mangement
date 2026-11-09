import csv, io
from datetime import date
from django.db import IntegrityError
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Product, Customer, SalesOrder, StockMovement
from .serializers import ProductSerializer, OrderCreateSerializer, OrderSerializer
from .services import create_order, confirm_order, cancel_order, adjust_stock
from .permissions import IsAdminRole

class ProductListAPI(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        qs = Product.objects.filter(is_active=True)
        q = self.request.query_params.get("search", "")
        if q: qs = qs.filter(Q(name__icontains=q) | Q(product_code__icontains=q))
        return qs.order_by("name")

class OrderListCreateAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = SalesOrder.objects.select_related("customer", "created_by").prefetch_related("items__product")
        if not request.user.is_superuser and request.user.role != "ADMIN": qs = qs.filter(created_by=request.user)
        return Response(OrderSerializer(qs, many=True).data)
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            customer = Customer.objects.get(pk=data["customer_id"], is_active=True)
            order = create_order(customer=customer, order_date=data["order_date"],
                discount_percentage=data["discount_percentage"], items=data["items"], user=request.user)
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except Customer.DoesNotExist: return Response({"error": "Active customer not found."}, status=404)
        except Product.DoesNotExist: return Response({"error": "One or more active products were not found."}, status=400)
        except ValueError as exc: return Response({"error": str(exc)}, status=400)

class OrderDetailAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, request, pk):
        qs = SalesOrder.objects.select_related("customer", "created_by").prefetch_related("items__product")
        if not request.user.is_superuser and request.user.role != "ADMIN": qs = qs.filter(created_by=request.user)
        return qs.get(pk=pk)
    def get(self, request, pk):
        try: return Response(OrderSerializer(self.get_object(request, pk)).data)
        except SalesOrder.DoesNotExist: return Response({"error": "Order not found."}, status=404)
    def post(self, request, pk, action):
        try:
            order = self.get_object(request, pk)
            if action == "confirm": order = confirm_order(pk, request.user)
            elif action == "cancel": order = cancel_order(pk, request.user)
            else: return Response({"error": "Unknown action."}, status=404)
            return Response(OrderSerializer(order).data)
        except SalesOrder.DoesNotExist: return Response({"error": "Order not found."}, status=404)
        except ValueError as exc: return Response({"error": str(exc)}, status=400)

class StockAdjustmentAPI(APIView):
    permission_classes = [IsAdminRole]
    def post(self, request, pk):
        try:
            product = adjust_stock(pk, int(request.data.get("quantity_change")), str(request.data.get("reason", "")), request.user)
            return Response(ProductSerializer(product).data)
        except (ValueError, TypeError) as exc: return Response({"error": str(exc)}, status=400)
        except Product.DoesNotExist: return Response({"error": "Product not found."}, status=404)

class ProductCSVImportAPI(APIView):
    permission_classes = [IsAdminRole]
    def post(self, request):
        upload = request.FILES.get("file")
        if not upload: return Response({"error": "Upload a CSV file using field 'file'."}, status=400)
        try: rows = list(csv.DictReader(io.StringIO(upload.read().decode("utf-8-sig"))))
        except UnicodeDecodeError: return Response({"error": "CSV must be UTF-8 encoded."}, status=400)
        required = ["product_code", "product_name", "category", "price", "stock_quantity", "status"]
        if not rows or not set(required).issubset(rows[0].keys()):
            return Response({"error": "Required columns: " + ", ".join(required)}, status=400)
        errors, seen, clean = [], set(), []
        for line, row in enumerate(rows, start=2):
            code = (row.get("product_code") or "").strip()
            try:
                name = (row.get("product_name") or "").strip()
                category = (row.get("category") or "").strip()
                price = float(row.get("price", ""))
                stock = int(row.get("stock_quantity", ""))
                active = (row.get("status") or "").strip().lower()
                if not code or not name: raise ValueError("product_code and product_name are required")
                if code in seen: raise ValueError("duplicate product_code in file")
                if Product.objects.filter(product_code=code).exists(): raise ValueError("product_code already exists")
                if price < 0 or stock < 0: raise ValueError("price and stock must be non-negative")
                if active not in ("active", "inactive"): raise ValueError("status must be Active or Inactive")
                seen.add(code); clean.append((code, name, category, price, stock, active == "active"))
            except (ValueError, TypeError) as exc: errors.append({"row": line, "reason": str(exc)})
        if errors: return Response({"imported": 0, "errors": errors}, status=400)
        from django.db import transaction
        with transaction.atomic():
            for code, name, category, price, stock, active in clean:
                p = Product.objects.create(product_code=code, name=name, category=category, price=price, stock_quantity=stock, is_active=active)
                if stock:
                    StockMovement.objects.create(product=p, movement_type="OPENING", quantity_change=stock,
                        reason="CSV opening stock", created_by=request.user)
        return Response({"imported": len(clean), "errors": []}, status=201)

class ReportsAPI(APIView):
    permission_classes = [IsAdminRole]
    def get(self, request):
        start = request.query_params.get("start_date", "2000-01-01")
        end = request.query_params.get("end_date", "2100-12-31")
        threshold = int(request.query_params.get("threshold", 10))
        confirmed = SalesOrder.objects.filter(status="CONFIRMED", order_date__range=[start, end])
        customer_sales = list(Customer.objects.annotate(
            confirmed_order_count=Count("orders", filter=Q(orders__status="CONFIRMED", orders__order_date__range=[start, end])),
            total_sales=Sum("orders__grand_total", filter=Q(orders__status="CONFIRMED", orders__order_date__range=[start, end]))
        ).values("id", "name", "confirmed_order_count", "total_sales"))
        product_sales = list(Product.objects.annotate(quantity_sold=Sum("order_items__quantity",
            filter=Q(order_items__sales_order__status="CONFIRMED", order_items__sales_order__order_date__range=[start, end])),
            gross_item_value=Sum("order_items__amount",
            filter=Q(order_items__sales_order__status="CONFIRMED", order_items__sales_order__order_date__range=[start, end]))
        ).values("id", "name", "quantity_sold", "gross_item_value"))
        low_stock = list(Product.objects.filter(stock_quantity__lt=threshold).values("product_code", "name", "stock_quantity"))
        movements = list(StockMovement.objects.select_related("product", "sales_order").values(
            "product__name", "movement_type", "quantity_change", "sales_order__order_number", "reason", "created_at")[:500])
        return Response({"customer_sales": customer_sales, "product_sales": product_sales,
                         "low_stock": low_stock, "stock_movements": movements})

class CustomerListAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = Customer.objects.all()
        if request.query_params.get("status") in ("active", "inactive"):
            qs = qs.filter(is_active=request.query_params["status"] == "active")
        q = request.query_params.get("search", "")
        if q: qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(mobile__icontains=q))
        return Response(list(qs.values("id", "name", "email", "mobile", "city", "is_active")))
    def post(self, request):
        if not (request.user.is_superuser or request.user.role == "ADMIN"): return Response({"error":"Admin only."}, status=403)
        c = Customer.objects.create(**{k:v for k,v in request.data.items() if k in ["name","email","mobile","city","is_active"]})
        return Response({"id":c.id, "name":c.name}, status=201)

class CustomerUpdateAPI(APIView):
    permission_classes = [IsAdminRole]
    def patch(self, request, pk):
        try: c = Customer.objects.get(pk=pk)
        except Customer.DoesNotExist: return Response({"error":"Customer not found."}, status=404)
        for k in ["name","email","mobile","city","is_active"]:
            if k in request.data: setattr(c,k,request.data[k])
        c.save()
        return Response({"id":c.id,"name":c.name,"is_active":c.is_active})
