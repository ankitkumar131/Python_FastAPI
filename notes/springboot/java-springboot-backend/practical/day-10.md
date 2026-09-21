# day-10

Type these files yourself under `~/springboot-practice/day-10` while following [the lesson](../day-10-service-layer.md).

```bash
mvn spring-boot:run
curl -s -X POST http://localhost:8080/api/users -H 'Content-Type: application/json' -d '{"name":"Ada","email":"ada@example.com"}'
curl -s -X POST http://localhost:8080/api/users -H 'Content-Type: application/json' -d '{"name":"Ada2","email":"ada@example.com"}'
```
