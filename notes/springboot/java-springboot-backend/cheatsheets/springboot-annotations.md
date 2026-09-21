# Spring Boot annotations cheat sheet

| Annotation | Where | What Spring does |
|---|---|---|
| `@SpringBootApplication` | main class | config + auto-config + scan |
| `@Component` | class | register bean |
| `@Service` | class | business bean |
| `@Repository` | class | persistence bean + exception translation |
| `@RestController` | class | MVC + JSON body |
| `@Controller` | class | MVC (views) |
| `@Configuration` | class | `@Bean` methods |
| `@Bean` | method | factory for a bean |
| `@Autowired` | ctor/setter/field | inject (omit on single ctor) |
| `@Qualifier` | param | pick among types |
| `@Primary` | class/method | default candidate |
| `@Value` | field/param | inject property |
| `@ConfigurationProperties` | class | bind a prefix |
| `@RequestMapping` | class/method | HTTP mapping |
| `@GetMapping` `@PostMapping` `@PutMapping` `@PatchMapping` `@DeleteMapping` | method | verb shortcuts |
| `@PathVariable` | param | path `{id}` |
| `@RequestParam` | param | query |
| `@RequestBody` | param | JSON → object |
| `@ResponseStatus` | method/exception | status |
| `@Valid` | param | Bean Validation |
| `@ExceptionHandler` | method | catch exception |
| `@RestControllerAdvice` | class | global JSON errors |
| `@Entity` `@Table` `@Id` `@GeneratedValue` `@Column` | JPA | table mapping |
| `@OneToOne` `@OneToMany` `@ManyToOne` `@ManyToMany` `@JoinColumn` | JPA | relations |
| `@Transactional` | service method | unit of work |
| `@Document` `@Field` | Mongo | collection mapping |
| `@PreAuthorize` | method | method security |

**Confused pairs**

- `@Component` vs `@Bean` — class badge vs factory method
- `@Controller` vs `@RestController` — view vs JSON
- `@Valid` vs `@Validated` — Jakarta body vs Spring groups
- `@Entity` vs `@Document` — SQL vs Mongo
