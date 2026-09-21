# day-29

Type these files yourself under `~/springboot-practice/day-29` while following [the lesson](../day-29-docker-deployment.md).

```bash
mvn -DskipTests package
docker compose up --build
curl http://localhost:8080/api/hello
```
