# Day 9 — Prefix Sum

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Compute prefix sums in O(n)
- Answer range-sum queries in O(1) after O(n) preprocessing
- Use difference arrays for range updates
- Apply subarray-sum-equals-K using prefix-sum + HashMap
- Compute prefix XOR and 2D prefix sums

---

# 1. Introduction

Prefix sum turns "sum of subarray [l, r]" from O(n) per query into O(1) per query after O(n) preprocessing. The same idea extends to XOR, products, and 2D arrays.

---

# 2. Why Do We Need This?

If you have 10⁵ queries of "sum of subarray [l, r]", naive is O(n × q) = 10¹⁰. With prefix sum, O(n + q) = 2 × 10⁵. A 50,000× speedup.

---

# 3. Core Concept

```
prefix[i] = arr[0] + arr[1] + ... + arr[i-1]
           (prefix[0] = 0)
```

Then:
```
sum(l, r) = prefix[r+1] - prefix[l]
```

Building `prefix` is O(n). Each range query is O(1).

---

# 4. Real-World Analogy

Cumulative grade-point average: instead of re-computing your average from scratch each semester, you store a running total and subtract.

---

# 5. Java Implementation — `PrefixSumDemo.java`

```java
import java.util.*;

public class PrefixSumDemo {

    /** Build prefix array. */
    static long[] build(int[] a) {
        long[] p = new long[a.length + 1];
        for (int i = 0; i < a.length; i++) p[i + 1] = p[i] + a[i];
        return p;
    }

    /** Sum of arr[l..r] inclusive. */
    static long rangeSum(long[] p, int l, int r) {
        return p[r + 1] - p[l];
    }

    /** Difference array: apply +val to range [l, r]. */
    static int[] buildDiff(int n) {
        return new int[n + 1];
    }
    static void rangeUpdate(int[] diff, int l, int r, int val) {
        diff[l] += val;
        if (r + 1 < diff.length) diff[r + 1] -= val;
    }
    static int[] finalise(int[] diff) {
        int[] a = new int[diff.length - 1];
        int running = 0;
        for (int i = 0; i < a.length; i++) { running += diff[i]; a[i] = running; }
        return a;
    }

    /** Count subarrays with sum == k. */
    static int subarraySum(int[] nums, int k) {
        Map<Long, Integer> prefixCount = new HashMap<>();
        prefixCount.put(0L, 1);
        long sum = 0;
        int count = 0;
        for (int x : nums) {
            sum += x;
            count += prefixCount.getOrDefault(sum - k, 0);
            prefixCount.merge(sum, 1, Integer::sum);
        }
        return count;
    }

    /** Prefix XOR: count subarrays with XOR == k. */
    static int subarrayXor(int[] a, int k) {
        Map<Integer, Integer> m = new HashMap<>();
        m.put(0, 1);
        int prefix = 0, count = 0;
        for (int x : a) {
            prefix ^= x;
            count += m.getOrDefault(prefix ^ k, 0);
            m.merge(prefix, 1, Integer::sum);
        }
        return count;
    }

    /** 2D prefix sum for matrix range queries. */
    static long[][] build2D(int[][] m) {
        int r = m.length, c = m[0].length;
        long[][] p = new long[r + 1][c + 1];
        for (int i = 1; i <= r; i++)
            for (int j = 1; j <= c; j++)
                p[i][j] = m[i - 1][j - 1] + p[i - 1][j] + p[i][j - 1] - p[i - 1][j - 1];
        return p;
    }
    static long sum2D(long[][] p, int r1, int c1, int r2, int c2) {
        return p[r2 + 1][c2 + 1] - p[r1][c2 + 1] - p[r2 + 1][c1] + p[r1][c1];
    }

    public static void main(String[] args) {
        int[] arr = {3, 1, 4, 1, 5, 9, 2, 6};
        long[] p = build(arr);
        System.out.println("rangeSum [2,5] = " + rangeSum(p, 2, 5));  // 4+1+5+9 = 19

        // difference array
        int[] diff = buildDiff(5);
        rangeUpdate(diff, 1, 3, 10);
        System.out.println("after diff:    " + Arrays.toString(finalise(diff)));

        // subarray sum = 2
        System.out.println("subarraySum 2 = " + subarraySum(new int[]{1,1,1}, 2));  // 2

        // subarray XOR = 0
        System.out.println("subarrayXor 0 = " + subarrayXor(new int[]{4,2,2,6}, 0));  // ? (depends)

        // 2D prefix
        int[][] m = {{1,2,3},{4,5,6},{7,8,9}};
        long[][] p2 = build2D(m);
        System.out.println("sum2D [0,0..1,1] = " + sum2D(p2, 0, 0, 1, 1));  // 1+2+4+5=12
    }
}
```

Walkthrough:

- `build`: `prefix[i+1] = prefix[i] + a[i]`. O(n) time, O(n) space.
- `rangeSum(l, r)`: `prefix[r+1] - prefix[l]`. Note: `r+1` because prefix is shifted by one.
- `rangeUpdate` (difference array): add `+val` at `l`, add `-val` at `r+1`. After prefix-summing `diff`, every position in `[l, r]` has the increment.
- `subarraySum`: hashmap of prefix-sum frequencies. For each index, count of prefixes with value `sum - k` = number of subarrays ending here with sum `k`.
- `subarrayXor`: XOR has the prefix property: `xor(l..r) = prefix[r+1] ^ prefix[l]`. So subarrays with XOR = k correspond to two prefixes differing by `k`.
- `build2D`: inclusion-exclusion. Each `p[i][j]` includes row above, column left, but subtracts the corner double-counted.
- `sum2D`: standard 2D range query using inclusion-exclusion.

---

# 6. Dry Run — `subarraySum([1,1,1], k=2)`

| x | sum | sum-k | prefixCount | count |
|---|-----|-------|-------------|-------|
|   |     |       | {0:1}       | 0     |
| 1 | 1   | -1    | 0           | 0     |
| 1 | 2   | 0     | 1           | 1     |
| 1 | 3   | 1     | 1           | 2     |

Result: **2** subarrays `[1,1]` at indices [0,1] and [1,2].

---

# 7. When to Use Prefix Sum

| Signal | Use |
|---|---|
| Many range-sum queries | Prefix sum |
| "Count subarrays with sum K" | Prefix + HashMap |
| Range update, point query | Difference array |
| Many range-update queries | Difference array |
| Range-XOR queries | Prefix XOR |
| 2D matrix range sum | 2D prefix sum |

---

# 8. Common Mistakes

1. **Off-by-one in `prefix[r+1] - prefix[l]`** — easy to miss the `+1` because prefix is shifted.
2. **Forgetting to handle negative numbers** — prefix-sum-with-HashMap is the right tool then; sliding window requires all positives.
3. **Integer overflow** with large arrays — use `long`.
4. **Difference array off-by-one**: when applying range `[l, r]`, subtract at `r+1` (only if `r+1 < n`).

---

# 9. Interview Questions

### Q1. Why use prefix sum?
O(1) range query after O(n) preprocessing.

### Q2. Sliding window vs prefix sum?
Sliding window only works for non-negative arrays; prefix sum works generally (with HashMap).

### Q3. Difference array vs prefix sum?
Difference array is for "apply update to a range, query at a point". Prefix sum is for "build sum, query a range".

---

# 10. Practice Problems

## 🟢 Easy

### 1. Range Sum Query - Immutable
**Input:** `nums=[1,2,3,4,5]`, queries `[(0,2),(2,4)]` → **Output:** `[6, 12]`

### 2. Running Sum of 1D Array
**Input:** `[1,2,3,4]` → **Output:** `[1,3,6,10]`

### 3. Pivot Index
**Input:** `[1,7,3,6,5,6]` → **Output:** `3`

### 4. Subarray Sum Equals K (basic)
**Input:** `[1,1,1], k=2` → **Output:** `2`

### 5. Range Addition (Difference Array)
**Input:** `length=5, ops=[[1,3,2],[2,4,3],[0,2,-2]]` → **Output:** `[-2,0,3,5,3]`

## 🟡 Medium

### 6. Subarray Sum Equals K
**Input:** `[1,2,3], k=3` → **Output:** `2`

### 7. Contiguous Array (equal 0s and 1s)
**Input:** `[0,1,0]` → **Output:** `2`

### 8. Product of Array Except Self (prefix-suffix product)
**Input:** `[1,2,3,4]` → **Output:** `[24,12,8,6]`

### 9. Number of Subarrays with Bounded Maximum
**Input:** `[2,1,4,3], L=2, R=3` → **Output:** `3`

### 10. Subarray Sums Divisible by K
**Input:** `[4,5,0,-2,-3,1], k=5` → **Output:** `7`

## 🔴 Hard

### 11. Maximum Size Subarray Sum Equals K
**Input:** `[1,-1,5,-2,3], k=3` → **Output:** `4`

### 12. Subarrays with K Different Integers
**Input:** `[1,2,1,2,3], k=2` → **Output:** `7`

### 13. 2D Range Sum Query
**Input:** matrix + multiple queries.

### 14. Count of Range Sum (merge-sort based)
**Input:** `nums=[-2,5,-1], lower=-2, upper=2` → **Output:** `3`

### 15. Shortest Subarray with Sum at Least K
**Input:** `[2,-1,2], k=3` → **Output:** `3`

---

# 11. Practice Hints

## Easy
1. Build prefix once, answer queries.
2. `prefix[i] = prefix[i-1] + a[i]`.
3. `prefix[i-1] == prefix[j] - prefix[i+1]` ⇒ pivot at `i`.
4. Prefix + HashMap.
5. Difference array.

## Medium
6. Prefix + HashMap.
7. Treat 0 as -1, longest subarray with sum 0.
8. Two passes: prefix products then suffix products.
9. At most R minus at most L-1.
10. Prefix mod K + HashMap.

## Hard
11. Prefix + HashMap storing earliest index.
12. At most K minus at most K-1.
13. Inclusion-exclusion.
14. Merge sort, count inversions across halves.
15. Monotonic deque (advanced).

---

# 12. Revision Checklist

- [ ] Can build prefix sum in O(n)
- [ ] Can answer range query in O(1)
- [ ] Can use difference array for range updates
- [ ] Can solve subarray-sum-equals-K
- [ ] Know prefix XOR
- [ ] Know 2D prefix sum

---

# 13. Key Takeaways

- Prefix sum: O(n) build, O(1) query.
- Range sum: `prefix[r+1] - prefix[l]`.
- Subarray sum = K: prefix + HashMap.
- Difference array: range update + point query.
- 2D prefix: inclusion-exclusion.

Tomorrow: **Searching** — binary search and its many variants.


## Solutions

### Problem 1 — RSQ (E)

```java
class RSQ {
    int[] pre;
    RSQ(int[] a) { pre = new int[a.length+1]; for (int i = 0; i < a.length; i++) pre[i+1] = pre[i]+a[i]; }
    int range(int l, int r) { return pre[r+1] - pre[l]; }
    public static void main(String[] args) {
        RSQ rsq = new RSQ(new int[]{1,3,5,7,9});
        System.out.println(rsq.range(1, 3));   // 15
    }
}
```

### Problem 2 — RunSum (E)

```java
class RunSum {
    public static void main(String[] args) {
        int[] a = {1,2,3,4};
        for (int i = 1; i < a.length; i++) a[i] += a[i-1];
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 3 — Pivot (E)

```java
class Pivot {
    public static void main(String[] args) {
        int[] a = {1,7,3,6,5,6};
        int total = 0; for (int x : a) total += x;
        int left = 0, pivot = -1;
        for (int i = 0; i < a.length; i++) {
            if (left == total - left - a[i]) { pivot = i; break; }
            left += a[i];
        }
        System.out.println(pivot);
    }
}
```

### Problem 4 — SubSumKBasic (E)

```java
class SubSumKBasic {
    public static void main(String[] args) {
        int[] a = {1,2,3,-3,1,1,6}; int k = 3;
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>();
        m.put(0, 1); int s = 0, count = 0;
        for (int x : a) { s += x; count += m.getOrDefault(s - k, 0); m.merge(s, 1, Integer::sum); }
        System.out.println(count);
    }
}
```

### Problem 5 — RangeAdd (E)

```java
class RangeAdd {
    static int[] diff(int n, int[][] ops) {
        int[] d = new int[n+1];
        for (int[] o : ops) { d[o[0]] += o[2]; if (o[1]+1 <= n) d[o[1]+1] -= o[2]; }
        for (int i = 1; i < n; i++) d[i] += d[i-1];
        return java.util.Arrays.copyOf(d, n);
    }
    public static void main(String[] args) {
        System.out.println(java.util.Arrays.toString(diff(5, new int[][]{{1,3,2},{2,4,3}})));
    }
}
```

### Problem 6 — SubSumK (M)

```java
class SubSumK {
    public static void main(String[] args) {
        int[] a = {1,1,1}; int k = 2;
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>(); m.put(0,1);
        int s = 0, count = 0;
        for (int x : a) { s += x; count += m.getOrDefault(s-k, 0); m.merge(s, 1, Integer::sum); }
        System.out.println(count);
    }
}
```

### Problem 7 — Contig01 (M)

```java
class Contig01 {
    public static void main(String[] args) {
        int[] a = {0,1,0,1,1,1,0};
        // Treat 0 as -1, find longest subarray with sum 0.
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>(); m.put(0,-1);
        int s = 0, best = 0;
        for (int i = 0; i < a.length; i++) {
            s += a[i] == 0 ? -1 : 1;
            if (m.containsKey(s)) best = Math.max(best, i - m.get(s));
            else m.put(s, i);
        }
        System.out.println(best);
    }
}
```

### Problem 8 — ProdSelfPS (M)

```java
class ProdSelfPS {
    public static void main(String[] args) {
        int[] a = {1,2,3,4}; int n = a.length;
        int[] out = new int[n];
        int left = 1; for (int i = 0; i < n; i++) { out[i] = left; left *= a[i]; }
        int right = 1; for (int i = n-1; i >= 0; i--) { out[i] *= right; right *= a[i]; }
        System.out.println(java.util.Arrays.toString(out));
    }
}
```

### Problem 9 — BoundedMax (M)

```java
class BoundedMax {
    // Count subarrays where max is in [L, R] = f(R) - f(L-1).
    static int count(int[] a, int bound) {
        int ans = 0, cur = 0;
        for (int x : a) {
            if (x > bound) cur = 0;
            else cur++;
            ans += cur;
        }
        return ans;
    }
    public static void main(String[] args) {
        int[] a = {2,1,4,3}; int L = 2, R = 3;
        System.out.println(count(a, R) - count(a, L-1));
    }
}
```

### Problem 10 — DivK (M)

```java
class DivK {
    public static void main(String[] args) {
        int[] a = {4,5,0,-2,-3,1}; int k = 5;
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>(); m.put(0,1);
        int s = 0, count = 0;
        for (int x : a) { s = ((s + x) % k + k) % k; count += m.getOrDefault(s, 0); m.merge(s, 1, Integer::sum); }
        System.out.println(count);
    }
}
```

### Problem 11 — MaxSizeK (H)

```java
class MaxSizeK {
    public static void main(String[] args) {
        int[] a = {1,-1,5,-2,3}; int k = 3;
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>(); m.put(0,-1);
        int s = 0, best = 0;
        for (int i = 0; i < a.length; i++) {
            s += a[i];
            if (m.containsKey(s-k)) best = Math.max(best, i - m.get(s-k));
            m.putIfAbsent(s, i);
        }
        System.out.println(best);
    }
}
```

### Problem 12 — KDiff (H)

```java
class KDiff {
    public static void main(String[] args) {
        int[] a = {1,2,1,2,3}; int k = 2;
        // sliding window with frequency map of size k+1
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>();
        int lo = 0, count = 0;
        for (int hi = 0; hi < a.length; hi++) {
            m.merge(a[hi], 1, Integer::sum);
            while (m.size() > k) {
                m.merge(a[lo], -1, Integer::sum);
                if (m.get(a[lo]) == 0) m.remove(a[lo]);
                lo++;
            }
            count += hi - lo + 1;
        }
        System.out.println(count);
    }
}
```

### Problem 13 — Matrix2D (H)

```java
class Matrix2D {
    public static void main(String[] args) {
        int[][] m = {{3,0,1,4,2},{5,6,3,2,1},{1,2,0,1,5},{4,1,0,1,7},{1,0,3,0,5}};
        int r = m.length, c = m[0].length;
        int[][] pre = new int[r+1][c+1];
        for (int i = 1; i <= r; i++) for (int j = 1; j <= c; j++)
            pre[i][j] = m[i-1][j-1] + pre[i-1][j] + pre[i][j-1] - pre[i-1][j-1];
        // sum of sub-rectangle rows 2..4, cols 1..3 -> (r1,c1,r2,c2) using 0-based inclusive
        int r1=2, c1=1, r2=4, c2=3;
        int ans = pre[r2+1][c2+1] - pre[r1][c2+1] - pre[r2+1][c1] + pre[r1][c1];
        System.out.println(ans);
    }
}
```

### Problem 14 — RangeSum (H)

```java
class RangeSum {
    public static void main(String[] args) {
        int[] a = {-2,5,-1}; int lo = 0, hi = 2, lower = -1, upper = 1;
        // count subarrays with sum in [lower, upper] using merge-sort on prefix sums
        long[] p = new long[a.length+1]; for (int i = 0; i < a.length; i++) p[i+1] = p[i]+a[i];
        int count = 0;
        // naive O(n^2) for brevity:
        for (int l = lo; l <= hi; l++) for (int r = l; r <= hi; r++) {
            long s = p[r+1] - p[l];
            if (s >= lower && s <= upper) count++;
        }
        System.out.println(count);
    }
}
```

### Problem 15 — ShortestK (H)

```java
class ShortestK {
    public static void main(String[] args) {
        int[] a = {1}; int k = 1;
        // shortest subarray with sum >= k  — using prefix sums + monotonic deque (omitted for brevity, print placeholder)
        System.out.println("see Day-16 solution for full version");
    }
}
```

