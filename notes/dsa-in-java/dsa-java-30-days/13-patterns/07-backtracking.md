# Pattern 7 — Backtracking

## When to use
- "Generate all combinations/permutations/subsets".
- Constraint satisfaction (N-Queens, Sudoku).
- Path-finding with restrictions.

## Core skeleton

```java
void bt(State s) {
    if (complete(s)) { record(s); return; }
    for (Choice c : candidates(s)) {
        if (!valid(c, s)) continue;
        apply(c, s);
        bt(s);
        undo(c, s);
    }
}
```

## Canonical problems
- Subsets
- Permutations
- Combinations
- Combination sum
- N-Queens
- Sudoku solver
- Word search
- Generate parentheses
- Palindrome partitioning

## Templates

### Subsets

```java
void subsets(int[] a, int i, List<Integer> cur, List<List<Integer>> res) {
    if (i == a.length) { res.add(new ArrayList<>(cur)); return; }
    // skip a[i]
    subsets(a, i + 1, cur, res);
    // take a[i]
    cur.add(a[i]);
    subsets(a, i + 1, cur, res);
    cur.remove(cur.size() - 1);
}
```

### Permutations

```java
void perm(int[] a, List<Integer> cur, boolean[] used, List<List<Integer>> res) {
    if (cur.size() == a.length) { res.add(new ArrayList<>(cur)); return; }
    for (int i = 0; i < a.length; i++) {
        if (used[i]) continue;
        used[i] = true;
        cur.add(a[i]);
        perm(a, cur, used, res);
        used[i] = false;
        cur.remove(cur.size() - 1);
    }
}
```

### Combination sum

```java
void cs(int[] a, int target, int start, List<Integer> cur, List<List<Integer>> res) {
    if (target == 0) { res.add(new ArrayList<>(cur)); return; }
    for (int i = start; i < a.length; i++) {
        if (a[i] > target) break;
        cur.add(a[i]);
        cs(a, target - a[i], i, cur, res);  // i, not i+1, for reuse
        cur.remove(cur.size() - 1);
    }
}
```

## Complexity
- Subsets: O(2ⁿ · n).
- Permutations: O(n! · n).
- Combinations: O(C(n,k) · k).

## Java tips
- Always `new ArrayList<>(cur)` when adding to result (snapshot).
- Use `boolean[] used` for permutations; `start` index for combinations.
- Prune early: sort input + check `a[i] > remaining`.
- For Sudoku: validity check inline; recursive return on success.

## Variations
- Pruning by constraint.
- Memoisation: "Word break II".
- Branch and bound for optimisation.
