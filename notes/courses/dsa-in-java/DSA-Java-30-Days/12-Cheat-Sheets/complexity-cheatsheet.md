# Time & Space Complexity Cheat Sheet

## 1. Big-O Notation

- **O(f(n))** — upper bound (worst-case).
- **Ω(f(n))** — lower bound (best-case).
- **Θ(f(n))** — tight bound (asymptotically exact).

We usually quote **O** in interviews.

## 2. Rules

1. Drop constants: `O(2n)` → `O(n)`.
2. Drop lower-order terms: `O(n² + n)` → `O(n²)`.
3. Different inputs → different variables: `O(a + b)`, not `O(n)`.
4. Recursion: `T(n) = aT(n/b) + f(n)` → Master Theorem.

## 3. Common time complexities (fastest → slowest)

| Complexity | Name | Example |
|---|---|---|
| O(1) | constant | hash lookup |
| O(log n) | logarithmic | binary search |
| O(√n) | square-root | prime check up to √n |
| O(n) | linear | array scan |
| O(n log n) | linearithmic | merge sort |
| O(n²) | quadratic | bubble sort, pair loops |
| O(n³) | cubic | triple loops, matrix multiply naive |
| O(2ⁿ) | exponential | subsets of n |
| O(n!) | factorial | permutations of n |

## 4. Recursion complexity cheat sheet

```java
// T(n) = T(n-1) + O(1) → O(n)            (e.g. factorial)
// T(n) = 2T(n-1) + O(1) → O(2ⁿ)          (e.g. fibonacci naive)
// T(n) = T(n/2) + O(1) → O(log n)        (e.g. binary search)
// T(n) = 2T(n/2) + O(n) → O(n log n)     (e.g. merge sort)
// T(n) = T(n/2) + O(n) → O(n)            (e.g. sum of subarray)
// T(n) = 2T(n/2) + O(n²) → O(n²)         (e.g. naive DP build)
```

## 5. Amortised analysis

Some operations have O(1) amortised cost despite occasional O(n):
- `ArrayList.add` — doubling.
- `HashMap.put` — average O(1) amortised.
- `StringBuilder.append` — amortised O(1).

## 6. Data-structure complexity

| Structure | Access | Search | Insert | Delete |
|---|---|---|---|---|
| Array | O(1) | O(n) | O(n) | O(n) |
| LinkedList | O(n) | O(n) | O(1) | O(1) |
| HashMap (avg) | – | O(1) | O(1) | O(1) |
| HashMap (worst) | – | O(n) | O(n) | O(n) |
| TreeMap | – | O(log n) | O(log n) | O(log n) |
| HashSet (avg) | – | O(1) | O(1) | O(1) |
| TreeSet | – | O(log n) | O(log n) | O(log n) |
| Heap | O(1) peek | O(n) | O(log n) | O(log n) |
| BST (balanced) | – | O(log n) | O(log n) | O(log n) |

## 7. Algorithm complexity

| Algorithm | Time | Space |
|---|---|---|
| Binary search | O(log n) | O(1) |
| Merge sort | O(n log n) | O(n) |
| Quick sort (avg) | O(n log n) | O(log n) |
| Quick sort (worst) | O(n²) | O(log n) |
| Heap sort | O(n log n) | O(1) |
| BFS/DFS | O(V+E) | O(V) |
| Dijkstra (binary heap) | O((V+E) log V) | O(V) |
| Bellman-Ford | O(VE) | O(V) |
| Floyd-Warshall | O(V³) | O(V²) |
| Kruskal | O(E log E) | O(V) |
| Prim (binary heap) | O(E log V) | O(V) |
| Topological sort | O(V+E) | O(V) |
| Knapsack DP | O(n·W) | O(W) |
| LCS DP | O(m·n) | O(m·n) |
| LIS (binary search) | O(n log n) | O(n) |
| KMP | O(n+m) | O(m) |

## 8. Space complexity

- **Auxiliary space** = what you allocate beyond input.
- **Recursive calls** count toward space due to call stack.

```java
int fib(int n) { return n < 2 ? n : fib(n-1) + fib(n-2); }
// Time: O(2ⁿ), Space: O(n) (call stack depth)
```

```java
int[] fib(int n) {
    int[] dp = new int[n+1];
    dp[0]=0; dp[1]=1;
    for (int i=2;i<=n;i++) dp[i]=dp[i-1]+dp[i-2];
    return dp;
}
// Time: O(n), Space: O(n)
```

## 9. Interview tips

1. Always state both **time** and **space**.
2. Use worst-case unless specifically asked.
3. Big-O of `n log n` is acceptable for `n ≤ 10⁶`.
4. Big-O of `n²` is fine for `n ≤ 10⁴`.
5. Big-O of `n³` is fine for `n ≤ 200`.
6. Big-O of `2ⁿ` only for `n ≤ 25`.
7. Big-O of `n!` only for `n ≤ 12`.

## 10. Quick sanity-check

```
n = 10     → O(n!) OK, O(2ⁿ) OK, O(n³) OK
n = 100    → O(2ⁿ) OK, O(n³) OK, O(n⁴) borderline
n = 1_000  → O(n³) slow, O(n²) OK, O(n log n) great
n = 10⁶    → O(n²) slow, O(n log n) great, O(n) ideal
n = 10⁹    → O(n) too slow, O(log n) or O(1) needed
```
