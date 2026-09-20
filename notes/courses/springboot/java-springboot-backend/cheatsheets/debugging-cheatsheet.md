# Debugging cheat sheet

| Symptom | Likely cause | Fix |
|---|---|---|
| Port already in use | leftover Boot | other port / kill process |
| 404 | not scanned / wrong path | main package, mapping log |
| 400 | `@Valid` or binding | check body + types |
| 401 | no/invalid token | login, Bearer |
| 403 | wrong role | hasRole |
| 409 | unique conflict | email exists |
| 500 | uncaught | logs + advice |
| BeanCreationException | missing bean / DB down | root cause in stack |
| NoSuchBeanDefinitionException | not a bean | `@Service` / scan |
| NoUniqueBeanDefinitionException | two impls | `@Primary` / `@Qualifier` |
| LazyInitializationException | lazy after session | DTO / fetch join |
| N+1 | lazy collections in loop | join fetch |
| CORS | browser SPA | CorsConfigurationSource |
| MySQL refused | not running | docker start |
| Postgres password failed | user mismatch | POSTGRES_USER |
| Mongo 27017 | not running | docker start |
| JWT invalid | secret/exp/tamper | check JwtService |

`--debug` on Boot prints auto-config report.
