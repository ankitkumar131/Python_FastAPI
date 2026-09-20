# Pattern 1 — Two Pointers

## When to use
- Sorted array, looking for a pair/triple with a property.
- In-place partitioning or filtering.
- Comparing two sequences element-by-element.

## When NOT to use
- Array is unsorted and you cannot sort.
- You need access to all elements at random order.

## Canonical problems
- Two Sum (sorted)
- 3Sum
- Container With Most Water
- Trapping Rain Water
- Remove Duplicates in-place
- Reverse string in-place
- Palindrome check

## Template (sorted pair)

```java
int lo = 0, hi = a.length - 1;
while (lo < hi) {
    int s = a[lo] + a[hi];
    if (s == target) { /* found */ return; }
    if (s < target) lo++;
    else hi--;
}
```

## Template (in-place slow/fast)

```java
int slow = 0;
for (int fast = 0; fast < a.length; fast++) {
    if (keep(a[fast])) a[slow++] = a[fast];
}
```

## Template (reverse)

```java
int lo = 0, hi = a.length - 1;
while (lo < hi) { swap(a, lo++, hi--); }
```

## Template (palindrome)

```java
int lo = 0, hi = s.length() - 1;
while (lo < hi) {
    if (s.charAt(lo) != s.charAt(hi)) return false;
    lo++; hi--;
}
return true;
```

## Complexity
- Time: O(n) (single pass) or O(n log n) (after sort).
- Space: O(1) if in-place.

## Java tips
- Use `while (lo < hi)` (not `<=`) for two-pointer.
- Watch for off-by-one in `hi = a.length - 1` for partition.

## Variations
- Three pointers (3Sum): fix one, two-pointer the rest.
- Dutch National Flag: three pointers (low, mid, high).
- Slow/fast on linked list: cycle detection, mid.
