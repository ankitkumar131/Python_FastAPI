# Practical — Day 29 (answer key)

Type these files yourself under `~/springboot-practice/day-29` while following
[the lesson](../../day-29-docker-deployment/README.md).

```bash
mvn -DskipTests package
docker compose up --build
curl http://localhost:8080/api/hello
```
