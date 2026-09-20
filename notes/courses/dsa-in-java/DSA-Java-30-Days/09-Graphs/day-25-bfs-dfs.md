# Day 25 — BFS & DFS (Deep)

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Iterate DFS cleanly (both recursive and stack versions)
- Solve number of islands, flood fill, bipartiteness
- Apply BFS for shortest path in a grid
- Distinguish cycle detection in directed vs undirected graphs
- Solve grid traversal problems

---

# 1. Introduction

Yesterday we covered graph fundamentals. Today we go deeper on two workhorse algorithms: BFS for shortest paths and components, DFS for cycle detection and backtracking.

---

# 2. Cycle Detection

### Undirected

```java
boolean hasCycleUndirected(Graph g) {
    boolean[] vis = new boolean[g.n];
    for (int i = 0; i < g.n; i++) if (!vis[i] && dfsCycle(g, i, -1, vis)) return true;
    return false;
}
boolean dfsCycle(Graph g, int u, int parent, boolean[] vis) {
    vis[u] = true;
    for (int v : g.adj.get(u)) {
        if (!vis[v]) { if (dfsCycle(g, v, u, vis)) return true; }
        else if (v != parent) return true;
    }
    return false;
}
```

### Directed (white/grey/black)

```java
boolean hasCycleDirected(Graph g) {
    int[] state = new int[g.n]; // 0 white, 1 grey, 2 black
    for (int i = 0; i < g.n; i++) if (state[i] == 0 && dfsDC(g, i, state)) return true;
    return false;
}
boolean dfsDC(Graph g, int u, int[] state) {
    state[u] = 1;
    for (int v : g.adj.get(u)) {
        if (state[v] == 1) return true;
        if (state[v] == 0 && dfsDC(g, v, state)) return true;
    }
    state[u] = 2;
    return false;
}
```

---

# 3. Bipartite Check

A graph is bipartite iff it has no odd cycle. BFS-color:

```java
boolean isBipartite(Graph g) {
    int[] color = new int[g.n];
    Arrays.fill(color, -1);
    for (int s = 0; s < g.n; s++) {
        if (color[s] != -1) continue;
        color[s] = 0;
        Deque<Integer> q = new ArrayDeque<>(); q.offer(s);
        while (!q.isEmpty()) {
            int u = q.poll();
            for (int v : g.adj.get(u)) {
                if (color[v] == -1) { color[v] = 1 - color[u]; q.offer(v); }
                else if (color[v] == color[u]) return false;
            }
        }
    }
    return true;
}
```

---

# 4. Grid Traversal

For an `m × n` grid, treat each cell as a node. Neighbours: 4-direction (`{−1,0},{1,0},{0,−1},{0,1}`) or 8-direction (diagonals).

---

# 5. Java Implementation — `BfsDfsDeepDemo.java`

```java
import java.util.*;

public class BfsDfsDeepDemo {

    static class Graph {
        int n; List<List<Integer>> adj;
        Graph(int n) { this.n = n; this.adj = new ArrayList<>(); for (int i = 0; i < n; i++) adj.add(new ArrayList<>()); }
        void addEdge(int u, int v) { adj.get(u).add(v); adj.get(v).add(u); }
        void addDir(int u, int v) { adj.get(u).add(v); }
    }

    /** Undirected cycle detection. */
    static boolean undirectedCycle(Graph g) {
        boolean[] vis = new boolean[g.n];
        for (int i = 0; i < g.n; i++) if (!vis[i] && ucDfs(g, i, -1, vis)) return true;
        return false;
    }
    static boolean ucDfs(Graph g, int u, int parent, boolean[] vis) {
        vis[u] = true;
        for (int v : g.adj.get(u)) {
            if (!vis[v]) { if (ucDfs(g, v, u, vis)) return true; }
            else if (v != parent) return true;
        }
        return false;
    }

    /** Directed cycle detection. */
    static boolean directedCycle(Graph g) {
        int[] state = new int[g.n];
        for (int i = 0; i < g.n; i++) if (state[i] == 0 && dcDfs(g, i, state)) return true;
        return false;
    }
    static boolean dcDfs(Graph g, int u, int[] state) {
        state[u] = 1;
        for (int v : g.adj.get(u)) {
            if (state[v] == 1) return true;
            if (state[v] == 0 && dcDfs(g, v, state)) return true;
        }
        state[u] = 2;
        return false;
    }

    /** Bipartite check. */
    static boolean isBipartite(Graph g) {
        int[] c = new int[g.n];
        Arrays.fill(c, -1);
        for (int s = 0; s < g.n; s++) {
            if (c[s] != -1) continue;
            c[s] = 0;
            Deque<Integer> q = new ArrayDeque<>(); q.offer(s);
            while (!q.isEmpty()) {
                int u = q.poll();
                for (int v : g.adj.get(u)) {
                    if (c[v] == -1) { c[v] = 1 - c[u]; q.offer(v); }
                    else if (c[v] == c[u]) return false;
                }
            }
        }
        return true;
    }

    /** Number of islands. */
    static int numIslands(char[][] g) {
        int c = 0;
        for (int i = 0; i < g.length; i++) for (int j = 0; j < g[0].length; j++)
            if (g[i][j] == '1') { flood(g, i, j); c++; }
        return c;
    }
    static void flood(char[][] g, int i, int j) {
        if (i < 0 || j < 0 || i >= g.length || j >= g[0].length || g[i][j] != '1') return;
        g[i][j] = '0';
        flood(g, i + 1, j); flood(g, i - 1, j); flood(g, i, j + 1); flood(g, i, j - 1);
    }

    /** Flood fill. */
    static int[][] floodFill(int[][] image, int sr, int sc, int color) {
        int orig = image[sr][sc];
        if (orig == color) return image;
        ff(image, sr, sc, orig, color);
        return image;
    }
    static void ff(int[][] g, int i, int j, int orig, int color) {
        if (i < 0 || j < 0 || i >= g.length || j >= g[0].length || g[i][j] != orig) return;
        g[i][j] = color;
        ff(g, i + 1, j, orig, color); ff(g, i - 1, j, orig, color);
        ff(g, i, j + 1, orig, color); ff(g, i, j - 1, orig, color);
    }

    /** Shortest path in grid. */
    static int shortestGridPath(int[][] g, int[] src, int[] dst) {
        int m = g.length, n = g[0].length;
        boolean[][] vis = new boolean[m][n];
        Deque<int[]> q = new ArrayDeque<>(); q.offer(src); vis[src[0]][src[1]] = true;
        int steps = 0;
        int[][] d = {{-1,0},{1,0},{0,-1},{0,1}};
        while (!q.isEmpty()) {
            for (int sz = q.size(); sz > 0; sz--) {
                int[] p = q.poll();
                if (p[0] == dst[0] && p[1] == dst[1]) return steps;
                for (int[] dd : d) {
                    int ni = p[0] + dd[0], nj = p[1] + dd[1];
                    if (ni >= 0 && nj >= 0 && ni < m && nj < n && !vis[ni][nj] && g[ni][nj] == 0) {
                        vis[ni][nj] = true; q.offer(new int[]{ni, nj});
                    }
                }
            }
            steps++;
        }
        return -1;
    }

    public static void main(String[] args) {
        Graph ug = new Graph(5);
        ug.addEdge(0, 1); ug.addEdge(1, 2); ug.addEdge(2, 0);
        System.out.println("undirected cycle = " + undirectedCycle(ug));

        Graph dg = new Graph(4);
        dg.addDir(0, 1); dg.addDir(1, 2); dg.addDir(2, 0);
        System.out.println("directed cycle   = " + directedCycle(dg));

        Graph bg = new Graph(4);
        bg.addEdge(0, 1); bg.addEdge(1, 2); bg.addEdge(2, 3); bg.addEdge(3, 0);
        System.out.println("bipartite        = " + isBipartite(bg));

        char[][] g = {{'1','1','0','0','0'},{'1','1','0','0','0'},{'0','0','1','0','0'},{'0','0','0','1','1'}};
        System.out.println("islands          = " + numIslands(g));

        int[][] img = {{1,1,1},{1,1,0},{1,0,1}};
        int[][] filled = floodFill(img, 1, 1, 2);
        System.out.print("floodFill        = ");
        for (int[] row : filled) System.out.print(Arrays.toString(row) + " ");
        System.out.println();

        int[][] grid = {{0,0,0},{0,1,0},{0,0,0}};
        System.out.println("shortest path    = " + shortestGridPath(grid, new int[]{0,0}, new int[]{2,2}));
    }
}
```

Walkthrough:

- **Undirected cycle**: when DFS sees a visited neighbour that isn't the parent, there's a cycle.
- **Directed cycle**: use 0/1/2 (white/grey/black). Back-edge to a grey node = cycle.
- **Bipartite**: 2-coloring. Conflict on equal colours = not bipartite.
- **Islands / flood fill**: classic grid DFS.
- **Shortest grid path**: BFS by levels.

---

# 6. Common Mistakes

1. **Mixing directed and undirected cycle checks**.
2. **Forgetting to mark visited** in flood fill.
3. **BFS without levels** — `steps++` after each layer, not per node.

---

# 7. Interview Questions

### Q1. Bipartite = 2-colourable?
Yes. A graph is bipartite iff it has no odd-length cycle.

### Q2. Why is BFS shortest path in unweighted?
First time we reach a node in BFS is via the shortest path.

---

# 8. Practice Problems

## 🟢 Easy

### 1. Flood Fill
**Input:** image, sr, sc, color → filled image.

### 2. Number of Islands
Standard.

### 3. Find if Path Exists in Graph
Standard.

### 4. Maximum Depth of N-ary Tree (BFS)
Standard.

### 5. Same Tree (recap)
Standard.

## 🟡 Medium

### 6. Rotting Oranges
Standard.

### 7. Walls and Gates
Standard.

### 8. Cycle Detection (Undirected)
Standard.

### 9. Cycle Detection (Directed)
Standard.

### 10. 01 Matrix (BFS from 0s)
**Input:** binary matrix → dist to nearest 0.

## 🔴 Hard

### 11. Bipartite Check
Standard.

### 12. Shortest Path in Grid with Obstacles
Standard.

### 13. Word Ladder (re-impl)
Standard.

### 14. Reachable Nodes in Subdivided Graph
Standard.

### 15. Bus Routes
**Input:** routes → min buses to reach target.

---

# 9. Practice Hints

## Easy
1. DFS flood.
2. Grid DFS.
3. BFS existence.
4. BFS level order.
5. Recursion.

## Medium
6. Multi-source BFS.
7. Multi-source BFS.
8. DFS with parent.
9. DFS with state.
10. BFS from each 0.

## Hard
11. 2-colour.
12. BFS with turns.
13. BFS over words.
14. Modified BFS.
15. BFS on bus lines.

---

# 10. Revision Checklist

- [ ] Can detect cycles in both kinds of graph
- [ ] Can check bipartiteness
- [ ] Can solve grid BFS/DFS
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 11. Key Takeaways

- Cycle: undirected uses parent; directed uses 3-state colouring.
- Bipartite: 2-colour check.
- BFS gives shortest path in unweighted.

Tomorrow: **Shortest Paths & Advanced Graphs**.


## Solutions

### Problem 1 — FloodFill (E)

```java
class FloodFill {
    static void ff(int[][] img, int i, int j, int nc, int oc) {
        if (i<0||j<0||i>=img.length||j>=img[0].length||img[i][j]!=oc) return;
        img[i][j] = nc;
        ff(img,i+1,j,nc,oc); ff(img,i-1,j,nc,oc); ff(img,i,j+1,nc,oc); ff(img,i,j-1,nc,oc);
    }
    public static void main(String[] args) {
        int[][] img = {{1,1,1},{1,1,0},{1,0,1}};
        ff(img, 1, 1, 2, 1);
        System.out.println("done");
    }
}
```

### Problem 2 — Islands2 (E)

```java
class Islands2 {
    static void dfs(char[][] g, int i, int j) {
        if (i<0||j<0||i>=g.length||j>=g[0].length||g[i][j]=='0') return;
        g[i][j]='0';
        dfs(g,i+1,j); dfs(g,i-1,j); dfs(g,i,j+1); dfs(g,i,j-1);
    }
    public static void main(String[] args) {
        char[][] g = {{'1','1','0'}};
        int c = 0;
        for (int i = 0; i < g.length; i++) for (int j = 0; j < g[0].length; j++) if (g[i][j]=='1') { dfs(g,i,j); c++; }
        System.out.println(c);
    }
}
```

### Problem 3 — PathExists2 (E)

```java
class PathExists2 {
    public static void main(String[] args) {
        int n = 3; int[][] e = {{0,1},{1,2},{2,0}};
        java.util.Set<Integer>[] g = new java.util.HashSet[n];
        for (int i = 0; i < n; i++) g[i] = new java.util.HashSet<>();
        for (int[] x : e) { g[x[0]].add(x[1]); g[x[1]].add(x[0]); }
        int src = 0, dst = 2; boolean[] v = new boolean[n];
        java.util.Deque<Integer> q = new java.util.ArrayDeque<>(); q.offer(src); v[src] = true;
        while (!q.isEmpty()) { int u = q.poll(); if (u == dst) { System.out.println(true); return; } for (int x : g[u]) if (!v[x]) { v[x] = true; q.offer(x); } }
        System.out.println(false);
    }
}
```

### Problem 4 — Nary (E)

```java
class Nary {
    static class N { int v; java.util.List<N> c = new java.util.ArrayList<>(); N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N root = new N(1); N c2 = new N(3); N c3 = new N(2); N c4 = new N(4);
        root.c.add(c2); root.c.add(c3); root.c.add(c4); c3.c.add(new N(5)); c3.c.add(new N(6));
        java.util.Deque<N> q = new java.util.ArrayDeque<>(); q.offer(root);
        int depth = 0;
        while (!q.isEmpty()) { int sz = q.size(); for (int i = 0; i < sz; i++) { N u = q.poll(); for (N x : u.c) q.offer(x); } depth++; }
        System.out.println(depth);
    }
}
```

### Problem 5 — Same2 (E)

```java
class Same2 {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static boolean eq(N a, N b) { if (a==null&&b==null) return true; if (a==null||b==null) return false; return a.v==b.v && eq(a.l,b.l) && eq(a.r,b.r); }
    public static void main(String[] args) {
        N a = new N(1); a.l = new N(2);
        N b = new N(1); b.l = new N(2);
        System.out.println(eq(a, b));
    }
}
```

### Problem 6 — Rotting2 (M)

```java
class Rotting2 {
    public static void main(String[] args) {
        int[][] g = {{2,1,1},{1,1,0},{0,1,1}};
        int m = g.length, n = g[0].length, t = 0;
        java.util.Deque<int[]> q = new java.util.ArrayDeque<>();
        for (int i = 0; i < m; i++) for (int j = 0; j < n; j++) if (g[i][j]==2) q.offer(new int[]{i,j});
        int[][] d = {{1,0},{-1,0},{0,1},{0,-1}};
        while (!q.isEmpty()) {
            int sz = q.size(); boolean any = false;
            for (int k = 0; k < sz; k++) {
                int[] u = q.poll();
                for (int[] dd : d) {
                    int ni = u[0]+dd[0], nj = u[1]+dd[1];
                    if (ni>=0 && nj>=0 && ni<m && nj<n && g[ni][nj]==1) { g[ni][nj]=2; q.offer(new int[]{ni,nj}); any = true; }
                }
            }
            if (any) t++;
        }
        System.out.println(t);
    }
}
```

### Problem 7 — WallsGates (M)

```java
class WallsGates {
    static int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};
    public static void main(String[] args) {
        int INF = Integer.MAX_VALUE;
        int[][] rooms = {{INF,-1,0,INF},{INF,INF,INF,-1},{INF,-1,INF,-1},{0,-1,INF,INF}};
        int m = rooms.length, n = rooms[0].length;
        java.util.Deque<int[]> q = new java.util.ArrayDeque<>();
        for (int i = 0; i < m; i++) for (int j = 0; j < n; j++) if (rooms[i][j] == 0) q.offer(new int[]{i,j});
        while (!q.isEmpty()) {
            int[] u = q.poll();
            for (int[] d : dirs) {
                int ni = u[0]+d[0], nj = u[1]+d[1];
                if (ni>=0 && nj>=0 && ni<m && nj<n && rooms[ni][nj] == INF) {
                    rooms[ni][nj] = rooms[u[0]][u[1]] + 1; q.offer(new int[]{ni,nj});
                }
            }
        }
        System.out.println("done");
    }
}
```

### Problem 8 — CycleU (M)

```java
class CycleU {
    public static void main(String[] args) {
        int n = 4; int[][] e = {{0,1},{1,2},{2,0},{2,3}};
        java.util.List<java.util.List<Integer>> g = new java.util.ArrayList<>();
        for (int i = 0; i < n; i++) g.add(new java.util.ArrayList<>());
        for (int[] x : e) { g.get(x[0]).add(x[1]); g.get(x[1]).add(x[0]); }
        int[] parent = new int[n]; java.util.Arrays.fill(parent, -1);
        boolean cycle = false;
        for (int i = 0; i < n && !cycle; i++) {
            boolean[] v = new boolean[n];
            java.util.Deque<Integer> q = new java.util.ArrayDeque<>(); q.offer(i); v[i] = true;
            while (!q.isEmpty() && !cycle) {
                int u = q.poll();
                for (int x : g.get(u)) {
                    if (!v[x]) { v[x] = true; parent[x] = u; q.offer(x); }
                    else if (parent[u] != x) cycle = true;
                }
            }
        }
        System.out.println(cycle);
    }
}
```

### Problem 9 — CycleD (M)

```java
class CycleD {
    public static void main(String[] args) {
        int n = 3; int[][] e = {{0,1},{1,2},{2,0}};
        java.util.List<java.util.List<Integer>> g = new java.util.ArrayList<>();
        for (int i = 0; i < n; i++) g.add(new java.util.ArrayList<>());
        for (int[] x : e) g.get(x[0]).add(x[1]);
        int[] s = new int[n]; boolean has = false;
        for (int i = 0; i < n && !has; i++) {
            if (s[i] == 0) {
                java.util.Deque<int[]> st = new java.util.ArrayDeque<>();
                st.push(new int[]{i, 0});
                s[i] = 1;
                while (!st.isEmpty() && !has) {
                    int[] top = st.peek();
                    if (top[1] < g.get(top[0]).size()) {
                        int v = g.get(top[0]).get(top[1]++);
                        if (s[v] == 1) has = true;
                        else if (s[v] == 0) { s[v] = 1; st.push(new int[]{v, 0}); }
                    } else { s[top[0]] = 2; st.pop(); }
                }
            }
        }
        System.out.println(has);
    }
}
```

### Problem 10 — M01 (M)

```java
class M01 {
    static int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};
    public static void main(String[] args) {
        int[][] m = {{0,0,0},{0,1,0},{0,0,0}};
        int r = m.length, c = m[0].length;
        java.util.Deque<int[]> q = new java.util.ArrayDeque<>();
        for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) if (m[i][j] == 0) q.offer(new int[]{i,j});
        while (!q.isEmpty()) {
            int[] u = q.poll();
            for (int[] d : dirs) {
                int ni = u[0]+d[0], nj = u[1]+d[1];
                if (ni>=0 && nj>=0 && ni<r && nj<c && m[ni][nj] == 1) {
                    m[ni][nj] = m[u[0]][u[1]] + 1; q.offer(new int[]{ni,nj});
                }
            }
        }
        System.out.println("done");
    }
}
```

### Problem 11 — Bipartite (H)

```java
class Bipartite {
    public static void main(String[] args) {
        int n = 4; int[][] e = {{1,2},{1,3},{2,4},{3,4}};
        java.util.List<java.util.List<Integer>> g = new java.util.ArrayList<>();
        for (int i = 0; i <= n; i++) g.add(new java.util.ArrayList<>());
        for (int[] x : e) { g.get(x[0]).add(x[1]); g.get(x[1]).add(x[0]); }
        int[] color = new int[n + 1]; java.util.Arrays.fill(color, -1);
        boolean bip = true;
        for (int i = 1; i <= n && bip; i++) {
            if (color[i] != -1) continue;
            color[i] = 0; java.util.Deque<Integer> q = new java.util.ArrayDeque<>(); q.offer(i);
            while (!q.isEmpty() && bip) {
                int u = q.poll();
                for (int v : g.get(u)) {
                    if (color[v] == -1) { color[v] = 1 - color[u]; q.offer(v); }
                    else if (color[v] == color[u]) bip = false;
                }
            }
        }
        System.out.println(bip);
    }
}
```

### Problem 12 — ShortObst (H)

```java
class ShortObst {
    public static void main(String[] args) {
        int[][] g = {{0,0,0},{1,1,0},{0,0,0},{0,1,1},{0,0,0}};
        int m = g.length, n = g[0].length;
        int[][] dirs = {{1,0},{-1,0},{0,1},{0,-1}};
        int[][] dist = new int[m][n]; for (int[] row : dist) java.util.Arrays.fill(row, -1);
        java.util.Deque<int[]> q = new java.util.ArrayDeque<>(); q.offer(new int[]{0,0}); dist[0][0] = 0;
        while (!q.isEmpty()) {
            int[] u = q.poll();
            if (u[0] == m - 1 && u[1] == n - 1) { System.out.println(dist[u[0]][u[1]]); return; }
            for (int[] d : dirs) {
                int ni = u[0]+d[0], nj = u[1]+d[1];
                if (ni>=0 && nj>=0 && ni<m && nj<n && g[ni][nj] == 0 && dist[ni][nj] == -1) {
                    dist[ni][nj] = dist[u[0]][u[1]] + 1; q.offer(new int[]{ni,nj});
                }
            }
        }
        System.out.println(-1);
    }
}
```

### Problem 13 — WordL2 (H)

```java
class WordL2 {
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

### Problem 14 — Subdivided (H)

```java
class Subdivided {
    static int target;
    static java.util.Map<Integer, java.util.List<int[]>> graph;
    static double[] ratios;
    static double dfs(int u, double p) {
        if (u == target) return p;
        if (!graph.containsKey(u)) return -1;
        double best = -1;
        for (int[] e : graph.get(u)) {
            double r = dfs(e[0], p * ratios[e[1]]);
            if (r > best) best = r;
        }
        return best;
    }
    public static void main(String[] args) {
        int[][] equations = {{0,1},{1,2},{1,3}}; double[] values = {1.0,2.0,3.0};
        target = 0;
        graph = new java.util.HashMap<>();
        ratios = values;
        for (int i = 0; i < equations.length; i++) {
            graph.computeIfAbsent(equations[i][0], k -> new java.util.ArrayList<>()).add(new int[]{equations[i][1], i});
            graph.computeIfAbsent(equations[i][1], k -> new java.util.ArrayList<>()).add(new int[]{equations[i][0], i});
        }
        System.out.println(dfs(1, 1.0));
    }
}
```

### Problem 15 — BusRoutes (H)

```java
class BusRoutes {
    public static void main(String[] args) {
        int[][] routes = {{1,2,7},{3,6,7}};
        int src = 1, target = 6;
        java.util.Map<Integer, java.util.List<Integer>> stopToRoutes = new java.util.HashMap<>();
        for (int i = 0; i < routes.length; i++) for (int s : routes[i]) stopToRoutes.computeIfAbsent(s, k -> new java.util.ArrayList<>()).add(i);
        java.util.Deque<Integer> q = new java.util.ArrayDeque<>();
        java.util.Set<Integer> visited = new java.util.HashSet<>();
        q.offer(src); int steps = 0;
        while (!q.isEmpty()) {
            int sz = q.size();
            for (int i = 0; i < sz; i++) {
                int stop = q.poll();
                if (stop == target) { System.out.println(steps); return; }
                for (int r : stopToRoutes.getOrDefault(stop, java.util.Collections.emptyList()))
                    if (visited.add(r))
                        for (int s : routes[r]) q.offer(s);
            }
            steps++;
        }
        System.out.println(-1);
    }
}
```

