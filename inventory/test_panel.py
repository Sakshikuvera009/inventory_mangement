from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Customer, Product, StockMovement

User = get_user_model()
PW = "Str0ng-Passw0rd!"


class RegisterTests(TestCase):
    def payload(self, **kw):
        data = {"first_name": "Aarav", "last_name": "Sharma", "username": "aarav", "email": "aarav@example.com",
                "password1": PW, "password2": PW}
        data.update(kw)
        return data

    def test_page_renders(self):
        self.assertContains(self.client.get(reverse("register")), "Create your account")

    def test_register_creates_sales_user_and_logs_in(self):
        r = self.client.post(reverse("register"), self.payload())
        self.assertRedirects(r, reverse("dashboard"))
        u = User.objects.get(username="aarav")
        self.assertEqual(u.role, "SALES")
        self.assertFalse(u.is_staff or u.is_superuser)
        self.assertEqual(int(self.client.session["_auth_user_id"]), u.pk)

    def test_cannot_self_assign_admin_role(self):
        self.client.post(reverse("register"), self.payload(role="ADMIN", is_superuser="on", is_staff="on"))
        u = User.objects.get(username="aarav")
        self.assertEqual(u.role, "SALES")
        self.assertFalse(u.is_superuser or u.is_staff)

    def test_duplicate_email_and_password_mismatch(self):
        User.objects.create_user("x", email="AARAV@example.com", password=PW)
        self.assertContains(self.client.post(reverse("register"), self.payload()), "already exists")
        r = self.client.post(reverse("register"), self.payload(email="n@e.com", password2="different"))
        self.assertEqual(User.objects.filter(username="aarav").count(), 0)
        self.assertEqual(r.status_code, 200)

    def test_logged_in_user_redirected(self):
        self.client.post(reverse("register"), self.payload())
        self.assertRedirects(self.client.get(reverse("register")), reverse("dashboard"))


class PanelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("boss", email="boss@e.com", password=PW, role="ADMIN")
        self.sales = User.objects.create_user("rep", email="rep@e.com", password=PW, role="SALES")

    def test_access_control(self):
        urls = ["panel_dashboard", "panel_users", "panel_customers", "panel_products", "panel_orders", "panel_movements",
                "panel_user_add", "panel_customer_add", "panel_product_add"]
        for name in urls:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)  # anonymous -> login
        self.client.force_login(self.sales)
        for name in urls:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)
        self.client.force_login(self.admin)
        for name in urls:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_sales_cannot_post_actions(self):
        self.client.force_login(self.sales)
        r = self.client.post(reverse("panel_user_toggle", args=[self.admin.pk]))
        self.assertEqual(r.status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_creates_edits_and_toggles_user(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("panel_user_add"), {"username": "new", "first_name": "N", "last_name": "U",
                             "email": "new@e.com", "role": "SALES", "is_active": "on", "password": PW})
        self.assertRedirects(r, reverse("panel_users"))
        u = User.objects.get(username="new")
        self.assertTrue(u.check_password(PW))
        self.client.post(reverse("panel_user_edit", args=[u.pk]), {"username": "new", "first_name": "N", "last_name": "U",
                         "email": "new@e.com", "role": "ADMIN", "is_active": "on", "password": ""})
        u.refresh_from_db()
        self.assertEqual(u.role, "ADMIN")
        self.assertTrue(u.check_password(PW))  # blank password keeps old one
        self.client.post(reverse("panel_user_toggle", args=[u.pk]))
        u.refresh_from_db()
        self.assertFalse(u.is_active)

    def test_admin_cannot_lock_self_out(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("panel_user_toggle", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.client.post(reverse("panel_user_edit", args=[self.admin.pk]), {
            "username": "boss", "first_name": "", "last_name": "", "email": "boss@e.com", "role": "SALES", "password": ""})
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, "ADMIN")
        self.assertTrue(self.admin.is_active)

    def test_product_crud_and_stock_adjust(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("panel_product_add"), {"product_code": "K1", "name": "Keyboard", "category": "PC",
                             "price": "499.00", "is_active": "on", "opening_stock": "12"})
        self.assertRedirects(r, reverse("panel_products"))
        p = Product.objects.get(product_code="K1")
        self.assertEqual(p.stock_quantity, 12)
        self.assertEqual(StockMovement.objects.get(product=p).movement_type, "OPENING")
        # product_code is read-only on edit, stock is untouched by edit
        self.client.post(reverse("panel_product_edit", args=[p.pk]), {"product_code": "HACK", "name": "KB2", "category": "PC",
                         "price": "550.00", "is_active": "on", "stock_quantity": "999"})
        p.refresh_from_db()
        self.assertEqual((p.product_code, p.name, p.stock_quantity), ("K1", "KB2", 12))
        self.client.post(reverse("panel_product_stock", args=[p.pk]), {"quantity_change": "-5", "reason": "Damaged"})
        p.refresh_from_db()
        self.assertEqual(p.stock_quantity, 7)
        r = self.client.post(reverse("panel_product_stock", args=[p.pk]), {"quantity_change": "-50", "reason": "Too many"})
        self.assertContains(r, "negative")
        p.refresh_from_db()
        self.assertEqual(p.stock_quantity, 7)

    def test_customer_create_and_toggle(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("panel_customer_add"), {"name": "Acme", "email": "", "mobile": "99", "city": "Pune", "is_active": "on"})
        c = Customer.objects.get(name="Acme")
        self.client.post(reverse("panel_customer_toggle", args=[c.pk]))
        c.refresh_from_db()
        self.assertFalse(c.is_active)

    def test_toggle_requires_post(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("panel_user_toggle", args=[self.sales.pk])).status_code, 405)
