# Pattern 8 — Greedy

## When to use
- Local optimal choice leads to global optimal.
- Activity/interval scheduling.
- "Minimum coins" (canonical), "minimum jumps", "gas station".

## When NOT to use
- Need exact DP (e.g. 0/1 knapsack, LCS).
- Local optimum does not equal global.

## Canonical problems
- Activity selection (max non-overlapping intervals)
- Jump game I/II
- Gas station
- Container With Most Water (sort + two-pointer)
- Minimum number of coins (canonical)
- Partition labels
- Candy distribution
- Fractional knapsack

## Template

```java
// Sort by some criterion, then sweep.
Arrays.sort(intervals, (a, b) -> Integer.compare(a[1], b[1]));
int count = 0, end = Integer.MIN_VALUE;
for (int[] in : intervals) {
    if (in[0] >= end) { count++; end = in[1]; }
}
```

## Proof of correctness

Always justify greedy by **exchange argument**:
- Suppose optimal solution differs from greedy.
- Show you can swap to match greedy without losing optimality.
- Therefore greedy is optimal.

## Complexity
- Time: usually O(n log n) due to sort.
- Space: O(1) or O(n).

## Java tips
- Sort with custom `Comparator` (lambdas).
- `Arrays.sort(intervals, (a, b) -> Integer.compare(a[1], b[1]))`.
- For "minimum", sort ascending; for "maximum", often descending.

## Variations
- Interval scheduling.
- Two-pointer + sort.
- Heap-based greedy (K-th smallest in sorted matrix).
