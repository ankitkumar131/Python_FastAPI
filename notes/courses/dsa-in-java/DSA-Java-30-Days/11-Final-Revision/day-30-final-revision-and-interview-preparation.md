# Day 30 — Final Revision & Interview Preparation

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Recognise any major DSA pattern on sight
- Quickly recall core Java implementations
- Walk through the standard interview communication script
- Avoid common interview mistakes

---

# 1. Introduction

This is the day to consolidate everything. No new material — just recall, drill, and prepare.

---

# 2. The 30-Day Cheat Sheet

| Day | Topic | Key takeaways |
|----:|-------|---------------|
| 1   | Java Foundations     | JVM entry, primitives, loops, methods, I/O |
| 2   | OOP                  | class/Object, this/static/final, inheritance, polymorphism |
| 3   | Complexity           | Big-O/Ω/Θ, drop constants, amortised |
| 4   | Math                 | GCD Euclidean, sieve, fast power, n&(n-1) |
| 5   | Arrays               | Kadane, two-pointer rotation |
| 6   | Strings              | StringBuilder, immutable, anagram |
| 7   | Two Pointers         | Sorted pair, in-place filtering |
| 8   | Sliding Window       | Fixed + variable window |
| 9   | Prefix Sum           | O(1) range query; subarray sum = K |
| 10  | Searching            | Binary search variants, lo+lo+lo+ |
| 11  | Sorting              | Merge, quick, counting, stable |
| 12  | Recursion            | Base case, memoisation |
| 13  | Linked List          | Fast/slow pointers, reverse |
| 14  | Adv. Linked Lists    | Floyd cycle start, LRU |
| 15  | Stack                | Monotonic stack, MinStack |
| 16  | Queue & Deque        | BFS, sliding-window max |
| 17  | Hashing              | HashMap/Set, collision, equals+hashCode |
| 18  | Binary Trees         | Traversal, height/size |
| 19  | BST                  | Insert/delete/validate, LCA |
| 20  | Heap                 | PriorityQueue, Kth largest |
| 21  | Adv. Tree Problems   | Diameter, LCA, vertical |
| 22  | Greedy               | Sort + local choice |
| 23  | Backtracking         | Choose/explore/undo |
| 24  | Graph Fundamentals   | BFS/DFS, components |
| 25  | BFS/DFS deep         | Cycle, bipartite, grid |
| 26  | Shortest Paths       | Dijkstra, Bellman-Ford, Floyd, MST |
| 27  | DP Fundamentals      | Memoisation, tabulation |
| 28  | DP Patterns          | Knapsack, LCS, LIS |
| 29  | Advanced DP          | Interval, tree, bitmask |
| 30  | Revision             | YOU ARE HERE |

---

# 3. The Pattern Recognition Cheat Sheet

```
Sorted array?
  → Binary search / Two Pointers / Sliding window

Subarray (contiguous)?
  → Sliding window / Prefix sum / Kadane

Frequency?
  → HashMap / HashSet

Top-K / Kth?
  → Heap / PriorityQueue / QuickSelect

Next greater / smaller?
  → Monotonic stack

Shortest path in UNWEIGHTED graph?
  → BFS

Shortest path with positive weights?
  → Dijkstra

Shortest path with negative weights?
  → Bellman-Ford

All-pairs shortest?
  → Floyd-Warshall

MST?
  → Kruskal (sparse) / Prim (dense)

Cycle in graph?
  → DFS with parent (undirected) / 3-colour (directed)
  → Kahn's algorithm (directed, by checking order size)

Tree traversal?
  → DFS (recursive) / BFS (level order)

Connected components?
  → BFS / DFS / Union-Find

Count all ways / min cost?
  → DP

Generate all combinations?
  → Backtracking

Shortest / longest in grid?
  → BFS / DFS + memo

Subsequence?
  → DP (LIS/LCS) or two pointers + sorting

String match with KMP?
  → KMP / Rabin-Karp

Interval scheduling / non-overlap?
  → Sort by end, greedy sweep

LCA?
  → Split-point (BST) / post-order (binary tree)
```

---

# 4. Java Implementation Quick Recall

### Binary search (no overflow)

```java
int lo = 0, hi = a.length - 1;
while (lo <= hi) {
    int mid = lo + (hi - lo) / 2;
    if (a[mid] == target) return mid;
    if (a[mid] < target) lo = mid + 1;
    else hi = mid - 1;
}
```

### Sliding window

```java
int lo = 0;
for (int hi = 0; hi < a.length; hi++) {
    // add a[hi]
    while (/* invalid */) { /* remove a[lo] */ lo++; }
    // update answer
}
```

### Linked list reverse

```java
Node prev = null, cur = head;
while (cur != null) {
    Node nxt = cur.next;
    cur.next = prev;
    prev = cur;
    cur = nxt;
}
```

### BFS

```java
Deque<Integer> q = new ArrayDeque<>();
boolean[] vis = new boolean[n];
q.offer(start); vis[start] = true;
while (!q.isEmpty()) {
    int u = q.poll();
    for (int v : g.adj.get(u))
        if (!vis[v]) { vis[v] = true; q.offer(v); }
}
```

### Dijkstra

```java
PriorityQueue<long[]> pq = new PriorityQueue<>((a,b) -> Long.compare(a[0], b[0]));
long[] dist = new long[n]; Arrays.fill(dist, INF); dist[src] = 0;
pq.offer(new long[]{0, src});
while (!pq.isEmpty()) {
    long[] cur = pq.poll();
    if (cur[0] > dist[(int) cur[1]]) continue;
    for (Edge e : g.get((int) cur[1]))
        if (cur[0] + e.w < dist[e.to]) { dist[e.to] = cur[0] + e.w; pq.offer(new long[]{dist[e.to], e.to}); }
}
```

### DP tabulation

```java
int[] dp = new int[n + 1];
dp[0] = base;
for (int i = 1; i <= n; i++)
    dp[i] = transition(dp[i - 1], ...);
```

### Backtracking

```java
void bt(int i, List<Choice> cur) {
    if (done) { record(cur); return; }
    for (Choice c : choices(i)) {
        if (valid(c)) {
            apply(c); bt(i + 1, cur); undo(c);
        }
    }
}
```

---

# 5. The Interview Script

When given a problem:

```
1. "Let me restate the problem in my own words."
2. "Here are 3 examples — minimum, typical, edge."
3. "Brute force: [describe]." Code it. Test.
4. "The bottleneck is X. The pattern that fits is Y."
5. "Here's the optimised version." Code it. Test.
6. "Time: O(?), Space: O(?)."
7. "Edge cases I tested: empty, single, all same."
```

Time-box:
- 5 min: clarify + examples + brute force
- 10 min: code brute force
- 15 min: optimised solution
- 5 min: test + complexity + edge cases

---

# 6. Common Interview Mistakes

| Mistake | Fix |
|---|---|
| Silent coding | Narrate constantly |
| No examples | Always give 3 |
| Skipping complexity | Always state it |
| Not testing | Run your code mentally |
| One attempt only | If stuck, restart |
| Ignoring hints | Take them gracefully |
| Wrong data structure | Justify your choice |
| Mutable key in HashMap | Use immutable key |

---

# 7. Java Gotchas to Remember

1. `int[] arr = new int[n]` — primitive, default 0.
2. `Integer[] arr` — boxed, default null.
3. `arr.length` (field) vs `s.length()` (method) vs `list.size()` (method).
4. `String.equals` for comparison; `==` is reference.
5. `ArrayList` resizes; pre-size if you know.
6. `PriorityQueue` is a **min-heap** by default.
7. `HashMap` is **not** thread-safe; use `ConcurrentHashMap`.
8. Use `long` for accumulators to avoid overflow.
9. `Math.abs(Integer.MIN_VALUE)` is still negative — beware.
10. `Integer.parseInt` throws on invalid input.

---

# 8. Behavioural / Soft Skills

- Have 2–3 STAR stories ready (Technical challenge, Conflict, Failure, Leadership).
- Know your top projects cold.
- Ask thoughtful questions at the end:
  - "What does success look like in the first 90 days?"
  - "What's the team's approach to code review?"
  - "What does the on-call rotation look like?"

---

# 9. Pre-Interview Checklist

- [ ] Solved 5+ problems from each major topic
- [ ] Can write binary search, BFS, DFS, Dijkstra, basic DP from memory
- [ ] Reviewed error log; no recurring mistakes
- [ ] Sleep at least 7 hours the night before
- [ ] Test your setup (camera, microphone, IDE)
- [ ] Have paper + pen ready
- [ ] Water bottle nearby

---

# 10. Practice Problems (capstone)

## 🟢 Easy

### 1. Two Sum
Re-solve in < 5 min.

### 2. Valid Parentheses
Re-solve.

### 3. Best Time to Buy and Sell Stock
Re-solve.

## 🟡 Medium

### 4. Group Anagrams
Re-solve.

### 5. Course Schedule
Re-solve.

### 6. Coin Change
Re-solve.

### 7. LRU Cache
Re-solve.

## 🔴 Hard

### 8. Word Ladder
Re-solve.

### 9. Trapping Rain Water
Re-solve.

### 10. Median from Data Stream
Re-solve.

---

# 11. Practice Hints

## Easy
1. HashMap value→index.
2. Stack of opens.
3. Track min so far.

## Medium
4. Sorted key.
5. Detect cycle via DFS / Kahn.
6. Unbounded knapsack.
7. HashMap + DLL.

## Hard
8. BFS over words.
9. Two-pointer max-of-min.
10. Two heaps.

---

# 12. The "Which Pattern Should I Use?" Decision Guide

```
PROBLEM
   │
   ├── Strings/arrays
   │      │
   │      ├── sorted → Binary Search / Two Pointers
   │      ├── contiguous segment → Sliding Window / Prefix Sum
   │      ├── frequency → HashMap
   │      ├── top-K → Heap
   │      ├── next greater → Monotonic Stack
   │      └── subsequence → DP (LIS/LCS)
   │
   ├── Linked List
   │      │
   │      ├── mid / cycle → Fast/slow pointers
   │      ├── reverse → Three-pointer
   │      ├── group reverse → Recursive group
   │      └── LRU → HashMap + DLL
   │
   ├── Trees
   │      │
   │      ├── traversal → DFS / BFS
   │      ├── BST ops → BST property
   │      ├── LCA → Split-point
   │      └── path sum → Post-order
   │
   ├── Graphs
   │      │
   │      ├── shortest path (unweighted) → BFS
   │      ├── shortest (weighted) → Dijkstra
   │      ├── cycle → DFS / Kahn
   │      ├── components → DFS/BFS/DSU
   │      └── MST → Kruskal/Prim
   │
   └── DP
          │
          ├── knapsack-style → 1D capacity
          ├── match strings → 2D
          ├── paths on grid → 2D
          └── interval → 2D with split point
```

---

# 13. Revision Checklist

- [ ] Can name 5+ patterns and pick them quickly
- [ ] Can code binary search, BFS, DFS, Dijkstra, basic DP from memory
- [ ] Knows all 8 Big-O classes
- [ ] Knows when to use HashMap vs TreeMap vs Heap
- [ ] Has rehearsed the interview script
- [ ] Has solved at least 50 problems in the last week

---

# 14. Final Encouragement

You have:
- ✅ Completed 30 days of structured learning
- ✅ Solved 450 practice problems
- ✅ Mastered 14 core Java implementations
- ✅ Built pattern recognition across all major topics

The course is over. The real practice begins now. Good luck — and remember: DSA is learned by **doing**, not reading. Keep solving.

---

# 15. Where to Go From Here

- **LeetCode**: https://leetcode.com — daily problem, contests
- **HackerRank**: https://hackerrank.com — topic-wise practice
- **Codeforces**: https://codeforces.com — contests
- **Books**: "Cracking the Coding Interview", "Algorithm Design Manual"
- **Mock interviews**: Pramp, interviewing.io

Stay consistent. Trust your preparation. You've earned it.


## Solutions

### Problem 1 — TwoSumF (E)

```java
class TwoSumF {
    public static void main(String[] args) {
        int[] a = {2,7,11,15}; int t = 9;
        java.util.Map<Integer, Integer> m = new java.util.HashMap<>();
        for (int i = 0; i < a.length; i++) if (m.containsKey(t - a[i])) { System.out.println(m.get(t - a[i]) + " " + i); return; } else m.put(a[i], i);
    }
}
```

### Problem 2 — ParenF (E)

```java
class ParenF {
    public static void main(String[] args) {
        int n = 3;
        java.util.List<String> res = new java.util.ArrayList<>();
        gen(n, 0, 0, new StringBuilder(), res);
        System.out.println(res);
    }
    static void gen(int n, int open, int close, StringBuilder cur, java.util.List<String> res) {
        if (cur.length() == 2 * n) { res.add(cur.toString()); return; }
        if (open < n) { cur.append('('); gen(n, open + 1, close, cur, res); cur.deleteCharAt(cur.length() - 1); }
        if (close < open) { cur.append(')'); gen(n, open, close + 1, cur, res); cur.deleteCharAt(cur.length() - 1); }
    }
}
```

### Problem 3 — StockF (E)

```java
class StockF {
    public static void main(String[] args) {
        int[] p = {7,1,5,3,6,4};
        int min = Integer.MAX_VALUE, best = 0;
        for (int x : p) { best = Math.max(best, x - min); min = Math.min(min, x); }
        System.out.println(best);
    }
}
```

### Problem 4 — GroupF (E)

```java
class GroupF {
    public static void main(String[] args) {
        String[] a = {"eat","tea","tan","ate","nat","bat"};
        java.util.Map<String, java.util.List<String>> m = new java.util.HashMap<>();
        for (String w : a) { char[] c = w.toCharArray(); java.util.Arrays.sort(c); m.computeIfAbsent(new String(c), k -> new java.util.ArrayList<>()).add(w); }
        System.out.println(m.values());
    }
}
```

### Problem 5 — CourseF (E)

```java
class CourseF {
    public static void main(String[] args) {
        int n = 2; int[][] p = {{1,0}};
        java.util.List<java.util.List<Integer>> g = new java.util.ArrayList<>();
        for (int i = 0; i < n; i++) g.add(new java.util.ArrayList<>());
        for (int[] x : p) g.get(x[1]).add(x[0]);
        int[] s = new int[n];
        for (int i = 0; i < n; i++) if (!dfs(g, s, i)) { System.out.println(false); return; }
        System.out.println(true);
    }
    static boolean dfs(java.util.List<java.util.List<Integer>> g, int[] s, int u) {
        if (s[u] == 1) return false; if (s[u] == 2) return true;
        s[u] = 1;
        for (int v : g.get(u)) if (!dfs(g, s, v)) return false;
        s[u] = 2; return true;
    }
}
```

### Problem 6 — CoinF (M)

```java
class CoinF {
    public static void main(String[] args) {
        int[] c = {1,2,5}; int a = 11;
        int[] dp = new int[a + 1]; dp[0] = 1;
        for (int x : c) for (int i = x; i <= a; i++) dp[i] += dp[i - x];
        System.out.println(dp[a]);
    }
}
```

### Problem 7 — LRUF (M)

```java
class LRUF {
    static class Node { int k, v; Node prev, next; Node(int k, int v) { this.k=k; this.v=v; } }
    static class LRU {
        int cap; java.util.Map<Integer, Node> m = new java.util.HashMap<>();
        Node head = new Node(0,0), tail = new Node(0,0);
        LRU(int cap) { this.cap = cap; head.next = tail; tail.prev = head; }
        void add(Node n) { n.prev = head; n.next = head.next; head.next.prev = n; head.next = n; }
        void remove(Node n) { n.prev.next = n.next; n.next.prev = n.prev; }
        int get(int k) { if (!m.containsKey(k)) return -1; Node n = m.get(k); remove(n); add(n); return n.v; }
        void put(int k, int v) {
            if (m.containsKey(k)) remove(m.get(k));
            Node n = new Node(k, v); add(n); m.put(k, n);
            if (m.size() > cap) { Node lru = tail.prev; remove(lru); m.remove(lru.k); }
        }
    }
    public static void main(String[] args) {
        LRU l = new LRU(2);
        l.put(1,1); l.put(2,2);
        System.out.println(l.get(1));
        l.put(3,3);
        System.out.println(l.get(2));
    }
}
```

### Problem 8 — LadderF (M)

```java
class LadderF {
    public static void main(String[] args) {
        String begin = "hit", end = "cog";
        java.util.List<String> wl = java.util.Arrays.asList("hot","dot","dog","lot","log","cog");
        java.util.Set<String> dict = new java.util.HashSet<>(wl);
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
                    for (char c = 'a'; c <= 'z'; c++) { if (c==orig) continue; a[j]=c; String n = new String(a); if (dict.contains(n) && seen.add(n)) q.offer(n); }
                    a[j] = orig;
                }
            }
            steps++;
        }
        System.out.println(0);
    }
}
```

### Problem 9 — TrapF (M)

```java
class TrapF {
    public static void main(String[] args) {
        int[] h = {0,1,0,2,1,0,1,3,2,1,2,1};
        int n = h.length;
        if (n == 0) { System.out.println(0); return; }
        int[] l = new int[n], r = new int[n]; l[0] = h[0]; for (int i = 1; i < n; i++) l[i] = Math.max(l[i-1], h[i]);
        r[n-1] = h[n-1]; for (int i = n-2; i >= 0; i--) r[i] = Math.max(r[i+1], h[i]);
        int ans = 0; for (int i = 0; i < n; i++) ans += Math.min(l[i], r[i]) - h[i];
        System.out.println(ans);
    }
}
```

### Problem 10 — MedF (M)

```java
class MedF {
    public static void main(String[] args) {
        java.util.PriorityQueue<Integer> lo = new java.util.PriorityQueue<>((a,b) -> b - a);
        java.util.PriorityQueue<Integer> hi = new java.util.PriorityQueue<>();
        int[] stream = {1,2,3,4,5};
        java.util.List<Double> res = new java.util.ArrayList<>();
        for (int x : stream) {
            lo.offer(x); hi.offer(lo.poll());
            if (lo.size() < hi.size()) lo.offer(hi.poll());
            if (lo.size() > hi.size()) res.add((double) lo.peek());
            else res.add((lo.peek() + hi.peek()) / 2.0);
        }
        System.out.println(res);
    }
}
```

