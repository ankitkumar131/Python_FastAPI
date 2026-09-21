# Pattern 9 — Graph

## When to use
- Nodes connected by edges.
- "Shortest path", "cycle", "components", "topological order".

## Representation

```java
// Adjacency list (preferred)
List<List<Integer>> g = new ArrayList<>();
// Adjacency list with weights
List<List<Edge>> g = new ArrayList<>();  // Edge = {int to; long w;}
// Adjacency matrix (only for dense small graphs)
int[][] m;
```

## BFS (shortest path in unweighted)

```java
Deque<Integer> q = new ArrayDeque<>();
int[] dist = new int[n];
Arrays.fill(dist, -1); dist[src] = 0;
q.offer(src);
while (!q.isEmpty()) {
    int u = q.poll();
    for (int v : g.get(u))
        if (dist[v] == -1) { dist[v] = dist[u] + 1; q.offer(v); }
}
```

## DFS (components, cycle detection)

```java
void dfs(int u, int[] state) {
    state[u] = 1; // visiting
    for (int v : g.get(u)) {
        if (state[v] == 0) dfs(v, state);
        else if (state[v] == 1) /* cycle */ ;
    }
    state[u] = 2; // done
}
```

## Topological sort (Kahn)

```java
int[] indeg = new int[n];
// fill
Queue<Integer> q = new ArrayDeque<>();
for (int i = 0; i < n; i++) if (indeg[i] == 0) q.offer(i);
while (!q.isEmpty()) {
    int u = q.poll();
    for (int v : g.get(u)) if (--indeg[v] == 0) q.offer(v);
}
```

## Dijkstra (positive weights)

```java
PriorityQueue<long[]> pq = new PriorityQueue<>((a, b) -> Long.compare(a[0], b[0]));
long[] dist = new long[n]; Arrays.fill(dist, INF); dist[src] = 0;
pq.offer(new long[]{0, src});
while (!pq.isEmpty()) {
    long[] cur = pq.poll();
    if (cur[0] > dist[(int) cur[1]]) continue;
    for (Edge e : g.get((int) cur[1]))
        if (cur[0] + e.w < dist[e.to]) { dist[e.to] = cur[0] + e.w; pq.offer(new long[]{dist[e.to], e.to}); }
}
```

## Union-Find (components)

```java
int find(int x) { return parent[x] == x ? x : (parent[x] = find(parent[x])); }
void union(int a, int b) {
    a = find(a); b = find(b);
    if (a != b) { if (rank[a] < rank[b]) swap(a, b); parent[b] = a; if (rank[a] == rank[b]) rank[a]++; }
}
```

## Canonical problems
- Number of islands (BFS/DFS)
- Course schedule (cycle detection)
- Clone graph (DFS/BFS)
- Pacific Atlantic water flow (DFS)
- Word ladder (BFS)
- Network delay time (Dijkstra)
- Cheapest flights within K stops (Bellman-Ford)
- Redundant connection (Union-Find)
- Minimum spanning tree (Kruskal/Prim)

## Complexity
- BFS/DFS: O(V + E).
- Dijkstra: O((V + E) log V) with heap.
- Bellman-Ford: O(V·E).
- Floyd-Warshall: O(V³).
- Kruskal: O(E log E).

## Java tips
- For grid BFS, encode cell as `r * cols + c`.
- For weighted graph, use `long` distances to avoid overflow.
- Visited `Set<Node>` for clone graph (avoid re-processing).
