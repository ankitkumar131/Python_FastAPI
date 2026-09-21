# day-25

Type these files yourself under `~/springboot-practice/day-25` while following [the lesson](../day-25-jwt-authentication.md).

```bash
mvn spring-boot:run
curl -s -X POST http://localhost:8080/api/auth/register -H 'Content-Type: application/json' -d '{"email":"ada@example.com","password":"secret"}'
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login -H 'Content-Type: application/json' -d '{"email":"ada@example.com","password":"secret"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["accessToken"])')
curl -s http://localhost:8080/api/users/me -H "Authorization: Bearer $TOKEN"
```
