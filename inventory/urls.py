from django.urls import path
from . import views, panel_views as panel
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("customers/", views.customers_page, name="customers"),
    path("products/", views.products_page, name="products"),
    path("orders/", views.orders_page, name="orders"),
    path("orders/new/", views.new_order_page, name="new_order"),
    path("reports/", views.reports_page, name="reports"),
    path("import/", views.import_page, name="import"),

    # Custom admin panel (Admin role only)
    path("panel/", panel.dashboard, name="panel_dashboard"),
    path("panel/users/", panel.users, name="panel_users"),
    path("panel/users/add/", panel.user_add, name="panel_user_add"),
    path("panel/users/<int:pk>/edit/", panel.user_edit, name="panel_user_edit"),
    path("panel/users/<int:pk>/toggle/", panel.user_toggle, name="panel_user_toggle"),
    path("panel/customers/", panel.customers, name="panel_customers"),
    path("panel/customers/add/", panel.customer_add, name="panel_customer_add"),
    path("panel/customers/<int:pk>/edit/", panel.customer_edit, name="panel_customer_edit"),
    path("panel/customers/<int:pk>/toggle/", panel.customer_toggle, name="panel_customer_toggle"),
    path("panel/products/", panel.products, name="panel_products"),
    path("panel/products/add/", panel.product_add, name="panel_product_add"),
    path("panel/products/<int:pk>/edit/", panel.product_edit, name="panel_product_edit"),
    path("panel/products/<int:pk>/toggle/", panel.product_toggle, name="panel_product_toggle"),
    path("panel/products/<int:pk>/stock/", panel.product_stock, name="panel_product_stock"),
    path("panel/orders/", panel.orders, name="panel_orders"),
    path("panel/movements/", panel.movements, name="panel_movements"),
]
