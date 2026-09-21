# Java interview questions (backend-focused)

See Days 1–2 for worked answers. Sample:

### What Java features does Spring Boot depend on?

Interfaces (injection by type), annotations (metadata), generics (`JpaRepository<User,Long>`), Optional, exceptions as RuntimeException, collections, records as DTOs.

### Why constructor + final?

Required deps, immutability of the reference, testability.

### equals/hashCode on JPA entities?

Don’t use lazy collections; prefer business key; Lombok `@Data` is dangerous.

### Optional rules?

Return from find*; unwrap in service; never as entity field.

### Instant vs Date?

java.time, immutable, ISO-8601.

More: every day’s Easy/Medium/Hard sections.
