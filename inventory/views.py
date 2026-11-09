from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from .forms import RegisterForm
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import date
from .models import Product, Customer, SalesOrder
from .permissions import is_admin

@login_required
def dashboard(request):
    orders = SalesOrder.objects.select_related("customer", "created_by")
    if not is_admin(request.user): orders = orders.filter(created_by=request.user)
    today = timezone.localdate()
    month_index = today.year * 12 + today.month - 1 - 5
    chart_start = date(month_index // 12, month_index % 12 + 1, 1)
    monthly_totals = {
        row["month"].strftime("%Y-%m"): row["total"] or 0
        for row in orders.filter(status="CONFIRMED", order_date__gte=chart_start)
        .annotate(month=TruncMonth("order_date"))
        .values("month")
        .annotate(total=Sum("grand_total"))
    }
    sales_chart = []
    for offset in range(6):
        month_index = chart_start.year * 12 + chart_start.month - 1 + offset
        month = date(month_index // 12, month_index % 12 + 1, 1)
        sales_chart.append({
            "label": month.strftime("%b"),
            "x": 45 + offset * 105,
            "total": monthly_totals.get(month.strftime("%Y-%m"), 0),
        })
    chart_max = max((item["total"] for item in sales_chart), default=0)
    for item in sales_chart:
        item["height"] = max(4, round(float(item["total"] / chart_max * 100))) if chart_max else 4
        item["y"] = 125 - item["height"]
    total_sales = orders.filter(status="CONFIRMED").aggregate(total=Sum("grand_total"))["total"] or 0
    return render(request, "dashboard.html", {
        "products": Product.objects.filter(is_active=True).count(),
        "customers": Customer.objects.filter(is_active=True).count(),
        "drafts": orders.filter(status="DRAFT").count(),
        "confirmed": orders.filter(status="CONFIRMED").count(),
        "total_sales": total_sales,
        "low_stock_products": Product.objects.filter(is_active=True, stock_quantity__lte=10).order_by("stock_quantity", "name")[:6],
        "sales_chart": sales_chart,
        "orders": orders[:12], "is_admin": is_admin(request.user),
    })
@login_required
def customers_page(request):
    q=request.GET.get("q","")
    qs=Customer.objects.filter(Q(name__icontains=q)|Q(email__icontains=q)|Q(mobile__icontains=q))
    return render(request,"customers.html",{"customers":qs,"is_admin":is_admin(request.user)})
@login_required
def products_page(request):
    q=request.GET.get("q","")
    qs=Product.objects.filter(Q(name__icontains=q)|Q(product_code__icontains=q))
    return render(request,"products.html",{"products":qs,"is_admin":is_admin(request.user)})
@login_required
def orders_page(request):
    qs=SalesOrder.objects.select_related("customer","created_by")
    if not is_admin(request.user): qs=qs.filter(created_by=request.user)
    return render(request,"orders.html",{"orders":qs,"is_admin":is_admin(request.user)})
@login_required
@login_required
def new_order_page(request):
    customers = Customer.objects.filter(is_active=True)

    products = list(
        Product.objects.filter(is_active=True).values(
            "id",
            "name",
            "product_code",
            "price",
            "stock_quantity"
        )
    )

    return render(request, "new_order.html", {
        "customers": customers,
        "products": products
    })
    return render(request,"new_order.html",{"customers":Customer.objects.filter(is_active=True),"products":Product.objects.filter(is_active=True)})
@login_required
def reports_page(request):
    if not is_admin(request.user):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request,"reports.html")
@login_required
def import_page(request):
    if not is_admin(request.user):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request,"import.html")

def register(request):
    """Public sign-up page. New accounts are always Sales Users."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Welcome to Northstar, {user.first_name or user.username}! Your account is ready.")
        return redirect("dashboard")
    return render(request, "register.html", {"form": form})
