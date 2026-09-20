# PostgreSQL cheat sheet

```properties
spring.datasource.url=jdbc:postgresql://localhost:5432/app_db
```

```sql
CREATE TABLE employees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  attrs JSONB NOT NULL DEFAULT '{}'::jsonb
);
INSERT ... ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name;
```

Not MySQL: real BOOLEAN, UUID type, JSONB, `ON CONFLICT`, quoted identifiers.
