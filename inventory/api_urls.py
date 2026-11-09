from django.urls import path
from .api_views import ProductListAPI, OrderListCreateAPI, OrderDetailAPI, StockAdjustmentAPI, ProductCSVImportAPI, ReportsAPI, CustomerListAPI, CustomerUpdateAPI
urlpatterns = [
    path("products/", ProductListAPI.as_view()),
    path("customers/", CustomerListAPI.as_view()),
    path("customers/<int:pk>/", CustomerUpdateAPI.as_view()),
    path("orders/", OrderListCreateAPI.as_view()),
    path("orders/<int:pk>/", OrderDetailAPI.as_view()),
    path("orders/<int:pk>/<str:action>/", OrderDetailAPI.as_view()),
    path("products/<int:pk>/adjust-stock/", StockAdjustmentAPI.as_view()),
    path("products/import-csv/", ProductCSVImportAPI.as_view()),
    path("reports/", ReportsAPI.as_view()),
]
