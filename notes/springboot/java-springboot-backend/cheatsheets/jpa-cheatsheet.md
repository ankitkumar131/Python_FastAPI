# JPA cheat sheet

```java
@Entity
@Table(name = "users")
public class User {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
}
```

```java
public interface UserRepository extends JpaRepository<User, Long> {
  Optional<User> findByEmail(String email);
}
```

- Owning side has `@JoinColumn`
- Inverse has `mappedBy`
- Default OneToMany **LAZY**
- N+1 → `JOIN FETCH` / DTO query
- `@Transactional` on **service**
- `ddl-auto=update` learning only; Flyway in prod
- Don’t return entities from REST
