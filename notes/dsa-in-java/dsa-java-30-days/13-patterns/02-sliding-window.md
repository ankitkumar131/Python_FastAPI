# Pattern 2 — Sliding Window

## When to use
- Contiguous subarray / substring.
- "Longest/shortest with constraint X".
- Both fixed-size and variable-size windows.

## When NOT to use
- Subsequence (non-contiguous).
- Need ALL pairs, not just contiguous.

## Two flavours

### Fixed-size window (size k)

```java
int sum = 0;
for (int i = 0; i < k; i++) sum += a[i];
int best = sum;
for (int i = k; i < a.length; i++) {
    sum += a[i] - a[i - k];
    best = Math.max(best, sum);
}
```

### Variable-size window

```java
int lo = 0, best = 0;
for (int hi = 0; hi < a.length; hi++) {
    add(a[hi]);
    while (invalid()) remove(a[lo++]);
    best = Math.max(best, hi - lo + 1);
}
```

## Canonical problems
- Maximum sum subarray of size K
- Longest substring without repeating characters
- Minimum window substring
- Longest repeating character replacement
- Permutation in string
- Fruit into baskets
- Subarrays with K different integers

## Complexity
- Time: O(n) — each element added and removed at most once.
- Space: O(1) or O(K) for the window state.

## Java tips
- Use `int lo = 0` not `int lo = -1`.
- Inner while loop must strictly shrink when invalid.
- Track window state in `int[] freq = new int[26]` or `Map<Character,Integer>`.

## Variations
- With prefix sum: "subarray sum equals K" (HashMap of prefix sums).
- Two arrays: "minimum window in S containing all chars of T".
