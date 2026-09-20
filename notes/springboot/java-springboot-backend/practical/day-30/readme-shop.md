# Shop capstone blueprint

Implement in `~/springboot-practice/shop`.

Auth: POST /api/auth/register /login
Products: GET /api/products?page&size&sort&category&q
Cart: POST /api/cart/items  GET /api/cart  DELETE /api/cart/items/{productId}
Orders: POST /api/orders  GET /api/orders  GET /api/orders/{id}
Admin: PUT /api/orders/{id}/status  product/category writes
