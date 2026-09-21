# Day 23 — Backtracking

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Recognise backtracking problems (decision tree + prune)
- Apply the choose-explore-undo pattern
- Generate subsets, permutations, combinations
- Solve N-Queens, Sudoku, rat-in-maze, word search

---

# 1. Introduction

Backtracking = recursion + pruning. You build a solution incrementally; whenever a partial choice can't lead to a valid answer, you "undo" and try another.

---

# 2. Why Do We Need This?

Many problems require enumerating all valid configurations:

- Subsets, permutations, combinations
- N-Queens, Sudoku
- Word search, maze paths

Brute force is exponential; pruning makes it tractable.

---

# 3. Core Concept — The Template

```java
void backtrack(state, choices):
    if state is complete:
        record answer
        return
    for each choice in choices:
        if choice is valid:
            make choice      // choose
            backtrack(state, choices) // explore
            undo choice      // undo
```

---

# 4. Real-World Analogy

Solving a maze: at each intersection, try one path. If you hit a dead end, back up to the last intersection and try another.

---

# 5. Java Implementation — `BacktrackingDemo.java`

```java
import java.util.*;

public class BacktrackingDemo {

    /** Subsets. */
    static List<List<Integer>> subsets(int[] a) {
        List<List<Integer>> out = new ArrayList<>();
        back(a, 0, new ArrayList<>(), out);
        return out;
    }
    static void back(int[] a, int i, List<Integer> cur, List<List<Integer>> out) {
        out.add(new ArrayList<>(cur));
        for (int j = i; j < a.length; j++) {
            cur.add(a[j]);
            back(a, j + 1, cur, out);
            cur.remove(cur.size() - 1);
        }
    }

    /** Permutations. */
    static List<List<Integer>> permutations(int[] a) {
        List<List<Integer>> out = new ArrayList<>();
        boolean[] used = new boolean[a.length];
        perm(a, new ArrayList<>(), used, out);
        return out;
    }
    static void perm(int[] a, List<Integer> cur, boolean[] used, List<List<Integer>> out) {
        if (cur.size() == a.length) { out.add(new ArrayList<>(cur)); return; }
        for (int i = 0; i < a.length; i++) {
            if (used[i]) continue;
            used[i] = true; cur.add(a[i]);
            perm(a, cur, used, out);
            used[i] = false; cur.remove(cur.size() - 1);
        }
    }

    /** Combination sum. */
    static List<List<Integer>> combinationSum(int[] a, int target) {
        Arrays.sort(a);
        List<List<Integer>> out = new ArrayList<>();
        cs(a, target, 0, new ArrayList<>(), out);
        return out;
    }
    static void cs(int[] a, int rem, int start, List<Integer> cur, List<List<Integer>> out) {
        if (rem == 0) { out.add(new ArrayList<>(cur)); return; }
        for (int i = start; i < a.length; i++) {
            if (a[i] > rem) break;
            cur.add(a[i]);
            cs(a, rem - a[i], i, cur, out);
            cur.remove(cur.size() - 1);
        }
    }

    /** N-Queens. */
    static List<List<String>> nQueens(int n) {
        List<List<String>> out = new ArrayList<>();
        char[][] board = new char[n][n];
        for (char[] row : board) Arrays.fill(row, '.');
        solve(board, 0, out);
        return out;
    }
    static void solve(char[][] b, int row, List<List<String>> out) {
        if (row == b.length) {
            List<String> snap = new ArrayList<>();
            for (char[] r : b) snap.add(new String(r));
            out.add(snap);
            return;
        }
        for (int c = 0; c < b.length; c++) {
            if (isSafe(b, row, c)) {
                b[row][c] = 'Q';
                solve(b, row + 1, out);
                b[row][c] = '.';
            }
        }
    }
    static boolean isSafe(char[][] b, int r, int c) {
        for (int i = 0; i < r; i++) if (b[i][c] == 'Q') return false;
        for (int i = r - 1, j = c - 1; i >= 0 && j >= 0; i--, j--) if (b[i][j] == 'Q') return false;
        for (int i = r - 1, j = c + 1; i >= 0 && j < b.length; i--, j++) if (b[i][j] == 'Q') return false;
        return true;
    }

    /** Word search. */
    static boolean wordSearch(char[][] b, String word) {
        for (int r = 0; r < b.length; r++)
            for (int c = 0; c < b[0].length; c++)
                if (dfs(b, word, r, c, 0)) return true;
        return false;
    }
    static boolean dfs(char[][] b, String w, int r, int c, int idx) {
        if (idx == w.length()) return true;
        if (r < 0 || c < 0 || r >= b.length || c >= b[0].length || b[r][c] != w.charAt(idx)) return false;
        char tmp = b[r][c]; b[r][c] = '#';
        boolean ok = dfs(b, w, r + 1, c, idx + 1) || dfs(b, w, r - 1, c, idx + 1)
                  || dfs(b, w, r, c + 1, idx + 1) || dfs(b, w, r, c - 1, idx + 1);
        b[r][c] = tmp;
        return ok;
    }

    /** Rat in a maze. */
    static List<String> ratInMaze(int[][] m) {
        List<String> out = new ArrayList<>();
        int n = m.length;
        boolean[][] vis = new boolean[n][n];
        if (m[0][0] == 0 || m[n - 1][n - 1] == 0) return out;
        mazeHelper(m, n, 0, 0, vis, "", out);
        Collections.sort(out);
        return out;
    }
    static void mazeHelper(int[][] m, int n, int r, int c, boolean[][] vis, String path, List<String> out) {
        if (r < 0 || c < 0 || r >= n || c >= n || m[r][c] == 0 || vis[r][c]) return;
        if (r == n - 1 && c == n - 1) { out.add(path); return; }
        vis[r][c] = true;
        mazeHelper(m, n, r + 1, c, vis, path + "D", out);
        mazeHelper(m, n, r, c - 1, vis, path + "L", out);
        mazeHelper(m, n, r, c + 1, vis, path + "R", out);
        mazeHelper(m, n, r - 1, c, vis, path + "U", out);
        vis[r][c] = false;
    }

    public static void main(String[] args) {
        System.out.println("subsets([1,2,3])     = " + subsets(new int[]{1,2,3}));
        System.out.println("perms([1,2,3])       = " + permutations(new int[]{1,2,3}));
        System.out.println("comboSum 7           = " + combinationSum(new int[]{2,3,6,7}, 7));
        System.out.println("nQueens(4)           = " + nQueens(4).size() + " solutions");
        char[][] grid = {{'A','B','C','E'},{'S','F','C','S'},{'A','D','E','E'}};
        System.out.println("wordSearch ABCCED    = " + wordSearch(grid, "ABCCED"));
        int[][] maze = {{1,0,0,0},{1,1,0,1},{1,1,0,0},{0,1,1,1}};
        System.out.println("ratInMaze            = " + ratInMaze(maze));
    }
}
```

Walkthrough:

- `subsets`: at each index, decide to include `a[i]` or not. Adding a snapshot at every node.
- `permutations`: same idea but with `used[]` flag to prevent reuse.
- `combinationSum`: candidates may repeat (`i` not `i+1`); sort so we can prune with `break`.
- `nQueens`: try each column; check safety; recurse; undo.
- `wordSearch`: mark cell visited (`#`), recurse, restore.
- `ratInMaze`: visit, try D/L/R/U, undo visit.

---

# 6. Dry Run — `subsets([1,2,3])`

```
back(0, []):  out=[[]]
  add 1; back(1, [1]): out=[[],[1]]
    add 2; back(2, [1,2]): out=[[],[1],[1,2]]
      add 3; back(3, [1,2,3])
    add 3; back(2, [1,3])
  add 2; back(1, [2])
  add 3; back(1, [3])
```

Output: `[[], [1], [1,2], [1,2,3], [1,3], [2], [2,3], [3]]`.

---

# 7. Common Mistakes

1. **Forgetting to undo** the choice — leaves stale state.
2. **Not copying** when adding to results — reference gets mutated later.
3. **Wrong bounds** in grid problems.

---

# 8. Interview Questions

### Q1. Subsets vs permutations?
Subsets: each element either in or out → 2ⁿ. Permutations: ordering matters → n!.

### Q2. How to optimise?
- Pruning: skip invalid branches early.
- Sorting: enables early break.

### Q3. Backtracking vs brute force?
Backtracking prunes during recursion, avoiding exponential blowup.

---

# 9. Practice Problems

## 🟢 Easy

### 1. Subsets
**Input:** `[1,2,3]` → **Output:** all 8 subsets.

### 2. Power Set
Same as subsets.

### 3. Letter Case Permutation
**Input:** `"a1b"` → **Output:** `["a1b","a1B","A1b","A1B"]`.

### 4. Generate Parentheses
**Input:** `n=3` → **Output:** `["((()))","(()())","(())()","()(())","()()()"]`.

### 5. Binary Watch
Read time combinations.

## 🟡 Medium

### 6. Permutations
Standard.

### 7. Permutations II (with duplicates)
Standard.

### 8. Combination Sum
Standard.

### 9. Combination Sum II (no reuse)
Standard.

### 10. Word Search
Standard.

## 🔴 Hard

### 11. N-Queens
Standard.

### 12. Sudoku Solver
Standard.

### 13. Rat in a Maze
Standard.

### 14. Regular Expression Matching
DP, but backtracking helps.

### 15. Palindrome Partitioning
Standard.

---

# 10. Practice Hints

## Easy
1. Choose / not choose.
2. Same.
3. Branch on each letter.
4. Track open/close count.
5. Backtrack over bits.

## Medium
6. Used[] array.
7. Sort + skip duplicates.
8. Recurse with `i` not `i+1`.
9. `i+1`, skip dup.
10. Mark visited.

## Hard
11. Row/col/diag checks.
12. Try digits, validate.
13. DFS, track path.
14. Recurse on char patterns.
15. Partition + palindrome check.

---

# 11. Revision Checklist

- [ ] Know the choose-explore-undo template
- [ ] Can generate subsets/permutations
- [ ] Can solve N-Queens and Sudoku
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 12. Key Takeaways

- Backtracking = DFS + prune.
- Always undo state.
- Sort inputs when possible for early break.

Tomorrow: **Graph Fundamentals**.


## Solutions

### Problem 1 — Subsets (E)

```java
class Subsets {
    public static void main(String[] args) {
        int[] a = {1,2,3};
        java.util.List<java.util.List<Integer>> res = new java.util.ArrayList<>();
        bt(a, 0, new java.util.ArrayList<>(), res);
        System.out.println(res);
    }
    static void bt(int[] a, int i, java.util.List<Integer> cur, java.util.List<java.util.List<Integer>> res) {
        res.add(new java.util.ArrayList<>(cur));
        for (int k = i; k < a.length; k++) { cur.add(a[k]); bt(a, k + 1, cur, res); cur.remove(cur.size() - 1); }
    }
}
```

### Problem 2 — PowerSet (E)

```java
class PowerSet {
    public static void main(String[] args) {
        int[] a = {1,2,3};
        java.util.List<java.util.List<Integer>> res = new java.util.ArrayList<>();
        bt(a, 0, new java.util.ArrayList<>(), res);
        System.out.println(res.size() + " subsets");
    }
    static void bt(int[] a, int i, java.util.List<Integer> cur, java.util.List<java.util.List<Integer>> res) {
        res.add(new java.util.ArrayList<>(cur));
        for (int k = i; k < a.length; k++) { cur.add(a[k]); bt(a, k + 1, cur, res); cur.remove(cur.size() - 1); }
    }
}
```

### Problem 3 — LetterCase (E)

```java
class LetterCase {
    static void bt(String s, int i, StringBuilder cur) {
        if (i == s.length()) { System.out.println(cur); return; }
        char c = s.charAt(i);
        if (Character.isLetter(c)) {
            cur.append(Character.toLowerCase(c)); bt(s, i+1, cur); cur.deleteCharAt(cur.length()-1);
            cur.append(Character.toUpperCase(c)); bt(s, i+1, cur); cur.deleteCharAt(cur.length()-1);
        } else { cur.append(c); bt(s, i+1, cur); cur.deleteCharAt(cur.length()-1); }
    }
    public static void main(String[] args) { bt("a1b2", 0, new StringBuilder()); }
}
```

### Problem 4 — GenParen (E)

```java
class GenParen {
    static void bt(int open, int close, int n, StringBuilder cur) {
        if (cur.length() == 2 * n) { System.out.println(cur); return; }
        if (open < n) { cur.append('('); bt(open + 1, close, n, cur); cur.deleteCharAt(cur.length() - 1); }
        if (close < open) { cur.append(')'); bt(open, close + 1, n, cur); cur.deleteCharAt(cur.length() - 1); }
    }
    public static void main(String[] args) { bt(0, 0, 3, new StringBuilder()); }
}
```

### Problem 5 — BinWatch (E)

```java
class BinWatch {
    public static void main(String[] args) {
        int turnedOn = 1;
        java.util.List<String> out = new java.util.ArrayList<>();
        for (int h = 0; h < 12; h++) for (int m = 0; m < 60; m++)
            if (Integer.bitCount(h) + Integer.bitCount(m) == turnedOn) out.add(String.format("%d:%02d", h, m));
        System.out.println(out);
    }
}
```

### Problem 6 — Perms (M)

```java
class Perms {
    public static void main(String[] args) {
        int[] a = {1,2,3};
        java.util.List<java.util.List<Integer>> res = new java.util.ArrayList<>();
        perm(a, new boolean[a.length], new java.util.ArrayList<>(), res);
        System.out.println(res);
    }
    static void perm(int[] a, boolean[] used, java.util.List<Integer> cur, java.util.List<java.util.List<Integer>> res) {
        if (cur.size() == a.length) { res.add(new java.util.ArrayList<>(cur)); return; }
        for (int i = 0; i < a.length; i++) {
            if (used[i]) continue;
            used[i] = true; cur.add(a[i]);
            perm(a, used, cur, res);
            used[i] = false; cur.remove(cur.size() - 1);
        }
    }
}
```

### Problem 7 — PermsDup (M)

```java
class PermsDup {
    public static void main(String[] args) {
        int[] a = {1,1,2};
        java.util.Arrays.sort(a);
        java.util.List<java.util.List<Integer>> res = new java.util.ArrayList<>();
        bt(a, new boolean[a.length], new java.util.ArrayList<>(), res);
        System.out.println(res);
    }
    static void bt(int[] a, boolean[] used, java.util.List<Integer> cur, java.util.List<java.util.List<Integer>> res) {
        if (cur.size() == a.length) { res.add(new java.util.ArrayList<>(cur)); return; }
        for (int i = 0; i < a.length; i++) {
            if (used[i] || (i > 0 && a[i] == a[i-1] && !used[i-1])) continue;
            used[i] = true; cur.add(a[i]);
            bt(a, used, cur, res);
            used[i] = false; cur.remove(cur.size() - 1);
        }
    }
}
```

### Problem 8 — CombSum (M)

```java
class CombSum {
    public static void main(String[] args) {
        int[] c = {2,3,6,7}; int t = 7;
        java.util.List<java.util.List<Integer>> res = new java.util.ArrayList<>();
        bt(c, 0, t, new java.util.ArrayList<>(), res);
        System.out.println(res);
    }
    static void bt(int[] c, int start, int t, java.util.List<Integer> cur, java.util.List<java.util.List<Integer>> res) {
        if (t == 0) { res.add(new java.util.ArrayList<>(cur)); return; }
        for (int i = start; i < c.length; i++) {
            if (c[i] > t) break;
            cur.add(c[i]); bt(c, i, t - c[i], cur, res); cur.remove(cur.size() - 1);
        }
    }
}
```

### Problem 9 — CombSumII (M)

```java
class CombSumII {
    public static void main(String[] args) {
        int[] c = {10,1,2,7,6,1,5}; int t = 8;
        java.util.Arrays.sort(c);
        java.util.List<java.util.List<Integer>> res = new java.util.ArrayList<>();
        bt(c, 0, t, new java.util.ArrayList<>(), res);
        System.out.println(res);
    }
    static void bt(int[] c, int start, int t, java.util.List<Integer> cur, java.util.List<java.util.List<Integer>> res) {
        if (t == 0) { res.add(new java.util.ArrayList<>(cur)); return; }
        for (int i = start; i < c.length; i++) {
            if (c[i] > t) break;
            if (i > start && c[i] == c[i-1]) continue;
            cur.add(c[i]); bt(c, i + 1, t - c[i], cur, res); cur.remove(cur.size() - 1);
        }
    }
}
```

### Problem 10 — WordSearch (M)

```java
class WordSearch {
    public static void main(String[] args) {
        char[][] b = {{'A','B','C','E'},{'S','F','C','S'},{'A','D','E','E'}};
        String w = "ABCCED";
        int m = b.length, n = b[0].length;
        boolean found = false;
        for (int i = 0; i < m && !found; i++) for (int j = 0; j < n && !found; j++)
            found = dfs(b, w, 0, i, j, new boolean[m][n]);
        System.out.println(found);
    }
    static boolean dfs(char[][] b, String w, int k, int i, int j, boolean[][] v) {
        if (k == w.length()) return true;
        if (i<0||j<0||i>=b.length||j>=b[0].length||v[i][j]||b[i][j]!=w.charAt(k)) return false;
        v[i][j] = true;
        boolean ok = dfs(b,w,k+1,i+1,j,v)||dfs(b,w,k+1,i-1,j,v)||dfs(b,w,k+1,i,j+1,v)||dfs(b,w,k+1,i,j-1,v);
        v[i][j] = false;
        return ok;
    }
}
```

### Problem 11 — NQueens (H)

```java
class NQueens {
    public static void main(String[] args) {
        int n = 4;
        java.util.List<java.util.List<String>> res = new java.util.ArrayList<>();
        char[][] b = new char[n][n];
        for (char[] r : b) java.util.Arrays.fill(r, '.');
        solve(b, 0, new boolean[n], new boolean[2*n], new boolean[2*n], res);
        System.out.println(res.size() + " solutions");
    }
    static void solve(char[][] b, int row, boolean[] col, boolean[] d1, boolean[] d2, java.util.List<java.util.List<String>> res) {
        if (row == b.length) {
            java.util.List<String> s = new java.util.ArrayList<>();
            for (char[] r : b) s.add(new String(r));
            res.add(s); return;
        }
        for (int j = 0; j < b.length; j++) {
            if (col[j] || d1[row+j] || d2[row-j+b.length]) continue;
            b[row][j] = 'Q'; col[j] = d1[row+j] = d2[row-j+b.length] = true;
            solve(b, row+1, col, d1, d2, res);
            b[row][j] = '.'; col[j] = d1[row+j] = d2[row-j+b.length] = false;
        }
    }
}
```

### Problem 12 — Sudoku (H)

```java
class Sudoku {
    public static void main(String[] args) {
        char[][] b = {
            {'5','3','.','.','7','.','.','.','.'},
            {'6','.','.','1','9','5','.','.','.'},
            {'.','9','8','.','.','.','.','6','.'},
            {'8','.','.','.','6','.','.','.','3'},
            {'4','.','.','8','.','3','.','.','1'},
            {'7','.','.','.','2','.','.','.','6'},
            {'.','6','.','.','.','.','2','8','.'},
            {'.','.','.','4','1','9','.','.','5'},
            {'.','.','.','.','8','.','.','7','9'}};
        solve(b);
        for (char[] r : b) System.out.println(new String(r));
    }
    static boolean solve(char[][] b) {
        for (int i = 0; i < 9; i++) for (int j = 0; j < 9; j++) if (b[i][j] == '.') {
            for (char c = '1'; c <= '9'; c++) if (ok(b, i, j, c)) {
                b[i][j] = c;
                if (solve(b)) return true;
                b[i][j] = '.';
            }
            return false;
        }
        return true;
    }
    static boolean ok(char[][] b, int i, int j, char c) {
        for (int k = 0; k < 9; k++) if (b[i][k] == c || b[k][j] == c) return false;
        int bi = (i/3)*3, bj = (j/3)*3;
        for (int x = bi; x < bi+3; x++) for (int y = bj; y < bj+3; y++) if (b[x][y] == c) return false;
        return true;
    }
}
```

### Problem 13 — RatMaze (H)

```java
class RatMaze {
    public static void main(String[] args) {
        int[][] m = {{1,0,0,0},{1,1,0,1},{0,1,0,0},{1,1,1,1}};
        int n = m.length;
        java.util.List<String> res = new java.util.ArrayList<>();
        dfs(m, n, 0, 0, "", res);
        System.out.println(res);
    }
    static void dfs(int[][] m, int n, int i, int j, String path, java.util.List<String> res) {
        if (i == n - 1 && j == n - 1) { res.add(path); return; }
        if (i < 0 || j < 0 || i >= n || j >= n || m[i][j] == 0) return;
        m[i][j] = 0;
        dfs(m, n, i+1, j, path+"D", res); dfs(m, n, i-1, j, path+"U", res);
        dfs(m, n, i, j+1, path+"R", res); dfs(m, n, i, j-1, path+"L", res);
        m[i][j] = 1;
    }
}
```

### Problem 14 — Regex (H)

```java
class Regex {
    public static void main(String[] args) {
        String s = "ab", p = ".*";
        System.out.println(match(s, p));
    }
    static boolean match(String s, String p) {
        if (p.isEmpty()) return s.isEmpty();
        boolean first = !s.isEmpty() && (p.charAt(0) == s.charAt(0) || p.charAt(0) == '.');
        if (p.length() >= 2 && p.charAt(1) == '*') return match(s, p.substring(2)) || (first && match(s.substring(1), p));
        return first && match(s.substring(1), p.substring(1));
    }
}
```

### Problem 15 — PalPartition (H)

```java
class PalPartition {
    public static void main(String[] args) {
        String s = "aab";
        java.util.List<java.util.List<String>> res = new java.util.ArrayList<>();
        bt(s, 0, new java.util.ArrayList<>(), res);
        System.out.println(res);
    }
    static void bt(String s, int start, java.util.List<String> cur, java.util.List<java.util.List<String>> res) {
        if (start == s.length()) { res.add(new java.util.ArrayList<>(cur)); return; }
        for (int end = start; end < s.length(); end++) {
            if (isPal(s, start, end)) {
                cur.add(s.substring(start, end + 1));
                bt(s, end + 1, cur, res);
                cur.remove(cur.size() - 1);
            }
        }
    }
    static boolean isPal(String s, int l, int r) {
        while (l < r) if (s.charAt(l++) != s.charAt(r--)) return false;
        return true;
    }
}
```

