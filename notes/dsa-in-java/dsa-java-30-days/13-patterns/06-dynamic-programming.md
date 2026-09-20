# Pattern 6 — Dynamic Programming

## When to use
- Optimal substructure: solution = best/worst/count of sub-solutions.
- Overlapping subproblems.
- "Count ways", "min cost", "longest/shortest path".

## When NOT to use
- Greedy suffices.
- No overlapping subproblems (just divide and conquer).

## Two approaches

### Top-down (memoisation)

```java
int solve(int i) {
    if (i == 0) return base;
    if (memo.containsKey(i)) return memo.get(i);
    int ans = transition(solve(i-1), ...);
    memo.put(i, ans);
    return ans;
}
```

### Bottom-up (tabulation)

```java
int[] dp = new int[n + 1];
dp[0] = base;
for (int i = 1; i <= n; i++)
    dp[i] = transition(dp[i-1], ...);
```

## Canonical problems by sub-pattern

### 1D DP
- Climbing stairs (Fibo)
- House robber
- Decode ways
- Maximum product subarray
- Word break

### 2D DP
- Unique paths
- Longest common subsequence
- Edit distance
- Minimum path sum
- Distinct subsequences

### Knapsack-style
- 0/1 knapsack (iterate capacity backwards)
- Unbounded knapsack (forward)
- Subset sum
- Partition equal subset sum
- Coin change

### String DP
- Longest palindromic subsequence
- Word break
- Interleaving string
- Regular expression matching

## Knapsack template

```java
// 0/1 knapsack — capacity W, n items
int[] dp = new int[W + 1];
for (int i = 0; i < n; i++)
    for (int w = W; w >= weight[i]; w--)
        dp[w] = Math.max(dp[w], dp[w - weight[i]] + value[i]);
```

## LCS template

```java
int[][] dp = new int[m + 1][n + 1];
for (int i = 1; i <= m; i++)
    for (int j = 1; j <= n; j++)
        if (s.charAt(i-1) == t.charAt(j-1))
            dp[i][j] = dp[i-1][j-1] + 1;
        else
            dp[i][j] = Math.max(dp[i-1][j], dp[i][j-1]);
```

## Complexity
- 1D: O(n) to O(n·k) for k-state.
- 2D: O(m·n).
- Knapsack: O(n·W).

## Java tips
- For `dp[i-1]`, ensure `i > 0` (or `dp[0]` initialised).
- 0/1 knapsack → reverse capacity loop.
- Unbounded knapsack → forward loop.
- Use `long[]` for large answers (paths in 50×50 grid).

## Variations
- Bitmask DP for n ≤ 20.
- Interval DP for "burst balloons", "matrix chain multiplication".
- Tree DP for "house robber III".
