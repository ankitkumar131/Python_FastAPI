# Day 1 — Java Foundations for DSA

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Explain what DSA is and why it matters
- Write a complete Java program from scratch
- Use variables, primitive types, operators, control flow, loops, methods
- Read input with `Scanner` and `BufferedReader`
- Declare and use 1D arrays
- Run and debug a Java file from the command line

---

# 1. Introduction

Welcome to your first day. Today is **not** about clever algorithms — it's about making sure your Java is solid enough to *implement* any algorithm you learn later.

Every algorithm from Day 5 onward is written in Java. If your basics are shaky, the rest of the course will feel like climbing a mountain in sand. If your basics are sharp, every later day becomes 2× easier.

---

# 2. Why Do We Need This?

You can solve simple problems with any language, but DSA problems ask for things like:
- iterating a million times fast,
- using the right data structure (`int[]` vs `ArrayList` vs `LinkedList`),
- writing functions that return the right type,
- reading input from a file-like stream.

Java handles all of these — *if* you know the right syntax. Today you'll learn exactly that syntax.

---

# 3. Core Concept — A Java Program's Skeleton

Every Java program you ever write has this shape:

```java
public class FileName {              // ← top-level container
    public static void main(String[] args) {  // ← entry point
        // your code here
    }
}
```

That's it. Everything else is inside this skeleton.

---

# 4. Real-World Analogy

Think of a Java program like a **book**:

- The **class** is the book itself.
- The **main method** is Chapter 1 — the chapter every reader starts with.
- **Variables** are the names of things in the story.
- **Methods** are the chapters that describe actions.

Java *requires* a `main` method because the JVM (Java Virtual Machine) needs a starting point — it literally looks for `public static void main(String[] args)` and starts there.

---

# 5. Syntax — Step by Step

## 5.1 `public class Hello`

```java
public class Hello {
```

- `public` — **access modifier**. Means *anyone* can see this class.
- `class` — keyword meaning "I'm defining a new blueprint / type".
- `Hello` — the name. **Must match the filename**: `Hello.java`.
- `{` — opens the class body.

In Java, every line of code lives inside a class. There are no free-floating functions.

## 5.2 `public static void main(String[] args)`

```java
    public static void main(String[] args) {
```

Read it token by token:

| Token            | What it is                | What it does |
|------------------|---------------------------|--------------|
| `public`         | access modifier           | JVM can call this method from anywhere |
| `static`         | keyword                   | The method belongs to the *class*, not to any object. The JVM can call `Hello.main(...)` without creating a `Hello` instance. |
| `void`           | return type               | This method returns nothing. |
| `main`           | method name               | The fixed name the JVM looks for. |
| `String[] args`  | parameter                 | An *array* of `String`s. Holds command-line arguments. |
| `{`              | opens the method body     | |

## 5.3 `System.out.println("Hello, DSA!");`

```java
        System.out.println("Hello, DSA!");
```

- `System` — a built-in class in `java.lang`.
- `out` — a static field of `System` of type `PrintStream`.
- `println(...)` — a method on `PrintStream` that prints the argument followed by a newline.

The semicolon `;` ends every statement. Forgetting it is a compile error.

---

# 6. Example — Full Program

```java
public class Hello {
    public static void main(String[] args) {
        System.out.println("Hello, DSA!");
    }
}
```

### Compile & run

```bash
javac Hello.java     # produces Hello.class
java Hello           # runs the .class file
```

Output:

```
Hello, DSA!
```

---

# 7. Step-by-Step Explanation

1. You write `Hello.java`.
2. `javac` compiles it to bytecode → `Hello.class`.
3. You type `java Hello`.
4. The JVM loads `Hello.class`.
5. The JVM looks for `public static void main(String[] args)`.
6. It calls that method.
7. The method runs `System.out.println(...)`.
8. Text appears on the terminal.

---

# 8. Java Implementation — All Day-1 Building Blocks

Below is the **single canonical example** that demonstrates every concept we'll touch today. Each concept has its own file under `src/day-01/` so you can run them individually.

## 8.1 Primitive Data Types

Java has 8 primitive types. These are the most common:

| Type    | Size    | Default  | Example          | Range                                  |
|---------|---------|----------|------------------|----------------------------------------|
| `byte`  | 1 byte  | `0`      | `byte b = 100;`  | -128 to 127                            |
| `short` | 2 bytes | `0`      | `short s = 1000;`| -32768 to 32767                        |
| `int`   | 4 bytes | `0`      | `int n = 100000;`| ~ -2.1 × 10⁹ to 2.1 × 10⁹              |
| `long`  | 8 bytes | `0L`     | `long l = 1L;`   | ~ -9.2 × 10¹⁸ to 9.2 × 10¹⁸            |
| `float` | 4 bytes | `0.0f`   | `float f = 3.14f;`| ~ ±3.4 × 10³⁸ (6–7 digits precision)  |
| `double`| 8 bytes | `0.0d`   | `double d = 3.14;`| ~ ±1.8 × 10³⁰ (15 digits precision)   |
| `char`  | 2 bytes | `'\u0000'`| `char c = 'A';`  | 0 to 65535 (Unicode)                   |
| `boolean`| 1 byte*| `false`  | `boolean ok = true;`| `true` or `false`                   |

> *`boolean` size is JVM-dependent.

For DSA, you'll use `int`, `long`, `double`, `char`, and `boolean` 99% of the time.

### Why these matter in DSA

- **Array size** is `int` by default. If `n` could exceed `Integer.MAX_VALUE` (~ 2.1 × 10⁹), you need `long` for sizes.
- **Counters** of very large arrays need `long`.
- **Mid computation**: `int mid = left + (right - left) / 2;` — see Day 10 for why this matters.

## 8.2 Variables

```java
int age = 25;
double pi = 3.14159;
char letter = 'A';
boolean isJavaFun = true;
```

- `int` / `double` / `char` / `boolean` — primitive types.
- `age` / `pi` / ... — variable names (must start with a letter, `_`, or `$`; can't be a Java keyword).
- `=` — assignment, **not** equality.

## 8.3 Operators

### Arithmetic

```java
int a = 10, b = 3;
int sum = a + b;       // 13
int diff = a - b;      // 7
int prod = a * b;      // 30
int quot = a / b;      // 3  (integer division — discards remainder!)
int rem = a % b;       // 1  (modulo — the remainder)
```

⚠️ **`int / int` truncates**. `7 / 2 == 3`, not `3.5`. To get a real result, at least one operand must be `double`.

### Comparison

```java
a == b     // false
a != b     // true
a > b      // true
a <= b     // false
```

### Logical

```java
boolean x = true, y = false;
x && y     // false  (AND)
x || y     // true   (OR)
!x         // false  (NOT)
```

### Increment / Decrement

```java
int i = 5;
i++;       // i becomes 6
i--;       // i becomes 5
++i;       // i becomes 6 (but used before increment if in expression)
```

## 8.4 Control Flow

### if / else if / else

```java
int score = 75;
if (score >= 90) {
    System.out.println("A");
} else if (score >= 80) {
    System.out.println("B");
} else if (score >= 70) {
    System.out.println("C");
} else {
    System.out.println("F");
}
```

The `else if` and `else` are optional. Conditions must be inside parentheses.

### switch

```java
int day = 3;
switch (day) {
    case 1: System.out.println("Mon"); break;
    case 2: System.out.println("Tue"); break;
    case 3: System.out.println("Wed"); break;
    default: System.out.println("Other");
}
```

- `break` exits the switch — forgetting it causes **fall-through** (one case runs into the next). This is a common bug.
- `default` runs if no case matches.

### Ternary (one-line if/else)

```java
int max = (a > b) ? a : b;
```

Syntax: `condition ? value_if_true : value_if_false`.

## 8.5 Loops

### for

```java
for (int i = 0; i < 5; i++) {
    System.out.println(i);
}
```

- `int i = 0` — initialiser, runs once.
- `i < 5` — condition, checked before each iteration.
- `i++` — update, runs after each iteration.

### while

```java
int i = 0;
while (i < 5) {
    System.out.println(i);
    i++;
}
```

Use `while` when you don't know in advance how many iterations.

### do-while

```java
int i = 0;
do {
    System.out.println(i);
    i++;
} while (i < 5);
```

The body runs **at least once**, even if the condition is false initially.

### for-each (arrays)

```java
int[] arr = {1, 2, 3};
for (int x : arr) {
    System.out.println(x);
}
```

`int x` is a *copy* of each element. Modifying `x` doesn't change `arr`.

### break and continue

- `break` — exits the loop immediately.
- `continue` — skips to the next iteration.

```java
for (int i = 0; i < 10; i++) {
    if (i == 5) break;     // stop at 5
    if (i % 2 == 0) continue; // skip even numbers
    System.out.println(i);  // prints 1, 3
}
```

## 8.6 Methods

```java
public static int add(int a, int b) {
    return a + b;
}
```

| Token       | Meaning |
|-------------|---------|
| `public`    | accessible from anywhere |
| `static`    | belongs to the class, not an instance |
| `int`       | return type — what the method gives back |
| `add`       | method name |
| `int a, int b` | parameters — inputs |
| `return a + b;` | sends the value back |

### Calling

```java
int result = add(3, 4);   // result = 7
```

### Method overloading

Same name, different parameter list:

```java
public static int add(int a, int b) { return a + b; }
public static double add(double a, double b) { return a + b; }
public static int add(int a, int b, int c) { return a + b + c; }
```

Java picks the right one based on the arguments.

## 8.7 Arrays (1D)

```java
int[] arr = new int[5];         // empty array of length 5
int[] arr2 = {1, 2, 3, 4, 5};   // initialised with values
```

- `int[]` — array of `int`. The `[]` denotes "array of".
- `new int[5]` — creates an array with 5 slots, **all initialised to 0**.
- `arr.length` — returns 5 (note: **no parentheses** — it's a field, not a method).

### Access

```java
arr[0] = 10;        // set
int x = arr[2];     // get
```

Array indices start at 0. `arr[5]` throws `ArrayIndexOutOfBoundsException`.

### Iterate

```java
for (int i = 0; i < arr.length; i++) {
    System.out.println(arr[i]);
}
```

## 8.8 Input with Scanner

```java
import java.util.Scanner;

public class ReadInput {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt();
        String s = sc.next();
        System.out.println("n=" + n + ", s=" + s);
        sc.close();
    }
}
```

- `import java.util.Scanner;` — pulls the `Scanner` class into scope.
- `Scanner sc = new Scanner(System.in);` — creates a Scanner that reads from standard input.
- `sc.nextInt()` — reads one whitespace-delimited token and parses it as `int`.
- `sc.next()` — reads one whitespace-delimited token as `String`.
- `sc.nextLine()` — reads the entire rest of the line.
- `sc.close()` — releases the resource.

`Scanner` is slow for huge inputs (> 10⁵ numbers). For competitive programming use `BufferedReader` (covered next).

## 8.9 Input with BufferedReader (faster)

```java
import java.io.*;
import java.util.*;

public class FastRead {
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        String line = br.readLine();                 // whole line
        String[] parts = line.split(" ");
        int a = Integer.parseInt(parts[0]);
        int b = Integer.parseInt(parts[1]);
        System.out.println(a + b);
    }
}
```

- `BufferedReader` — reads text efficiently in big chunks.
- `br.readLine()` — returns `String` or `null` at EOF.
- `String.split(" ")` — splits on spaces.
- `Integer.parseInt(...)` — converts `String` → `int`.
- `throws IOException` — required because `readLine` can fail (e.g. stream closed).

---

# 9. Code Walkthrough — A Complete Day-1 Program

Open `src/day-01/Day1Demo.java`. It runs through every concept above.

```java
public class Day1Demo {
    public static void main(String[] args) {
        // 1. Variables & primitives
        int n = 10;
        long big = 1_000_000_000L;
        double pi = 3.14159;
        char c = 'X';
        boolean ok = true;

        // 2. Operators
        int sum = n + 5;
        int rem = n % 3;

        // 3. Control flow
        if (n % 2 == 0) System.out.println("even");
        else System.out.println("odd");

        // 4. Loops
        for (int i = 0; i < n; i++) {
            if (i == 5) break;
            if (i % 2 == 0) continue;
            System.out.print(i + " ");
        }
        System.out.println();

        // 5. Arrays
        int[] arr = {3, 1, 4, 1, 5, 9, 2, 6};
        int max = arr[0];
        for (int i = 1; i < arr.length; i++) {
            if (arr[i] > max) max = arr[i];
        }
        System.out.println("max = " + max);

        // 6. Method call
        int result = add(3, 4);
        System.out.println("add(3,4) = " + result);
    }

    public static int add(int a, int b) {
        return a + b;
    }
}
```

Walkthrough line-by-line:

- `public class Day1Demo` — class declaration. Filename must be `Day1Demo.java`.
- `public static void main(String[] args)` — entry point.
- `int n = 10;` — declares `n` of type `int` and assigns 10.
- `long big = 1_000_000_000L;` — `L` suffix forces the literal to be `long`. The underscores are visual separators, ignored by the compiler (Java 7+).
- `double pi = 3.14159;` — `double` literal.
- `char c = 'X';` — `char` literal uses single quotes.
- `boolean ok = true;` — `boolean` literal.
- `int sum = n + 5;` — uses `n`'s value (10), produces 15.
- `int rem = n % 3;` — `10 % 3 = 1`.
- `if (n % 2 == 0) ... else ...` — checks if `n` is even. `10 % 2 == 0` is `true`, prints "even".
- `for (int i = 0; i < n; i++)` — iterates `i` from 0 to 9.
- `if (i == 5) break;` — exits the loop when `i` reaches 5.
- `if (i % 2 == 0) continue;` — skips even values.
- `int[] arr = {3,1,4,1,5,9,2,6};` — array literal, length 8.
- `int max = arr[0];` — initialise with the first element (important! Never initialise with 0 if the array may contain negatives).
- `for (int i = 1; i < arr.length; i++)` — `arr.length` is a *field*, not a method — no `()`.
- `if (arr[i] > max) max = arr[i];` — standard max-of-array.
- `int result = add(3, 4);` — calls the static method.
- `public static int add(int a, int b) { return a + b; }` — returns 7.

---

# 10. Dry Run

For `int[] arr = {3, 1, 4, 1, 5, 9, 2, 6};`

| i | arr[i] | max before | condition `arr[i] > max` | max after |
|---|--------|------------|---------------------------|-----------|
| 1 | 1      | 3          | 1 > 3 ? no                | 3         |
| 2 | 4      | 3          | 4 > 3 ? yes               | 4         |
| 3 | 1      | 4          | no                        | 4         |
| 4 | 5      | 4          | yes                       | 5         |
| 5 | 9      | 5          | yes                       | 9         |
| 6 | 2      | 9          | no                        | 9         |
| 7 | 6      | 9          | no                        | 9         |

Final `max = 9`. ✓

For the `for (int i = 0; i < n; i++)` loop (with `n = 10`):

| i | i == 5? | i % 2 == 0? | prints? |
|---|---------|-------------|---------|
| 0 | no      | yes (skip)  | -       |
| 1 | no      | no          | 1       |
| 2 | no      | yes (skip)  | -       |
| 3 | no      | no          | 3       |
| 4 | no      | yes (skip)  | -       |
| 5 | yes — break | -       | -       |

Output: `1 3`

---

# 11. Time & Space Complexity (today only)

We don't have algorithms yet, but here's a preview for the patterns above:

| Operation                               | Complexity |
|-----------------------------------------|-----------:|
| Accessing `arr[i]`                      | O(1)       |
| Setting `arr[i] = x`                    | O(1)       |
| Looping over n elements                 | O(n)       |
| Nested loops over n × n elements        | O(n²)      |
| `Scanner.nextInt()`                     | O(1) per call, slow in practice |
| `BufferedReader.readLine()`             | O(line length) |

Space: every program above uses O(1) *auxiliary* space (no extra structures proportional to input).

---

# 12. Space Complexity

For now: just note that `int[] arr = new int[n]` uses O(n) **space** (the array itself counts). Local variables like `int max` use O(1).

---

# 13. Common Mistakes

1. **Forgetting `;`** at the end of a statement → compile error.
2. **Off-by-one errors** in loops. `for (int i = 0; i < n; i++)` iterates `n` times; `for (int i = 0; i <= n; i++)` iterates `n+1` times and throws on the last access.
3. **Initialising max/min to 0**. If the array contains only negatives, `max = 0` is wrong. Initialise to `arr[0]`.
4. **Integer division**: `5 / 2 == 2`, not `2.5`. Use `5.0 / 2 == 2.5`.
5. **`arr.length` vs `arr.length()`**: arrays use the field `arr.length` (no parens); `String`s use the method `s.length()`.
6. **`String` comparison**: `==` checks reference, not content. Use `s1.equals(s2)`.
7. **`Scanner.nextInt()` after `Scanner.nextLine()`**: `nextInt()` leaves the newline in the buffer, so a subsequent `nextLine()` returns "". Use an extra `nextLine()` to consume it.
8. **Modifying a for-each loop variable** — it's a copy, so the original doesn't change.
9. **Confusing `&` vs `&&`**: `&&` short-circuits; `&` is bitwise. For boolean conditions, prefer `&&`.
10. **`switch` fall-through** — forgetting `break`.

---

# 14. Interview Questions

### Q1. What's the difference between `int` and `Integer`?
`int` is a primitive (no methods, stored directly). `Integer` is a reference type (object, can be `null`, has methods). Use `int` for DSA performance.

### Q2. Why does Java have 8 primitive types instead of just one?
Performance and memory. Each primitive is a fixed-size value, stored directly. Reference types are heap-allocated objects — slower to create and GC-tracked.

### Q3. What's the default value of an `int[]` element?
0. Default-initialised arrays always have all-zero values for primitives.

### Q4. When would you use `long` over `int`?
When the value can exceed ~ 2.1 × 10⁹ (e.g. counting, prefix sums, factorials, large n).

### Q5. What's the output of `7 / 2` and `7 % 2` in Java?
`7 / 2 == 3`, `7 % 2 == 1`. Both are integer division / modulo.

### Q6. What's the difference between `break` and `continue`?
`break` exits the loop. `continue` jumps to the next iteration.

### Q7. Why is `Scanner` slower than `BufferedReader`?
`Scanner` parses tokens on every `nextInt()` call and uses regex internally. `BufferedReader` reads raw characters in big chunks; you parse them yourself, but it's much faster.

### Q8. What's `String[] args` used for?
Holds command-line arguments. `java MyClass hello world` → `args = ["hello", "world"]`.

### Q9. Why does `main` need to be `static`?
The JVM calls `MyClass.main(...)` without first creating a `MyClass` object. `static` makes the method callable on the class itself.

### Q10. What happens if you write `float f = 3.14;`?
Compile error: `3.14` is a `double` literal, can't be assigned to `float` without a cast. Use `3.14f`.

---

# 15. Practice Problems

## 🟢 Easy

### 1. Sum of Two Numbers

**Difficulty:** Easy
**Problem:** Read two integers and print their sum.
**Input:** `3 5`
**Output:** `8`
**Expected Concept:** I/O, operators
**Target Complexity:** O(1)
**Interview Relevance:** Low

### 2. Even or Odd

**Difficulty:** Easy
**Problem:** Read an integer. Print "even" or "odd".
**Input:** `7`
**Output:** `odd`
**Expected Concept:** Modulo
**Target Complexity:** O(1)
**Interview Relevance:** Low

### 3. Max of Three Numbers

**Difficulty:** Easy
**Problem:** Read three integers and print the largest.
**Input:** `3 9 5`
**Output:** `9`
**Expected Concept:** Branching
**Target Complexity:** O(1)
**Interview Relevance:** Low

### 4. FizzBuzz (1 to n)

**Difficulty:** Easy
**Problem:** Print 1..n. For multiples of 3 print "Fizz", for 5 "Buzz", for both "FizzBuzz".
**Input:** `n = 15`
**Output:** `1, 2, Fizz, 4, Buzz, Fizz, 7, 8, Fizz, Buzz, 11, Fizz, 13, 14, FizzBuzz`
**Expected Concept:** Loops, modulo
**Target Complexity:** O(n)
**Interview Relevance:** Medium

### 5. Reverse an Array

**Difficulty:** Easy
**Problem:** Read n then n integers. Print them in reverse order.
**Input:** `n=4, arr=[1,2,3,4]`
**Output:** `4 3 2 1`
**Expected Concept:** Array traversal
**Target Complexity:** O(n)
**Interview Relevance:** Medium

## 🟡 Medium

### 6. Count Digits

**Difficulty:** Medium
**Problem:** Read an integer n. Count the number of digits in n (without converting to string).
**Input:** `12345`
**Output:** `5`
**Expected Concept:** While loop, division
**Target Complexity:** O(log n)
**Interview Relevance:** Low

### 7. Sum of First N Naturals

**Difficulty:** Medium
**Problem:** Read n. Print 1+2+...+n.
**Input:** `5`
**Output:** `15`
**Expected Concept:** Loops or formula
**Target Complexity:** O(1) with formula, O(n) with loop
**Interview Relevance:** Low

### 8. Power of Two Check

**Difficulty:** Medium
**Problem:** Given a positive integer n, return true if it is a power of two, false otherwise.
**Input:** `n = 16`
**Output:** `true`
**Expected Concept:** While loop or bitwise
**Target Complexity:** O(log n)
**Interview Relevance:** Medium

### 9. Swap Two Numbers Without Temp

**Difficulty:** Medium
**Problem:** Read a and b. Swap them without using a third variable.
**Input:** `a=3, b=5`
**Output:** `a=5, b=3`
**Expected Concept:** Arithmetic or XOR
**Target Complexity:** O(1)
**Interview Relevance:** Low

### 10. Second Largest

**Difficulty:** Medium
**Problem:** Read n then n integers. Print the second-largest distinct value.
**Input:** `[5, 2, 8, 8, 3]`
**Output:** `5`
**Expected Concept:** Single pass tracking
**Target Complexity:** O(n)
**Interview Relevance:** High

## 🔴 Hard

### 11. Rotate Array by K (in-place)

**Difficulty:** Hard
**Problem:** Rotate an array to the right by k positions in place. Example: [1,2,3,4,5], k=2 → [4,5,1,2,3].
**Input:** `n=5, arr=[1,2,3,4,5], k=2`
**Output:** `[4,5,1,2,3]`
**Expected Concept:** Reversal algorithm
**Target Complexity:** O(n) time, O(1) space
**Interview Relevance:** High

### 12. Print All Prime Numbers up to N

**Difficulty:** Hard
**Problem:** Print all primes from 2 to n inclusive.
**Input:** `n = 20`
**Output:** `2 3 5 7 11 13 17 19`
**Expected Concept:** Sieve of Eratosthenes (preview)
**Target Complexity:** O(n log log n)
**Interview Relevance:** Medium

### 13. Reverse an Integer (handle overflow)

**Difficulty:** Hard
**Problem:** Reverse digits of a 32-bit signed integer. Return 0 if overflow.
**Input:** `x = 123`
**Output:** `321`
**Expected Concept:** Modulo, division, careful bounds
**Target Complexity:** O(log x)
**Interview Relevance:** High

### 14. Count Set Bits

**Difficulty:** Hard
**Problem:** Count the number of 1-bits in an integer.
**Input:** `n = 11` (binary `1011`)
**Output:** `3`
**Expected Concept:** Bitwise AND
**Target Complexity:** O(1) with `n & (n-1)` trick
**Interview Relevance:** High

### 15. Pascal's Triangle

**Difficulty:** Hard
**Problem:** Print the first n rows of Pascal's triangle.
**Input:** `n = 5`
**Output:**
```
1
1 1
1 2 1
1 3 3 1
1 4 6 4 1
```
**Expected Concept:** 2D array, recurrence
**Target Complexity:** O(n²)
**Interview Relevance:** Medium

---

# 16. Practice Hints

## Easy
1. Two `nextInt()` calls then `println(a + b)`.
2. `n % 2 == 0`.
3. Track three variables.
4. Inside the loop, use `if/else` on modulo.
5. Loop from `n-1` down to 0.

## Medium
6. Repeatedly divide by 10.
7. Use the formula `n*(n+1)/2` (watch for `long` overflow).
8. While `n % 2 == 0`, divide. Then check if `n == 1`.
9. `a = a + b; b = a - b; a = a - b;` (careful with overflow).
10. Track `first` and `second` largest in one pass.

## Hard
11. Reverse first `n-k`, reverse last `k`, reverse whole array.
12. Mark multiples of each prime as composite.
13. Pop digits with `% 10` and `/ 10`, check overflow before `result = result * 10 + digit`.
14. `while (n != 0) { count++; n = n & (n - 1); }`.
15. `C(i, j) = C(i-1, j-1) + C(i-1, j)`.

---

# 17. Revision Checklist

- [ ] Can write a Java program with `main`, print output
- [ ] Know all 8 primitive types and their ranges
- [ ] Can use `if/else`, `switch`, `for`, `while`, `do-while`
- [ ] Can write and call a method
- [ ] Can read input with `Scanner`
- [ ] Can read input with `BufferedReader`
- [ ] Can declare, initialise, traverse a 1D array
- [ ] Know common mistakes (off-by-one, integer division, `arr.length` vs `arr.length()`)
- [ ] Solved all 5 Easy problems
- [ ] Solved all 5 Medium problems
- [ ] Attempted all 5 Hard problems
- [ ] Ran `Day1Demo.java` and modified it

---

# 18. Key Takeaways

- Every Java program needs a class and a `public static void main(String[] args)`.
- Primitives: `int`, `long`, `double`, `char`, `boolean` — these cover DSA.
- `int / int` truncates; at least one operand must be `double` for real division.
- Array length is `arr.length` (field), `String` length is `s.length()` (method).
- Use `Scanner` for simple input, `BufferedReader` for fast/large input.
- `break` exits a loop, `continue` skips to the next iteration.
- Always initialise `max`/`min` to `arr[0]`, never to 0 (negatives!).
- `&&` short-circuits, `&` is bitwise.

Tomorrow: **OOP in Java** — the foundation for every data structure we'll build from Day 13 onward.


## Solutions

### Problem 1 — SumTwo (E)

```java
class SumTwo {
    public static void main(String[] args) {
        java.util.Scanner sc = new java.util.Scanner(System.in);
        int a = sc.nextInt(), b = sc.nextInt();
        System.out.println(a + b);
    }
}
```

### Problem 2 — EvenOdd (E)

```java
class EvenOdd {
    public static void main(String[] args) {
        java.util.Scanner sc = new java.util.Scanner(System.in);
        int n = sc.nextInt();
        System.out.println(n % 2 == 0 ? "even" : "odd");
    }
}
```

### Problem 3 — MaxThree (E)

```java
class MaxThree {
    public static void main(String[] args) {
        java.util.Scanner sc = new java.util.Scanner(System.in);
        int a = sc.nextInt(), b = sc.nextInt(), c = sc.nextInt();
        System.out.println(Math.max(a, Math.max(b, c)));
    }
}
```

### Problem 4 — FizzBuzz (E)

```java
class FizzBuzz {
    public static void main(String[] args) {
        int n = 15;
        for (int i = 1; i <= n; i++) {
            if (i % 15 == 0) System.out.println("FizzBuzz");
            else if (i % 3 == 0) System.out.println("Fizz");
            else if (i % 5 == 0) System.out.println("Buzz");
            else System.out.println(i);
        }
    }
}
```

### Problem 5 — ReverseArr (E)

```java
class ReverseArr {
    public static void main(String[] args) {
        int[] a = {1, 2, 3, 4};
        for (int i = a.length - 1; i >= 0; i--) System.out.print(a[i] + " ");
    }
}
```

### Problem 6 — CountDigits (M)

```java
class CountDigits {
    public static void main(String[] args) {
        int n = 12345, c = 0;
        while (n != 0) { c++; n /= 10; }
        System.out.println(c);
    }
}
```

### Problem 7 — SumN (M)

```java
class SumN {
    public static void main(String[] args) {
        long n = 100;
        System.out.println(n * (n + 1) / 2);
    }
}
```

### Problem 8 — PowerOfTwo (M)

```java
class PowerOfTwo {
    public static void main(String[] args) {
        int n = 16;
        System.out.println(n > 0 && (n & (n - 1)) == 0);
    }
}
```

### Problem 9 — SwapNoTemp (M)

```java
class SwapNoTemp {
    public static void main(String[] args) {
        int a = 3, b = 5;
        a = a + b; b = a - b; a = a - b;
        System.out.println(a + " " + b);
    }
}
```

### Problem 10 — SecondLargest (M)

```java
class SecondLargest {
    public static void main(String[] args) {
        int[] a = {5, 2, 8, 8, 3};
        int first = Integer.MIN_VALUE, second = Integer.MIN_VALUE;
        for (int x : a) {
            if (x > first) { second = first; first = x; }
            else if (x < first && x > second) second = x;
        }
        System.out.println(second);
    }
}
```

### Problem 11 — RotateArrK (H)

```java
class RotateArrK {
    static void reverse(int[] a, int l, int r) {
        while (l < r) { int t = a[l]; a[l] = a[r]; a[r] = t; l++; r--; }
    }
    static void rotate(int[] a, int k) {
        k %= a.length;
        reverse(a, 0, a.length - 1);
        reverse(a, 0, k - 1);
        reverse(a, k, a.length - 1);
    }
    public static void main(String[] args) {
        int[] a = {1,2,3,4,5}; rotate(a, 2);
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 12 — Sieve (H)

```java
class Sieve {
    public static void main(String[] args) {
        int n = 20;
        boolean[] p = new boolean[n+1];
        java.util.Arrays.fill(p, true);
        p[0] = p[1] = false;
        for (int i = 2; (long)i*i <= n; i++)
            if (p[i]) for (int j = i*i; j <= n; j += i) p[j] = false;
        for (int i = 2; i <= n; i++) if (p[i]) System.out.print(i + " ");
    }
}
```

### Problem 13 — ReverseInt (H)

```java
class ReverseInt {
    public static void main(String[] args) {
        int x = 123, r = 0;
        while (x != 0) {
            int d = x % 10;
            if (r > Integer.MAX_VALUE/10 || r < Integer.MIN_VALUE/10) { r = 0; break; }
            r = r * 10 + d; x /= 10;
        }
        System.out.println(r);
    }
}
```

### Problem 14 — CountSetBits (H)

```java
class CountSetBits {
    public static void main(String[] args) {
        int n = 11, c = 0;
        while (n != 0) { c++; n &= (n - 1); }
        System.out.println(c);
    }
}
```

### Problem 15 — Pascals (H)

```java
class Pascals {
    public static void main(String[] args) {
        int n = 5;
        for (int i = 0; i < n; i++) {
            int v = 1;
            StringBuilder sb = new StringBuilder();
            for (int j = 0; j <= i; j++) { sb.append(v).append(' '); v = v * (i - j) / (j + 1); }
            System.out.println(sb);
        }
    }
}
```

