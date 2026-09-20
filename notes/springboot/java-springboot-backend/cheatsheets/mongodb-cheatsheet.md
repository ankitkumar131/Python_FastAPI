# MongoDB cheat sheet

```properties
spring.data.mongodb.uri=mongodb://localhost:27017/app_db
```

```java
@Document(collection = "posts")
public class Post {
  @Id private String id;
}
public interface PostRepository extends MongoRepository<Post, String> {}
```

Embed small nested data. Reference large/shared data. 16MB document limit. Aggregation: `$match $group $unwind`.
