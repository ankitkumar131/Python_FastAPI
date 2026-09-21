# Day 11 — Sorting

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Implement bubble, selection, insertion, merge, quick, counting, and radix sort
- Understand stability, in-place, and complexity for each
- Pick the right sort for the situation
- Sort custom objects with `Comparable` / `Comparator`

---

# 1. Introduction

Sorting is everywhere. Even when you don't explicitly sort, you're often relying on it (e.g. binary search, two pointers on sorted arrays). Today you'll learn all the important sorts and when to use each.

---

# 2. Why Do We Need This?

- `Arrays.sort(arr)` exists, but interviewers want you to **implement** sorts.
- Many algorithms become trivial after sorting.
- Understanding sort internals helps you reason about stability and complexity.

---

# 3. Core Concept — Stability

A sort is **stable** if equal elements retain their original relative order.

`[(2, 'a'), (1, 'b'), (2, 'c')]` sorted by first key →
- Stable: `[(1, 'b'), (2, 'a'), (2, 'c')]`
- Unstable: could be `[(1, 'b'), (2, 'c'), (2, 'a')]`

Stable sorts: bubble, insertion, merge, counting, radix.
Unstable: selection, heap, quick.

---

# 4. Real-World Analogy

Sorting a deck of cards by rank: with a stable algorithm, suits appear in the original order. With an unstable one, suits may shuffle within each rank.

---

# 5. Java Implementation — `SortingDemos.java`

```java
import java.util.Arrays;

public class SortingDemos {

    static void bubble(int[] a) {
        int n = a.length;
        for (int i = 0; i < n - 1; i++)
            for (int j = 0; j < n - i - 1; j++)
                if (a[j] > a[j + 1]) { int t = a[j]; a[j] = a[j + 1]; a[j + 1] = t; }
    }

    static void selection(int[] a) {
        int n = a.length;
        for (int i = 0; i < n - 1; i++) {
            int min = i;
            for (int j = i + 1; j < n; j++) if (a[j] < a[min]) min = j;
            int t = a[i]; a[i] = a[min]; a[min] = t;
        }
    }

    static void insertion(int[] a) {
        for (int i = 1; i < a.length; i++) {
            int key = a[i], j = i - 1;
            while (j >= 0 && a[j] > key) { a[j + 1] = a[j]; j--; }
            a[j + 1] = key;
        }
    }

    static void mergeSort(int[] a, int lo, int hi) {
        if (lo >= hi) return;
        int mid = lo + (hi - lo) / 2;
        mergeSort(a, lo, mid);
        mergeSort(a, mid + 1, hi);
        merge(a, lo, mid, hi);
    }
    static void merge(int[] a, int lo, int mid, int hi) {
        int[] left = Arrays.copyOfRange(a, lo, mid + 1);
        int[] right = Arrays.copyOfRange(a, mid + 1, hi + 1);
        int i = 0, j = 0, k = lo;
        while (i < left.length && j < right.length)
            a[k++] = (left[i] <= right[j]) ? left[i++] : right[j++];
        while (i < left.length) a[k++] = left[i++];
        while (j < right.length) a[k++] = right[j++];
    }

    static void quickSort(int[] a, int lo, int hi) {
        if (lo < hi) {
            int p = partition(a, lo, hi);
            quickSort(a, lo, p - 1);
            quickSort(a, p + 1, hi);
        }
    }
    static int partition(int[] a, int lo, int hi) {
        int pivot = a[hi], i = lo - 1;
        for (int j = lo; j < hi; j++)
            if (a[j] <= pivot) { i++; int t = a[i]; a[i] = a[j]; a[j] = t; }
        int t = a[i + 1]; a[i + 1] = a[hi]; a[hi] = t;
        return i + 1;
    }

    static void countingSort(int[] a, int k) {
        int[] count = new int[k + 1];
        for (int x : a) count[x]++;
        for (int i = 1; i <= k; i++) count[i] += count[i - 1];
        int[] out = new int[a.length];
        for (int i = a.length - 1; i >= 0; i--) out[--count[a[i]]] = a[i];
        System.arraycopy(out, 0, a, 0, a.length);
    }

    static void radixSort(int[] a) {
        int max = Arrays.stream(a).max().orElse(0);
        for (int exp = 1; max / exp > 0; exp *= 10) countingByDigit(a, exp);
    }
    static void countingByDigit(int[] a, int exp) {
        int n = a.length, out[] = new int[n], count[] = new int[10];
        for (int x : a) count[(x / exp) % 10]++;
        for (int i = 1; i < 10; i++) count[i] += count[i - 1];
        for (int i = n - 1; i >= 0; i--) { int d = (a[i] / exp) % 10; out[--count[d]] = a[i]; }
        System.arraycopy(out, 0, a, 0, n);
    }

    public static void main(String[] args) {
        int[][] tests = {
            {5, 2, 8, 1, 9, 3, 7, 4, 6},
            {3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5},
            {1}
        };
        for (int[] a : tests) {
            int[] b = a.clone();
            bubble(b);
            System.out.println("bubble       " + Arrays.toString(b));
        }
        int[] s = {5,2,8,1,9,3};
        selection(s.clone());
        System.out.println("selection    " + Arrays.toString(s));

        int[] i = {5,2,8,1,9,3};
        insertion(i.clone());
        System.out.println("insertion    " + Arrays.toString(i));

        int[] m = {5,2,8,1,9,3};
        mergeSort(m, 0, m.length - 1);
        System.out.println("merge        " + Arrays.toString(m));

        int[] q = {5,2,8,1,9,3};
        quickSort(q, 0, q.length - 1);
        System.out.println("quick        " + Arrays.toString(q));

        int[] c = {1,4,1,2,7,5,2};
        countingSort(c, 7);
        System.out.println("counting     " + Arrays.toString(c));

        int[] r = {170,45,75,90,802,24,2,66};
        radixSort(r);
        System.out.println("radix        " + Arrays.toString(r));
    }
}
```

Walkthrough:

- **Bubble**: each pass floats the largest remaining to the end. O(n²).
- **Selection**: each pass selects the minimum of the unsorted part and swaps it to position `i`. O(n²).
- **Insertion**: shift elements right to make room for the key. Fast for nearly-sorted data.
- **Merge sort**: divide and conquer. O(n log n). Stable. Needs O(n) extra space.
- **Quick sort**: partition around a pivot. Average O(n log n), worst O(n²). In-place. Unstable.
- **Counting sort**: O(n + k) when values are in `[0, k]`. Stable.
- **Radix sort**: process digit by digit. O(d·(n + k)). Stable.

---

# 6. Comparison Table

| Sort            | Best        | Average     | Worst       | Space    | Stable |
|-----------------|------------:|------------:|------------:|---------:|:------:|
| Bubble          | O(n)        | O(n²)       | O(n²)       | O(1)     | ✅    |
| Selection       | O(n²)       | O(n²)       | O(n²)       | O(1)     | ❌    |
| Insertion       | O(n)        | O(n²)       | O(n²)       | O(1)     | ✅    |
| Merge           | O(n log n)  | O(n log n)  | O(n log n)  | O(n)     | ✅    |
| Quick           | O(n log n)  | O(n log n)  | O(n²)       | O(log n) | ❌    |
| Heap            | O(n log n)  | O(n log n)  | O(n log n)  | O(1)     | ❌    |
| Counting        | O(n+k)      | O(n+k)      | O(n+k)      | O(k)     | ✅    |
| Radix           | O(n·k)      | O(n·k)      | O(n·k)      | O(n+k)   | ✅    |

---

# 7. Java's `Arrays.sort`

- Primitive arrays: tuned **dual-pivot quicksort** — fast, not stable.
- Object arrays: **TimSort** — stable, O(n log n).

Use `Arrays.sort(arr, comparator)` for custom order.

---

# 8. Common Mistakes

1. **Confusing `Comparator` and `Comparable`**. `Comparable.compareTo` is the natural order on the object. `Comparator` is an external ordering.
2. **Off-by-one in merge sort** boundaries.
3. **Quick sort's worst case** on already-sorted input with naive pivot choice — randomise or use median-of-three.
4. **Counting sort** requires knowing the value range.

---

# 9. Interview Questions

### Q1. What's stable sort, why care?
Equal elements preserve original order. Important when sorting by multiple keys (e.g. sort students by name, then by grade — name sort must be stable).

### Q2. Why is quicksort usually faster than merge sort?
Better cache locality, in-place, low constant factor.

### Q3. When to use counting sort?
When values are integers in a small range.

### Q4. Why is Java's `Arrays.sort` different for primitives vs objects?
Primitives: speed (unstable dual-pivot quick). Objects: stability needed (TimSort).

---

# 10. Practice Problems

## 🟢 Easy

### 1. Sort an Array (insertion or selection)
**Input:** `[5,2,3,1]` → **Output:** `[1,2,3,5]`

### 2. Sort by Absolute Value
**Input:** `[1,-3,2,-5,4]` → **Output:** `[1,2,-3,4,-5]`

### 3. Sort Squares
**Input:** `[-4,-1,0,3,10]` → **Output:** `[0,1,9,16,100]`

### 4. Sort People by Height
**Input:** `[["Alice",165],["Bob",180],["Eve",170]]` → sorted by height.

### 5. Bubble Sort Trace
**Input:** `[5,1,4,2,8]` → trace each pass.

## 🟡 Medium

### 6. Merge Intervals
**Input:** `[[1,3],[2,6],[8,10],[15,18]]` → **Output:** `[[1,6],[8,10],[15,18]]`

### 7. Sort Colors (counting)
**Input:** `[2,0,2,1,1,0]` → **Output:** `[0,0,1,1,2,2]`

### 8. Sort Array by Parity
**Input:** `[3,1,2,4]` → **Output:** `[2,4,3,1]` or `[4,2,1,3]`

### 9. Top K Frequent Elements
**Input:** `[1,1,1,2,2,3], k=2` → **Output:** `[1,2]`

### 10. Kth Largest (quickselect)
**Input:** `[3,2,1,5,6,4], k=2` → **Output:** `5`

## 🔴 Hard

### 11. Sort an Array (merge, full)
**Input:** `[5,2,3,1]` → **Output:** `[1,2,3,5]`

### 12. Count Inversions (merge-sort based)
**Input:** `[2,4,1,3,5]` → **Output:** `3`

### 13. Largest Number
**Input:** `[3,30,34,5,9]` → **Output:** `"9534330"`

### 14. Sort List (linked-list merge sort)
**Input:** `4->2->1->3` → **Output:** `1->2->3->4`

### 15. Wiggle Sort II
**Input:** `[1,5,1,1,6,4]` → **Output:** `[1,6,1,5,1,4]`

---

# 11. Practice Hints

## Easy
1. Selection/insertion.
2. Sort by `(a, Math.abs(a))`.
3. Two-pointer (Day 7).
4. Comparator on int field.
5. Bubble.

## Medium
6. Sort by start, then merge.
7. Count 0s, 1s, 2s.
8. Two-pointer partition.
9. HashMap + bucket or heap.
10. Quickselect.

## Hard
11. Merge sort top-down.
12. Modify merge to count.
13. Custom comparator `b+a` vs `a+b`.
14. Find middle, merge two halves.
15. Find median, three-way partition.

---

# 12. Revision Checklist

- [ ] Can implement bubble/selection/insertion
- [ ] Can implement merge sort
- [ ] Can implement quick sort
- [ ] Know stability & complexity of each
- [ ] Can sort custom objects

---

# 13. Key Takeaways

- O(n log n) sorts: merge, quick, heap.
- Stable sorts: bubble, insertion, merge, counting, radix.
- Counting sort: integer range, O(n+k).
- Java sorts: dual-pivot quick for primitives, TimSort for objects.

Tomorrow: **Recursion**.


## Solutions

### Problem 1 — InsertionSort (E)

```java
class InsertionSort {
    static void sort(int[] a) {
        for (int i = 1; i < a.length; i++) {
            int k = a[i], j = i - 1;
            while (j >= 0 && a[j] > k) { a[j+1] = a[j]; j--; }
            a[j+1] = k;
        }
    }
    public static void main(String[] args) {
        int[] a = {5,2,8,1,3}; sort(a);
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 2 — AbsSort (E)

```java
class AbsSort {
    public static void main(String[] args) {
        Integer[] a = {5,-3,2,-8,1};
        java.util.Arrays.sort(a, (x,y) -> Integer.compare(Math.abs(x), Math.abs(y)));
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 3 — SqSort (E)

```java
class SqSort {
    public static void main(String[] args) {
        int[] a = {-4,-1,0,3,10}; int n = a.length;
        int[] out = new int[n]; int l = 0, r = n - 1, k = n - 1;
        while (l <= r) {
            int ls = a[l]*a[l], rs = a[r]*a[r];
            if (ls > rs) { out[k--] = ls; l++; } else { out[k--] = rs; r--; }
        }
        System.out.println(java.util.Arrays.toString(out));
    }
}
```

### Problem 4 — HeightSort (E)

```java
class HeightSort {
    public static void main(String[] args) {
        String[] names = {"Alice","Bob","Charlie"};
        int[] h = {155,180,170};
        Integer[] idx = {0,1,2};
        java.util.Arrays.sort(idx, (i,j) -> Integer.compare(h[i], h[j]));
        for (int i : idx) System.out.println(names[i] + " " + h[i]);
    }
}
```

### Problem 5 — Bubble (E)

```java
class Bubble {
    static void sort(int[] a) {
        int n = a.length;
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n - i - 1; j++)
                if (a[j] > a[j+1]) { int t = a[j]; a[j] = a[j+1]; a[j+1] = t; }
    }
    public static void main(String[] args) {
        int[] a = {5,2,8,1,3}; sort(a);
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 6 — MergeIntervals (M)

```java
class MergeIntervals {
    public static void main(String[] args) {
        int[][] iv = {{1,3},{2,6},{8,10},{15,18}};
        java.util.Arrays.sort(iv, (a,b) -> Integer.compare(a[0], b[0]));
        java.util.List<int[]> out = new java.util.ArrayList<>();
        int[] cur = iv[0]; out.add(cur);
        for (int[] x : iv) {
            if (x[0] <= cur[1]) cur[1] = Math.max(cur[1], x[1]);
            else { cur = x; out.add(cur); }
        }
        System.out.println(out);
    }
}
```

### Problem 7 — SortColorsCount (M)

```java
class SortColorsCount {
    public static void main(String[] args) {
        int[] a = {2,0,2,1,1,0};
        int c0 = 0, c1 = 0, c2 = 0;
        for (int x : a) if (x==0) c0++; else if (x==1) c1++; else c2++;
        int i = 0;
        while (c0-- > 0) a[i++] = 0;
        while (c1-- > 0) a[i++] = 1;
        while (c2-- > 0) a[i++] = 2;
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 8 — ParitySort (M)

```java
class ParitySort {
    public static void main(String[] args) {
        int[] a = {3,1,2,4};
        int j = 0;
        for (int i = 0; i < a.length; i++) if (a[i] % 2 == 0) { int t = a[i]; a[i] = a[j]; a[j++] = t; }
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 9 — TopK (M)

```java
class TopK {
    public static void main(String[] args) {
        int[] a = {1,1,1,2,2,3}; int k = 2;
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>();
        for (int x : a) m.merge(x, 1, Integer::sum);
        java.util.PriorityQueue<int[]> pq = new java.util.PriorityQueue<>((x,y) -> x[0]-y[0]);
        for (var e : m.entrySet()) {
            pq.offer(new int[]{e.getValue(), e.getKey()});
            if (pq.size() > k) pq.poll();
        }
        java.util.List<Integer> out = new java.util.ArrayList<>();
        while (!pq.isEmpty()) out.add(pq.poll()[1]);
        System.out.println(out);
    }
}
```

### Problem 10 — KthLargest (M)

```java
class KthLargest {
    static int qs(int[] a, int k) {
        // partial sort: sort and pick — O(n log n). Replace with quickselect for O(n) avg.
        java.util.Arrays.sort(a);
        return a[a.length - k];
    }
    public static void main(String[] args) { System.out.println(qs(new int[]{3,2,1,5,6,4}, 2)); }
}
```

### Problem 11 — MergeSort (H)

```java
class MergeSort {
    static void sort(int[] a) {
        if (a.length < 2) return;
        int m = a.length / 2;
        int[] l = java.util.Arrays.copyOfRange(a, 0, m);
        int[] r = java.util.Arrays.copyOfRange(a, m, a.length);
        sort(l); sort(r);
        int i=0,j=0,k=0;
        while (i<l.length && j<r.length) a[k++] = l[i]<=r[j] ? l[i++] : r[j++];
        while (i<l.length) a[k++] = l[i++];
        while (j<r.length) a[k++] = r[j++];
    }
    public static void main(String[] args) {
        int[] a = {5,2,8,1,3}; sort(a);
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 12 — Inv (H)

```java
class Inv {
    static long sort(int[] a, int l, int r) {
        if (r - l <= 1) return 0;
        int m = (l + r) / 2;
        long inv = sort(a, l, m) + sort(a, m, r);
        int[] merged = new int[r - l]; int i = l, j = m, k = 0;
        while (i < m && j < r) {
            if (a[i] <= a[j]) merged[k++] = a[i++];
            else { merged[k++] = a[j++]; inv += m - i; }
        }
        while (i < m) merged[k++] = a[i++];
        while (j < r) merged[k++] = a[j++];
        System.arraycopy(merged, 0, a, l, r - l);
        return inv;
    }
    public static void main(String[] args) { System.out.println(sort(new int[]{2,4,1,3,5}, 0, 5)); }
}
```

### Problem 13 — LargestNum (H)

```java
class LargestNum {
    public static void main(String[] args) {
        int[] a = {10,2};
        String[] s = new String[a.length];
        for (int i = 0; i < a.length; i++) s[i] = String.valueOf(a[i]);
        java.util.Arrays.sort(s, (x,y) -> (y+x).compareTo(x+y));
        StringBuilder sb = new StringBuilder();
        for (String t : s) sb.append(t);
        System.out.println(sb);
    }
}
```

### Problem 14 — SortList (H)

```java
class SortList {
    static class Node { int v; Node n; Node(int v) { this.v = v; } }
    static Node sort(Node h) {
        if (h == null || h.n == null) return h;
        Node slow = h, fast = h.n;
        while (fast != null && fast.n != null) { slow = slow.n; fast = fast.n.n; }
        Node mid = slow.n; slow.n = null;
        return merge(sort(h), sort(mid));
    }
    static Node merge(Node a, Node b) {
        Node d = new Node(0), t = d;
        while (a != null && b != null) { if (a.v <= b.v) { t.n = a; a = a.n; } else { t.n = b; b = b.n; } t = t.n; }
        t.n = a == null ? b : a; return d.n;
    }
    public static void main(String[] args) {
        Node h = new Node(4); h.n = new Node(2); h.n.n = new Node(1); h.n.n.n = new Node(3);
        for (Node c = sort(h); c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 15 — Wiggle (H)

```java
class Wiggle {
    public static void main(String[] args) {
        int[] a = {1,5,1,1,6,4};
        java.util.Arrays.sort(a); // simple O(n log n) wiggle II via virtual index
        int n = a.length; int[] out = new int[n];
        int i = 0, j = n - 1, k = 0;
        for (; i < j; i++, j--) { out[k++] = a[i]; out[k++] = a[j]; }
        if (i == j) out[k] = a[i];
        System.out.println(java.util.Arrays.toString(out));
    }
}
```

