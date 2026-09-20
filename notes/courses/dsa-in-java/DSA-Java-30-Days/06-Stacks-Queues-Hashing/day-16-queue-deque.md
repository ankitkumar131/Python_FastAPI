# Day 16 — Queue & Deque

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Explain FIFO and use cases
- Implement a queue (array + linked list)
- Implement a circular queue
- Use `ArrayDeque` as queue and deque
- Implement BFS using a queue (preview)
- Use `PriorityQueue` for top-K / min-stream

---

# 1. Introduction

A queue is FIFO (First-In-First-Out). It models "fair" processing: the first to arrive is the first to be served.

---

# 2. Why Do We Need This?

- BFS uses a queue.
- Scheduling (CPU, print, OS).
- Producer-consumer problems.
- Sliding-window max (with monotonic deque).

---

# 3. Core Concept

```
enqueue 1,2,3,4:
[1, 2, 3, 4]
 ^  ^        ^
head       tail

dequeue → 1
[_, 2, 3, 4]
 ^  ^  ^    ^
```

---

# 4. Real-World Analogy

A queue at a coffee shop: the first person in line is served first. Newcomers join the back.

---

# 5. Java Implementation — `QueueDemo.java`

```java
import java.util.*;

public class QueueDemo {

    /** Array queue with head/tail pointers (no wrap). */
    static class ArrayQueue {
        int[] a; int head = 0, tail = 0, size = 0;
        ArrayQueue(int cap) { a = new int[cap]; }
        void enqueue(int x) {
            if (size == a.length) throw new RuntimeException("full");
            a[tail++] = x; size++;
        }
        int dequeue() {
            if (size == 0) throw new RuntimeException("empty");
            int v = a[head++]; size--; return v;
        }
    }

    /** Circular queue. */
    static class CircularQueue {
        int[] a; int head = 0, tail = 0, size = 0;
        CircularQueue(int cap) { a = new int[cap]; }
        boolean enqueue(int x) {
            if (size == a.length) return false;
            a[tail] = x; tail = (tail + 1) % a.length; size++;
            return true;
        }
        int dequeue() {
            if (size == 0) return -1;
            int v = a[head]; head = (head + 1) % a.length; size--;
            return v;
        }
        boolean isEmpty() { return size == 0; }
    }

    /** LL queue. */
    static class LLQueue {
        static class Node { int data; Node next; }
        Node head, tail;
        void enqueue(int x) {
            Node n = new Node(); n.data = x;
            if (tail != null) tail.next = n;
            tail = n;
            if (head == null) head = n;
        }
        int dequeue() {
            int v = head.data; head = head.next;
            if (head == null) tail = null;
            return v;
        }
    }

    /** Sliding-window maximum with deque. */
    static int[] maxSlidingWindow(int[] a, int k) {
        int[] out = new int[a.length - k + 1];
        Deque<Integer> dq = new ArrayDeque<>();
        for (int i = 0; i < a.length; i++) {
            while (!dq.isEmpty() && dq.peekFirst() <= i - k) dq.pollFirst();
            while (!dq.isEmpty() && a[dq.peekLast()] <= a[i]) dq.pollLast();
            dq.offerLast(i);
            if (i >= k - 1) out[i - k + 1] = a[dq.peekFirst()];
        }
        return out;
    }

    /** BFS preview (level order). */
    static List<Integer> bfs(List<List<Integer>> graph, int start) {
        List<Integer> order = new ArrayList<>();
        boolean[] visited = new boolean[graph.size()];
        Deque<Integer> q = new ArrayDeque<>();
        q.offer(start); visited[start] = true;
        while (!q.isEmpty()) {
            int u = q.poll();
            order.add(u);
            for (int v : graph.get(u))
                if (!visited[v]) { visited[v] = true; q.offer(v); }
        }
        return order;
    }

    /** Priority queue demo — Kth largest. */
    static int kthLargest(int[] a, int k) {
        PriorityQueue<Integer> min = new PriorityQueue<>();
        for (int x : a) {
            min.offer(x);
            if (min.size() > k) min.poll();
        }
        return min.peek();
    }

    public static void main(String[] args) {
        CircularQueue cq = new CircularQueue(3);
        cq.enqueue(1); cq.enqueue(2); cq.enqueue(3);
        System.out.println("dequeue = " + cq.dequeue());
        cq.enqueue(4);
        System.out.println("dequeue = " + cq.dequeue());
        System.out.println("dequeue = " + cq.dequeue());

        System.out.println("maxSlidingWindow = " + Arrays.toString(maxSlidingWindow(new int[]{1,3,-1,-3,5,3,6,7}, 3)));
        System.out.println("kthLargest(2)    = " + kthLargest(new int[]{3,2,1,5,6,4}, 2));
        // BFS demo
        List<List<Integer>> g = new ArrayList<>();
        for (int i = 0; i < 5; i++) g.add(new ArrayList<>());
        g.get(0).addAll(Arrays.asList(1, 2));
        g.get(1).addAll(Arrays.asList(3));
        g.get(2).addAll(Arrays.asList(3, 4));
        System.out.println("bfs from 0       = " + bfs(g, 0));
    }
}
```

Walkthrough:

- `ArrayQueue`: simple, but `tail` never wraps → wasted space if many dequeues.
- `CircularQueue`: `tail = (tail + 1) % cap` reuses space.
- `LLQueue`: O(1) enqueue/dequeue, no fixed cap.
- `maxSlidingWindow`: monotonic deque of indices; front is always the max.
- `bfs`: classic level-order; visited prevents revisiting.
- `kthLargest`: a min-heap of size k — top of heap is the kth largest overall.

---

# 6. Dry Run — `maxSlidingWindow([1,3,-1,-3,5,3,6,7], k=3)`

| i | a[i] | deque (front→back, indices) | out |
|---|------|------------------------------|-----|
| 0 | 1    | [0]                          | -   |
| 1 | 3    | [1]                          | -   |
| 2 | -1   | [1, 2]                       | 3   |
| 3 | -3   | [1, 2, 3]                    | 3   |
| 4 | 5    | [4]                          | 5   |
| 5 | 3    | [4, 5]                       | 5   |
| 6 | 6    | [6]                          | 6   |
| 7 | 7    | [7]                          | 7   |

Result: `[3, 3, 5, 5, 6, 7]` ✓

---

# 7. Priority Queue

`PriorityQueue<Integer>` is a min-heap by default.

```java
PriorityQueue<Integer> min = new PriorityQueue<>();
min.offer(5); min.offer(2); min.offer(8);
min.poll();   // 2 (smallest)
```

Custom comparator:

```java
PriorityQueue<Integer> max = new PriorityQueue<>(Comparator.reverseOrder());
```

For **Kth largest**, keep a min-heap of size K. For **Kth smallest**, keep a max-heap of size K.

---

# 8. When to Use Each

| Need | Structure |
|---|---|
| FIFO processing | Queue / ArrayDeque |
| Sliding window max / min | Deque (monotonic) |
| Top K frequent / Kth largest | PriorityQueue |
| LIFO | Stack / ArrayDeque |
| BFS | Queue |
| DFS (iterative) | Stack |

---

# 9. Common Mistakes

1. **`java.util.Queue` is an interface** — use `LinkedList` or `ArrayDeque` (preferred) as implementation.
2. **Circular queue empty vs full**: track `size` to disambiguate.
3. **PriorityQueue is not sorted** — only `peek()` gives the smallest.

---

# 10. Interview Questions

### Q1. ArrayDeque vs LinkedList for queue?
`ArrayDeque` is faster (cache-friendly). Use it unless you need `null`s or specific LinkedList ops.

### Q2. Why use a min-heap for kth largest?
After processing all elements, the heap's smallest is the kth largest overall.

### Q3. Sliding window max time?
O(n) with monotonic deque.

---

# 11. Practice Problems

## 🟢 Easy

### 1. Implement Queue Using Stacks
**Input:** push 1,2; pop → **Output:** `1`

### 2. Implement Stack Using Queues
**Input:** push 1,2; pop → **Output:** `2`

### 3. First Unique Character in Stream
**Input:** stream "aabc" → first unique at index 2.

### 4. Number of Recent Calls
**Input:** calls at t=1, 100, 3001 → counts within 3000.

### 5. Design Circular Queue
Standard.

## 🟡 Medium

### 6. Sliding Window Maximum
**Input:** `[1,3,-1,-3,5,3,6,7], k=3` → **Output:** `[3,3,5,5,6,7]`

### 7. Kth Largest Element
**Input:** `[3,2,1,5,6,4], k=2` → **Output:** `5`

### 8. Top K Frequent Elements
**Input:** `[1,1,1,2,2,3], k=2` → **Output:** `[1,2]`

### 9. Binary Tree Level Order (BFS)
**Input:** tree → **Output:** `[[3],[9,20],[15,7]]`

### 10. Rotting Oranges (BFS)
**Input:** grid → **Output:** minutes.

## 🔴 Hard

### 11. Sliding Window Median
**Input:** `[1,3,-1,-3,5,3,6,7], k=3` → medians.

### 12. Shortest Subarray with Sum ≥ K
Reuse Day 9.

### 13. Trapping Rain Water II (2D BFS)
**Input:** heightmap → **Output:** water units.

### 14. Word Ladder (BFS)
**Input:** begin="hit", end="cog", list → **Output:** `5`

### 15. Shortest Path in Binary Matrix (BFS)
**Input:** grid → **Output:** shortest path length.

---

# 12. Practice Hints

## Easy
1. Two stacks (in, out).
2. One queue, rotate on push.
3. Queue + freq map.
4. Queue of timestamps.
5. Circular array with size tracking.

## Medium
6. Monotonic deque.
7. Min-heap of size K.
8. Bucket or heap.
9. Queue per level.
10. Multi-source BFS.

## Hard
11. Two heaps.
12. Prefix + monotonic deque.
13. BFS from borders.
14. BFS over word graph.
15. 8-direction BFS.

---

# 13. Revision Checklist

- [ ] Can implement queue (array / LL / circular)
- [ ] Can solve sliding-window maximum
- [ ] Can use PriorityQueue for top-K
- [ ] Knows BFS skeleton

---

# 14. Key Takeaways

- Queue = FIFO. Use `ArrayDeque`.
- Sliding window max = monotonic deque.
- PriorityQueue = min-heap by default.
- BFS = queue + visited.

Tomorrow: **Hashing**.


## Solutions

### Problem 1 — QueueS (E)

```java
class QueueS {
    java.util.Deque<Integer> in = new java.util.ArrayDeque<>(), out = new java.util.ArrayDeque<>();
    void push(int x) { in.push(x); }
    int pop() { if (out.isEmpty()) while (!in.isEmpty()) out.push(in.pop()); return out.pop(); }
    int peek() { if (out.isEmpty()) while (!in.isEmpty()) out.push(in.pop()); return out.peek(); }
    public static void main(String[] args) {
        QueueS q = new QueueS(); q.push(1); q.push(2);
        System.out.println(q.peek() + " " + q.pop());
    }
}
```

### Problem 2 — Queue2Stacks (E)

```java
class Queue2Stacks {
    java.util.Deque<Integer> a = new java.util.ArrayDeque<>(), b = new java.util.ArrayDeque<>();
    void push(int x) { a.push(x); }
    int pop() { while (b.isEmpty()) while (!a.isEmpty()) b.push(a.pop()); return b.pop(); }
    public static void main(String[] args) {
        Queue2Stacks q = new Queue2Stacks(); q.push(1); q.push(2);
        System.out.println(q.pop());
    }
}
```

### Problem 3 — FirstUniq (E)

```java
class FirstUniq {
    java.util.Map<Character,Integer> cnt = new java.util.LinkedHashMap<>();
    java.util.Deque<Character> q = new java.util.ArrayDeque<>();
    void add(char c) {
        cnt.merge(c, 1, Integer::sum);
        q.offer(c);
        while (!q.isEmpty() && cnt.get(q.peek()) > 1) q.poll();
    }
    char first() { return q.isEmpty() ? '#' : q.peek(); }
    public static void main(String[] args) {
        FirstUniq f = new FirstUniq();
        for (char c : "aabcc".toCharArray()) f.add(c);
        System.out.println(f.first());
    }
}
```

### Problem 4 — RecentCalls (E)

```java
class RecentCalls {
    java.util.Deque<Integer> q = new java.util.ArrayDeque<>();
    void ping(int t) { q.offer(t); while (q.peek() < t - 3000) q.poll(); }
    int count() { return q.size(); }
    public static void main(String[] args) {
        RecentCalls r = new RecentCalls();
        r.ping(1); r.ping(100); r.ping(3001); r.ping(3002);
        System.out.println(r.count());
    }
}
```

### Problem 5 — CircQ (E)

```java
class CircQ {
    int[] a; int head = 0, tail = 0, size = 0, cap;
    CircQ(int k) { a = new int[k]; cap = k; }
    boolean enq(int v) { if (size == cap) return false; a[tail] = v; tail = (tail+1)%cap; size++; return true; }
    int deq() { if (size == 0) return -1; int v = a[head]; head = (head+1)%cap; size--; return v; }
    public static void main(String[] args) {
        CircQ q = new CircQ(3);
        q.enq(1); q.enq(2); q.enq(3);
        System.out.println(q.deq() + " " + q.deq());
    }
}
```

### Problem 6 — SWMax (M)

```java
class SWMax {
    public static void main(String[] args) {
        int[] a = {1,3,-1,-3,5,3,6,7}; int k = 3;
        java.util.Deque<Integer> dq = new java.util.ArrayDeque<>();
        int[] out = new int[a.length - k + 1];
        for (int i = 0; i < a.length; i++) {
            while (!dq.isEmpty() && dq.peekFirst() <= i - k) dq.pollFirst();
            while (!dq.isEmpty() && a[dq.peekLast()] <= a[i]) dq.pollLast();
            dq.offerLast(i);
            if (i >= k - 1) out[i - k + 1] = a[dq.peekFirst()];
        }
        System.out.println(java.util.Arrays.toString(out));
    }
}
```

### Problem 7 — KthLg (M)

```java
class KthLg {
    public static void main(String[] args) {
        int[] a = {3,2,3,1,2,4,5,5,6}; int k = 4;
        java.util.PriorityQueue<Integer> pq = new java.util.PriorityQueue<>();
        for (int x : a) { pq.offer(x); if (pq.size() > k) pq.poll(); }
        System.out.println(pq.peek());
    }
}
```

### Problem 8 — TopKFreq (M)

```java
class TopKFreq {
    public static void main(String[] args) {
        int[] a = {1,1,1,2,2,3}; int k = 2;
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>();
        for (int x : a) m.merge(x, 1, Integer::sum);
        java.util.PriorityQueue<int[]> pq = new java.util.PriorityQueue<>((x,y) -> x[0]-y[0]);
        for (var e : m.entrySet()) { pq.offer(new int[]{e.getValue(), e.getKey()}); if (pq.size() > k) pq.poll(); }
        java.util.List<Integer> out = new java.util.ArrayList<>();
        while (!pq.isEmpty()) out.add(pq.poll()[1]);
        System.out.println(out);
    }
}
```

### Problem 9 — LevelOrder (M)

```java
class LevelOrder {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static void lo(N root) {
        java.util.Deque<N> q = new java.util.ArrayDeque<>();
        q.offer(root);
        while (!q.isEmpty()) {
            N u = q.poll();
            System.out.print(u.v + " ");
            if (u.l != null) q.offer(u.l);
            if (u.r != null) q.offer(u.r);
        }
    }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3);
        lo(root);
    }
}
```

### Problem 10 — Rotting (M)

```java
class Rotting {
    public static void main(String[] args) {
        int[][] g = {{2,1,1},{1,1,0},{0,1,1}};
        int m = g.length, n = g[0].length, t = 0;
        java.util.Deque<int[]> q = new java.util.ArrayDeque<>();
        for (int i = 0; i < m; i++) for (int j = 0; j < n; j++) if (g[i][j] == 2) q.offer(new int[]{i, j});
        int[][] d = {{1,0},{-1,0},{0,1},{0,-1}};
        while (!q.isEmpty()) {
            int sz = q.size(); boolean rotted = false;
            for (int k = 0; k < sz; k++) {
                int[] u = q.poll();
                for (int[] dd : d) {
                    int ni = u[0]+dd[0], nj = u[1]+dd[1];
                    if (ni>=0 && nj>=0 && ni<m && nj<n && g[ni][nj]==1) { g[ni][nj]=2; q.offer(new int[]{ni,nj}); rotted=true; }
                }
            }
            if (rotted) t++;
        }
        System.out.println(t);
    }
}
```

### Problem 11 — SWMedian (H)

```java
class SWMedian {
    public static void main(String[] args) {
        int[] a = {1,3,-1,-3,5,3,6,7}; int k = 3;
        // Simple approach: insert each new, remove old, sort to find median. O(k log k) per step.
        java.util.List<Integer> win = new java.util.ArrayList<>();
        double[] out = new double[a.length - k + 1];
        for (int i = 0; i < a.length; i++) {
            win.add(a[i]);
            if (win.size() > k) win.remove((Integer) a[i-k]);
            java.util.Collections.sort(win);
            int m = win.size();
            out[i - k + 1] = m % 2 == 1 ? win.get(m/2) : (win.get(m/2 - 1) + win.get(m/2)) / 2.0;
        }
        System.out.println(java.util.Arrays.toString(out));
    }
}
```

### Problem 12 — ShortestK (H)

```java
class ShortestK {
    public static void main(String[] args) {
        int[] a = {1}; int k = 1;
        // shortest subarray with sum >= k (deque-based) — placeholder answer
        long[] p = new long[a.length+1]; for (int i = 0; i < a.length; i++) p[i+1] = p[i]+a[i];
        int ans = a.length + 1;
        java.util.Deque<Integer> dq = new java.util.ArrayDeque<>();
        for (int i = 0; i < p.length; i++) {
            while (!dq.isEmpty() && p[i] - p[dq.peekFirst()] >= k) ans = Math.min(ans, i - dq.pollFirst());
            while (!dq.isEmpty() && p[i] <= p[dq.peekLast()]) dq.pollLast();
            dq.offerLast(i);
        }
        System.out.println(ans == a.length + 1 ? -1 : ans);
    }
}
```

### Problem 13 — Trap2D (H)

```java
class Trap2D {
    public static void main(String[] args) {
        int[][] h = {{1,4,3,1,3,2},{3,2,1,3,2,4},{2,3,3,2,3,1}};
        int m = h.length, n = h[0].length;
        java.util.PriorityQueue<int[]> pq = new java.util.PriorityQueue<>((a,b) -> a[2]-b[2]);
        boolean[][] vis = new boolean[m][n];
        for (int i = 0; i < m; i++) { pq.offer(new int[]{i,0,h[i][0]}); pq.offer(new int[]{i,n-1,h[i][n-1]}); vis[i][0]=vis[i][n-1]=true; }
        for (int j = 0; j < n; j++) { pq.offer(new int[]{0,j,h[0][j]}); pq.offer(new int[]{m-1,j,h[m-1][j]}); vis[0][j]=vis[m-1][j]=true; }
        int[][] d = {{1,0},{-1,0},{0,1},{0,-1}};
        int w = 0;
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

### Problem 14 — WordLadder (H)

```java
class WordLadder {
    public static void main(String[] args) {
        String begin = "hit", end = "cog";
        java.util.List<String> wordList = java.util.Arrays.asList("hot","dot","dog","lot","log","cog");
        java.util.Set<String> dict = new java.util.HashSet<>(wordList);
        if (!dict.contains(end)) { System.out.println(0); return; }
        java.util.Deque<String> q = new java.util.ArrayDeque<>();
        java.util.Set<String> seen = new java.util.HashSet<>();
        q.offer(begin); seen.add(begin); int steps = 1;
        while (!q.isEmpty()) {
            int sz = q.size();
            for (int i = 0; i < sz; i++) {
                String w = q.poll();
                if (w.equals(end)) { System.out.println(steps); return; }
                char[] a = w.toCharArray();
                for (int j = 0; j < a.length; j++) {
                    char orig = a[j];
                    for (char c = 'a'; c <= 'z'; c++) {
                        if (c == orig) continue;
                        a[j] = c; String n = new String(a);
                        if (dict.contains(n) && !seen.contains(n)) { seen.add(n); q.offer(n); }
                    }
                    a[j] = orig;
                }
            }
            steps++;
        }
        System.out.println(0);
    }
}
```

### Problem 15 — BinMat (H)

```java
class BinMat {
    public static void main(String[] args) {
        int[][] g = {{0,0,0},{1,1,0},{1,1,0}};
        int m = g.length, n = g[0].length;
        java.util.Deque<int[]> q = new java.util.ArrayDeque<>();
        if (g[0][0] == 1) { System.out.println(-1); return; }
        q.offer(new int[]{0,0,1});
        int[][] dirs = {{1,0},{0,1},{-1,0},{0,-1},{1,1},{-1,-1},{1,-1},{-1,1}};
        int best = -1;
        while (!q.isEmpty()) {
            int[] u = q.poll();
            if (u[0]==m-1 && u[1]==n-1) { best = u[2]; break; }
            for (int[] d : dirs) {
                int ni = u[0]+d[0], nj = u[1]+d[1];
                if (ni>=0 && nj>=0 && ni<m && nj<n && g[ni][nj]==0) { g[ni][nj]=1; q.offer(new int[]{ni,nj,u[2]+1}); }
            }
        }
        System.out.println(best);
    }
}
```

