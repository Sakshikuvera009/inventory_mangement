from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import Product, SalesOrder, SalesOrderItem, StockMovement

CENT = Decimal("0.01")
def money(value): return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)

def calculate_order(items, discount_percentage):
    if not items: raise ValueError("An order must contain at least one item.")
    discount = Decimal(str(discount_percentage))
    if discount < 0 or discount > 20: raise ValueError("Discount must be between 0 and 20%.")
    seen, subtotal = set(), Decimal("0.00")
    calculated = []
    for row in items:
        try:
            pid, qty = int(row["product_id"]), int(row["quantity"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Each item needs a valid product_id and whole-number quantity.")
        if qty <= 0: raise ValueError("Quantity must be a positive whole number.")
        if pid in seen: raise ValueError("Duplicate products are not allowed in one order.")
        seen.add(pid)
        product = Product.objects.get(pk=pid, is_active=True)
        rate = money(product.price)
        amount = money(rate * qty)
        subtotal += amount
        calculated.append((product, qty, rate, amount))
    subtotal = money(subtotal)
    discount_amount = money(subtotal * discount / Decimal("100"))
    return calculated, subtotal, discount_amount, money(subtotal - discount_amount)

def create_order(*, customer, order_date, discount_percentage, items, user):
    calculated, subtotal, discount_amount, grand_total = calculate_order(items, discount_percentage)
    order = SalesOrder.objects.create(
        order_number=f"SO-{timezone.now():%Y%m%d%H%M%S%f}", customer=customer,
        order_date=order_date, discount_percentage=discount_percentage,
        subtotal=subtotal, discount_amount=discount_amount, grand_total=grand_total, created_by=user)
    SalesOrderItem.objects.bulk_create([
        SalesOrderItem(sales_order=order, product=p, quantity=q, rate=r, amount=a)
        for p, q, r, a in calculated])
    return order

@transaction.atomic
def confirm_order(order_id, user):
    order = SalesOrder.objects.select_for_update().get(pk=order_id)
    if order.status != SalesOrder.Status.DRAFT:
        raise ValueError("Only Draft orders can be confirmed.")
    items = list(order.items.select_related("product"))
    # Lock all product rows in deterministic order to prevent competing confirmations.
    products = {p.pk: p for p in Product.objects.select_for_update().filter(
        pk__in=[i.product_id for i in items]).order_by("pk")}
    shortages = [f"{products[i.product_id].name}: available {products[i.product_id].stock_quantity}, required {i.quantity}"
                 for i in items if products[i.product_id].stock_quantity < i.quantity]
    if shortages: raise ValueError("Insufficient stock. " + "; ".join(shortages))
    for item in items:
        product = products[item.product_id]
        product.stock_quantity -= item.quantity
        product.save(update_fields=["stock_quantity"])
        StockMovement.objects.create(product=product, movement_type=StockMovement.Type.SALE,
            quantity_change=-item.quantity, sales_order=order, reason=f"Confirmed {order.order_number}", created_by=user)
    order.status = SalesOrder.Status.CONFIRMED
    order.save(update_fields=["status"])
    return order

@transaction.atomic
def cancel_order(order_id, user):
    order = SalesOrder.objects.select_for_update().get(pk=order_id)
    if order.status not in [SalesOrder.Status.DRAFT, SalesOrder.Status.CONFIRMED]:
        raise ValueError("This order cannot be cancelled.")
    if order.status == SalesOrder.Status.CONFIRMED:
        items = list(order.items.select_related("product"))
        products = {p.pk: p for p in Product.objects.select_for_update().filter(
            pk__in=[i.product_id for i in items]).order_by("pk")}
        for item in items:
            product = products[item.product_id]
            product.stock_quantity += item.quantity
            product.save(update_fields=["stock_quantity"])
            StockMovement.objects.create(product=product, movement_type=StockMovement.Type.SALE_RETURN,
                quantity_change=item.quantity, sales_order=order, reason=f"Cancelled {order.order_number}", created_by=user)
    order.status = SalesOrder.Status.CANCELLED
    order.save(update_fields=["status"])
    return order

@transaction.atomic
def adjust_stock(product_id, quantity_change, reason, user):
    product = Product.objects.select_for_update().get(pk=product_id)
    if not reason.strip(): raise ValueError("A reason is required.")
    if int(quantity_change) == 0: raise ValueError("Stock adjustment cannot be zero.")
    if product.stock_quantity + int(quantity_change) < 0: raise ValueError("Adjustment would make stock negative.")
    product.stock_quantity += int(quantity_change)
    product.save(update_fields=["stock_quantity"])
    StockMovement.objects.create(product=product, movement_type=StockMovement.Type.IN if quantity_change > 0 else StockMovement.Type.OUT,
        quantity_change=quantity_change, reason=reason, created_by=user)
    return product

def calculate_total(items):
    total = Decimal("0.00")
    for item in items:
        if "qty" not in item or "rate" not in item: raise ValueError("Each item must include qty and rate.")
        qty, rate = item["qty"], Decimal(str(item["rate"]))
        if not isinstance(qty, int) or isinstance(qty, bool) or qty < 0 or rate < 0:
            raise ValueError("Quantity and rate must be non-negative; quantity must be an integer.")
        total += qty * rate
    return money(total)
