# Sales Order & Inventory Management

A Django + PostgreSQL implementation of the supplied Fresher/Trainee Sales Order & Inventory assignment. The assignment document names MySQL; this version intentionally uses **PostgreSQL**, as requested. The business requirements are otherwise used as the implementation baseline.

## Features
- Session login/logout; Admin and Sales User roles enforced in backend APIs.
- Customer and product master views, search, active/inactive status; Django Admin provides create/edit/deactivate controls.
- Draft multi-item orders, backend-only rates and money calculations, 0–20% discount.
- Transactional confirm/cancel with row locks, atomic stock movement records and repeat-action protection.
- Admin-only stock adjustment and all-or-nothing CSV import with row-level errors.
- Customer/product sales, low-stock and movement reports.
- REST JSON endpoints, SQL deliverables, sample CSV files and automated tests.
- Debugging exercise corrected in `inventory/services.py::calculate_total`.

## Requirements
- Python 3.10+
- PostgreSQL 13+
- Git

## Windows setup
1. Create a PostgreSQL database named `sales_inventory` (pgAdmin or psql).
2. Open this folder in VS Code / terminal.
3. Create and activate a virtual environment:
   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   ```
4. Install packages:
   ```bat
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and enter your PostgreSQL username/password.
6. Create schema and an admin:
   ```bat
   python manage.py makemigrations inventory
   python manage.py migrate
   python manage.py createsuperuser
   ```
7. Run:
   ```bat
   python manage.py runserver
   ```
8. Open `http://127.0.0.1:8000/` and sign in. Django Admin is at `/admin/`.

## Create a Sales User
Use Django Admin → Users → Add User, then set Role to `SALES`. Admin users should have Role `ADMIN` (or be superusers). Never use the sample development password in a real environment.

## Register page & custom admin panel
- `/register/` - public sign-up (name, username, email, password). New accounts are **always Sales Users**; the role cannot be chosen on this page. After sign-up the user is logged in automatically.
- `/panel/` - custom admin panel, visible only to Admin-role users / superusers (others get 403). Sections: overview, Users (add/edit/role/reset password/activate-deactivate), Manage customers, Manage products (edit, activate, **Adjust stock** with audit trail), All orders (confirm/cancel/details), Stock movements log.
- Safeguards: an admin cannot deactivate or demote their own account; deactivate is used instead of delete (records are protected by foreign keys); stock is only changed through stock movements.
- Fully responsive: tables turn into cards on phones, sidebar becomes a slide-in menu.

## Main pages
- `/` Dashboard
- `/customers/` Customers
- `/products/` Products
- `/orders/` Orders
- `/orders/new/` Create draft
- `/reports/` Admin reports
- `/import/` Admin CSV import
- `/panel/` Custom admin panel (see above)
- `/register/` Sign-up
- `/admin/` Django Admin (still available)

## API
All endpoints require a logged-in session. For browser/API testing, authenticate through `/login/` and retain the session cookie and CSRF token.
- `GET /api/products/?search=key`
- `GET /api/customers/?search=...&status=active`
- `POST /api/customers/` (Admin only)
- `PATCH /api/customers/{id}/` (Admin only)
- `GET|POST /api/orders/`
- `GET /api/orders/{id}/`
- `POST /api/orders/{id}/confirm/`
- `POST /api/orders/{id}/cancel/`
- `POST /api/products/{id}/adjust-stock/` (Admin only; JSON: `quantity_change`, `reason`)
- `POST /api/products/import-csv/` (Admin only; multipart field `file`)
- `GET /api/reports/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&threshold=10` (Admin only)

Order create JSON:
```json
{
  "customer_id": 1,
  "order_date": "2026-11-08",
  "discount_percentage": "10.00",
  "items": [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 3}]
}
```
The backend fetches current product rates and calculates all totals; browser-supplied totals/rates/status/owner are ignored.

## Tests
```bat
python manage.py test inventory
```
Tests cover calculation, discounts, quantity validation, stock deduction/rollback, repeated confirmation, cancellation restoration, order ownership and atomic CSV rejection.

## Database design
Six requested business entities are present: User, Customer, Product, SalesOrder, SalesOrderItem, StockMovement. User uses Django's secure password hashing. Customer/Product are protected from deletion when referenced; product stock is changed through stock movement-aware operations. Money uses DecimalField. PostgreSQL migrations create keys, constraints and indexes.

## Stock concurrency
Confirmation uses `transaction.atomic()` and `select_for_update()` to lock the order and all involved product rows in sorted primary-key order. Competing confirmations therefore serialize on the same stock rows. Stock checks happen after locks are acquired; if any item is short, the transaction raises before changing stock. The order status and movement rows commit in the same transaction.

## Debugging exercise
The original function overwrote `total` on each iteration. The corrected implementation accumulates each line amount. Empty input returns 0. Missing keys, negative values and non-integer quantities raise a clear `ValueError`.

## Notes / known limitations to review
- The supplied assignment asks for MySQL, but the user requested PostgreSQL. Confirm with the evaluator that PostgreSQL is accepted.
- Admin master-data create/edit/deactivate screens are available through Django Admin; custom customer/product CRUD screens can be added if required by the evaluator.
- Product list API currently returns all matching active rows (no pagination yet).
- The order page's confirm/cancel buttons and create-order form are functional; customer/product management UI is primarily read/search with changes handled in Django Admin.
- Run the automated tests against PostgreSQL before submission. This generated starter has not been executed against your local database in this environment.
- Add meaningful Git commits and create a feature branch/merge in your own repository; repository history cannot be pre-created here.

## Security checklist before deployment
Set a strong SECRET_KEY, DEBUG=False, restricted ALLOWED_HOSTS, secure database credentials, HTTPS and production cookie settings. Do not commit `.env`.
