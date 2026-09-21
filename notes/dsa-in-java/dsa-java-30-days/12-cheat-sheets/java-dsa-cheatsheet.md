# Java DSA Cheat Sheet

## 1. Basic Types

| Type | Size | Default |
|---|---|---|
| `byte` | 1 | 0 |
| `short` | 2 | 0 |
| `int` | 4 | 0 |
| `long` | 8 | 0L |
| `float` | 4 | 0.0f |
| `double` | 8 | 0.0d |
| `char` | 2 | '\u0000' |
| `boolean` | 1 | false |

## 2. Operators (most useful for DSA)

```
arithmetic:    + - * / %
comparison:    == != < > <= >=
logical:       && || !
bitwise:       & | ^ ~ << >> >>>
assignment:    = += -= *= /= %= &= |= ^= <<= >>= >>>=
ternary:       cond ? a : b
```

## 3. Bit tricks

```java
// Check if n is a power of 2:
(n & (n - 1)) == 0

// Get lowest set bit:
n & -n

// Clear lowest set bit:
n & (n - 1)

// Iterate all set bits:
for (long x = n; x != 0; x &= x - 1) {
    int b = Long.numberOfTrailingZeros(x);
}

// Set, clear, toggle bit i:
set:    n | (1 << i)
clear:  n & ~(1 << i)
toggle: n ^ (1 << i)

// Iterate all subsets of a bitmask:
for (int sub = mask; ; sub = (sub - 1) & mask) {
    // use sub
    if (sub == 0) break;
}
```

## 4. Math utilities

```java
Math.max(a, b);     Math.min(a, b);
Math.abs(x);        // beware Integer.MIN_VALUE
Math.pow(a, b);     // double, slow — use fastPow for ints
Math.sqrt(x);
Math.log(x);        // natural log
Math.ceil(x);       Math.floor(x);     Math.round(x);
Math.gcd(a, b);     // Java 17+
Math.PI;            Math.E;
```

Fast power:
```java
long pow(long base, long exp, long mod) {
    long result = 1; base %= mod;
    while (exp > 0) {
        if ((exp & 1) == 1) result = result * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return result;
}
```

GCD (Euclidean):
```java
int gcd(int a, int b) { return b == 0 ? a : gcd(b, a % b); }
int lcm(int a, int b) { return a / gcd(a, b) * b; } // avoid overflow
```

Sieve of Eratosthenes:
```java
boolean[] sieve(int n) {
    boolean[] isPrime = new boolean[n+1];
    Arrays.fill(isPrime, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; i*i <= n; i++)
        if (isPrime[i])
            for (int j = i*i; j <= n; j += i) isPrime[j] = false;
    return isPrime;
}
```

## 5. Strings

```java
String s = "abc";
char c = s.charAt(i);          // char access
s.length();                    // length
s.substring(lo, hi);           // [lo, hi)
s.indexOf(c);                  // first index, -1 if absent
s.equals(t);                   // content compare
s.compareTo(t);                // lexicographic compare
s.split(regex);                // regex split
s.toCharArray();               // char[]
new String(chars);             // rebuild
StringBuilder sb = new StringBuilder();
sb.append(x);                  // amortised O(1)
sb.reverse();
sb.toString();
```

Char ↔ int:
```java
char c = '5'; int d = c - '0'; // digit to int
char c = (char) (d + '0');     // int to digit
```

## 6. Arrays

```java
int[] a = new int[n];         // 0-initialised
int[] a = {1,2,3};
Arrays.sort(a);                // ascending
Arrays.sort(a, lo, hi);        // sub-range
Arrays.sort(a, Comparator.reverseOrder()); // boxed only
Integer[] boxed = {1,2,3};
int[] unbox = Arrays.stream(boxed).mapToInt(Integer::intValue).toArray();
int idx = Arrays.binarySearch(a, t);
Arrays.fill(a, v);
int[] c = Arrays.copyOf(a, k);
int[] d = Arrays.copyOfRange(a, lo, hi);
Arrays.equals(a, b);
```

## 7. Loops and control

```java
for (int i = 0; i < n; i++)          // classic
for (int x : arr)                     // enhanced
for (int i = arr.length - 1; i >= 0; i--)  // reverse
while (lo <= hi) { ... }
do { ... } while (cond);
```

`break`/`continue`/`return` as usual. Labels:
```java
outer: for (...) {
    for (...) {
        if (...) break outer;
    }
}
```

## 8. Common patterns

### Two pointers
```java
int lo = 0, hi = arr.length - 1;
while (lo < hi) {
    if (...) lo++;
    else hi--;
}
```

### Sliding window
```java
int lo = 0;
for (int hi = 0; hi < n; hi++) {
    add(arr[hi]);
    while (invalid) remove(arr[lo++]);
    update();
}
```

### BFS
```java
Deque<Node> q = new ArrayDeque<>();
Set<Node> seen = new HashSet<>();
q.offer(start); seen.add(start);
while (!q.isEmpty()) {
    Node u = q.poll();
    for (Node v : u.neighbors())
        if (seen.add(v)) q.offer(v);
}
```

### DFS recursive
```java
void dfs(Node u, Set<Node> seen) {
    if (!seen.add(u)) return;
    for (Node v : u.neighbors()) dfs(v, seen);
}
```

### Binary search
```java
int lo = 0, hi = n - 1;
while (lo <= hi) {
    int mid = lo + (hi - lo) / 2;
    if (arr[mid] == t) return mid;
    if (arr[mid] < t) lo = mid + 1; else hi = mid - 1;
}
```

### Topological sort (Kahn)
```java
int[] indeg = new int[n];
// fill indeg
Queue<Integer> q = new ArrayDeque<>();
for (int i = 0; i < n; i++) if (indeg[i] == 0) q.offer(i);
while (!q.isEmpty()) {
    int u = q.poll();
    for (int v : g.get(u)) if (--indeg[v] == 0) q.offer(v);
}
```

### Union-Find
```java
int[] parent = new int[n], rank = new int[n];
for (int i = 0; i < n; i++) parent[i] = i;
int find(int x) { return parent[x] == x ? x : (parent[x] = find(parent[x])); }
void union(int a, int b) {
    a = find(a); b = find(b);
    if (a == b) return;
    if (rank[a] < rank[b]) { int t = a; a = b; b = t; }
    parent[b] = a;
    if (rank[a] == rank[b]) rank[a]++;
}
```

## 9. Java gotchas

1. `int` division truncates: `5 / 2 == 2`.
2. `==` on `Integer` is reference equality until -128..127.
3. `ArrayList` initial size 0; first `add` triggers resize.
4. `HashMap` keys must be immutable (or treat as immutable).
5. `String` is immutable — every concatenation creates new object.
6. `Math.abs(Integer.MIN_VALUE)` is still negative.
7. `i++` vs `++i`: post-increment uses old value then increments.
8. `for (int x : list)` — `x` is a copy, not a reference (for boxed types).
9. `switch` on `String` is allowed since Java 7.
10. `var` (Java 10+) — local type inference only.

## 10. Common imports

```java
import java.util.*;          // collections
import java.util.stream.*;   // streams
import java.util.function.*; // functional interfaces
import java.math.BigInteger; // arbitrary precision
import java.io.*;            // I/O
import java.util.concurrent.*;
import java.util.regex.*;
```
