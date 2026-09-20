# Day 26 — Shortest Paths & Advanced Graphs

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Implement Dijkstra, Bellman-Ford, Floyd-Warshall, topological sort
- Build a minimum spanning tree with Prim and Kruskal
- Use Union-Find / Disjoint Set Union (DSU)
- Pick the right algorithm for a given graph

---

# 1. Introduction

When graphs have weighted edges, BFS no longer gives shortest paths. You need graph-specific shortest-path and MST algorithms. Today we cover the four most important.

---

# 2. Dijkstra (Single-Source Shortest Path)

For non-negative weights. Use a min-heap.

```
dist[start] = 0
while pq not empty:
    (d, u) = pq.pop()
    if d > dist[u]: continue
    for (v, w) in adj[u]:
        if dist[u] + w < dist[v]:
            dist[v] = dist[u] + w
            pq.push((dist[v], v))
```

Complexity: O((V + E) log V).

---

# 3. Bellman-Ford (Negative Weights OK)

Relax all edges V−1 times. Detects negative cycles.

```
for i in 1..V-1:
    for (u, v, w) in edges:
        if dist[u] + w < dist[v]:
            dist[v] = dist[u] + w
```

Complexity: O(V · E).

---

# 4. Floyd-Warshall (All-Pairs)

Triple loop: `dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])`.

Complexity: O(V³).

---

# 5. Topological Sort

For DAGs only. DFS-based or Kahn's algorithm.

```java
List<Integer> topo(List<List<Integer>> adj, int n) {
    int[] indeg = new int[n];
    for (int u = 0; u < n; u++) for (int v : adj.get(u)) indeg[v]++;
    Deque<Integer> q = new ArrayDeque<>();
    for (int i = 0; i < n; i++) if (indeg[i] == 0) q.offer(i);
    List<Integer> out = new ArrayList<>();
    while (!q.isEmpty()) {
        int u = q.poll(); out.add(u);
        for (int v : adj.get(u)) if (--indeg[v] == 0) q.offer(v);
    }
    return out.size() == n ? out : new ArrayList<>();
}
```

---

# 6. Minimum Spanning Tree (Prim & Kruskal)

**Prim** — grow a tree by adding the cheapest edge that doesn't form a cycle.

**Kruskal** — sort edges, add if they don't form a cycle (DSU).

---

# 7. Union-Find (DSU)

```java
static class DSU {
    int[] parent, rank;
    DSU(int n) { parent = new int[n]; rank = new int[n]; for (int i = 0; i < n; i++) parent[i] = i; }
    int find(int x) { while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; }
    boolean union(int a, int b) {
        int ra = find(a), rb = find(b);
        if (ra == rb) return false;
        if (rank[ra] < rank[rb]) { parent[ra] = rb; }
        else if (rank[ra] > rank[rb]) { parent[rb] = ra; }
        else { parent[rb] = ra; rank[ra]++; }
        return true;
    }
}
```

---

# 8. Java Implementation — `ShortestPathsDemo.java`

```java
import java.util.*;

public class ShortestPathsDemo {

    static class Edge { int to; int w; Edge(int t, int w) { to = t; this.w = w; } }

    /** Dijkstra: returns distances from src, or INF if unreachable. */
    static long[] dijkstra(List<List<Edge>> g, int src) {
        int n = g.size();
        long[] dist = new long[n];
        Arrays.fill(dist, Long.MAX_VALUE);
        dist[src] = 0;
        PriorityQueue<long[]> pq = new PriorityQueue<>((a, b) -> Long.compare(a[0], b[0]));
        pq.offer(new long[]{0, src});
        while (!pq.isEmpty()) {
            long[] cur = pq.poll();
            long d = cur[0]; int u = (int) cur[1];
            if (d > dist[u]) continue;
            for (Edge e : g.get(u))
                if (dist[u] + e.w < dist[e.to]) {
                    dist[e.to] = dist[u] + e.w;
                    pq.offer(new long[]{dist[e.to], e.to});
                }
        }
        return dist;
    }

    /** Bellman-Ford. */
    static long[] bellmanFord(int n, int[][] edges, int src) {
        long[] dist = new long[n];
        Arrays.fill(dist, Long.MAX_VALUE);
        dist[src] = 0;
        for (int i = 0; i < n - 1; i++)
            for (int[] e : edges)
                if (dist[e[0]] != Long.MAX_VALUE && dist[e[0]] + e[2] < dist[e[1]])
                    dist[e[1]] = dist[e[0]] + e[2];
        // optional: detect negative cycle by another pass
        return dist;
    }

    /** Floyd-Warshall. */
    static long[][] floyd(int n, int[][] edges) {
        long[][] d = new long[n][n];
        for (long[] row : d) Arrays.fill(row, Long.MAX_VALUE / 4);
        for (int i = 0; i < n; i++) d[i][i] = 0;
        for (int[] e : edges) d[e[0]][e[1]] = e[2];
        for (int k = 0; k < n; k++)
            for (int i = 0; i < n; i++)
                for (int j = 0; j < n; j++)
                    if (d[i][k] + d[k][j] < d[i][j]) d[i][j] = d[i][k] + d[k][j];
        return d;
    }

    /** Topological sort (Kahn). */
    static List<Integer> topo(int n, List<List<Integer>> adj) {
        int[] indeg = new int[n];
        for (int u = 0; u < n; u++) for (int v : adj.get(u)) indeg[v]++;
        Deque<Integer> q = new ArrayDeque<>();
        for (int i = 0; i < n; i++) if (indeg[i] == 0) q.offer(i);
        List<Integer> out = new ArrayList<>();
        while (!q.isEmpty()) {
            int u = q.poll(); out.add(u);
            for (int v : adj.get(u)) if (--indeg[v] == 0) q.offer(v);
        }
        return out.size() == n ? out : new ArrayList<>();
    }

    /** DSU. */
    static class DSU {
        int[] parent, rank;
        DSU(int n) { parent = new int[n]; rank = new int[n]; for (int i = 0; i < n; i++) parent[i] = i; }
        int find(int x) { while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; }
        boolean union(int a, int b) {
            int ra = find(a), rb = find(b);
            if (ra == rb) return false;
            if (rank[ra] < rank[rb]) { parent[ra] = rb; }
            else if (rank[ra] > rank[rb]) { parent[rb] = ra; }
            else { parent[rb] = ra; rank[ra]++; }
            return true;
        }
    }

    /** Kruskal MST. */
    static int kruskal(int n, int[][] edges) {
        Arrays.sort(edges, (a, b) -> Integer.compare(a[2], b[2]));
        DSU d = new DSU(n);
        int total = 0, used = 0;
        for (int[] e : edges) {
            if (d.union(e[0], e[1])) { total += e[2]; if (++used == n - 1) break; }
        }
        return total;
    }

    /** Prim MST using a heap. */
    static int prim(List<List<Edge>> g, int n) {
        boolean[] inMST = new boolean[n];
        PriorityQueue<Edge> pq = new PriorityQueue<>((a, b) -> Integer.compare(a.w, b.w));
        pq.offer(new Edge(0, 0));
        int total = 0, edges = 0;
        while (!pq.isEmpty() && edges < n) {
            Edge e = pq.poll();
            if (inMST[e.to]) continue;
            inMST[e.to] = true; total += e.w; edges++;
            for (Edge nb : g.get(e.to)) if (!inMST[nb.to]) pq.offer(nb);
        }
        return total;
    }

    public static void main(String[] args) {
        int n = 4;
        List<List<Edge>> g = new ArrayList<>();
        for (int i = 0; i < n; i++) g.add(new ArrayList<>());
        g.get(0).add(new Edge(1, 1)); g.get(0).add(new Edge(2, 4));
        g.get(1).add(new Edge(2, 2)); g.get(1).add(new Edge(3, 5));
        g.get(2).add(new Edge(3, 1));

        System.out.println("dijkstra   = " + Arrays.toString(dijkstra(g, 0)));
        System.out.println("bellman    = " + Arrays.toString(bellmanFord(n, new int[][]{{0,1,1},{0,2,4},{1,2,2},{1,3,5},{2,3,1}}, 0)));

        long[][] fw = floyd(n, new int[][]{{0,1,1},{0,2,4},{1,2,2},{1,3,5},{2,3,1}});
        System.out.println("floyd[0][3] = " + fw[0][3]);

        List<List<Integer>> adj = new ArrayList<>();
        for (int i = 0; i < 4; i++) adj.add(new ArrayList<>());
        adj.get(0).add(1); adj.get(0).add(2); adj.get(1).add(3); adj.get(2).add(3);
        System.out.println("topo        = " + topo(4, adj));

        System.out.println("kruskal     = " + kruskal(n, new int[][]{{0,1,1},{0,2,4},{1,2,2},{1,3,5},{2,3,1}}));
        System.out.println("prim        = " + prim(g, n));
    }
}
```

Walkthrough:

- **Dijkstra**: classic min-heap approach. Skip stale entries via the `d > dist[u]` check.
- **Bellman-Ford**: V−1 iterations of edge relaxation.
- **Floyd-Warshall**: triple loop; intermediate node `k`.
- **Topological sort (Kahn)**: BFS with indegree; cycle = output size < n.
- **DSU**: path compression + union by rank.
- **Kruskal**: sort edges, union finds groups.
- **Prim**: heap-based, add cheapest edge reaching outside the tree.

---

# 9. When to Use Which

| Problem | Algorithm |
|---|---|
| Single-source, non-negative | Dijkstra |
| Single-source, negative weights | Bellman-Ford |
| All-pairs | Floyd-Warshall |
| DAG shortest path | Topological sort + relax |
| MST | Prim (dense) or Kruskal (sparse) |
| Cycle detection (directed) | Kahn (size mismatch) or 3-colour DFS |

---

# 10. Common Mistakes

1. **Dijkstra with negative weights** — doesn't work.
2. **Forgetting path compression** in DSU → TLE.
3. **Cycle in topological sort** — output size < n.

---

# 11. Interview Questions

### Q1. Why doesn't Dijkstra work with negative weights?
A node popped from the heap could later receive a shorter path through a negative-weight edge.

### Q2. How to detect negative cycle in Bellman-Ford?
Run one more pass; if anything relaxes, there's a negative cycle.

### Q3. Prim vs Kruskal?
Prim uses a heap and is O(E log V). Kruskal sorts edges O(E log E) and uses DSU; better for sparse graphs.

---

# 12. Practice Problems

## 🟢 Easy

### 1. Network Delay Time (Dijkstra)
**Input:** times → time for all to receive signal.

### 2. Cheapest Flights Within K Stops (Bellman-Ford)
**Input:** flights, src, dst, k → cheapest.

### 3. Find the Town Judge (in/out degrees)
Standard.

### 4. Course Schedule II (topo)
Standard.

### 5. Keys and Rooms (DFS)
Standard.

## 🟡 Medium

### 6. Dijkstra Implementation
Standard.

### 7. Bellman-Ford
Standard.

### 8. Floyd-Warshall
Standard.

### 9. Topological Sort
Standard.

### 10. Union-Find (basic)
Standard.

## 🔴 Hard

### 11. Minimum Spanning Tree (Kruskal/Prim)
Standard.

### 12. Strongly Connected Components (Kosaraju)
Re-do.

### 13. Critical Connections (Tarjan)
Re-do.

### 14. Shortest Path with Alternating Colours
**Input:** red/blue edges → shortest alternating path.

### 15. Swim in Rising Water
**Input:** grid → min time to reach bottom-right.

---

# 13. Practice Hints

## Easy
1. Dijkstra to all nodes, return max.
2. Bellman-Ford with step limit.
3. indeg - outdeg.
4. Kahn's algorithm.
5. DFS from 0.

## Medium
6. Min-heap.
7. V-1 relax passes.
8. Triple loop.
9. Kahn or DFS.
10. Path compression + union by rank.

## Hard
11. Sort + DSU / heap.
12. Two DFS passes.
13. Low-link DFS.
14. BFS with state.
15. Binary search + BFS.

---

# 14. Revision Checklist

- [ ] Can implement Dijkstra, Bellman-Ford, Floyd
- [ ] Can do topological sort
- [ ] Can do Kruskal and Prim
- [ ] Can use DSU

---

# 15. Key Takeaways

- Dijkstra: non-negative weights, min-heap.
- Bellman-Ford: handles negatives.
- Floyd: all-pairs, O(V³).
- DSU is the engine behind Kruskal.

Tomorrow: **DP Fundamentals**.


## Solutions

### Problem 1 — NetworkDelay (E)

```java
class NetworkDelay {
    static class E { int to; int w; E(int t, int w) { to=t; this.w=w; } }
    public static void main(String[] args) {
        int[][] t = {{1,2,1},{2,3,2},{1,3,4}};
        int n = 3, k = 1;
        java.util.List<java.util.List<E>> g = new java.util.ArrayList<>();
        for (int i = 0; i <= n; i++) g.add(new java.util.ArrayList<>());
        for (int[] x : t) g.get(x[0]).add(new E(x[1], x[2]));
        int[] dist = new int[n + 1]; java.util.Arrays.fill(dist, Integer.MAX_VALUE); dist[k] = 0;
        java.util.PriorityQueue<int[]> pq = new java.util.PriorityQueue<>((a,b) -> a[0]-b[0]);
        pq.offer(new int[]{0, k});
        while (!pq.isEmpty()) {
            int[] u = pq.poll();
            if (u[0] > dist[u[1]]) continue;
            for (E e : g.get(u[1])) if (u[0] + e.w < dist[e.to]) { dist[e.to] = u[0] + e.w; pq.offer(new int[]{dist[e.to], e.to}); }
        }
        int max = 0; for (int i = 1; i <= n; i++) max = Math.max(max, dist[i]);
        System.out.println(max == Integer.MAX_VALUE ? -1 : max);
    }
}
```

### Problem 2 — KStops (E)

```java
class KStops {
    static class E { int to; int w; E(int t, int w) { to=t; this.w=w; } }
    public static void main(String[] args) {
        int n = 3; int[][] f = {{0,1,100},{1,2,100},{0,2,500}};
        int src = 0, dst = 2, k = 1;
        int[] dist = new int[n]; java.util.Arrays.fill(dist, Integer.MAX_VALUE); dist[src] = 0;
        for (int i = 0; i <= k; i++) {
            int[] tmp = dist.clone();
            for (int[] x : f) if (dist[x[0]] != Integer.MAX_VALUE) tmp[x[1]] = Math.min(tmp[x[1]], dist[x[0]] + x[2]);
            dist = tmp;
        }
        System.out.println(dist[dst] == Integer.MAX_VALUE ? -1 : dist[dst]);
    }
}
```

### Problem 3 — Judge (E)

```java
class Judge {
    public static void main(String[] args) {
        int n = 2; int[][] trust = {{1,2}};
        int[] in = new int[n + 1], out = new int[n + 1];
        for (int[] t : trust) { in[t[1]]++; out[t[0]]++; }
        int ans = -1;
        for (int i = 1; i <= n; i++) if (in[i] == n - 1 && out[i] == 0) ans = i;
        System.out.println(ans);
    }
}
```

### Problem 4 — CourseII (E)

```java
class CourseII {
    public static void main(String[] args) {
        int n = 4; int[][] p = {{1,0},{2,0},{3,1},{3,2}};
        java.util.List<java.util.List<Integer>> g = new java.util.ArrayList<>();
        for (int i = 0; i < n; i++) g.add(new java.util.ArrayList<>());
        int[] indeg = new int[n];
        for (int[] x : p) { g.get(x[1]).add(x[0]); indeg[x[0]]++; }
        java.util.Deque<Integer> q = new java.util.ArrayDeque<>();
        for (int i = 0; i < n; i++) if (indeg[i] == 0) q.offer(i);
        java.util.List<Integer> order = new java.util.ArrayList<>();
        while (!q.isEmpty()) { int u = q.poll(); order.add(u); for (int v : g.get(u)) if (--indeg[v] == 0) q.offer(v); }
        System.out.println(order.size() == n ? order : new int[]{});
    }
}
```

### Problem 5 — Keys (E)

```java
class Keys {
    public static void main(String[] args) {
        int[][] rooms = {{1,3},{3,0,1},{2},{0}};
        boolean[] v = new boolean[rooms.length];
        java.util.Deque<Integer> q = new java.util.ArrayDeque<>(); q.offer(0); v[0] = true;
        while (!q.isEmpty()) { int u = q.poll(); for (int k : rooms[u]) if (!v[k]) { v[k] = true; q.offer(k); } }
        for (boolean x : v) if (!x) { System.out.println(false); return; }
        System.out.println(true);
    }
}
```

### Problem 6 — Dijkstra (M)

```java
class Dijkstra {
    static class E { int to; int w; E(int t, int w) { to=t; this.w=w; } }
    public static void main(String[] args) {
        int[][] e = {{0,1,4},{0,2,1},{1,3,1},{2,1,2},{2,3,5}};
        int n = 4;
        java.util.List<java.util.List<E>> g = new java.util.ArrayList<>();
        for (int i = 0; i < n; i++) g.add(new java.util.ArrayList<>());
        for (int[] x : e) { g.get(x[0]).add(new E(x[1], x[2])); g.get(x[1]).add(new E(x[0], x[2])); }
        int[] dist = new int[n]; java.util.Arrays.fill(dist, Integer.MAX_VALUE); dist[0] = 0;
        java.util.PriorityQueue<int[]> pq = new java.util.PriorityQueue<>((a,b) -> a[0]-b[0]); pq.offer(new int[]{0, 0});
        while (!pq.isEmpty()) { int[] u = pq.poll(); if (u[0] > dist[u[1]]) continue; for (E ed : g.get(u[1])) if (u[0] + ed.w < dist[ed.to]) { dist[ed.to] = u[0] + ed.w; pq.offer(new int[]{dist[ed.to], ed.to}); } }
        System.out.println(java.util.Arrays.toString(dist));
    }
}
```

### Problem 7 — Bellman (M)

```java
class Bellman {
    public static void main(String[] args) {
        int V = 5, E = 8; int[][] e = {{0,1,-1},{0,2,4},{1,2,3},{3,2,5},{3,1,1},{1,4,2},{4,3,-3},{2,1,1}};
        int[] d = new int[V]; java.util.Arrays.fill(d, Integer.MAX_VALUE); d[0] = 0;
        for (int i = 0; i < V - 1; i++)
            for (int[] x : e) if (d[x[0]] != Integer.MAX_VALUE && d[x[0]] + x[2] < d[x[1]]) d[x[1]] = d[x[0]] + x[2];
        boolean neg = false;
        for (int[] x : e) if (d[x[0]] != Integer.MAX_VALUE && d[x[0]] + x[2] < d[x[1]]) neg = true;
        System.out.println(neg ? "negative cycle" : java.util.Arrays.toString(d));
    }
}
```

### Problem 8 — Floyd (M)

```java
class Floyd {
    public static void main(String[] args) {
        int[][] d = {{0,3,Integer.MAX_VALUE,7},{8,0,2,Integer.MAX_VALUE},{5,Integer.MAX_VALUE,0,1},{2,Integer.MAX_VALUE,Integer.MAX_VALUE,0}};
        int n = 4;
        for (int k = 0; k < n; k++) for (int i = 0; i < n; i++) for (int j = 0; j < n; j++)
            if (d[i][k] != Integer.MAX_VALUE && d[k][j] != Integer.MAX_VALUE && d[i][k] + d[k][j] < d[i][j]) d[i][j] = d[i][k] + d[k][j];
        for (int[] row : d) System.out.println(java.util.Arrays.toString(row));
    }
}
```

### Problem 9 — Topo (M)

```java
class Topo {
    public static void main(String[] args) {
        int n = 4; int[][] e = {{0,1},{0,2},{1,2},{2,3}};
        java.util.List<java.util.List<Integer>> g = new java.util.ArrayList<>();
        for (int i = 0; i < n; i++) g.add(new java.util.ArrayList<>());
        int[] indeg = new int[n];
        for (int[] x : e) { g.get(x[0]).add(x[1]); indeg[x[1]]++; }
        java.util.Deque<Integer> q = new java.util.ArrayDeque<>();
        for (int i = 0; i < n; i++) if (indeg[i] == 0) q.offer(i);
        java.util.List<Integer> order = new java.util.ArrayList<>();
        while (!q.isEmpty()) { int u = q.poll(); order.add(u); for (int v : g.get(u)) if (--indeg[v] == 0) q.offer(v); }
        System.out.println(order);
    }
}
```

### Problem 10 — DSU (M)

```java
class DSU {
    int[] p, r;
    DSU(int n) { p = new int[n]; r = new int[n]; for (int i = 0; i < n; i++) p[i] = i; }
    int find(int x) { return p[x] == x ? x : (p[x] = find(p[x])); }
    void union(int a, int b) {
        a = find(a); b = find(b);
        if (a == b) return;
        if (r[a] < r[b]) { int t = a; a = b; b = t; }
        p[b] = a;
        if (r[a] == r[b]) r[a]++;
    }
    public static void main(String[] args) {
        DSU d = new DSU(5);
        d.union(0, 1); d.union(1, 2);
        System.out.println(d.find(0) == d.find(2));
    }
}
```

### Problem 11 — MST (H)

```java
class MST {
    static class E { int u, v, w; E(int u, int v, int w) { this.u=u; this.v=v; this.w=w; } }
    public static void main(String[] args) {
        int[][] edges = {{0,1,10},{0,2,6},{0,3,5},{1,3,15},{2,3,4}};
        java.util.List<E> es = new java.util.ArrayList<>();
        for (int[] x : edges) es.add(new E(x[0], x[1], x[2]));
        java.util.Collections.sort(es, (a,b) -> Integer.compare(a.w, b.w));
        DSU d = new DSU(4);
        int total = 0;
        for (E e : es) if (d.find(e.u) != d.find(e.v)) { d.union(e.u, e.v); total += e.w; }
        System.out.println(total);
    }
}
```

### Problem 12 — Kosaraju (H)

```java
class Kosaraju {
    static int t = 0;
    static void dfs1(java.util.List<java.util.List<Integer>> g, int u, boolean[] v, java.util.Deque<Integer> st) {
        v[u] = true;
        for (int x : g.get(u)) if (!v[x]) dfs1(g, x, v, st);
        st.push(u);
    }
    static void dfs2(java.util.List<java.util.List<Integer>> gr, int u, boolean[] v) { v[u] = true; for (int x : gr.get(u)) if (!v[x]) dfs2(gr, x, v); }
    public static void main(String[] args) {
        int n = 5; int[][] e = {{1,0},{0,2},{2,1},{0,3},{3,4}};
        java.util.List<java.util.List<Integer>> g = new java.util.ArrayList<>(), gr = new java.util.ArrayList<>();
        for (int i = 0; i < n; i++) { g.add(new java.util.ArrayList<>()); gr.add(new java.util.ArrayList<>()); }
        for (int[] x : e) { g.get(x[0]).add(x[1]); gr.get(x[1]).add(x[0]); }
        boolean[] v = new boolean[n]; java.util.Deque<Integer> st = new java.util.ArrayDeque<>();
        for (int i = 0; i < n; i++) if (!v[i]) dfs1(g, i, v, st);
        v = new boolean[n]; int scc = 0;
        while (!st.isEmpty()) { int u = st.pop(); if (!v[u]) { dfs2(gr, u, v); scc++; } }
        System.out.println(scc);
    }
}
```

### Problem 13 — Bridges2 (H)

```java
class Bridges2 {
    static int t = 0;
    static void dfs(java.util.List<java.util.List<Integer>> g, int u, int p, int[] disc, int[] low, java.util.List<int[]> res) {
        disc[u] = low[u] = ++t;
        for (int v : g.get(u)) {
            if (v == p) continue;
            if (disc[v] == 0) { dfs(g, v, u, disc, low, res); low[u] = Math.min(low[u], low[v]); if (low[v] > disc[u]) res.add(new int[]{u, v}); }
            else low[u] = Math.min(low[u], disc[v]);
        }
    }
    public static void main(String[] args) {
        int n = 5; int[][] e = {{0,1},{1,2},{2,0},{1,3},{3,4}};
        java.util.List<java.util.List<Integer>> g = new java.util.ArrayList<>();
        for (int i = 0; i < n; i++) g.add(new java.util.ArrayList<>());
        for (int[] x : e) { g.get(x[0]).add(x[1]); g.get(x[1]).add(x[0]); }
        java.util.List<int[]> res = new java.util.ArrayList<>();
        dfs(g, 0, -1, new int[n], new int[n], res);
        System.out.println(res);
    }
}
```

### Problem 14 — ShortestAlt (H)

```java
class ShortestAlt {
    public static void main(String[] args) {
        int n = 3; int[][] red = {{0,1},{1,2}}, blue = {};
        int[][] dist = new int[n][2];
        for (int[] row : dist) java.util.Arrays.fill(row, -1);
        java.util.Deque<int[]> q = new java.util.ArrayDeque<>();
        dist[0][0] = dist[0][1] = 0; q.offer(new int[]{0, 0}); q.offer(new int[]{0, 1});
        while (!q.isEmpty()) {
            int[] u = q.poll();
            for (int[] e : (u[1] == 0 ? red : blue)) if (dist[e[1]][1 - u[1]] == -1) { dist[e[1]][1 - u[1]] = dist[u[0]][u[1]] + 1; q.offer(new int[]{e[1], 1 - u[1]}); }
        }
        System.out.println(java.util.Arrays.deepToString(dist));
    }
}
```

### Problem 15 — SwimRising (H)

```java
class SwimRising {
    public static void main(String[] args) {
        int[][] g = {{0,2},{1,3}};
        int n = g.length;
        boolean[] v = new boolean[n];
        java.util.PriorityQueue<int[]> pq = new java.util.PriorityQueue<>((a,b) -> a[1]-b[1]);
        for (int i = 0; i < n; i++) pq.offer(new int[]{i, g[i][0]});
        int time = 0;
        while (!v[pq.peek()[0]]) {
            int[] u = pq.poll();
            if (v[u[0]]) continue;
            v[u[0]] = true; time = Math.max(time, u[1]);
            for (int j = 0; j < n; j++) if (!v[j]) pq.offer(new int[]{j, Math.max(u[1], g[j][0])});
        }
        System.out.println(time);
    }
}
```

