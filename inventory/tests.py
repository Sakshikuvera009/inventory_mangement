from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from .models import Customer, Product, SalesOrder, StockMovement
from .services import calculate_order, confirm_order, cancel_order, calculate_total, create_order

User=get_user_model()
class OrderInventoryTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_user(username="admin",password="TestPass123!",role="ADMIN")
        self.sales=User.objects.create_user(username="sales",password="TestPass123!",role="SALES")
        self.customer=Customer.objects.create(name="Acme")
        self.p1=Product.objects.create(product_code="P1",name="Keyboard",price="100.00",stock_quantity=10)
        self.p2=Product.objects.create(product_code="P2",name="Mouse",price="50.00",stock_quantity=2)
    def test_multi_item_discount_calculation(self):
        _,sub,disc,total=calculate_order([{"product_id":self.p1.id,"quantity":2},{"product_id":self.p2.id,"quantity":3}],10)
        self.assertEqual((sub,disc,total),(Decimal("350.00"),Decimal("35.00"),Decimal("315.00")))
    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError): calculate_order([{"product_id":self.p1.id,"quantity":0}],0)
    def test_discount_over_limit_rejected(self):
        with self.assertRaises(ValueError): calculate_order([{"product_id":self.p1.id,"quantity":1}],21)
    def make_order(self, items):
        return create_order(customer=self.customer,order_date=date.today(),discount_percentage=0,items=items,user=self.sales)
    def test_confirm_deducts_stock_once(self):
        o=self.make_order([{"product_id":self.p1.id,"quantity":3}]);confirm_order(o.id,self.sales)
        self.p1.refresh_from_db();self.assertEqual(self.p1.stock_quantity,7)
        with self.assertRaises(ValueError): confirm_order(o.id,self.sales)
        self.p1.refresh_from_db();self.assertEqual(self.p1.stock_quantity,7)
    def test_insufficient_one_item_rolls_back_everything(self):
        o=self.make_order([{"product_id":self.p1.id,"quantity":1},{"product_id":self.p2.id,"quantity":5}])
        with self.assertRaises(ValueError): confirm_order(o.id,self.sales)
        o.refresh_from_db();self.p1.refresh_from_db()
        self.assertEqual(o.status,"DRAFT");self.assertEqual(self.p1.stock_quantity,10)
        self.assertFalse(StockMovement.objects.filter(sales_order=o).exists())
    def test_confirmed_cancel_restores_once(self):
        o=self.make_order([{"product_id":self.p1.id,"quantity":4}]);confirm_order(o.id,self.sales);cancel_order(o.id,self.sales)
        self.p1.refresh_from_db();self.assertEqual(self.p1.stock_quantity,10)
        with self.assertRaises(ValueError): cancel_order(o.id,self.sales)
        self.p1.refresh_from_db();self.assertEqual(self.p1.stock_quantity,10)
    def test_sales_user_cannot_access_other_order(self):
        other=self.make_order([{"product_id":self.p1.id,"quantity":1}])
        client=APIClient();client.force_authenticate(self.sales)
        outsider=User.objects.create_user(username="other",password="TestPass123!",role="SALES")
        client.force_authenticate(outsider)
        response=client.get(f"/api/orders/{other.id}/")
        self.assertEqual(response.status_code,404)
    def test_csv_invalid_row_imports_nothing(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        client=APIClient();client.force_authenticate(self.admin)
        content=b"product_code,product_name,category,price,stock_quantity,status\nP3,Valid,Tools,10,5,Active\nP4,Bad,Tools,-1,5,Active\n"
        response=client.post("/api/products/import-csv/",{"file":SimpleUploadedFile("x.csv",content)},format="multipart")
        self.assertEqual(response.status_code,400);self.assertFalse(Product.objects.filter(product_code="P3").exists())
    def test_debugging_function(self):
        self.assertEqual(calculate_total([{"qty":2,"rate":100},{"qty":3,"rate":50}]),Decimal("350.00"))
        self.assertEqual(calculate_total([]),Decimal("0.00"))
        with self.assertRaises(ValueError): calculate_total([{"qty":1}])
