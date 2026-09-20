# MySQL cheat sheet

```sql
CREATE DATABASE app_db;
USE app_db;
CREATE TABLE users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  email VARCHAR(120) NOT NULL UNIQUE
);
```

```properties
spring.datasource.url=jdbc:mysql://localhost:3306/app_db
spring.datasource.username=root
spring.datasource.password=secret
```

Errors: connection refused → not running. Access denied → password. Unknown database → CREATE DATABASE.
