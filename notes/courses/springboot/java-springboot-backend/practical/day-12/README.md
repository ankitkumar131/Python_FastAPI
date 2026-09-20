# Practical — Day 12 (answer key)

Type these files yourself under `~/springboot-practice/day-12` while following
[the lesson](../../day-12-validation-exceptions/README.md).

```bash
mvn spring-boot:run
curl -i -X POST http://localhost:8080/api/users -H 'Content-Type: application/json' -d '{"name":"","email":"nope"}'
curl -i http://localhost:8080/api/users/99
```
