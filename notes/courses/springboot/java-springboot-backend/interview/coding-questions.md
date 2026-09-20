# Java coding questions for backend interviews

For each: problem, example, approach, solution, complexity.

## Reverse a string

```java
new StringBuilder(s).reverse().toString();
```

O(n)

## Frequency map

```java
Map<String, Long> freq = list.stream().collect(Collectors.groupingBy(x -> x, Collectors.counting()));
```

## Two sum (indices)

HashMap value→index, one pass O(n).

## Remove duplicates preserve order

`new LinkedHashSet<>(list)`

## groupingBy

`Collectors.groupingBy(User::department)`

## Custom comparator

`list.sort(Comparator.comparing(User::getName).thenComparing(User::getId));`

## Immutable class

private final fields, no setters, defensive copies.

## Optional

`repo.findById(id).orElseThrow(...)` — never `.get()` blindly.

Tie streams to DTO mapping, not to replacing SQL.
