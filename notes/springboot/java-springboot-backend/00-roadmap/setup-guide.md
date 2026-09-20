# Setup Guide

Install and verify every tool before you need it. Each section has: installation, verification, expected output, common problem, solution.

Do **not** put real production passwords in `application.properties`. Local learning passwords such as `secret` are fine.

---

# 1. Java 21

## Installation

- **Windows:** Install Temurin 21 from Adoptium, tick “Set JAVA_HOME”.
- **macOS:** `brew install --cask temurin@21`
- **Linux (Debian/Ubuntu):** `sudo apt install temurin-21-jdk` (or your distro’s `openjdk-21-jdk`)

## Verification

```bash
java -version
javac -version
echo $JAVA_HOME
```

## Expected output

```text
openjdk version "21.0.x"
OpenJDK Runtime Environment ...
```

## Common problem

`java` works but Maven compiles with Java 11.

## Solution

Set `JAVA_HOME` to the 21 JDK, not a JRE. In `pom.xml` this course uses:

```xml
<java.version>21</java.version>
```

---

# 2. Maven

Spring Initializr projects include `mvnw` (Maven Wrapper). You can skip a global Maven install, but having one helps.

## Installation

- **macOS:** `brew install maven`
- **Windows:** Chocolatey `choco install maven` or install from maven.apache.org
- **Linux:** `sudo apt install maven`

## Verification

```bash
mvn -version
```

## Expected output

```text
Apache Maven 3.9.x
Java version: 21.x
```

## Common problem

Maven points at Java 8.

## Solution

Fix `JAVA_HOME`, open a new terminal, run `mvn -version` again.

## Commands you will use daily

```bash
./mvnw spring-boot:run    # start the app
./mvnw test               # run tests
./mvnw clean              # delete target/
./mvnw package            # compile + tests + jar
./mvnw clean package -DskipTests
```

| Command | What it does |
|---|---|
| `clean` | Deletes `target/` |
| `compile` | Compiles main sources |
| `test` | Compiles and runs tests |
| `package` | Builds the jar |
| `install` | Puts the jar in local `.m2` |

---

# 3. IntelliJ IDEA Community

## Installation

Download from jetbrains.com/idea or `brew install --cask intellij-idea-ce`.

## Verification

File → New → Project from Existing Sources → open a course `pom.xml`. After indexing, the green run icon appears on `*Application.java`.

## Common problem

“Invalid source release: 21”

## Solution

Settings → Build → Compiler → Java Compiler → Project bytecode version 21. Also: File → Project Structure → Project SDK 21.

---

# 4. VS Code (optional)

## Installation

Install VS Code plus extensions: **Extension Pack for Java**, **Spring Boot Extension Pack**.

## Verification

Open the project folder. `pom.xml` is recognized. Run/Debug on the main class works.

## Common problem

Java language server stuck on “importing Maven project”.

## Solution

Command Palette → “Java: Clean Java Language Server Workspace”. Confirm `java.configuration.runtimes` includes JDK 21.

---

# 5. Spring Initializr

You do not install Initializr. It is a website and an IntelliJ wizard.

URL: https://start.spring.io

**Course defaults**

| Field | Value |
|---|---|
| Project | Maven |
| Language | Java |
| Spring Boot | 3.4.x |
| Group | `com.course` |
| Artifact | changes per project |
| Packaging | Jar |
| Java | 21 |

Typical dependencies, added when the lesson needs them:

```text
Spring Web
Spring Data JPA
Spring Data MongoDB
Spring Security
Validation
Spring Boot Actuator
Spring Boot DevTools
MySQL Driver
PostgreSQL Driver
```

---

# 6. MySQL 8

## Installation

- **Docker (recommended):**

```bash
docker run --name course-mysql -e MYSQL_ROOT_PASSWORD=secret -e MYSQL_DATABASE=app_db -p 3306:3306 -d mysql:8.4
```

- **Native:** MySQL Community Server 8 from mysql.com, or `brew install mysql`.

## Verification

```bash
mysql -h 127.0.0.1 -P 3306 -u root -p
```

Inside the client:

```sql
SELECT VERSION();
SHOW DATABASES;
```

## Expected output

A version starting with `8.` and a database `app_db` if you used the Docker command.

## Common problem

`Access denied for user 'root'@'localhost'`

## Solution

Password mismatch. Recreate the container or reset the native root password. Spring config:

```properties
spring.datasource.url=jdbc:mysql://localhost:3306/app_db
spring.datasource.username=root
spring.datasource.password=secret
```

`Communications link failure` means MySQL is not running or the port is wrong.

GUI: **MySQL Workbench** is optional.

---

# 7. PostgreSQL 16

## Installation

```bash
docker run --name course-postgres -e POSTGRES_USER=app -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=app_db -p 5432:5432 -d postgres:16
```

Native: `brew install postgresql@16` or the EDB installer on Windows.

## Verification

```bash
psql -h localhost -U app -d app_db
```

```sql
SELECT version();
```

## Common problem

`password authentication failed for user`

## Solution

The user in `spring.datasource.username` must match `POSTGRES_USER`. URL:

```properties
spring.datasource.url=jdbc:postgresql://localhost:5432/app_db
spring.datasource.username=app
spring.datasource.password=secret
```

GUI: pgAdmin, DBeaver, or Azure Data Studio.

---

# 8. MongoDB 7

## Installation

```bash
docker run --name course-mongo -p 27017:27017 -d mongo:7
```

## Verification

```bash
mongosh
```

```javascript
db.version()
show dbs
```

## Expected output

MongoDB 7.x shell prompt `test>`.

## Common problem

`Connection refused 127.0.0.1:27017`

## Solution

Container not running: `docker ps -a` then `docker start course-mongo`.

Spring:

```properties
spring.data.mongodb.uri=mongodb://localhost:27017/app_db
```

**MongoDB Compass** (GUI): connect to `mongodb://localhost:27017`.

---

# 9. Postman

## Installation

Download Postman, or use curl only.

## Verification

Create a GET request to `https://postman-echo.com/get`. Status 200.

## Common problem

Calling `http://localhost:8080` from Postman works, but a browser SPA fails with CORS. That is Day 26, not a Postman bug.

---

# 10. Git

## Installation

`git --version` should already work. If not: `brew install git` / `sudo apt install git` / git-scm.com.

## Verification

```bash
git --version
```

## Course commands you should be fluent with

```bash
git init
git add .
git commit -m "Day 09 in-memory user API"
git branch
git switch -c feature/users
git merge
git pull
git push
```

Backend repo hygiene:

- Commit `pom.xml`, source, `.gitignore`
- Do **not** commit `target/`, `.idea/`, `application-local.properties` with secrets
- Use `application.yml` + environment variables for passwords

Sample `.gitignore`:

```gitignore
target/
.idea/
*.iml
.classpath
.project
.settings/
.env
```

---

# 11. Docker

## Installation

Docker Desktop (Windows/macOS) or Docker Engine + Compose plugin (Linux).

## Verification

```bash
docker version
docker compose version
```

## Expected output

Client and Server versions printed. If Server fails, the daemon is not running — start Docker Desktop.

## Common problem

Port 3306 / 5432 / 27017 already in use.

## Solution

Stop the native database **or** map another host port: `-p 3307:3306`.

---

# 12. Quick “am I ready?” script

```bash
java -version
mvn -version
git --version
docker version
```

If Java 21 and Git work, you can start **Day 1**. Databases can wait until Day 13 / 18 / 21. Docker can wait until Day 29.
