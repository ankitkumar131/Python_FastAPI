# Day 24 — Graph Fundamentals

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Define graph terminology (vertex, edge, directed, undirected, weighted)
- Choose between adjacency matrix, adjacency list, edge list
- Implement a graph in Java
- Perform BFS and DFS

---

# 1. Introduction

A **graph** is a set of vertices connected by edges. Trees are special graphs (connected, acyclic). Graphs model networks: roads, friendships, dependencies, web pages.

---

# 2. Why Do We Need This?

- Social networks, maps, routing.
- Dependency graphs, course schedules.
- Anything where pairwise relationships matter.

---

# 3. Core Concept

### Terminology

- **Vertex / Node**: an entity.
- **Edge**: connection between two vertices.
- **Directed**: edges have direction (a → b).
- **Undirected**: edges are bidirectional.
- **Weighted**: edges carry a cost/distance.
- **Cyclic**: contains a cycle.
- **Connected**: every vertex reachable from every other (undirected).

---

# 4. Real-World Analogy

Google Maps: cities are vertices, roads are weighted edges. Finding the shortest path is a graph problem.

---

# 5. Representations

| Representation | Space | Edge lookup | Neighbours |
|---|---|---|---|
| Adjacency matrix | O(V²) | O(1) | O(V) |
| Adjacency list   | O(V + E) | O(deg) | O(deg) |
| Edge list        | O(E) | O(E) | O(E) |

**Adjacency list** is the go-to for sparse graphs.

---

# 6. Java Implementation — `GraphDemo.java`

```java
import java.util.*;

public class GraphDemo {

    /** Graph as adjacency list. */
    static class Graph {
        int n;
        List<List<Integer>> adj;
        Graph(int n) { this.n = n; this.adj = new ArrayList<>(); for (int i = 0; i < n; i++) adj.add(new ArrayList<>()); }
        void addEdge(int u, int v) { adj.get(u).add(v); adj.get(v).add(u); }
        void addDirected(int u, int v) { adj.get(u).add(v); }
    }

    /** BFS from start. */
    static List<Integer> bfs(Graph g, int start) {
        List<Integer> order = new ArrayList<>();
        boolean[] vis = new boolean[g.n];
        Deque<Integer> q = new ArrayDeque<>();
        q.offer(start); vis[start] = true;
        while (!q.isEmpty()) {
            int u = q.poll(); order.add(u);
            for (int v : g.adj.get(u)) if (!vis[v]) { vis[v] = true; q.offer(v); }
        }
        return order;
    }

    /** Recursive DFS. */
    static List<Integer> dfs(Graph g, int start) {
        List<Integer> out = new ArrayList<>();
        boolean[] vis = new boolean[g.n];
        dfsRec(g, start, vis, out);
        return out;
    }
    static void dfsRec(Graph g, int u, boolean[] vis, List<Integer> out) {
        vis[u] = true; out.add(u);
        for (int v : g.adj.get(u)) if (!vis[v]) dfsRec(g, v, vis, out);
    }

    /** Iterative DFS using a stack. */
    static List<Integer> dfsIter(Graph g, int start) {
        List<Integer> out = new ArrayList<>();
        boolean[] vis = new boolean[g.n];
        Deque<Integer> st = new ArrayDeque<>();
        st.push(start);
        while (!st.isEmpty()) {
            int u = st.pop();
            if (vis[u]) continue;
            vis[u] = true; out.add(u);
            for (int v : g.adj.get(u)) if (!vis[v]) st.push(v);
        }
        return out;
    }

    /** Number of connected components. */
    static int components(Graph g) {
        boolean[] vis = new boolean[g.n];
        int count = 0;
        for (int i = 0; i < g.n; i++) if (!vis[i]) { bfsComponent(g, i, vis); count++; }
        return count;
    }
    static void bfsComponent(Graph g, int start, boolean[] vis) {
        Deque<Integer> q = new ArrayDeque<>();
        q.offer(start); vis[start] = true;
        while (!q.isEmpty()) {
            int u = q.poll();
            for (int v : g.adj.get(u)) if (!vis[v]) { vis[v] = true; q.offer(v); }
        }
    }

    /** Clone a graph (BFS). */
    static class GNode { int val; List<GNode> neighbors; GNode(int v) { val = v; neighbors = new ArrayList<>(); } }
    static GNode clone(GNode n) {
        if (n == null) return null;
        Map<GNode, GNode> map = new HashMap<>();
        Deque<GNode> q = new ArrayDeque<>();
        q.offer(n); map.put(n, new GNode(n.val));
        while (!q.isEmpty()) {
            GNode cur = q.poll();
            for (GNode nb : cur.neighbors) {
                if (!map.containsKey(nb)) { map.put(nb, new GNode(nb.val)); q.offer(nb); }
                map.get(cur).neighbors.add(map.get(nb));
            }
        }
        return map.get(n);
    }

    public static void main(String[] args) {
        Graph g = new Graph(6);
        g.addEdge(0, 1); g.addEdge(0, 2);
        g.addEdge(1, 3); g.addEdge(2, 3);
        g.addEdge(3, 4); g.addEdge(4, 5);

        System.out.println("BFS from 0: " + bfs(g, 0));
        System.out.println("DFS from 0: " + dfs(g, 0));
        System.out.println("DFSiter 0:  " + dfsIter(g, 0));
        System.out.println("Components: " + components(g));
    }
}
```

Walkthrough:

- `Graph`: adjacency list — list of neighbours per node.
- `bfs`: queue; visit; enqueue unvisited neighbours.
- `dfsRec`: recursive — pushes the call stack. Returns the preorder traversal.
- `dfsIter`: stack; pop; mark visited; push children. Equivalent order to recursive (depending on push order).
- `components`: run BFS/DFS from each unvisited vertex.
- `clone`: BFS with HashMap old→new.

---

# 7. BFS vs DFS

| | BFS | DFS |
|---|---|---|
| Data structure | Queue | Stack / recursion |
| Order | Level-by-level | As deep as possible |
| Shortest path (unweighted) | ✅ | ❌ |
| Memory | O(width) | O(depth) |

---

# 8. Common Mistakes

1. **Forgetting `visited`** in DFS — infinite recursion.
2. **Resetting `visited` between components** when counting — keep it global.
3. **Iterative DFS order ≠ recursive** if push order differs.

---

# 9. Interview Questions

### Q1. Adjacency matrix vs list?
Matrix: O(V²) space, O(1) edge check. List: O(V+E), preferred for sparse.

### Q2. When to use BFS over DFS?
Shortest path in unweighted graph, level-order.

### Q3. What's a DAG?
Directed acyclic graph — used for topological sort, dependencies.

---

# 10. Practice Problems

## 🟢 Easy

### 1. BFS Traversal
**Input:** graph, start → **Output:** bfs order.

### 2. DFS Traversal
Same.

### 3. Find if Path Exists
**Input:** graph, src, dst → **Output:** true/false.

### 4. Count Connected Components
Standard.

### 5. Clone Graph
Standard.

## 🟡 Medium

### 6. Number of Islands
**Input:** grid → **Output:** count.

### 7. Max Area of Island
**Input:** grid → **Output:** max area.

### 8. Surrounded Regions
**Input:** grid → capture regions.

### 9. Course Schedule (cycle detection)
**Input:** n, prereqs → can finish?

### 10. Pacific Atlantic Water Flow
**Input:** heights → cells reaching both oceans.

## 🔴 Hard

### 11. Word Ladder
**Input:** begin, end, list → min length.

### 12. Strongly Connected Components (Kosaraju/Tarjan)

### 13. Critical Connections (Tarjan's bridges)

### 14. Alien Dictionary
**Input:** sorted words → order.

### 15. Reconstruct Itinerary
**Input:** tickets → itinerary.

---

# 11. Practice Hints

## Easy
1. Queue BFS.
2. Recursive DFS.
3. BFS visit check.
4. Loop BFS from each.
5. BFS + HashMap.

## Medium
6. DFS on grid.
7. DFS with area count.
8. Boundary DFS then flip.
9. DFS cycle detect.
10. Multi-source DFS.

## Hard
11. BFS over word graph.
12. Two DFS passes.
13. Tarjan's low-link.
14. Build graph, topo sort.
15. Eulerian path (Hierholzer).

---

# 12. Revision Checklist

- [ ] Can pick a graph representation
- [ ] Can implement BFS and DFS
- [ ] Can count connected components
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 13. Key Takeaways

- Adjacency list = default representation.
- BFS for shortest path in unweighted graphs.
- DFS for cycle detection, topological sort, connectivity.
- Iterative DFS uses a stack explicitly.

Tomorrow: **BFS & DFS deep**.


## Solutions

### Problem 1 — BFS (E)

```java
class BFS {
    public static void main(String[] args) {
        java.util.List<java.util.List<Integer>> g = new java.util.ArrayList<>();
        for (int i = 0; i < 4; i++) g.add(new java.util.ArrayList<>());
        g.get(0).addAll(java.util.Arrays.asList(1, 2)); g.get(1).add(2); g.get(2).add(0); g.get(3).add(0);
        java.util.Deque<Integer> q = new java.util.ArrayDeque<>();
        boolean[] v = new boolean[4]; q.offer(0); v[0] = true;
        while (!q.isEmpty()) { int u = q.poll(); System.out.print(u + " "); for (int x : g.get(u)) if (!v[x]) { v[x] = true; q.offer(x); } }
    }
}
```

### Problem 2 — DFS (E)

```java
class DFS {
    static java.util.List<java.util.List<Integer>> g;
    static boolean[] v;
    static void dfs(int u) { v[u] = true; System.out.print(u + " "); for (int x : g.get(u)) if (!v[x]) dfs(x); }
    public static void main(String[] args) {
        g = new java.util.ArrayList<>(); for (int i = 0; i < 4; i++) g.add(new java.util.ArrayList<>());
        g.get(0).addAll(java.util.Arrays.asList(1, 2)); g.get(1).add(2); g.get(2).add(0); g.get(3).add(0);
        v = new boolean[4]; dfs(0);
    }
}
```

### Problem 3 — PathExists (E)

```java
class PathExists {
    public static void main(String[] args) {
        int[][] e = {{0,1},{1,2},{3,5},{5,4},{4,3}};
        java.util.Map<Integer, java.util.List<Integer>> g = new java.util.HashMap<>();
        for (int[] x : e) { g.computeIfAbsent(x[0], k -> new java.util.ArrayList<>()).add(x[1]); g.computeIfAbsent(x[1], k -> new java.util.ArrayList<>()).add(x[0]); }
        int src = 0, dst = 2; boolean[] v = new boolean[6];
        java.util.Deque<Integer> q = new java.util.ArrayDeque<>(); q.offer(src); v[src] = true;
        while (!q.isEmpty()) { int u = q.poll(); if (u == dst) { System.out.println(true); return; } for (int x : g.getOrDefault(u, java.util.Collections.emptyList())) if (!v[x]) { v[x] = true; q.offer(x); } }
        System.out.println(false);
    }
}
```

### Problem 4 — CC (E)

```java
class CC {
    static java.util.List<java.util.List<Integer>> g;
    static boolean[] v;
    static void dfs(int u) { v[u] = true; for (int x : g.get(u)) if (!v[x]) dfs(x); }
    public static void main(String[] args) {
        g = new java.util.ArrayList<>(); for (int i = 0; i < 5; i++) g.add(new java.util.ArrayList<>());
        g.get(0).add(1); g.get(1).add(0); g.get(2).add(3); g.get(3).add(2); g.get(4).add(4);
        v = new boolean[5]; int c = 0;
        for (int i = 0; i < 5; i++) if (!v[i]) { dfs(i); c++; }
        System.out.println(c);
    }
}
```

### Problem 5 — Clone (E)

```java
class Clone {
    static class N { int v; java.util.List<N> n = new java.util.ArrayList<>(); N(int v) { this.v = v; } }
    static java.util.Map<N, N> m = new java.util.HashMap<>();
    static N clone(N u) {
        if (u == null) return null;
        if (m.containsKey(u)) return m.get(u);
        N c = new N(u.v); m.put(u, c);
        for (N x : u.n) c.n.add(clone(x));
        return c;
    }
    public static void main(String[] args) {
        N a = new N(1); N b = new N(2); N c = new N(3); a.n.add(b); b.n.add(c);
        System.out.println(clone(a).v);
    }
}
```

### Problem 6 — Islands (M)

```java
class Islands {
    static void dfs(char[][] g, int i, int j) {
        if (i<0||j<0||i>=g.length||j>=g[0].length||g[i][j]=='0') return;
        g[i][j] = '0';
        dfs(g,i+1,j); dfs(g,i-1,j); dfs(g,i,j+1); dfs(g,i,j-1);
    }
    public static void main(String[] args) {
        char[][] g = {{'1','1','0','0','0'},{'1','1','0','0','0'},{'0','0','1','0','0'},{'0','0','0','1','1'}};
        int n = g.length, m = g[0].length, c = 0;
        for (int i = 0; i < n; i++) for (int j = 0; j < m; j++) if (g[i][j]=='1') { dfs(g,i,j); c++; }
        System.out.println(c);
    }
}
```

### Problem 7 — MaxArea (M)

```java
class MaxArea {
    static int dfs(char[][] g, int i, int j) {
        if (i<0||j<0||i>=g.length||j>=g[0].length||g[i][j]=='0') return 0;
        g[i][j] = '0';
        return 1 + dfs(g,i+1,j)+dfs(g,i-1,j)+dfs(g,i,j+1)+dfs(g,i,j-1);
    }
    public static void main(String[] args) {
        char[][] g = {{'0','0','1','0','0'},{'0','0','0','0','0'},{'0','0','0','0','1'}};
        int best = 0;
        for (int i = 0; i < g.length; i++) for (int j = 0; j < g[0].length; j++) if (g[i][j]=='1') best = Math.max(best, dfs(g,i,j));
        System.out.println(best);
    }
}
```

### Problem 8 — Surround (M)

```java
class Surround {
    static void dfs(char[][] b, int i, int j) {
        if (i<0||j<0||i>=b.length||j>=b[0].length||b[i][j]!='O') return;
        b[i][j] = '#';
        dfs(b,i+1,j); dfs(b,i-1,j); dfs(b,i,j+1); dfs(b,i,j-1);
    }
    public static void main(String[] args) {
        char[][] b = {{'X','X','X','X'},{'X','O','O','X'},{'X','X','O','X'},{'X','O','X','X'}};
        int m = b.length, n = b[0].length;
        for (int i = 0; i < m; i++) { dfs(b,i,0); dfs(b,i,n-1); }
        for (int j = 0; j < n; j++) { dfs(b,0,j); dfs(b,m-1,j); }
        for (int i = 0; i < m; i++) for (int j = 0; j < n; j++)
            if (b[i][j]=='O') b[i][j]='X'; else if (b[i][j]=='#') b[i][j]='O';
        System.out.println("done");
    }
}
```

### Problem 9 — Course (M)

```java
class Course {
    public static void main(String[] args) {
        int n = 2; int[][] p = {{1,0}};
        java.util.List<java.util.List<Integer>> g = new java.util.ArrayList<>();
        for (int i = 0; i < n; i++) g.add(new java.util.ArrayList<>());
        for (int[] x : p) g.get(x[1]).add(x[0]);
        int[] state = new int[n]; boolean ok = true;
        for (int i = 0; i < n && ok; i++) ok = dfs(g, state, i);
        System.out.println(ok);
    }
    static boolean dfs(java.util.List<java.util.List<Integer>> g, int[] s, int u) {
        if (s[u] == 1) return false; if (s[u] == 2) return true;
        s[u] = 1;
        for (int v : g.get(u)) if (!dfs(g, s, v)) return false;
        s[u] = 2; return true;
    }
}
```

### Problem 10 — Pacific (M)

```java
class Pacific {
    static int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};
    static void dfs(int[][] h, int i, int j, boolean[][] reach) {
        if (reach[i][j]) return; reach[i][j] = true;
        for (int[] d : dirs) {
            int ni = i+d[0], nj = j+d[1];
            if (ni>=0 && nj>=0 && ni<h.length && nj<h[0].length && h[ni][nj] >= h[i][j])
                dfs(h, ni, nj, reach);
        }
    }
    public static void main(String[] args) {
        int[][] h = {{1,2,2,3,5},{3,2,3,4,4},{2,4,5,3,1},{6,7,1,4,5},{5,1,1,2,4}};
        int m = h.length, n = h[0].length;
        boolean[][] pac = new boolean[m][n], atl = new boolean[m][n];
        for (int i = 0; i < m; i++) { dfs(h,i,0,pac); dfs(h,i,n-1,atl); }
        for (int j = 0; j < n; j++) { dfs(h,0,j,pac); dfs(h,m-1,j,atl); }
        java.util.List<int[]> out = new java.util.ArrayList<>();
        for (int i = 0; i < m; i++) for (int j = 0; j < n; j++) if (pac[i][j] && atl[i][j]) out.add(new int[]{i,j});
        System.out.println(out);
    }
}
```

### Problem 11 — WordLadder (H)

```java
class WordLadder {
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

### Problem 12 — SCC (H)

```java
class SCC {
    static int t = 0;
    static void dfs1(java.util.List<java.util.List<Integer>> g, int u, boolean[] v, java.util.Deque<Integer> st) {
        v[u] = true;
        for (int x : g.get(u)) if (!v[x]) dfs1(g, x, v, st);
        st.push(u);
    }
    static void dfs2(java.util.List<java.util.List<Integer>> gr, int u, boolean[] v) {
        v[u] = true; System.out.print(u + " ");
        for (int x : gr.get(u)) if (!v[x]) dfs2(gr, x, v);
    }
    public static void main(String[] args) {
        int n = 5; int[][] e = {{1,0},{0,2},{2,1},{0,3},{3,4}};
        java.util.List<java.util.List<Integer>> g = new java.util.ArrayList<>(), gr = new java.util.ArrayList<>();
        for (int i = 0; i < n; i++) { g.add(new java.util.ArrayList<>()); gr.add(new java.util.ArrayList<>()); }
        for (int[] x : e) { g.get(x[0]).add(x[1]); gr.get(x[1]).add(x[0]); }
        boolean[] v = new boolean[n]; java.util.Deque<Integer> st = new java.util.ArrayDeque<>();
        for (int i = 0; i < n; i++) if (!v[i]) dfs1(g, i, v, st);
        v = new boolean[n];
        while (!st.isEmpty()) {
            int u = st.pop();
            if (!v[u]) { dfs2(gr, u, v); System.out.println(); }
        }
    }
}
```

### Problem 13 — Bridges (H)

```java
class Bridges {
    static int t = 0;
    static void dfs(java.util.List<java.util.List<Integer>> g, int u, int p, int[] disc, int[] low, java.util.List<int[]> res) {
        disc[u] = low[u] = ++t;
        for (int v : g.get(u)) {
            if (v == p) continue;
            if (disc[v] == 0) {
                dfs(g, v, u, disc, low, res);
                low[u] = Math.min(low[u], low[v]);
                if (low[v] > disc[u]) res.add(new int[]{u, v});
            } else low[u] = Math.min(low[u], disc[v]);
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

### Problem 14 — Alien (H)

```java
class Alien {
    public static void main(String[] args) {
        String[] w = {"wrt","wrf","er","ett","rftt"};
        java.util.Map<Character, java.util.Set<Character>> g = new java.util.HashMap<>();
        java.util.Map<Character, Integer> indeg = new java.util.HashMap<>();
        for (String s : w) for (char c : s.toCharArray()) { g.computeIfAbsent(c, k -> new java.util.HashSet<>()); indeg.putIfAbsent(c, 0); }
        for (int i = 0; i < w.length - 1; i++) {
            String a = w[i], b = w[i+1];
            for (int j = 0; j < Math.min(a.length(), b.length()); j++)
                if (a.charAt(j) != b.charAt(j)) {
                    if (g.get(a.charAt(j)).add(b.charAt(j))) indeg.merge(b.charAt(j), 1, Integer::sum);
                    break;
                }
        }
        java.util.Deque<Character> q = new java.util.ArrayDeque<>();
        for (char c : indeg.keySet()) if (indeg.get(c) == 0) q.offer(c);
        StringBuilder sb = new StringBuilder();
        while (!q.isEmpty()) { char u = q.poll(); sb.append(u); for (char v : g.get(u)) indeg.merge(v, -1, Integer::sum); if (indeg.get(v) == 0) q.offer(v); }
        System.out.println(sb.length() == indeg.size() ? sb : "");
    }
}
```

### Problem 15 — Itinerary (H)

```java
class Itinerary {
    public static void main(String[] args) {
        java.util.List<java.util.List<String>> t = java.util.Arrays.asList(java.util.Arrays.asList("MUC","LHR"), java.util.Arrays.asList("JFK","MUC"), java.util.Arrays.asList("SFO","SJC"), java.util.Arrays.asList("LHR","SFO"));
        java.util.Map<String, java.util.PriorityQueue<String>> g = new java.util.HashMap<>();
        for (java.util.List<String> e : t) g.computeIfAbsent(e.get(0), k -> new java.util.PriorityQueue<>()).offer(e.get(1));
        java.util.Deque<String> st = new java.util.ArrayDeque<>();
        dfs("JFK", g, st);
        System.out.println(st);
    }
    static void dfs(String u, java.util.Map<String, java.util.PriorityQueue<String>> g, java.util.Deque<String> st) {
        while (g.containsKey(u) && !g.get(u).isEmpty()) dfs(g.get(u).poll(), g, st);
        st.push(u);
    }
}
```

