# Day 27 — DP Fundamentals

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Identify DP problems (overlapping subproblems + optimal substructure)
- Convert recursion → memoisation → tabulation
- Solve Fibonacci, climbing stairs, house robber, coin change
- Recognise top-down vs bottom-up

---

# 1. Introduction

Dynamic Programming (DP) solves problems by combining solutions to overlapping subproblems. It's essentially "memoised recursion".

---

# 2. Why Do We Need This?

Without DP, many natural recursive solutions are exponential. DP reduces them to polynomial time.

---

# 3. Core Concept — Two Properties

1. **Overlapping subproblems**: same subproblem solved many times.
2. **Optimal substructure**: optimal solution built from optimal sub-solutions.

---

# 4. Real-World Analogy

Like a chef who keeps the same mise en place ready instead of re-preparing it for every dish. Once computed, reuse.

---

# 5. Top-Down vs Bottom-Up

| | Top-Down (memoisation) | Bottom-Up (tabulation) |
|---|---|---|
| Style | Recursion + cache | Loop filling a table |
| Order | As needed | Iterative, base → top |
| Stack | Yes | No |
| Java feel | `Map<Integer,Integer>` | `int[] dp = new int[n+1]` |

---

# 6. Java Implementation — `DpDemo.java`

```java
import java.util.*;

public class DpDemo {

    /** Fibonacci: naive recursion vs memoised. */
    static long fibNaive(int n) {
        if (n < 2) return n;
        return fibNaive(n - 1) + fibNaive(n - 2);
    }
    static long fibMemo(int n, long[] memo) {
        if (n < 2) return n;
        if (memo[n] != 0) return memo[n];
        return memo[n] = fibMemo(n - 1, memo) + fibMemo(n - 2, memo);
    }
    static long fibIter(int n) {
        if (n < 2) return n;
        long a = 0, b = 1;
        for (int i = 2; i <= n; i++) { long c = a + b; a = b; b = c; }
        return b;
    }

    /** Climbing stairs: 1 or 2 steps. */
    static int climbStairs(int n) {
        if (n <= 2) return n;
        int a = 1, b = 2;
        for (int i = 3; i <= n; i++) { int c = a + b; a = b; b = c; }
        return b;
    }

    /** House robber: max sum of non-adjacent. */
    static int rob(int[] a) {
        if (a.length == 0) return 0;
        int prev = 0, cur = 0;
        for (int x : a) { int t = Math.max(cur, prev + x); prev = cur; cur = t; }
        return cur;
    }

    /** Coin change: min coins to make amount. */
    static int coinChange(int[] coins, int amount) {
        int[] dp = new int[amount + 1];
        Arrays.fill(dp, amount + 1);
        dp[0] = 0;
        for (int i = 1; i <= amount; i++)
            for (int c : coins)
                if (c <= i) dp[i] = Math.min(dp[i], dp[i - c] + 1);
        return dp[amount] > amount ? -1 : dp[amount];
    }

    /** Coin change II: count combinations. */
    static int change(int amount, int[] coins) {
        int[] dp = new int[amount + 1]; dp[0] = 1;
        for (int c : coins)
            for (int i = c; i <= amount; i++) dp[i] += dp[i - c];
        return dp[amount];
    }

    public static void main(String[] args) {
        System.out.println("fib(40)         = " + fibMemo(40, new long[41]));
        System.out.println("fibIter(40)     = " + fibIter(40));
        System.out.println("climbStairs(10) = " + climbStairs(10));
        System.out.println("rob([2,7,9,3,1])= " + rob(new int[]{2,7,9,3,1}));
        System.out.println("coinChange 11   = " + coinChange(new int[]{1,2,5}, 11));
        System.out.println("change 5        = " + change(5, new int[]{1,2,5}));
    }
}
```

Walkthrough:

- **fibMemo**: check cache before computing. Top-down.
- **fibIter**: bottom-up with two variables. O(1) space.
- **climbStairs**: classic Fibonacci in disguise.
- **rob**: prev = dp[i-2], cur = dp[i-1]; new = max(cur, prev + a[i]).
- **coinChange**: dp[i] = min(dp[i-c] + 1) for c ≤ i.
- **change**: count combinations; outer loop over coins (so order doesn't matter).

---

# 7. How to Spot a DP Problem

| Signal | Use |
|---|---|
| "Count ways to ..." | DP |
| "Min/max cost to ..." | DP |
| "Is it possible to ..." | DP / BFS |
| Choices at each step | DP |
| Subproblems depend on previous | DP |

If the recursion has repeated subproblems, DP applies.

---

# 8. Common Mistakes

1. **Off-by-one in dp array bounds**.
2. **Wrong base case** (e.g., dp[0] = 1 for counting, but = 0 for min).
3. **Order of loops**: outer/inner choice affects whether order matters (combinations vs permutations).

---

# 9. Interview Questions

### Q1. Top-down vs bottom-up?
Top-down: recursive + memo. Bottom-up: iterative, builds from base.

### Q2. Space optimisation?
Often yes — keep only the last row/col needed.

### Q3. When is DP not applicable?
When subproblems are independent (use divide-and-conquer) or have no optimal substructure.

---

# 10. Practice Problems

## 🟢 Easy

### 1. Fibonacci
Standard.

### 2. Climbing Stairs
Standard.

### 3. Min Cost Climbing Stairs
**Input:** cost[] → min cost to reach top.

### 4. House Robber
Standard.

### 5. Pascal's Triangle
Standard.

## 🟡 Medium

### 6. Coin Change
Standard.

### 7. Coin Change II (combinations)
Standard.

### 8. 0/1 Knapsack
**Input:** weights, values, capacity → max value.

### 9. Unique Paths
**Input:** grid → count paths.

### 10. Decode Ways
**Input:** `s="226"` → **Output:** `3`.

## 🔴 Hard

### 11. Edit Distance
**Input:** `word1, word2` → min ops.

### 12. Longest Common Subsequence
Standard.

### 13. Longest Increasing Subsequence
Standard.

### 14. Matrix Chain Multiplication
Standard.

### 15. Burst Balloons
Standard.

---

# 11. Practice Hints

## Easy
1. `dp[n] = dp[n-1] + dp[n-2]`.
2. Same.
3. Two jumps from each.
4. Track prev/cur.
5. Build row by row.

## Medium
6. Unbounded knapsack.
7. Outer coin loop.
8. 0/1: each item once.
9. `dp[i][j] = dp[i-1][j] + dp[i][j-1]`.
10. Two ways per digit.

## Hard
11. Insert/delete/replace.
12. Match/don't match.
13. Patience sorting or DP.
14. Catalan's recurrence.
15. Interval DP.

---

# 12. Revision Checklist

- [ ] Can memoise recursion
- [ ] Can convert to tabulation
- [ ] Can identify DP problems
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 13. Key Takeaways

- DP = recursion + cache.
- Two properties: overlapping subproblems + optimal substructure.
- Often space-optimisable to O(1) or O(n).

Tomorrow: **DP Patterns**.


## Solutions

### Problem 1 — Fib (E)

```java
class Fib {
    static long[] dp;
    static long fib(int n) { if (n <= 1) return n; if (dp[n] != 0) return dp[n]; return dp[n] = fib(n - 1) + fib(n - 2); }
    public static void main(String[] args) { dp = new long[40]; System.out.println(fib(30)); }
}
```

### Problem 2 — Climb (E)

```java
class Climb {
    public static void main(String[] args) {
        int n = 5; int[] dp = new int[n + 1]; dp[0] = 1;
        for (int i = 1; i <= n; i++) for (int j = 1; j <= 2 && j <= i; j++) dp[i] += dp[i - j];
        System.out.println(dp[n]);
    }
}
```

### Problem 3 — MinCost (E)

```java
class MinCost {
    public static void main(String[] args) {
        int[][] c = {{1,3,1},{1,5,1},{4,2,1}};
        int m = c.length, n = c[0].length;
        int[][] dp = new int[m][n]; dp[0][0] = c[0][0];
        for (int j = 1; j < n; j++) dp[0][j] = dp[0][j-1] + c[0][j];
        for (int i = 1; i < m; i++) for (int j = 0; j < n; j++) {
            dp[i][j] = c[i][j] + Math.min(dp[i-1][j], (j > 0 ? dp[i-1][j-1] : Integer.MAX_VALUE));
            if (j + 1 < n) dp[i][j] = Math.min(dp[i][j], c[i][j] + Math.min(dp[i-1][j], (j > 0 ? dp[i-1][j-1] : Integer.MAX_VALUE)));
            else dp[i][j] = Math.min(dp[i][j], c[i][j] + dp[i-1][j]);
        }
        System.out.println(dp[m-1][n-1]);
    }
}
```

### Problem 4 — Rob (E)

```java
class Rob {
    public static void main(String[] args) {
        int[] a = {2,7,9,3,1};
        int n = a.length;
        if (n == 0) { System.out.println(0); return; }
        if (n == 1) { System.out.println(a[0]); return; }
        int[] dp = new int[n]; dp[0] = a[0]; dp[1] = Math.max(a[0], a[1]);
        for (int i = 2; i < n; i++) dp[i] = Math.max(dp[i-1], dp[i-2] + a[i]);
        System.out.println(dp[n-1]);
    }
}
```

### Problem 5 — Pascal (E)

```java
class Pascal {
    public static void main(String[] args) {
        int n = 5;
        int[][] dp = new int[n][];
        for (int i = 0; i < n; i++) { dp[i] = new int[i+1]; dp[i][0] = dp[i][i] = 1; for (int j = 1; j < i; j++) dp[i][j] = dp[i-1][j-1] + dp[i-1][j]; }
        for (int[] row : dp) System.out.println(java.util.Arrays.toString(row));
    }
}
```

### Problem 6 — CoinChg (M)

```java
class CoinChg {
    public static void main(String[] args) {
        int[] c = {1,2,5}; int a = 11;
        int[] dp = new int[a + 1]; dp[0] = 1;
        for (int x : c) for (int i = x; i <= a; i++) dp[i] += dp[i-x];
        System.out.println(dp[a]);
    }
}
```

### Problem 7 — CoinChg2 (M)

```java
class CoinChg2 {
    public static void main(String[] args) {
        int[] c = {1,2,5}; int a = 11;
        int[] dp = new int[a + 1]; dp[0] = 1;
        for (int i = 1; i <= a; i++) for (int x : c) if (i >= x) dp[i] += dp[i - x];
        System.out.println(dp[a]);
    }
}
```

### Problem 8 — Knap01 (M)

```java
class Knap01 {
    public static void main(String[] args) {
        int[] w = {1,2,3}; int[] v = {6,10,12}; int W = 5;
        int[] dp = new int[W + 1];
        for (int i = 0; i < w.length; i++) for (int j = W; j >= w[i]; j--) dp[j] = Math.max(dp[j], dp[j - w[i]] + v[i]);
        System.out.println(dp[W]);
    }
}
```

### Problem 9 — UniquePaths (M)

```java
class UniquePaths {
    public static void main(String[] args) {
        int m = 3, n = 7;
        int[] dp = new int[n];
        java.util.Arrays.fill(dp, 1);
        for (int i = 1; i < m; i++) for (int j = 1; j < n; j++) dp[j] += dp[j-1];
        System.out.println(dp[n-1]);
    }
}
```

### Problem 10 — DecodeWays (M)

```java
class DecodeWays {
    public static void main(String[] args) {
        String s = "226";
        int n = s.length();
        if (n == 0) { System.out.println(0); return; }
        int[] dp = new int[n + 1]; dp[0] = 1; dp[1] = (s.charAt(0) != '0') ? 1 : 0;
        for (int i = 2; i <= n; i++) {
            if (s.charAt(i-1) != '0') dp[i] += dp[i-1];
            int two = (s.charAt(i-2) - '0') * 10 + (s.charAt(i-1) - '0');
            if (two >= 10 && two <= 26) dp[i] += dp[i-2];
        }
        System.out.println(dp[n]);
    }
}
```

### Problem 11 — Edit2 (H)

```java
class Edit2 {
    public static void main(String[] args) {
        String a = "horse", b = "ros"; int m = a.length(), n = b.length();
        int[] dp = new int[n + 1];
        for (int j = 0; j <= n; j++) dp[j] = j;
        for (int i = 1; i <= m; i++) {
            int[] ndp = new int[n + 1]; ndp[0] = i;
            for (int j = 1; j <= n; j++)
                ndp[j] = a.charAt(i-1) == b.charAt(j-1) ? dp[j-1] : 1 + Math.min(dp[j-1], Math.min(dp[j], ndp[j-1]));
            dp = ndp;
        }
        System.out.println(dp[n]);
    }
}
```

### Problem 12 — LCS2 (H)

```java
class LCS2 {
    public static void main(String[] args) {
        String a = "abcde", b = "ace"; int m = a.length(), n = b.length();
        int[] dp = new int[n + 1];
        for (int i = 1; i <= m; i++) {
            int[] ndp = new int[n + 1];
            for (int j = 1; j <= n; j++) ndp[j] = a.charAt(i-1) == b.charAt(j-1) ? dp[j-1] + 1 : Math.max(dp[j], ndp[j-1]);
            dp = ndp;
        }
        System.out.println(dp[n]);
    }
}
```

### Problem 13 — LIS (H)

```java
class LIS {
    public static void main(String[] args) {
        int[] a = {10,9,2,5,3,7,101,18};
        int n = a.length;
        int[] dp = new int[n];
        int ans = 0;
        for (int i = 0; i < n; i++) { dp[i] = 1; for (int j = 0; j < i; j++) if (a[j] < a[i]) dp[i] = Math.max(dp[i], dp[j] + 1); ans = Math.max(ans, dp[i]); }
        System.out.println(ans);
    }
}
```

### Problem 14 — MatrixChain (H)

```java
class MatrixChain {
    public static void main(String[] args) {
        int[] d = {10,30,5,60}; int n = d.length - 1;
        int[][] dp = new int[n][n];
        for (int len = 2; len <= n; len++) for (int i = 0; i <= n - len; i++) {
            int j = i + len - 1; dp[i][j] = Integer.MAX_VALUE;
            for (int k = i; k < j; k++) dp[i][j] = Math.min(dp[i][j], dp[i][k] + dp[k+1][j] + d[i] * d[k+1] * d[j+1]);
        }
        System.out.println(dp[0][n-1]);
    }
}
```

### Problem 15 — Burst (H)

```java
class Burst {
    public static void main(String[] args) {
        int[] a = {3,1,5,8};
        int n = a.length;
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

