# Java Collections Cheat Sheet

## 1. Interface Hierarchy

```
Iterable
 └── Collection
      ├── List       (ordered, index-based, duplicates)
      │    ├── ArrayList      — O(1) get, O(n) insert/remove
      │    ├── LinkedList     — O(n) get, O(1) insert/remove at ends
      │    └── Vector         — synchronized ArrayList (legacy)
      │
      ├── Set        (no duplicates)
      │    ├── HashSet        — O(1), hash-table backed, unordered
      │    ├── LinkedHashSet  — preserves insertion order
      │    └── TreeSet        — O(log n), sorted, red-black tree
      │
      └── Queue      (FIFO)
           ├── LinkedList     — also implements Queue
           ├── ArrayDeque     — circular array, faster than LinkedList as queue
           └── PriorityQueue  — heap, O(log n) insert/extract
                (min-heap by default; pass Comparator to override)

Map (separate hierarchy, not under Collection)
 ├── HashMap         — O(1), unordered
 ├── LinkedHashMap   — preserves insertion or access order
 ├── TreeMap         — O(log n), sorted by key
 └── ConcurrentHashMap — thread-safe, segmented
```

## 2. List — when to use

| Operation | ArrayList | LinkedList |
|---|---|---|
| `get(i)` | **O(1)** | O(n) |
| `add(end)` | amortised O(1) | O(1) |
| `add(0)` / `add(mid)` | O(n) | O(1) |
| `remove(0)` / `remove(mid)` | O(n) | O(1) |
| Memory | compact | 2x (prev+next) |

**Rule**: default to `ArrayList`. Use `LinkedList` only for queue/deque with frequent `addFirst`/`removeFirst`.

## 3. Set — when to use

- `HashSet`: deduplication, O(1) membership check.
- `LinkedHashSet`: same + insertion-order iteration.
- `TreeSet`: need sorted iteration or `first()`/`last()`/`floor()`/`ceiling()`.

## 4. Queue vs Deque

- `Queue` → `offer`, `poll`, `peek`.
- `Deque` → double-ended: `offerFirst`, `offerLast`, `pollFirst`, `pollLast`, `peekFirst`, `peekLast`.
- `ArrayDeque` is the modern replacement for `Stack` (LIFO) — `push`/`pop` map to `addFirst`/`removeFirst`.

## 5. PriorityQueue — min-heap by default

```java
PriorityQueue<Integer> minHeap = new PriorityQueue<>();           // min
PriorityQueue<Integer> maxHeap = new PriorityQueue<>(Comparator.reverseOrder()); // max
```

Operations: `offer` O(log n), `poll` O(log n), `peek` O(1).

## 6. Map — when to use

| Need | Use |
|---|---|
| Key → Value, O(1) | `HashMap` |
| Sorted by key, range queries | `TreeMap` |
| LRU cache (access-order) | `LinkedHashMap(accessOrder=true)` |
| Thread-safe | `ConcurrentHashMap` |
| Insertion-order iteration | `LinkedHashMap` |
| Multi-key lookup | `Map<K, List<V>>` or `Map<K, Map<K2, V>>` |

## 7. equals + hashCode contract

If `a.equals(b)` then `a.hashCode() == b.hashCode()`. Always override both. `HashMap` uses `hashCode()` to bucket and `equals()` to disambiguate collisions.

```java
@Override public int hashCode() { return Objects.hash(field1, field2); }
@Override public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof Foo)) return false;
    Foo f = (Foo) o;
    return field1 == f.field1 && Objects.equals(field2, f.field2);
}
```

## 8. Iteration

```java
for (T x : coll)                  // enhanced for
coll.forEach(x -> ...);            // lambda (Collection only)
Iterator<T> it = coll.iterator();  // explicit (use when removing)
```

`Map`:
```java
for (Map.Entry<K,V> e : m.entrySet()) { K k = e.getKey(); V v = e.getValue(); }
m.forEach((k,v) -> ...);
```

## 9. Thread-safety

- `Collections.synchronizedList(new ArrayList<>())` — coarse.
- `CopyOnWriteArrayList` — many readers, few writers.
- `ConcurrentHashMap` — concurrent reads/writes.
- `Collections.unmodifiableX(...)` — read-only view.

## 10. Common idioms

- Top-K frequent: `Map<K,Integer> count; PriorityQueue<Map.Entry<K,Integer>> minHeap = new PriorityQueue<>(Comparator.comparingInt(Map.Entry::getValue));`
- LRU: `LinkedHashMap` with accessOrder and override `removeEldestEntry`.
- Dedupe stream: `list.stream().distinct().collect(toList())`.
- Group by: `list.stream().collect(Collectors.groupingBy(x -> x.field))`.

## 11. Performance traps

1. **Autoboxing** in tight loops → use `IntStream` / primitive arrays.
2. `ArrayList` resize: pre-size with `new ArrayList<>(n)`.
3. `HashMap` resize: pre-size with `new HashMap<>(n)` or specify load factor.
4. `Iterator.remove()` vs `for` removal — use iterator to avoid `ConcurrentModificationException`.
5. `TreeMap` is O(log n); if you only need ordered iteration over HashMap, sort keys once.

## 12. Quick-reference table

| I want to | Use |
|---|---|
| Find duplicate | `Set<T> seen` |
| Count frequencies | `Map<T,Integer> counter` |
| Top-K | `PriorityQueue` |
| LRU | `LinkedHashMap` |
| Stack | `ArrayDeque` |
| Queue | `ArrayDeque` |
| Min/Max | `PriorityQueue` |
| Range query | `TreeMap` |
| FIFO thread-safe | `ConcurrentLinkedQueue` |
| Producer-consumer | `BlockingQueue` |
