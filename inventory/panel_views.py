"""Custom admin panel (/panel/). Only Admin-role users and superusers can open it."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CustomerForm, PanelUserForm, ProductForm, StockAdjustForm
from .models import Customer, Product, SalesOrder, StockMovement
from .permissions import is_admin
from .services import adjust_stock

User = get_user_model()
LOW_STOCK = 10


def panel_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def _form_page(request, form, *, title, subtitle, eyebrow, back_url, submit_label, extra_note=""):
    return render(request, "panel/form.html", {
        "form": form, "title": title, "subtitle": subtitle, "eyebrow": eyebrow,
        "back_url": back_url, "submit_label": submit_label, "extra_note": extra_note,
    })


# ---------------------------------------------------------------- dashboard
@panel_required
def dashboard(request):
    orders = SalesOrder.objects.all()
    confirmed = orders.filter(status="CONFIRMED")
    revenue = confirmed.aggregate(t=Sum("grand_total"))["t"] or 0
    return render(request, "panel/dashboard.html", {
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "admins": User.objects.filter(Q(role="ADMIN") | Q(is_superuser=True)).distinct().count(),
        "customers": Customer.objects.filter(is_active=True).count(),
        "products": Product.objects.filter(is_active=True).count(),
        "low_stock_count": Product.objects.filter(is_active=True, stock_quantity__lte=LOW_STOCK).count(),
        "drafts": orders.filter(status="DRAFT").count(),
        "confirmed_count": confirmed.count(),
        "revenue": revenue,
        "recent_users": User.objects.order_by("-date_joined")[:5],
        "recent_orders": orders.select_related("customer", "created_by")[:6],
        "low_stock": Product.objects.filter(is_active=True, stock_quantity__lte=LOW_STOCK).order_by("stock_quantity", "name")[:6],
        "recent_movements": StockMovement.objects.select_related("product", "created_by")[:6],
    })


# ---------------------------------------------------------------- users
@panel_required
def users(request):
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    state = request.GET.get("state", "")
    qs = User.objects.annotate(order_count=Count("sales_orders")).order_by("-date_joined")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    if role == "ADMIN":
        qs = qs.filter(Q(role="ADMIN") | Q(is_superuser=True))
    elif role == "SALES":
        qs = qs.filter(role="SALES", is_superuser=False)
    if state == "active":
        qs = qs.filter(is_active=True)
    elif state == "inactive":
        qs = qs.filter(is_active=False)
    return render(request, "panel/users.html", {"users": qs, "q": q, "role": role, "state": state})


@panel_required
def user_add(request):
    form = PanelUserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"User “{user.username}” was created.")
        return redirect("panel_users")
    return _form_page(request, form, title="Add user", eyebrow="User management",
                      subtitle="Create an account for a teammate and choose what they can access.",
                      back_url="panel_users", submit_label="Create user")


@panel_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = PanelUserForm(request.POST or None, instance=user, editing_self=(user.pk == request.user.pk))
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"User “{user.username}” was updated.")
        return redirect("panel_users")
    return _form_page(request, form, title=f"Edit {user.username}", eyebrow="User management",
                      subtitle="Update profile details, role, access or reset the password.",
                      back_url="panel_users", submit_label="Save changes")


@panel_required
@require_POST
def user_toggle(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(request, f"“{user.username}” is now {'active' if user.is_active else 'inactive'}.")
    return redirect("panel_users")


# ---------------------------------------------------------------- customers
@panel_required
def customers(request):
    q = request.GET.get("q", "").strip()
    state = request.GET.get("state", "")
    qs = Customer.objects.annotate(order_count=Count("orders"))
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(mobile__icontains=q) | Q(city__icontains=q))
    if state == "active":
        qs = qs.filter(is_active=True)
    elif state == "inactive":
        qs = qs.filter(is_active=False)
    return render(request, "panel/customers.html", {"customers": qs, "q": q, "state": state})


@panel_required
def customer_add(request):
    form = CustomerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        c = form.save()
        messages.success(request, f"Customer “{c.name}” was added.")
        return redirect("panel_customers")
    return _form_page(request, form, title="Add customer", eyebrow="Customers",
                      subtitle="Add a customer so your sales team can create orders for them.",
                      back_url="panel_customers", submit_label="Save customer")


@panel_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Customer “{customer.name}” was updated.")
        return redirect("panel_customers")
    return _form_page(request, form, title=f"Edit {customer.name}", eyebrow="Customers",
                      subtitle="Update contact details or deactivate this customer.",
                      back_url="panel_customers", submit_label="Save changes")


@panel_required
@require_POST
def customer_toggle(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.is_active = not customer.is_active
    customer.save(update_fields=["is_active"])
    messages.success(request, f"“{customer.name}” is now {'active' if customer.is_active else 'inactive'}.")
    return redirect("panel_customers")


# ---------------------------------------------------------------- products
@panel_required
def products(request):
    q = request.GET.get("q", "").strip()
    state = request.GET.get("state", "")
    stock = request.GET.get("stock", "")
    qs = Product.objects.all()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(product_code__icontains=q) | Q(category__icontains=q))
    if state == "active":
        qs = qs.filter(is_active=True)
    elif state == "inactive":
        qs = qs.filter(is_active=False)
    if stock == "low":
        qs = qs.filter(stock_quantity__lte=LOW_STOCK)
    return render(request, "panel/products.html", {
        "products": qs, "q": q, "state": state, "stock": stock, "low_stock": LOW_STOCK,
    })


@panel_required
def product_add(request):
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            product = form.save(commit=False)
            opening = form.cleaned_data.get("opening_stock") or 0
            product.stock_quantity = opening
            product.save()
            if opening:
                StockMovement.objects.create(
                    product=product, movement_type=StockMovement.Type.OPENING, quantity_change=opening,
                    reason="Opening stock (admin panel)", created_by=request.user)
        messages.success(request, f"Product “{product.name}” was added.")
        return redirect("panel_products")
    return _form_page(request, form, title="Add product", eyebrow="Catalog",
                      subtitle="Add a new item to your catalog with its price and opening stock.",
                      back_url="panel_products", submit_label="Save product")


@panel_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Product “{product.name}” was updated.")
        return redirect("panel_products")
    return _form_page(request, form, title=f"Edit {product.name}", eyebrow="Catalog",
                      subtitle="Change name, category, price or availability.",
                      back_url="panel_products", submit_label="Save changes",
                      extra_note=f"Current stock: {product.stock_quantity}. Use “Adjust stock” on the product list to change it.")


@panel_required
@require_POST
def product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save(update_fields=["is_active"])
    messages.success(request, f"“{product.name}” is now {'active' if product.is_active else 'inactive'}.")
    return redirect("panel_products")


@panel_required
def product_stock(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = StockAdjustForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            adjust_stock(product.pk, form.cleaned_data["quantity_change"], form.cleaned_data["reason"], request.user)
        except ValueError as exc:
            form.add_error("quantity_change", str(exc))
        else:
            messages.success(request, f"Stock for “{product.name}” was adjusted.")
            return redirect("panel_products")
    return _form_page(request, form, title=f"Adjust stock · {product.name}", eyebrow="Inventory",
                      subtitle=f"{product.product_code} currently has {product.stock_quantity} units in stock.",
                      back_url="panel_products", submit_label="Apply adjustment")


# ---------------------------------------------------------------- orders & movements
@panel_required
def orders(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    qs = SalesOrder.objects.select_related("customer", "created_by")
    if q:
        qs = qs.filter(Q(order_number__icontains=q) | Q(customer__name__icontains=q) | Q(created_by__username__icontains=q))
    if status in {"DRAFT", "CONFIRMED", "CANCELLED"}:
        qs = qs.filter(status=status)
    return render(request, "panel/orders.html", {"orders": qs, "q": q, "status": status})


@panel_required
def movements(request):
    q = request.GET.get("q", "").strip()
    kind = request.GET.get("type", "")
    qs = StockMovement.objects.select_related("product", "created_by", "sales_order")
    if q:
        qs = qs.filter(Q(product__name__icontains=q) | Q(product__product_code__icontains=q) | Q(reason__icontains=q))
    if kind in dict(StockMovement.Type.choices):
        qs = qs.filter(movement_type=kind)
    return render(request, "panel/movements.html", {
        "movements": qs[:300], "q": q, "kind": kind, "types": StockMovement.Type.choices,
    })
