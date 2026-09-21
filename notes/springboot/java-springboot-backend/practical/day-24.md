# day-24

Type these files yourself under `~/springboot-practice/day-24` while following [the lesson](../day-24-spring-security.md).

```bash
mvn spring-boot:run
curl -i http://localhost:8080/api/public/ping
curl -i http://localhost:8080/api/private/me
curl -u ada:password http://localhost:8080/api/private/me
```
