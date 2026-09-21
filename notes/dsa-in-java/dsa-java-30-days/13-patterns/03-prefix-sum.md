# Pattern 3 — Prefix Sum

## When to use
- Range sum queries.
- Subarray sum equals K.
- "How many subarrays have property X?"

## Core idea

```java
int[] prefix = new int[n + 1]; // prefix[0] = 0
for (int i = 0; i < n; i++)
    prefix[i + 1] = prefix[i] + a[i];
// sum(i..j) = prefix[j+1] - prefix[i]
```

## Canonical problems
- Range sum query (static, immutable)
- Subarray sum equals K → HashMap of prefix sums.
- Product of array except self.
- Maximum size subarray sum equals K.
- 2D prefix sum for matrix range queries.

## Subarray sum equals K

```java
Map<Integer, Integer> seen = new HashMap<>();
seen.put(0, 1);  // empty prefix
int sum = 0, count = 0;
for (int x : a) {
    sum += x;
    count += seen.getOrDefault(sum - k, 0);
    seen.merge(sum, 1, Integer::sum);
}
```

## 2D prefix sum

```java
int[][] pre = new int[m + 1][n + 1];
for (int i = 1; i <= m; i++)
    for (int j = 1; j <= n; j++)
        pre[i][j] = a[i-1][j-1] + pre[i-1][j] + pre[i][j-1] - pre[i-1][j-1];

// sum of sub-rectangle (r1..r2, c1..c2):
return pre[r2+1][c2+1] - pre[r1][c2+1] - pre[r2+1][c1] + pre[r1][c1];
```

## Complexity
- Build: O(n).
- Query: O(1) per query.
- Subarray-sum-equals-K: O(n) with HashMap.

## Java tips
- Use `long` for prefix sums if values are large.
- `seen.put(0, 1)` initialisation is critical.
- Use `merge` to update counts atomically.

## Variations
- Difference array: for range updates on static array.
- Prefix XOR for subarray XOR queries.
