# REST API cheat sheet

## Verbs

| Method | Use | Idempotent | Status |
|---|---|---|---|
| GET | read | yes | 200 |
| POST | create | no | 201 + Location |
| PUT | replace | yes | 200 |
| PATCH | partial | usually | 200 |
| DELETE | remove | yes | 204 |

## Status codes

200 201 204 400 401 403 404 409 422 500

401 stranger · 403 known but forbidden

## URL style

Good: `/api/users/5`  
Bad: `/api/getUser?id=5`

## JSON

`Content-Type: application/json`

## Pagination

`GET /api/products?page=0&size=10&sort=name,asc`
