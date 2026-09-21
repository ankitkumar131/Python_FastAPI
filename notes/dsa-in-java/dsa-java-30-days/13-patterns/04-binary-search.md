# Pattern 4 — Binary Search

## When to use
- Sorted array / "find in O(log n)".
- Monotonic predicate (search space).
- Kth smallest / largest in sorted-by-key data.

## When NOT to use
- Unsorted data you can't sort.
- Linear search on small data is simpler.

## Canonical problems
- Classic search in sorted array
- First/last occurrence
- Search in rotated sorted array
- Find minimum in rotated sorted array
- Kth smallest in sorted matrix
- Median of two sorted arrays
- Search a 2D matrix
- Capacity to ship packages (monotonic)

## Templates

### Classic (find exact)

```java
int lo = 0, hi = a.length - 1;
while (lo <= hi) {
    int mid = lo + (hi - lo) / 2;
    if (a[mid] == target) return mid;
    if (a[mid] < target) lo = mid + 1;
    else hi = mid - 1;
}
return -1;
```

### Lower bound (first ≥ target)

```java
int lo = 0, hi = a.length;  // hi = n (not n-1)
while (lo < hi) {
    int mid = lo + (hi - lo) / 2;
    if (a[mid] < target) lo = mid + 1;
    else hi = mid;
}
return lo;
```

### Upper bound (first > target)

```java
int lo = 0, hi = a.length;
while (lo < hi) {
    int mid = lo + (hi - lo) / 2;
    if (a[mid] <= target) lo = mid + 1;
    else hi = mid;
}
return lo;
```

### Monotonic predicate ("search space")

```java
int lo = MIN_POSSIBLE, hi = MAX_POSSIBLE;
while (lo < hi) {
    int mid = lo + (hi - lo) / 2;
    if (predicate(mid)) hi = mid;       // try smaller
    else lo = mid + 1;
}
return lo;
```

## Complexity
- Time: O(log n).
- Space: O(1).

## Java tips
- **Always** use `lo + (hi - lo) / 2` to avoid overflow.
- Decide between `lo <= hi` (exact) and `lo < hi` (lower/upper bound) up front.
- For "search space" BS, define `predicate(mid)` first.

## Variations
- Binary search on answer (monotonic predicate).
- Binary search + nested O(n) check → O(n log range).
- Ternary search (unimodal function).
