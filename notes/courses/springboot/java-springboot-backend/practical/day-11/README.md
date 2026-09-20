# Practical — Day 11 (answer key)

Type these files yourself under `~/springboot-practice/day-11` while following
[the lesson](../../day-11-dtos/README.md).

```bash
mvn spring-boot:run
curl -s -X POST http://localhost:8080/api/users -H 'Content-Type: application/json' -d '{"name":"Ada","email":"ada@example.com","password":"secret"}'
```
