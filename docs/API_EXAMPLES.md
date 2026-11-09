# API quick examples

All requests require an authenticated Django session. Include the session cookie and CSRF token on POST/PATCH.

## Create draft order
`POST /api/orders/`
```json
{"customer_id":1,"order_date":"2026-11-08","discount_percentage":"10.00","items":[{"product_id":1,"quantity":2}]}
```

## Confirm
`POST /api/orders/1/confirm/`

## Cancel
`POST /api/orders/1/cancel/`

## Adjust stock (Admin)
`POST /api/products/1/adjust-stock/`
```json
{"quantity_change":15,"reason":"Physical stock count"}
```
