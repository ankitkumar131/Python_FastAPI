# day-08

Type these files yourself under `~/springboot-practice/day-08` while following [the lesson](../day-08-rest-apis.md).

```bash
mvn spring-boot:run
curl http://localhost:8080/api/widgets
curl -i -X POST http://localhost:8080/api/widgets -H 'Content-Type: application/json' -d '{"name":"gizmo"}'
curl -i -X DELETE http://localhost:8080/api/widgets/1
```
