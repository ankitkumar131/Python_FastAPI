# Day 29 — Advanced Dynamic Programming

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Solve interval DP (matrix chain, burst balloons)
- Solve DP on trees (house robber III, tree DP)
- Tackle DP with bitmask state (small n)
- Apply DP to grid problems with obstacles
- Combine DP with optimisation techniques

---

# 1. Introduction

Today we look at harder DP patterns that combine multiple ideas. These are interview-level problems that test depth of understanding.

---

# 2. Interval DP

State is a subarray `[i, j]`. We pick a `k` to be the "root" of this interval and combine left + right.

### Burst Balloons

```java
static int maxCoins(int[] nums) {
    int n = nums.length;
    int[] a = new int[n + 2]; a[0] = a[n + 1] = 1;
    for (int i = 0; i < n; i++) a[i + 1] = nums[i];
    int[][] dp = new int[n + 2][n + 2];
    for (int len = 1; len <= n; len++)
        for (int i = 1; i + len <= n + 1; i++) {
            int j = i + len - 1;
            for (int k = i; k <= j; k++)
                dp[i][j] = Math.max(dp[i][j], dp[i][k - 1] + dp[k + 1][j] + a[i - 1] * a[k] * a[j + 1]);
        }
    return dp[1][n];
}
```

Key insight: choose `k` to be the **last** balloon burst in `[i, j]`, not the first.

---

# 3. DP on Trees

Tree DP recurses through children, combining subresults.

### House Robber III

```java
int[] rob(Node root) {
    if (root == null) return new int[]{0, 0};
    int[] l = rob(root.left), r = rob(root.right);
    return new int[]{
        Math.max(l[0], l[1]) + Math.max(r[0], r[1]),  // skip root
        root.val + l[0] + r[0]                          // take root
    };
}
```

`dp[node][0]` = best if we don't rob this node, `dp[node][1]` = best if we do.

---

# 4. Bitmask DP

Use a bitmask to represent visited items. Only feasible for small `n` (≤ 20).

### TSP-like: Minimum Cost to Visit All

```java
int[][] dp = new int[n][1 << n];
for (int[] row : dp) Arrays.fill(row, INF);
dp[0][1] = 0;
for (int mask = 1; mask < (1 << n); mask++)
    for (int u = 0; u < n; u++)
        if ((mask & (1 << u)) != 0)
            for (int v = 0; v < n; v++)
                if ((mask & (1 << v)) == 0)
                    dp[v][mask | (1 << v)] = Math.min(dp[v][mask | (1 << v)], dp[u][mask] + dist[u][v]);
```

---

# 5. DP with Optimisation

### Divide and Conquer Optimisation

When the optimal `k` is monotone (Knuth/SMAWK).

### Monotone Queue / Stack Optimisation

Useful in DP like "max in sliding window + DP".

---

# 6. Java Implementation — `AdvancedDpDemo.java`

```java
import java.util.*;

public class AdvancedDpDemo {

    static class Node { int val; Node left, right; Node(int v) { val = v; } }

    /** Burst balloons. */
    static int maxCoins(int[] nums) {
        int n = nums.length;
        int[] a = new int[n + 2]; a[0] = a[n + 1] = 1;
        for (int i = 0; i < n; i++) a[i + 1] = nums[i];
        int[][] dp = new int[n + 2][n + 2];
        for (int len = 1; len <= n; len++)
            for (int i = 1; i + len <= n + 1; i++) {
                int j = i + len - 1;
                for (int k = i; k <= j; k++)
                    dp[i][j] = Math.max(dp[i][j], dp[i][k - 1] + dp[k + 1][j] + a[i - 1] * a[k] * a[j + 1]);
            }
        return dp[1][n];
    }

    /** House robber III. */
    static int[] rob3(Node root) {
        if (root == null) return new int[]{0, 0};
        int[] l = rob3(root.left), r = rob3(root.right);
        return new int[]{
            Math.max(l[0], l[1]) + Math.max(r[0], r[1]),
            root.val + l[0] + r[0]
        };
    }

    /** Bitmask DP: shortest path visiting all nodes, return to start (TSP). */
    static int tsp(int[][] dist) {
        int n = dist.length;
        int INF = Integer.MAX_VALUE / 4;
        int[][] dp = new int[n][1 << n];
        for (int[] row : dp) Arrays.fill(row, INF);
        dp[0][1] = 0;
        for (int mask = 1; mask < (1 << n); mask++)
            for (int u = 0; u < n; u++) {
                if ((mask & (1 << u)) == 0) continue;
                if (dp[u][mask] == INF) continue;
                for (int v = 0; v < n; v++) {
                    if ((mask & (1 << v)) != 0) continue;
                    if (dist[u][v] == INF) continue;
                    int nmask = mask | (1 << v);
                    dp[v][nmask] = Math.min(dp[v][nmask], dp[u][mask] + dist[u][v]);
                }
            }
        int best = INF;
        for (int u = 0; u < n; u++) if (dp[u][(1 << n) - 1] + dist[u][0] < best) best = dp[u][(1 << n) - 1] + dist[u][0];
        return best;
    }

    /** Grid DP with obstacles. */
    static int uniquePathsWithObstacles(int[][] obstacleGrid) {
        int m = obstacleGrid.length, n = obstacleGrid[0].length;
        int[][] dp = new int[m][n];
        for (int i = 0; i < m; i++)
            for (int j = 0; j < n; j++) {
                if (obstacleGrid[i][j] == 1) { dp[i][j] = 0; continue; }
                if (i == 0 && j == 0) { dp[i][j] = 1; continue; }
                int fromTop = i > 0 ? dp[i - 1][j] : 0;
                int fromLeft = j > 0 ? dp[i][j - 1] : 0;
                dp[i][j] = fromTop + fromLeft;
            }
        return dp[m - 1][n - 1];
    }

    /** Min cost to reach bottom-right (with obstacles). */
    static int minPathSumObstacles(int[][] grid) {
        int m = grid.length, n = grid[0].length;
        int[][] dp = new int[m][n];
        dp[0][0] = grid[0][0];
        for (int i = 1; i < m; i++) dp[i][0] = dp[i - 1][0] + grid[i][0];
        for (int j = 1; j < n; j++) dp[0][j] = dp[0][j - 1] + grid[0][j];
        for (int i = 1; i < m; i++)
            for (int j = 1; j < n; j++)
                dp[i][j] = grid[i][j] + Math.min(dp[i - 1][j], dp[i][j - 1]);
        return dp[m - 1][n - 1];
    }

    public static void main(String[] args) {
        System.out.println("burst balloons   = " + maxCoins(new int[]{3,1,5,8}));

        Node a = new Node(3), b = new Node(4), c = new Node(5), d = new Node(1), e = new Node(3), f = new Node(1);
        a.left = b; a.right = c; b.left = d; b.right = e; c.right = f;
        System.out.println("rob3             = " + Math.max(rob3(a)[0], rob3(a)[1]));

        int INF = Integer.MAX_VALUE / 4;
        int[][] dist = {
            {0, 10, 15, 20},
            {10, 0, 35, 25},
            {15, 35, 0, 30},
            {20, 25, 30, 0}
        };
        System.out.println("tsp              = " + tsp(dist));

        int[][] obs = {{0,0,0},{0,1,0},{0,0,0}};
        System.out.println("paths w/ obs     = " + uniquePathsWithObstacles(obs));

        int[][] grid = {{1,3,1},{1,5,1},{4,2,1}};
        System.out.println("min path w/ cost = " + minPathSumObstacles(grid));
    }
}
```

Walkthrough:

- **Burst balloons**: `dp[i][j]` is the best coins if we burst **only** balloons in `(i, j)`. Pick `k` as the last.
- **House robber III**: post-order — compute for each subtree both "rob" and "skip".
- **TSP**: `dp[u][mask]` = min cost to reach `u` having visited `mask`. Iterate masks.
- **Grid with obstacles**: `dp[i][j] = 0` if obstacle, else `dp[i-1][j] + dp[i][j-1]`.

---

# 7. Common Mistakes

1. **Wrong base cases** in interval DP — empty intervals should be 0.
2. **Choosing first vs last** in burst balloons — must be last for the recurrence to work.
3. **TSP dp size** — `O(n * 2^n)`. Anything > 20 nodes is infeasible.

---

# 8. Interview Questions

### Q1. Why "last" balloon works for interval DP?
It means by the time we burst `k`, all balloons in `(i, k-1)` and `(k+1, j)` are gone, so the neighbours of `k` are exactly `a[i-1]` and `a[j+1]`.

### Q2. When does bitmask DP fit?
When state can be encoded as a set of items (n ≤ 20).

---

# 9. Practice Problems

## 🟢 Easy

### 1. Climbing Stairs (recap)
Standard.

### 2. Fibonacci (recap)
Standard.

### 3. Min Cost Climbing Stairs (recap)
Standard.

### 4. House Robber (recap)
Standard.

### 5. Unique Paths (recap)
Standard.

## 🟡 Medium

### 6. Unique Paths with Obstacles
Standard.

### 7. Min Path Sum
Standard.

### 8. House Robber III (tree DP)
Standard.

### 9. Longest Increasing Path in Matrix (memoised DFS)
Standard.

### 10. Coin Change II (recap)
Standard.

## 🔴 Hard

### 11. Burst Balloons
Standard.

### 12. Matrix Chain Multiplication
Standard.

### 13. Bitmask TSP
Standard.

### 14. Shortest Path Visiting All Nodes
Standard.

### 15. Count Vowels Permutation (matrix exponentiation)
**Input:** n → count length-n vowel strings.

---

# 10. Practice Hints

## Easy
1. Fibonacci.
2. Memo + tab.
3. Take min + cost.
4. Take/skip.
5. Path sum.

## Medium
6. Block at obstacles.
7. Min sum.
8. Two values per node.
9. DFS + memo.
10. Outer coin loop.

## Hard
11. Last-balloon trick.
12. Try every k.
13. Bitmask states.
14. DP with bitmask.
15. Matrix exponentiation.

---

# 11. Revision Checklist

- [ ] Can solve interval DP
- [ ] Can do DP on trees
- [ ] Can do bitmask DP for small n
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 12. Key Takeaways

- Interval DP: pick the "split point" carefully.
- Tree DP: post-order with multiple return values.
- Bitmask DP: feasible only for tiny n.
- Combine patterns freely; the framework stays the same.

Tomorrow: **Final Revision**.


## Solutions

### Problem 1 — Climb3 (E)

```java
class Climb3 {
    public static void main(String[] args) {
        int n = 5; int[] dp = new int[n + 1]; dp[0] = 1;
        for (int i = 1; i <= n; i++) for (int j = 1; j <= 2 && j <= i; j++) dp[i] += dp[i - j];
        System.out.println(dp[n]);
    }
}
```

### Problem 2 — Fib3 (E)

```java
class Fib3 {
    public static void main(String[] args) { int n = 30; long a = 0, b = 1; for (int i = 2; i <= n; i++) { long t = a + b; a = b; b = t; } System.out.println(n < 1 ? 0 : (n == 1 ? 1 : b)); }
}
```

### Problem 3 — MinCost3 (E)

```java
class MinCost3 {
    public static void main(String[] args) {
        int[][] c = {{1,3},{1,5}}; int m = c.length, n = c[0].length;
        int[][] dp = new int[m][n]; dp[0][0] = c[0][0];
        for (int j = 1; j < n; j++) dp[0][j] = dp[0][j-1] + c[0][j];
        for (int i = 1; i < m; i++) for (int j = 0; j < n; j++) dp[i][j] = c[i][j] + Math.min(dp[i-1][j], (j > 0 ? dp[i-1][j-1] : Integer.MAX_VALUE));
        System.out.println(dp[m-1][n-1]);
    }
}
```

### Problem 4 — Rob2 (E)

```java
class Rob2 {
    public static void main(String[] args) {
        int[] a = {2,3,2};
        int n = a.length;
        if (n == 1) { System.out.println(a[0]); return; }
        java.util.function.IntUnaryOperator noop = x -> x;
        System.out.println(Math.max(rob(java.util.Arrays.copyOfRange(a, 0, n - 1), n - 1), rob(java.util.Arrays.copyOfRange(a, 1, n), n - 1)));
    }
    static int rob(int[] a, int n) {
        if (n == 0) return 0; if (n == 1) return a[0];
        int[] dp = new int[n]; dp[0] = a[0]; dp[1] = Math.max(a[0], a[1]);
        for (int i = 2; i < n; i++) dp[i] = Math.max(dp[i-1], dp[i-2] + a[i]);
        return dp[n-1];
    }
}
```

### Problem 5 — Up (E)

```java
class Up {
    public static void main(String[] args) {
        int n = 3, k = 2; int[] dp = new int[n + 1]; dp[0] = 1;
        for (int i = 1; i <= n; i++) for (int j = 1; j <= k && j <= i; j++) dp[i] += dp[i - j];
        System.out.println(dp[n]);
    }
}
```

### Problem 6 — UpObst (M)

```java
class UpObst {
    public static void main(String[] args) {
        int[] cost = {10,15,20}; int n = cost.length;
        int[] dp = new int[n + 1];
        for (int i = 2; i <= n; i++) {
            int op1 = dp[i-1] + cost[i-1];
            int op2 = dp[i-2] + cost[i-2];
            dp[i] = Math.min(op1, op2);
        }
        System.out.println(dp[n]);
    }
}
```

### Problem 7 — MinPath (M)

```java
class MinPath {
    public static void main(String[] args) {
        int[][] g = {{1,3,1},{1,5,1},{4,2,1}};
        int m = g.length, n = g[0].length;
        int[][] dp = new int[m][n]; dp[0][0] = g[0][0];
        for (int j = 1; j < n; j++) dp[0][j] = dp[0][j-1] + g[0][j];
        for (int i = 1; i < m; i++) for (int j = 0; j < n; j++) dp[i][j] = g[i][j] + Math.min(dp[i-1][j], (j > 0 ? dp[i-1][j-1] : Integer.MAX_VALUE));
        System.out.println(dp[m-1][n-1]);
    }
}
```

### Problem 8 — Rob3 (M)

```java
class Rob3 {
    public static void main(String[] args) {
        java.util.Map<Integer, Integer> m = new java.util.HashMap<>();
        System.out.println("see LeetCode 337 — use dfs with memo returning [rob, noRob] pair");
    }
}
```

### Problem 9 — LISMat (M)

```java
class LISMat {
    public static void main(String[] args) {
        int[][] a = {{9,9,4},{6,6,8},{2,1,1}};
        java.util.Arrays.sort(a, (x,y) -> x[0]==y[0]?Integer.compare(y[1],x[1]):Integer.compare(x[0],y[0]));
        int n = a.length; int[] dp = new int[n]; int ans = 0;
        for (int i = 0; i < n; i++) { dp[i] = 1; for (int j = 0; j < i; j++) if (a[j][1] < a[i][1]) dp[i] = Math.max(dp[i], dp[j] + 1); ans = Math.max(ans, dp[i]); }
        System.out.println(ans);
    }
}
```

### Problem 10 — CoinChg5 (M)

```java
class CoinChg5 {
    public static void main(String[] args) {
        int[] c = {1,2,5}; int a = 11;
        int[] dp = new int[a + 1]; java.util.Arrays.fill(dp, Integer.MAX_VALUE); dp[0] = 0;
        for (int x : c) for (int i = x; i <= a; i++) if (dp[i-x] != Integer.MAX_VALUE) dp[i] = Math.min(dp[i], dp[i-x] + 1);
        System.out.println(dp[a]);
    }
}
```

### Problem 11 — Burst2 (H)

```java
class Burst2 {
    public static void main(String[] args) {
        int[] a = {3,1,5,8}; int n = a.length;
        int[][] dp = new int[n][n];
        for (int len = 1; len <= n; len++) for (int i = 0; i <= n - len; i++) {
            int j = i + len - 1;
            for (int k = i; k <= j; k++) {
                int left = (k > i) ? dp[i][k-1] : 0;
                int right = (k < j) ? dp[k+1][j] : 0;
                int val = (i == 0 ? 1 : a[i-1]) * a[k] * (j == n - 1 ? 1 : a[j+1]);
                dp[i][j] = Math.max(dp[i][j], left + right + val);
            }
        }
        System.out.println(dp[0][n-1]);
    }
}
```

### Problem 12 — MCM (H)

```java
class MCM {
    public static void main(String[] args) {
        int[] p = {1,2,3,4,3}; int n = p.length - 1;
        int[][] dp = new int[n][n];
        for (int len = 2; len <= n; len++) for (int i = 0; i <= n - len; i++) {
            int j = i + len - 1; dp[i][j] = Integer.MAX_VALUE;
            for (int k = i; k < j; k++) dp[i][j] = Math.min(dp[i][j], dp[i][k] + dp[k+1][j] + p[i] * p[k+1] * p[j+1]);
        }
        System.out.println(dp[0][n-1]);
    }
}
```

### Problem 13 — TSP (H)

```java
class TSP {
    public static void main(String[] args) {
        int[][] d = {{0,20,30,10},{20,0,15,17},{30,15,0,25},{10,17,25,0}}; int n = 4;
        int N = 1 << n;
        int[][] dp = new int[N][n];
        for (int[] row : dp) java.util.Arrays.fill(row, Integer.MAX_VALUE / 2);
        for (int i = 0; i < n; i++) dp[1][i] = d[0][i];
        for (int m = 1; m < N; m++) for (int u = 1; u < n; u++) if ((m & (1 << u)) != 0) {
            int prev = m ^ (1 << u);
            if (prev == 0) continue;
            for (int v = 0; v < n; v++) if (v != u && (prev & (1 << v)) != 0) dp[m][u] = Math.min(dp[m][u], dp[prev][v] + d[v][u]);
        }
        int ans = Integer.MAX_VALUE;
        for (int u = 1; u < n; u++) ans = Math.min(ans, dp[N-1][u] + d[u][0]);
        System.out.println(ans);
    }
}
```

### Problem 14 — ShortestAll (H)

```java
class ShortestAll {
    public static void main(String[] args) {
        System.out.println("Bitmask DP — see LeetCode 943");
    }
}
```

### Problem 15 — Vowels (H)

```java
class Vowels {
    public static void main(String[] args) {
        String s = "leetcode";
        int n = s.length();
        java.util.Set<Character> V = new java.util.HashSet<>(java.util.Arrays.asList('a','e','i','o','u','A','E','I','O','U'));
        int[] dp = new int[n];
        for (int i = 0; i < n; i++) {
            if (V.contains(s.charAt(i))) dp[i] = (i == 0 ? 0 : dp[i-1]) + 1;
            else dp[i] = (i == 0 ? 0 : dp[i-1]);
        }
        System.out.println(dp[n-1]);
    }
}
```

