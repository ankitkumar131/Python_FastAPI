# Day 20 — Heap & Priority Queue

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Define min-heap and max-heap
- Explain heap as a complete binary tree stored in an array
- Implement heapify, insert, extract-min/max, peek
- Use Java's `PriorityQueue`
- Solve top-K, Kth largest, merge K sorted, median-from-stream

---

# 1. Introduction

A heap is a complete binary tree with the heap property: each parent is smaller (min-heap) or larger (max-heap) than its children.

In Java, `PriorityQueue` is a min-heap by default.

---

# 2. Why Do We Need This?

- O(log n) insert and extract.
- O(1) peek.
- Ideal for "always serve the smallest/largest next" — scheduling, Dijkstra, top-K.

---

# 3. Core Concept

### As an array (1-indexed)

```
         1                arr: [_, 1, 3, 5, 7, 9, 8]
       /   \               index: 1  2  3  4  5  6
      3     5
     / \   / \
    7   9 8
```

- `parent(i) = i / 2`
- `left(i)  = 2 * i`
- `right(i) = 2 * i + 1`

---

# 4. Real-World Analogy

An ER triage queue: the most critical patient (highest priority) is always treated first, regardless of arrival order.

---

# 5. Java Implementation — `HeapDemo.java`

```java
import java.util.*;

public class HeapDemo {

    /** Min-heap with array storage. */
    static class MinHeap {
        int[] a = new int[8];
        int size = 0;
        void offer(int x) {
            if (size == a.length) a = Arrays.copyOf(a, a.length * 2);
            a[++size] = x;
            siftUp(size);
        }
        int poll() {
            if (size == 0) throw new RuntimeException("empty");
            int v = a[1];
            a[1] = a[size--];
            siftDown(1);
            return v;
        }
        int peek() { return a[1]; }
        void siftUp(int i) {
            while (i > 1 && a[i] < a[i / 2]) { swap(i, i / 2); i /= 2; }
        }
        void siftDown(int i) {
            while (2 * i <= size) {
                int c = 2 * i;
                if (c + 1 <= size && a[c + 1] < a[c]) c++;
                if (a[i] <= a[c]) break;
                swap(i, c); i = c;
            }
        }
        void swap(int i, int j) { int t = a[i]; a[i] = a[j]; a[j] = t; }
    }

    /** Top-K frequent using min-heap of size K. */
    static int[] topKFrequent(int[] a, int k) {
        Map<Integer, Integer> m = new HashMap<>();
        for (int x : a) m.merge(x, 1, Integer::sum);
        PriorityQueue<Map.Entry<Integer, Integer>> min =
            new PriorityQueue<>(Comparator.comparingInt(Map.Entry::getValue));
        for (var e : m.entrySet()) {
            min.offer(e);
            if (min.size() > k) min.poll();
        }
        int[] out = new int[k];
        for (int i = 0; i < k; i++) out[i] = min.poll().getKey();
        return out;
    }

    /** Kth largest with min-heap of size K. */
    static int kthLargest(int[] a, int k) {
        PriorityQueue<Integer> min = new PriorityQueue<>();
        for (int x : a) { min.offer(x); if (min.size() > k) min.poll(); }
        return min.peek();
    }

    /** Median from data stream using two heaps. */
    static class MedianFinder {
        PriorityQueue<Integer> low = new PriorityQueue<>(Comparator.reverseOrder());
        PriorityQueue<Integer> high = new PriorityQueue<>();
        void addNum(int n) {
            low.offer(n);
            high.offer(low.poll());
            if (low.size() < high.size()) low.offer(high.poll());
        }
        double findMedian() {
            return low.size() > high.size() ? low.peek() : (low.peek() + high.peek()) / 2.0;
        }
    }

    public static void main(String[] args) {
        MinHeap h = new MinHeap();
        for (int v : new int[]{5, 3, 8, 1, 9, 2}) h.offer(v);
        System.out.print("poll order: ");
        while (h.size > 0) System.out.print(h.poll() + " ");
        System.out.println();

        System.out.println("topKFrequent = " + Arrays.toString(topKFrequent(new int[]{1,1,1,2,2,3}, 2)));
        System.out.println("kthLargest   = " + kthLargest(new int[]{3,2,1,5,6,4}, 2));

        MedianFinder mf = new MedianFinder();
        for (int v : new int[]{1, 2, 3}) mf.addNum(v);
        System.out.println("median = " + mf.findMedian());
    }
}
```

Walkthrough:

- `offer`: append at end, sift up.
- `poll`: take root, move last to root, sift down.
- `topKFrequent`: keep min-heap of size k by frequency; root is the kth-most-frequent.
- `MedianFinder`: max-heap holds lower half, min-heap holds upper half. Balance after each insert.

---

# 6. Java `PriorityQueue`

```java
PriorityQueue<Integer> min = new PriorityQueue<>();                 // min-heap
PriorityQueue<Integer> max = new PriorityQueue<>(Comparator.reverseOrder());
max.offer(3); max.offer(1); max.offer(5);
System.out.println(max.poll());   // 5
```

Important: `PriorityQueue.iterator()` does **not** return sorted order — only `peek/poll` give the heap order.

---

# 7. Common Mistakes

1. **Iterating a PriorityQueue expecting sorted output** — only the top is guaranteed.
2. **Wrong heap type for Kth** — Kth largest uses min-heap of size K; Kth smallest uses max-heap.
3. **Forgetting to rebalance** in MedianFinder.

---

# 8. Interview Questions

### Q1. Why array-based heap?
Complete binary tree ⇒ no gaps ⇒ array indices give parent/children in O(1).

### Q2. Build heap complexity?
O(n), not O(n log n).

### Q3. Why two heaps for median?
Each heap is balanced; median is always at the top of one or two peeks.

---

# 9. Practice Problems

## 🟢 Easy

### 1. Last Stone Weight (heap simulation)
**Input:** `[2,7,4,1,8]` → **Output:** `1`

### 2. Kth Largest
**Input:** `[3,2,1,5,6,4], k=2` → **Output:** `5`

### 3. Top K Frequent
**Input:** `[1,1,1,2,2,3], k=2` → **Output:** `[1,2]`

### 4. Min-Heap Implementation
Build / offer / poll.

### 5. PriorityQueue Demo
Insert 5 ints, peek/poll.

## 🟡 Medium

### 6. Kth Smallest
**Input:** `[7,10,4,3,20,15], k=3` → **Output:** `7`

### 7. Sort an Almost Sorted Array
**Input:** `k=2, arr=[6,5,3,2,8,10,9]` → sort.

### 8. Meeting Rooms II (min-heap)
**Input:** intervals → min rooms.

### 9. Reorganise String (heap)
**Input:** `"aab"` → **Output:** `"aba"`.

### 10. Ugly Number II (heap)
**Input:** `n=10` → **Output:** `12`.

## 🔴 Hard

### 11. Median from Data Stream
**Input:** stream → **Output:** median so far.

### 12. Merge K Sorted Lists
**Input:** k sorted lists → merged.

### 13. Smallest Number Range (K lists)
**Input:** k lists → smallest range covering at least one from each.

### 14. Sliding Window Median
**Input:** window → medians.

### 15. Trapping Rain Water II (heap)
BFS + heap.

---

# 10. Practice Hints

## Easy
1. Max-heap, smash top two.
2. Min-heap of size K.
3. Frequency map + heap.
4. Array + siftUp/siftDown.
5. Standard usage.

## Medium
6. Max-heap of size K.
7. Min-heap of size K.
8. Sort + heap of end times.
9. Max-heap by count.
10. Multiply by 2/3/5 with set.

## Hard
11. Two heaps.
12. Heap of (head, listIndex).
13. Heap of (value, row, col).
14. Lazy removal.
15. Heap from borders.

---

# 11. Revision Checklist

- [ ] Can implement heap operations
- [ ] Can use PriorityQueue
- [ ] Knows two-heap median
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 12. Key Takeaways

- Heap = complete binary tree with heap property.
- O(1) peek, O(log n) insert/extract.
- Kth largest → min-heap of size K.
- Median stream → max-heap + min-heap.

Tomorrow: **Advanced Tree Problems**.


## Solutions

### Problem 1 — Stones (E)

```java
class Stones {
    public static void main(String[] args) {
        int[] s = {2,7,4,1,8,1};
        java.util.PriorityQueue<Integer> pq = new java.util.PriorityQueue<>(java.util.Comparator.reverseOrder());
        for (int x : s) pq.offer(x);
        while (pq.size() > 1) { int a = pq.poll(), b = pq.poll(); if (a != b) pq.offer(a - b); }
        System.out.println(pq.isEmpty() ? 0 : pq.peek());
    }
}
```

### Problem 2 — Kth (E)

```java
class Kth {
    public static void main(String[] args) {
        int[] a = {3,2,3,1,2,4,5,5,6}; int k = 4;
        java.util.PriorityQueue<Integer> pq = new java.util.PriorityQueue<>();
        for (int x : a) { pq.offer(x); if (pq.size() > k) pq.poll(); }
        System.out.println(pq.peek());
    }
}
```

### Problem 3 — TopK (E)

```java
class TopK {
    public static void main(String[] args) {
        int[] a = {1,1,1,2,2,3}; int k = 2;
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>();
        for (int x : a) m.merge(x, 1, Integer::sum);
        java.util.PriorityQueue<int[]> pq = new java.util.PriorityQueue<>((x,y) -> x[0]-y[0]);
        for (var e : m.entrySet()) { pq.offer(new int[]{e.getValue(), e.getKey()}); if (pq.size() > k) pq.poll(); }
        System.out.println(pq);
    }
}
```

### Problem 4 — MinHeap (E)

```java
class MinHeap {
    int[] a = new int[100]; int n = 0;
    void offer(int x) { a[n++] = x; siftUp(n - 1); }
    int poll() { int v = a[0]; a[0] = a[--n]; siftDown(0); return v; }
    void siftUp(int i) { while (i > 0 && a[i] < a[(i-1)/2]) { int t = a[i]; a[i] = a[(i-1)/2]; a[(i-1)/2] = t; i = (i-1)/2; } }
    void siftDown(int i) { while (2*i+1 < n) { int c = 2*i+1; if (c+1 < n && a[c+1] < a[c]) c++; if (a[i] <= a[c]) break; int t = a[i]; a[i] = a[c]; a[c] = t; i = c; } }
    public static void main(String[] args) {
        MinHeap h = new MinHeap();
        for (int x : new int[]{3,1,4,1,5}) h.offer(x);
        System.out.println(h.poll());
    }
}
```

### Problem 5 — PQD (E)

```java
class PQD {
    public static void main(String[] args) {
        java.util.PriorityQueue<Integer> pq = new java.util.PriorityQueue<>();
        for (int x : new int[]{5,1,4,2,3}) pq.offer(x);
        while (!pq.isEmpty()) System.out.print(pq.poll() + " ");
    }
}
```

### Problem 6 — KthSm (M)

```java
class KthSm {
    public static void main(String[] args) {
        int[] a = {3,2,1,5,6,4}; int k = 2;
        java.util.PriorityQueue<Integer> pq = new java.util.PriorityQueue<>(java.util.Comparator.reverseOrder());
        for (int x : a) { pq.offer(x); if (pq.size() > k) pq.poll(); }
        System.out.println(pq.peek());
    }
}
```

### Problem 7 — AlmostSort (M)

```java
class AlmostSort {
    public static void main(String[] args) {
        int[] a = {6,5,3,2,8,10,9}; int k = 3;
        java.util.PriorityQueue<Integer> pq = new java.util.PriorityQueue<>();
        int idx = 0;
        for (int x : a) {
            pq.offer(x);
            if (pq.size() > k) System.out.print(pq.poll() + " ");
        }
        while (!pq.isEmpty()) System.out.print(pq.poll() + " ");
    }
}
```

### Problem 8 — Meeting (M)

```java
class Meeting {
    public static void main(String[] args) {
        int[][] iv = {{0,30},{5,10},{15,20}};
        java.util.Arrays.sort(iv, (a,b) -> Integer.compare(a[0], b[0]));
        java.util.PriorityQueue<Integer> pq = new java.util.PriorityQueue<>();
        for (int[] x : iv) {
            if (!pq.isEmpty() && pq.peek() <= x[0]) pq.poll();
            pq.offer(x[1]);
        }
        System.out.println(pq.size());
    }
}
```

### Problem 9 — Reorg (M)

```java
class Reorg {
    public static void main(String[] args) {
        String s = "aab";
        int[] c = new int[26]; for (char ch : s.toCharArray()) c[ch-'a']++;
        java.util.PriorityQueue<int[]> pq = new java.util.PriorityQueue<>((x,y) -> y[0]-x[0]);
        for (int i = 0; i < 26; i++) if (c[i] > 0) pq.offer(new int[]{c[i], i});
        StringBuilder sb = new StringBuilder();
        while (!pq.isEmpty()) {
            int[] first = pq.poll();
            sb.append((char)(first[1] + 'a'));
            first[0]--;
            int[] second = pq.peek();
            if (second != null && second[0] * 2 > s.length() + 1) { System.out.println(""); return; }
            if (first[0] > 0) pq.offer(first);
        }
        System.out.println(sb);
    }
}
```

### Problem 10 — Ugly (M)

```java
class Ugly {
    public static void main(String[] args) {
        int n = 10;
        java.util.PriorityQueue<Long> pq = new java.util.PriorityQueue<>();
        java.util.Set<Long> seen = new java.util.HashSet<>();
        long[] fac = {2, 3, 5};
        pq.offer(1L); seen.add(1L);
        for (int i = 0; i < n; i++) {
            long x = pq.poll();
            for (long f : fac) {
                long y = x * f;
                if (seen.add(y)) pq.offer(y);
            }
        }
        System.out.println(pq.peek() + " (or " + pq + ")");
    }
}
```

### Problem 11 — Med (H)

```java
class Med {
    java.util.PriorityQueue<Integer> lo = new java.util.PriorityQueue<>(java.util.Comparator.reverseOrder());
    java.util.PriorityQueue<Integer> hi = new java.util.PriorityQueue<>();
    void add(int n) { lo.offer(n); hi.offer(lo.poll()); if (lo.size() < hi.size()) lo.offer(hi.poll()); }
    double m() { return lo.size() > hi.size() ? lo.peek() : ((double)lo.peek() + hi.peek()) / 2; }
    public static void main(String[] args) {
        Med x = new Med();
        for (int v : new int[]{1,2,3,4,5}) x.add(v);
        System.out.println(x.m());
    }
}
```

### Problem 12 — MergeK (H)

```java
class MergeK {
    static class N { int v; N n; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N[] lists = new N[3];
        lists[0] = new N(1); lists[0].n = new N(4); lists[0].n.n = new N(5);
        lists[1] = new N(1); lists[1].n = new N(3); lists[1].n.n = new N(4);
        lists[2] = new N(2); lists[2].n = new N(6);
        java.util.PriorityQueue<N> pq = new java.util.PriorityQueue<>((a,b) -> a.v - b.v);
        for (N h : lists) if (h != null) pq.offer(h);
        N dummy = new N(0), t = dummy;
        while (!pq.isEmpty()) { t.n = pq.poll(); t = t.n; if (t.n != null) pq.offer(t.n); }
        for (N c = dummy.n; c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 13 — RangeK (H)

```java
class RangeK {
    public static void main(String[] args) {
        java.util.List<java.util.List<Integer>> lists = java.util.Arrays.asList(
            java.util.Arrays.asList(4,10,15,24,26),
            java.util.Arrays.asList(0,9,12,20),
            java.util.Arrays.asList(5,18,22,30)
        );
        java.util.PriorityQueue<int[]> pq = new java.util.PriorityQueue<>((a,b) -> Integer.compare(a[0], b[0]));
        int max = Integer.MIN_VALUE;
        for (int i = 0; i < lists.size(); i++) { pq.offer(new int[]{lists.get(i).get(0), i, 0}); max = Math.max(max, lists.get(i).get(0)); }
        int[] range = {Integer.MAX_VALUE, Integer.MIN_VALUE}; // lo..hi
        while (pq.size() == lists.size()) {
            int[] top = pq.poll();
            if (max - top[0] < range[1] - range[0]) { range[0] = top[0]; range[1] = max; }
            if (top[2] + 1 < lists.get(top[1]).size()) {
                int nxt = lists.get(top[1]).get(top[2] + 1);
                pq.offer(new int[]{nxt, top[1], top[2] + 1});
                max = Math.max(max, nxt);
            }
        }
        System.out.println(java.util.Arrays.toString(range));
    }
}
```

### Problem 14 — SWMed (H)

```java
class SWMed {
    public static void main(String[] args) {
        int[] a = {1,3,-1,-3,5,3,6,7}; int k = 3;
        java.util.List<Integer> win = new java.util.ArrayList<>();
        double[] out = new double[a.length - k + 1];
        for (int i = 0; i < a.length; i++) {
            win.add(a[i]); if (win.size() > k) win.remove((Integer) a[i-k]);
            java.util.Collections.sort(win);
            int m = win.size(); out[i - k + 1] = m % 2 == 1 ? win.get(m/2) : (win.get(m/2 - 1) + win.get(m/2)) / 2.0;
        }
        System.out.println(java.util.Arrays.toString(out));
    }
}
```

### Problem 15 — Trap2 (H)

```java
class Trap2 {
    public static void main(String[] args) {
        int[][] h = {{1,4,3,1,3,2},{3,2,1,3,2,4},{2,3,3,2,3,1}};
        int m = h.length, n = h[0].length, w = 0;
        java.util.PriorityQueue<int[]> pq = new java.util.PriorityQueue<>((a,b) -> a[2]-b[2]);
        boolean[][] vis = new boolean[m][n];
        for (int i = 0; i < m; i++) { pq.offer(new int[]{i,0,h[i][0]}); pq.offer(new int[]{i,n-1,h[i][n-1]}); vis[i][0]=vis[i][n-1]=true; }
        for (int j = 0; j < n; j++) { pq.offer(new int[]{0,j,h[0][j]}); pq.offer(new int[]{m-1,j,h[m-1][j]}); vis[0][j]=vis[m-1][j]=true; }
        int[][] d = {{1,0},{-1,0},{0,1},{0,-1}};
        while (!pq.isEmpty()) {
            int[] u = pq.poll();
            for (int[] dd : d) {
                int ni = u[0]+dd[0], nj = u[1]+dd[1];
                if (ni>=0 && nj>=0 && ni<m && nj<n && !vis[ni][nj]) {
                    w += Math.max(0, u[2] - h[ni][nj]);
                    pq.offer(new int[]{ni, nj, Math.max(u[2], h[ni][nj])});
                    vis[ni][nj] = true;
                }
            }
        }
        System.out.println(w);
    }
}
```

