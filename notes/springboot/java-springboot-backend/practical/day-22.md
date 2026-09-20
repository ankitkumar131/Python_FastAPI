# day-22

Type these files yourself under `~/springboot-practice/day-22` while following [the lesson](../day-22-spring-data-mongodb.md).

```bash
mvn spring-boot:run
curl -s -X POST http://localhost:8080/api/posts -H 'Content-Type: application/json' -d '{"title":"Hello","body":"...","authorName":"Ada","tags":["java"]}'
```
