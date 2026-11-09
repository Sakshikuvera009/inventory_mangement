-- 1. Top three customers by Confirmed order grand total
SELECT c.id, c.name, SUM(so.grand_total) AS total_sales
FROM inventory_customer c JOIN inventory_salesorder so ON so.customer_id=c.id
WHERE so.status='CONFIRMED' GROUP BY c.id,c.name ORDER BY total_sales DESC LIMIT 3;

-- 2. Top three products by quantity sold in Confirmed orders
SELECT p.id,p.name,SUM(i.quantity) AS quantity_sold
FROM inventory_product p JOIN inventory_salesorderitem i ON i.product_id=p.id
JOIN inventory_salesorder so ON so.id=i.sales_order_id
WHERE so.status='CONFIRMED' GROUP BY p.id,p.name ORDER BY quantity_sold DESC LIMIT 3;

-- 3. Customers who have never placed any order
SELECT c.* FROM inventory_customer c
WHERE NOT EXISTS (SELECT 1 FROM inventory_salesorder so WHERE so.customer_id=c.id);

-- 4. Month-wise Confirmed sales totals, grouped by year and month
SELECT EXTRACT(YEAR FROM order_date)::int AS year,
       EXTRACT(MONTH FROM order_date)::int AS month,
       SUM(grand_total) AS confirmed_sales
FROM inventory_salesorder WHERE status='CONFIRMED'
GROUP BY year,month ORDER BY year,month;

-- 5. Products below a supplied stock threshold (:threshold)
SELECT id,product_code,name,stock_quantity FROM inventory_product
WHERE stock_quantity < :threshold ORDER BY stock_quantity ASC;
