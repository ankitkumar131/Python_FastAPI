# Day 10 — Searching

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Implement linear and binary search
- Find first/last occurrence and lower/upper bound
- Apply binary search on the answer
- Search in rotated sorted arrays
- Find the peak element
- Recognise and avoid common off-by-one errors

---

# 1. Introduction

Searching is the act of finding a target in a collection. Two flavours:

- **Linear search**: O(n), works on any array.
- **Binary search**: O(log n), requires a sorted array or monotonic condition.

Binary search is one of the most-failed interview topics because of off-by-one errors. Today you'll master it.

---

# 2. Why Do We Need This?

Without binary search, finding an element in a 10⁹-sorted array takes 10⁹ steps. With it, ~ 30 steps. The pattern also generalises: "binary search on the answer" solves countless optimisation problems.

---

# 3. Core Concept

### Linear Search

```java
for (int i = 0; i < arr.length; i++)
    if (arr[i] == target) return i;
return -1;
```

### Binary Search

Maintain `[lo, hi]`. Each iteration, look at `mid`. If `arr[mid] < target`, search right; if greater, search left.

```
lo = 0, hi = n - 1
while (lo <= hi):
    mid = lo + (hi - lo) / 2
    if arr[mid] == target: return mid
    if arr[mid] < target: lo = mid + 1
    else: hi = mid - 1
```

The `mid` formula avoids overflow when `lo + hi` would exceed `Integer.MAX_VALUE`.

---

# 4. Real-World Analogy

Looking up a word in a dictionary: you don't read it cover to cover; you open near where the word would be, then adjust.

---

# 5. Java Implementation — `BinarySearchDemo.java`

```java
public class BinarySearchDemo {

    /** Standard binary search. Returns index or -1. */
    static int search(int[] a, int target) {
        int lo = 0, hi = a.length - 1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (a[mid] == target) return mid;
            else if (a[mid] < target) lo = mid + 1;
            else hi = mid - 1;
        }
        return -1;
    }

    /** First occurrence. */
    static int firstOccurrence(int[] a, int target) {
        int lo = 0, hi = a.length - 1, ans = -1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (a[mid] == target) { ans = mid; hi = mid - 1; }
            else if (a[mid] < target) lo = mid + 1;
            else hi = mid - 1;
        }
        return ans;
    }

    /** Last occurrence. */
    static int lastOccurrence(int[] a, int target) {
        int lo = 0, hi = a.length - 1, ans = -1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (a[mid] == target) { ans = mid; lo = mid + 1; }
            else if (a[mid] < target) lo = mid + 1;
            else hi = mid - 1;
        }
        return ans;
    }

    /** Lower bound: first index where a[i] >= target. */
    static int lowerBound(int[] a, int target) {
        int lo = 0, hi = a.length - 1, ans = a.length;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (a[mid] >= target) { ans = mid; hi = mid - 1; }
            else lo = mid + 1;
        }
        return ans;
    }

    /** Upper bound: first index where a[i] > target. */
    static int upperBound(int[] a, int target) {
        int lo = 0, hi = a.length - 1, ans = a.length;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (a[mid] > target) { ans = mid; hi = mid - 1; }
            else lo = mid + 1;
        }
        return ans;
    }

    /** Search insert position (LeetCode 35). */
    static int searchInsert(int[] a, int target) {
        return lowerBound(a, target);
    }

    /** Peak element: any i with a[i] > a[i-1] and a[i] > a[i+1]. */
    static int peakElement(int[] a) {
        int lo = 0, hi = a.length - 1;
        while (lo < hi) {
            int mid = lo + (hi - lo) / 2;
            if (a[mid] < a[mid + 1]) lo = mid + 1;
            else hi = mid;
        }
        return lo;
    }

    /** Search in rotated sorted array (distinct). */
    static int searchRotated(int[] a, int target) {
        int lo = 0, hi = a.length - 1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (a[mid] == target) return mid;
            if (a[lo] <= a[mid]) {  // left half sorted
                if (target >= a[lo] && target < a[mid]) hi = mid - 1;
                else lo = mid + 1;
            } else {                  // right half sorted
                if (target > a[mid] && target <= a[hi]) lo = mid + 1;
                else hi = mid - 1;
            }
        }
        return -1;
    }

    /** Binary search on answer: minimum in arr[] such that condition(x) is true. */
    static int minSpeedToFinish(int[] piles, int h) {
        int lo = 1, hi = 0;
        for (int p : piles) hi = Math.max(hi, p);
        while (lo < hi) {
            int mid = lo + (hi - lo) / 2;
            long hours = 0;
            for (int p : piles) hours += (p + mid - 1) / mid;
            if (hours <= h) hi = mid; else lo = mid + 1;
        }
        return lo;
    }

    public static void main(String[] args) {
        int[] a = {1, 2, 2, 2, 3, 4, 5};
        System.out.println("search(2)         = " + search(a, 2));
        System.out.println("firstOccurrence(2)= " + firstOccurrence(a, 2));
        System.out.println("lastOccurrence(2) = " + lastOccurrence(a, 2));
        System.out.println("lowerBound(2)     = " + lowerBound(a, 2));
        System.out.println("upperBound(2)     = " + upperBound(a, 2));
        System.out.println("searchInsert(2.5) = " + searchInsert(a, 3));

        int[] peak = {1, 3, 5, 4, 2};
        System.out.println("peakIndex         = " + peakElement(peak));

        int[] rot = {4, 5, 6, 7, 0, 1, 2};
        System.out.println("searchRotated(0)  = " + searchRotated(rot, 0));

        System.out.println("minEatingSpeed    = " + minSpeedToFinish(new int[]{3,6,7,11}, 8));
    }
}
```

Walkthrough:

- `lo + (hi - lo) / 2` — equivalent to `(lo + hi) / 2` but avoids overflow when `lo + hi > Integer.MAX_VALUE`.
- `firstOccurrence`: when found, record `ans = mid` and keep searching left (`hi = mid - 1`).
- `lastOccurrence`: when found, record `ans = mid` and keep searching right (`lo = mid + 1`).
- `lowerBound`: smallest index with `a[i] ≥ target`. `upperBound`: smallest index with `a[i] > target`. Note `ans` defaults to `a.length` (sentinel "no such element").
- `peakElement`: compare with right neighbour. If smaller, peak is to the right; otherwise (including equal), peak is at mid or left.
- `searchRotated`: at every step, one half is sorted (compare `a[lo]` with `a[mid]`). Decide which side contains `target`.
- `minSpeedToFinish`: binary search on the answer (eating speed). For each candidate speed, compute hours; if ≤ H, try slower; else faster.

---

# 6. Dry Run — `searchRotated([4,5,6,7,0,1,2], target=0)`

| lo | hi | mid | a[mid] | a[lo]<=a[mid]? | Decision |
|----|----|-----|--------|----------------|----------|
| 0  | 6  | 3   | 7      | yes            | target(0) < a[lo]=4? yes → lo = mid+1 = 4 |
| 4  | 6  | 5   | 1      | a[4]=0 ≤ a[5]=1 yes | target(0) > a[mid]=1? no, target ≤ a[hi]? no → hi = mid-1 = 4 |
| 4  | 4  | 4   | 0      | match          | return 4 ✓ |

---

# 7. The "Binary Search on Answer" Pattern

When you can ask "is X feasible?" monotonically, binary search the answer space.

Examples:
- Minimum speed to eat all bananas in H hours.
- Minimum capacity to ship packages in D days.
- Smallest divisor such that sum of divisions ≤ threshold.

Pattern:

```
lo = minimum possible answer
hi = maximum possible answer
while (lo < hi):
    mid = (lo + hi) / 2
    if feasible(mid): hi = mid
    else: lo = mid + 1
return lo
```

---

# 8. Common Mistakes

1. **`while (lo < hi)` vs `while (lo <= hi)`** — different invariants; mixing causes infinite loop or missing the answer.
2. **Updating `lo` or `hi` to `mid` (not `mid ± 1`)** — infinite loop when `lo == hi`.
3. **Off-by-one in `mid = (lo + hi) / 2`** — overflow risk; use `lo + (hi - lo) / 2`.
4. **Wrong sorted-half in rotated array**.
5. **Using binary search on an unsorted array** — won't work; sort first (O(n log n)) if you must, or use linear search.

---

# 9. Interview Questions

### Q1. Why `lo + (hi - lo) / 2`?
Avoids overflow when `lo + hi > Integer.MAX_VALUE`.

### Q2. Lower bound vs upper bound?
Lower: first ≥ target. Upper: first > target. Difference = count of target.

### Q3. What is "binary search on answer"?
When the answer is monotonic in some parameter — binary search the parameter.

### Q4. How to handle duplicates in search?
Pick the side that's definitely sorted; be careful with boundaries.

---

# 10. Practice Problems

## 🟢 Easy

### 1. Binary Search
**Input:** `[1,3,5,7,9], t=5` → **Output:** `2`

### 2. Search Insert Position
**Input:** `[1,3,5,6], t=2` → **Output:** `1`

### 3. First Bad Version
**Input:** `n=5, bad=4` → **Output:** `4`

### 4. Valid Perfect Square
**Input:** `16` → **Output:** `true`

### 5. Find Smallest Letter Greater Than Target
**Input:** `letters=['c','f','j'], t='a'` → **Output:** `'c'`

## 🟡 Medium

### 6. First and Last Position
**Input:** `[5,7,7,8,8,10], t=8` → **Output:** `[3,4]`

### 7. Search in Rotated Sorted Array
**Input:** `[4,5,6,7,0,1,2], t=0` → **Output:** `4`

### 8. Find Minimum in Rotated Sorted Array
**Input:** `[3,4,5,1,2]` → **Output:** `1`

### 9. Find Peak Element
**Input:** `[1,2,3,1]` → **Output:** `2`

### 10. Single Element in Sorted Array
**Input:** `[1,1,2,3,3,4,4,8,8]` → **Output:** `2`

## 🔴 Hard

### 11. Search in Rotated Sorted Array II (with duplicates)
**Input:** `[2,5,6,0,0,1,2], t=0` → **Output:** `true`

### 12. Find Median of Two Sorted Arrays
**Input:** `[1,3], [2]` → **Output:** `2.0`

### 13. Minimum Speed to Arrive on Time
**Input:** `dist=[1,3,4], hour=6` → **Output:** `1`

### 14. Aggressive Cows
**Input:** `stalls=[1,2,4,8,9], cows=3` → **Output:** `3`

### 15. Split Array Largest Sum
**Input:** `nums=[7,2,5,10,8], m=2` → **Output:** `18`

---

# 11. Practice Hints

## Easy
1. Standard template.
2. Lower bound.
3. Find first bad — leftmost bad.
4. Binary search on integer sqrt.
5. Upper bound on char array.

## Medium
6. First + last occurrence.
7. Rotated template.
8. Rotated: compare with `a[hi]`.
9. Compare with right neighbour.
10. Pairs differ at single element.

## Hard
11. Shrink duplicates.
12. Binary search on partition.
13. Feasibility = sum of ceil(dist/speed).
14. Place cows greedily, binary search min distance.
15. Feasibility = greedy assignment to ≤ m buckets.

---

# 12. Revision Checklist

- [ ] Can write binary search without off-by-one
- [ ] Know first/last/lower/upper bound
- [ ] Can handle rotated arrays
- [ ] Can do "binary search on answer"
- [ ] Know `lo + (hi - lo) / 2` overflow trick

---

# 13. Key Takeaways

- `lo + (hi - lo) / 2` avoids overflow.
- Lower bound = first ≥ target. Upper bound = first > target.
- Rotated: one half is always sorted — decide which.
- "Binary search on answer" works for any monotonic feasibility check.

Tomorrow: **Sorting** — bubble to merge to quick to counting.


## Solutions

### Problem 1 — BS (E)

```java
class BS {
    static int search(int[] a, int t) {
        int l = 0, r = a.length - 1;
        while (l <= r) {
            int m = l + (r - l) / 2;
            if (a[m] == t) return m;
            if (a[m] < t) l = m + 1; else r = m - 1;
        }
        return -1;
    }
    public static void main(String[] args) { System.out.println(search(new int[]{1,3,5,7,9}, 5)); }
}
```

### Problem 2 — Insert (E)

```java
class Insert {
    static int pos(int[] a, int t) {
        int l = 0, r = a.length;  // hi = n for insertion
        while (l < r) {
            int m = l + (r - l) / 2;
            if (a[m] < t) l = m + 1; else r = m;
        }
        return l;
    }
    public static void main(String[] args) { System.out.println(pos(new int[]{1,3,5,6}, 2)); }
}
```

### Problem 3 — FirstBad (E)

```java
class FirstBad {
    static int firstBad(int n) {
        int l = 1, r = n, ans = n;
        while (l <= r) {
            int m = l + (r - l) / 2;
            // pretend isBad(m)
            if (m >= 4) { ans = m; r = m - 1; } else l = m + 1;
        }
        return ans;
    }
    public static void main(String[] args) { System.out.println(firstBad(10)); }
}
```

### Problem 4 — PerfectSq (E)

```java
class PerfectSq {
    static boolean isSquare(int n) {
        long l = 1, r = n;
        while (l <= r) {
            long m = l + (r - l) / 2, sq = m * m;
            if (sq == n) return true;
            if (sq < n) l = m + 1; else r = m - 1;
        }
        return false;
    }
    public static void main(String[] args) { System.out.println(isSquare(16)); }
}
```

### Problem 5 — NextLetter (E)

```java
class NextLetter {
    static char next(char[] a, char t) {
        int l = 0, r = a.length; // wrap-around; return a[0] if past last
        while (l < r) {
            int m = l + (r - l) / 2;
            if (a[m] <= t) l = m + 1; else r = m;
        }
        return a[l % a.length];
    }
    public static void main(String[] args) { System.out.println(next(new char[]{'c','f','j'}, 'g')); }
}
```

### Problem 6 — FirstLast (M)

```java
class FirstLast {
    static int[] fl(int[] a, int t) {
        int[] res = {-1, -1};
        int l = 0, r = a.length - 1;
        while (l <= r) {
            int m = l + (r - l) / 2;
            if (a[m] >= t) r = m - 1;
            else l = m + 1;
            if (a[m] == t) res[0] = m;
        }
        l = 0; r = a.length - 1;
        while (l <= r) {
            int m = l + (r - l) / 2;
            if (a[m] <= t) l = m + 1;
            else r = m - 1;
            if (a[m] == t) res[1] = m;
        }
        return res;
    }
    public static void main(String[] args) { System.out.println(java.util.Arrays.toString(fl(new int[]{5,7,7,8,8,10}, 8))); }
}
```

### Problem 7 — Rotated (M)

```java
class Rotated {
    static int search(int[] a, int t) {
        int l = 0, r = a.length - 1;
        while (l <= r) {
            int m = l + (r - l) / 2;
            if (a[m] == t) return m;
            if (a[l] <= a[m]) {
                if (a[l] <= t && t < a[m]) r = m - 1; else l = m + 1;
            } else {
                if (a[m] < t && t <= a[r]) l = m + 1; else r = m - 1;
            }
        }
        return -1;
    }
    public static void main(String[] args) { System.out.println(search(new int[]{4,5,6,7,0,1,2}, 0)); }
}
```

### Problem 8 — MinRot (M)

```java
class MinRot {
    static int min(int[] a) {
        int l = 0, r = a.length - 1;
        while (l < r) {
            int m = l + (r - l) / 2;
            if (a[m] > a[r]) l = m + 1; else r = m;
        }
        return a[l];
    }
    public static void main(String[] args) { System.out.println(min(new int[]{3,4,5,1,2})); }
}
```

### Problem 9 — Peak (M)

```java
class Peak {
    static int peak(int[] a) {
        int l = 0, r = a.length - 1;
        while (l < r) {
            int m = l + (r - l) / 2;
            if (a[m] > a[m+1]) r = m; else l = m + 1;
        }
        return l;
    }
    public static void main(String[] args) { System.out.println(peak(new int[]{1,2,3,1})); }
}
```

### Problem 10 — Single (M)

```java
class Single {
    static int single(int[] a) {
        int l = 0, r = a.length - 1;
        while (l < r) {
            int m = l + (r - l) / 2;
            if (m % 2 == 1) m--; // make m even
            if (a[m] == a[m+1]) l = m + 2; else r = m;
        }
        return a[l];
    }
    public static void main(String[] args) { System.out.println(single(new int[]{1,1,2,3,3,4,4,8,8})); }
}
```

### Problem 11 — RotatedDup (H)

```java
class RotatedDup {
    static boolean search(int[] a, int t) {
        int l = 0, r = a.length - 1;
        while (l <= r) {
            int m = l + (r - l) / 2;
            if (a[m] == t) return true;
            if (a[l] == a[m] && a[m] == a[r]) { l++; r--; }
            else if (a[l] <= a[m]) {
                if (a[l] <= t && t < a[m]) r = m - 1; else l = m + 1;
            } else {
                if (a[m] < t && t <= a[r]) l = m + 1; else r = m - 1;
            }
        }
        return false;
    }
    public static void main(String[] args) { System.out.println(search(new int[]{2,5,6,0,0,1,2}, 0)); }
}
```

### Problem 12 — Median2 (H)

```java
class Median2 {
    static double median(int[] a, int[] b) {
        int[] merged = new int[a.length + b.length];
        int i = 0, j = 0, k = 0;
        while (i < a.length && j < b.length) merged[k++] = a[i] <= b[j] ? a[i++] : b[j++];
        while (i < a.length) merged[k++] = a[i++];
        while (j < b.length) merged[k++] = b[j++];
        int m = merged.length;
        return (merged[(m-1)/2] + merged[m/2]) / 2.0;
    }
    public static void main(String[] args) { System.out.println(median(new int[]{1,3}, new int[]{2})); }
}
```

### Problem 13 — MinSpeed (H)

```java
class MinSpeed {
    static int minSpeed(int[] d, int h) {
        int l = 1, r = 1_000_000_00, ans = -1;
        while (l <= r) {
            int m = l + (r - l) / 2;
            long t = 0;
            for (int i = 0; i < d.length - 1; i++) t += ((d[i] + m - 1) / m);
            t += d[d.length - 1]; // last leg no rounding
            if (t <= h) { ans = m; r = m - 1; } else l = m + 1;
        }
        return ans;
    }
    public static void main(String[] args) { System.out.println(minSpeed(new int[]{1,3,6,9,12}, 50)); }
}
```

### Problem 14 — AggCows (H)

```java
class AggCows {
    static int largestMin(int[] pos, int cows) {
        java.util.Arrays.sort(pos);
        int l = 1, r = pos[pos.length-1] - pos[0], ans = 0;
        while (l <= r) {
            int m = l + (r - l) / 2, last = pos[0], placed = 1;
            for (int i = 1; i < pos.length; i++) if (pos[i] - last >= m) { placed++; last = pos[i]; }
            if (placed >= cows) { ans = m; l = m + 1; } else r = m - 1;
        }
        return ans;
    }
    public static void main(String[] args) { System.out.println(largestMin(new int[]{1,2,8,4,9}, 3)); }
}
```

### Problem 15 — SplitLargest (H)

```java
class SplitLargest {
    static int split(int[] a, int m) {
        long lo = 0, hi = 0;
        for (int x : a) { lo = Math.max(lo, x); hi += x; }
        while (lo < hi) {
            long mid = lo + (hi - lo) / 2;
            int parts = 1, cur = 0;
            for (int x : a) { if (cur + x > mid) { parts++; cur = 0; } cur += x; }
            if (parts <= m) hi = mid; else lo = mid + 1;
        }
        return (int) lo;
    }
    public static void main(String[] args) { System.out.println(split(new int[]{7,2,5,10,8}, 2)); }
}
```

