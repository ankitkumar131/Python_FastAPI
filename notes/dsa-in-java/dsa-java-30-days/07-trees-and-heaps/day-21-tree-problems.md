# Day 21 — Advanced Tree Problems

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Compute tree height, diameter, balanced check
- Find the maximum path sum
- Compute lowest common ancestor (binary tree)
- Compute views: left, right, top, bottom
- Perform vertical traversal
- Serialize and deserialize a binary tree

---

# 1. Introduction

Today's problems are interview classics. Each one teaches a distinct recursive pattern that you can apply to many other tree problems.

---

# 2. Height and Balanced Check

A tree is **height-balanced** if for every node, |height(left) − height(right)| ≤ 1.

```java
int check(Node n) {
    if (n == null) return 0;
    int l = check(n.left);
    if (l == -1) return -1;
    int r = check(n.right);
    if (r == -1) return -1;
    if (Math.abs(l - r) > 1) return -1;
    return 1 + Math.max(l, r);
}
boolean isBalanced(Node r) { return check(r) != -1; }
```

The `-1` propagates a "fail" signal without recomputation.

---

# 3. Diameter

The longest path between any two nodes (may or may not pass through the root).

```java
int diameter(Node root) {
    int[] best = {0};
    h(root, best); return best[0];
}
int h(Node n, int[] best) {
    if (n == null) return 0;
    int l = h(n.left, best), r = h(n.right, best);
    best[0] = Math.max(best[0], l + r);     // path through this node
    return 1 + Math.max(l, r);              // height
}
```

---

# 4. Maximum Path Sum

Path can start/end anywhere. Value can be negative — use `Math.max(0, ...)` to skip non-contributing subtrees.

```java
int maxPath(Node n, int[] best) {
    if (n == null) return 0;
    int l = Math.max(0, maxPath(n.left, best));
    int r = Math.max(0, maxPath(n.right, best));
    best[0] = Math.max(best[0], n.val + l + r);
    return n.val + Math.max(l, r);
}
```

---

# 5. Lowest Common Ancestor (Binary Tree)

For nodes `p` and `q`, the LCA is the deepest node that's an ancestor of both.

```java
Node lca(Node n, Node p, Node q) {
    if (n == null || n == p || n == q) return n;
    Node left = lca(n.left, p, q);
    Node right = lca(n.right, p, q);
    return (left != null && right != null) ? n : (left != null ? left : right);
}
```

---

# 6. Views of a Binary Tree

| View | Approach |
|---|---|
| Right view | BFS, take last node per level |
| Left view  | BFS, take first node per level |
| Top view   | BFS with horizontal distance; first seen at each distance |
| Bottom view| BFS with horizontal distance; last seen at each distance |

Vertical traversal: BFS by (row, col), group by col.

---

# 7. Serialize / Deserialize

A common technique: preorder traversal with null markers.

```
serialize:   "1 2 # # 3 4 # # 5 # #"
deserialize: parse tokens, build tree.
```

---

# 8. Java Implementation — `AdvancedTreeDemo.java`

```java
import java.util.*;

public class AdvancedTreeDemo {

    static class Node { int val; Node left, right; Node(int v) { val = v; } }

    static int height(Node n) { return n == null ? 0 : 1 + Math.max(height(n.left), height(n.right)); }

    static boolean isBalanced(Node n) { return checkBal(n) != -1; }
    static int checkBal(Node n) {
        if (n == null) return 0;
        int l = checkBal(n.left); if (l == -1) return -1;
        int r = checkBal(n.right); if (r == -1) return -1;
        if (Math.abs(l - r) > 1) return -1;
        return 1 + Math.max(l, r);
    }

    static int diameter(Node root) { int[] best = {0}; hDiam(root, best); return best[0]; }
    static int hDiam(Node n, int[] b) {
        if (n == null) return 0;
        int l = hDiam(n.left, b), r = hDiam(n.right, b);
        b[0] = Math.max(b[0], l + r);
        return 1 + Math.max(l, r);
    }

    static int maxPathSum(Node root) { int[] best = {Integer.MIN_VALUE}; mp(root, best); return best[0]; }
    static int mp(Node n, int[] b) {
        if (n == null) return 0;
        int l = Math.max(0, mp(n.left, b));
        int r = Math.max(0, mp(n.right, b));
        b[0] = Math.max(b[0], n.val + l + r);
        return n.val + Math.max(l, r);
    }

    static Node lca(Node n, Node p, Node q) {
        if (n == null || n == p || n == q) return n;
        Node l = lca(n.left, p, q), r = lca(n.right, p, q);
        return l != null && r != null ? n : (l != null ? l : r);
    }

    static List<Integer> rightSideView(Node r) {
        List<Integer> out = new ArrayList<>();
        if (r == null) return out;
        Deque<Node> q = new ArrayDeque<>(); q.offer(r);
        while (!q.isEmpty()) {
            int sz = q.size();
            for (int i = 0; i < sz; i++) {
                Node n = q.poll();
                if (i == sz - 1) out.add(n.val);
                if (n.left != null)  q.offer(n.left);
                if (n.right != null) q.offer(n.right);
            }
        }
        return out;
    }

    static List<List<Integer>> vertical(Node root) {
        List<List<Integer>> out = new ArrayList<>();
        if (root == null) return out;
        TreeMap<Integer, List<Integer>> map = new TreeMap<>();
        Deque<Node> q = new ArrayDeque<>();
        Deque<Integer> cols = new ArrayDeque<>();
        q.offer(root); cols.offer(0);
        while (!q.isEmpty()) {
            Node n = q.poll(); int c = cols.poll();
            map.computeIfAbsent(c, k -> new ArrayList<>()).add(n.val);
            if (n.left != null)  { q.offer(n.left);  cols.offer(c - 1); }
            if (n.right != null) { q.offer(n.right); cols.offer(c + 1); }
        }
        out.addAll(map.values());
        return out;
    }

    static String serialize(Node r) {
        StringBuilder sb = new StringBuilder();
        ser(r, sb);
        return sb.toString();
    }
    static void ser(Node n, StringBuilder sb) {
        if (n == null) { sb.append("# "); return; }
        sb.append(n.val).append(" ");
        ser(n.left, sb); ser(n.right, sb);
    }
    static Node deserialize(String s) {
        Deque<String> t = new ArrayDeque<>(Arrays.asList(s.split(" ")));
        return deser(t);
    }
    static Node deser(Deque<String> t) {
        String x = t.poll();
        if (x.equals("#")) return null;
        Node n = new Node(Integer.parseInt(x));
        n.left = deser(t); n.right = deser(t);
        return n;
    }

    public static void main(String[] args) {
        Node r = new Node(1);
        r.left = new Node(2); r.right = new Node(3);
        r.left.left = new Node(4); r.left.right = new Node(5);
        r.right.left = new Node(6); r.right.right = new Node(7);

        System.out.println("height       = " + height(r));
        System.out.println("balanced     = " + isBalanced(r));
        System.out.println("diameter     = " + diameter(r));

        Node p = new Node(-10);
        p.left = new Node(9); p.right = new Node(20);
        p.right.left = new Node(15); p.right.right = new Node(7);
        System.out.println("maxPathSum   = " + maxPathSum(p));

        Node p1 = r.left.left, p2 = r.left.right;
        System.out.println("LCA(4,5)     = " + lca(r, p1, p2).val);

        System.out.println("rightView    = " + rightSideView(r));
        System.out.println("vertical     = " + vertical(r));

        String s = serialize(r);
        Node d = deserialize(s);
        System.out.println("deser root   = " + d.val);
    }
}
```

Walkthrough:

- `checkBal` returns height on success, `-1` on fail.
- `diameter` — at each node, candidate diameter = l + r. Update best, return height upward.
- `maxPathSum` — same shape; ignore negative branches.
- `lca` — standard post-order split.
- `rightSideView` — BFS, last per level.
- `vertical` — BFS with column, group via TreeMap.
- `serialize/deserialize` — preorder with `#` markers.

---

# 9. Common Mistakes

1. **Returning `height` from `maxPathSum`** — return the maximum downward gain, not the through-node path.
2. **Not marking visited in vertical** — use TreeMap for sorted output.
3. **Off-by-one** in column indices for views.

---

# 10. Interview Questions

### Q1. Diameter vs height?
Height: longest root→leaf path. Diameter: longest path between any two nodes (not necessarily through root).

### Q2. LCA in BST vs binary tree?
BST: use ordering. Binary tree: post-order split.

### Q3. Why preorder for serialize?
Easy to reconstruct: first token is root, then left subtree, then right subtree.

---

# 11. Practice Problems

## 🟢 Easy

### 1. Height of Binary Tree
Standard.

### 2. Balanced Binary Tree
Standard.

### 3. Maximum Depth
Same as height.

### 4. Same Tree (done) and Symmetric Tree (done)
Recap.

### 5. Invert Binary Tree (done)
Recap.

## 🟡 Medium

### 6. Diameter of Binary Tree
Standard.

### 7. Maximum Path Sum
Standard.

### 8. Lowest Common Ancestor
Standard.

### 9. Right Side View
Standard.

### 10. Validate BST (done)
Recap.

## 🔴 Hard

### 11. Vertical Order Traversal
Standard.

### 12. Serialize/Deserialize
Standard.

### 13. Recover BST
Standard.

### 14. Binary Tree Maximum Path Sum (done)
Recap.

### 15. Count Complete Tree Nodes
**Input:** perfect-ish tree → **Output:** count in O(log² n).

---

# 12. Practice Hints

## Easy
1. Recursive height.
2. `-1` sentinel.
3. Same as height.
4. Same as Day 18.
5. Swap children.

## Medium
6. Update best per node.
7. `max(0, child)` + root.
8. Post-order.
9. BFS, last per level.
10. Day 19.

## Hard
11. BFS + TreeMap.
12. Preorder + null markers.
13. Inorder anomaly.
14. Same as Q7.
15. Check completeness + binary-search by row.

---

# 13. Revision Checklist

- [ ] Can compute height, balanced, diameter
- [ ] Can find LCA
- [ ] Can compute views
- [ ] Can serialize/deserialize
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 14. Key Takeaways

- Many tree problems share the pattern: post-order return value + update global.
- LCA = first node where `p` and `q` are on different sides.
- BFS-with-column handles views and vertical traversal cleanly.

Tomorrow: **Greedy Algorithms**.


## Solutions

### Problem 1 — Height (E)

```java
class Height {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static int h(N u) { return u == null ? 0 : 1 + Math.max(h(u.l), h(u.r)); }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3); root.l.l = new N(4);
        System.out.println(h(root));
    }
}
```

### Problem 2 — Balanced (E)

```java
class Balanced {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static boolean ok = true;
    static int h(N u) { if (u == null) return 0; int l = h(u.l), r = h(u.r); if (Math.abs(l-r) > 1) ok = false; return 1 + Math.max(l, r); }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3); root.l.l = new N(4);
        h(root); System.out.println(ok);
    }
}
```

### Problem 3 — Depth (E)

```java
class Depth {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static int d(N u) { return u == null ? 0 : 1 + Math.max(d(u.l), d(u.r)); }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3);
        System.out.println(d(root));
    }
}
```

### Problem 4 — Same (E)

```java
class Same {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static boolean eq(N a, N b) { if (a==null&&b==null) return true; if (a==null||b==null) return false; return a.v==b.v && eq(a.l,b.l) && eq(a.r,b.r); }
    public static void main(String[] args) {
        N a = new N(1); a.l = new N(2);
        N b = new N(1); b.l = new N(2);
        System.out.println(eq(a, b));
    }
}
```

### Problem 5 — Invert (E)

```java
class Invert {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N inv(N u) { if (u == null) return null; N t = u.l; u.l = inv(u.r); u.r = inv(t); return u; }
    public static void main(String[] args) { N root = new N(1); root.l = new N(2); inv(root); System.out.println("done"); }
}
```

### Problem 6 — Dia (M)

```java
class Dia {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static int best = 0;
    static int d(N u) { if (u == null) return 0; int l = d(u.l), r = d(u.r); best = Math.max(best, l+r); return 1 + Math.max(l, r); }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3); root.l.l = new N(4); root.l.r = new N(5);
        d(root); System.out.println(best);
    }
}
```

### Problem 7 — MPS (M)

```java
class MPS {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static int best = Integer.MIN_VALUE;
    static int g(N u) { if (u == null) return 0; int l = Math.max(0, g(u.l)), r = Math.max(0, g(u.r)); best = Math.max(best, l+r+u.v); return u.v + Math.max(l, r); }
    public static void main(String[] args) {
        N root = new N(-10); root.l = new N(9); root.r = new N(20); root.r.l = new N(15); root.r.r = new N(7);
        g(root); System.out.println(best);
    }
}
```

### Problem 8 — LCA (M)

```java
class LCA {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N lca(N u, N p, N q) {
        if (u == null || u == p || u == q) return u;
        N L = lca(u.l, p, q), R = lca(u.r, p, q);
        if (L != null && R != null) return u;
        return L != null ? L : R;
    }
    public static void main(String[] args) {
        N root = new N(3); root.l = new N(5); root.r = new N(1); root.l.l = new N(6); root.l.r = new N(2); root.r.l = new N(0); root.r.r = new N(8);
        System.out.println("see day-21 demo");
    }
}
```

### Problem 9 — Right (M)

```java
class Right {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static void dfs(N u, int d, java.util.List<Integer> out) {
        if (u == null) return;
        if (d == out.size()) out.add(u.v);
        dfs(u.r, d + 1, out); dfs(u.l, d + 1, out);
    }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3); root.l.r = new N(5); root.r.r = new N(4);
        java.util.List<Integer> out = new java.util.ArrayList<>(); dfs(root, 0, out); System.out.println(out);
    }
}
```

### Problem 10 — ValidBST (M)

```java
class ValidBST {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static boolean ok(N u, long lo, long hi) {
        if (u == null) return true;
        if (u.v <= lo || u.v >= hi) return false;
        return ok(u.l, lo, u.v) && ok(u.r, u.v, hi);
    }
    public static void main(String[] args) {
        N root = new N(2); root.l = new N(1); root.r = new N(3);
        System.out.println(ok(root, Long.MIN_VALUE, Long.MAX_VALUE));
    }
}
```

### Problem 11 — Vertical (H)

```java
class Vertical {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static void dfs(N u, int col, java.util.Map<Integer, java.util.List<Integer>> m) {
        if (u == null) return;
        m.computeIfAbsent(col, k -> new java.util.ArrayList<>()).add(u.v);
        dfs(u.l, col - 1, m); dfs(u.r, col + 1, m);
    }
    public static void main(String[] args) {
        N root = new N(3); root.l = new N(9); root.r = new N(20); root.r.l = new N(15); root.r.r = new N(7);
        java.util.Map<Integer, java.util.List<Integer>> m = new java.util.TreeMap<>();
        dfs(root, 0, m); System.out.println(m.values());
    }
}
```

### Problem 12 — Ser (H)

```java
class Ser {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static String s(N u) { return u == null ? "#" : u.v + "," + s(u.l) + "," + s(u.r); }
    static int i = 0;
    static N d(String[] t) { if (t[i].equals("#")) { i++; return null; } N u = new N(Integer.parseInt(t[i++])); u.l = d(t); u.r = d(t); return u; }
    public static void main(String[] args) { System.out.println("see day-21 demo"); }
}
```

### Problem 13 — RecoverBST (H)

```java
class RecoverBST {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N a, b, prev;
    static void ino(N u) { if (u == null) return; ino(u.l); if (prev != null && prev.v > u.v) { if (a == null) a = prev; b = u; } prev = u; ino(u.r); }
    public static void main(String[] args) {
        N root = new N(3); root.l = new N(1); root.r = new N(4); root.r.l = new N(2);
        ino(root); int t = a.v; a.v = b.v; b.v = t;
        System.out.println("recovered");
    }
}
```

### Problem 14 — MaxPath (H)

```java
class MaxPath {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static int best = Integer.MIN_VALUE;
    static int g(N u) { if (u == null) return 0; int l = Math.max(0, g(u.l)), r = Math.max(0, g(u.r)); best = Math.max(best, l+r+u.v); return u.v + Math.max(l, r); }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3);
        g(root); System.out.println(best);
    }
}
```

### Problem 15 — Complete (H)

```java
class Complete {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static int count(N u) {
        int h = 0; N cur = u;
        while (cur != null) { h++; cur = cur.l; }
        if (Math.pow(2, h) - 1 == 0) return (int)(Math.pow(2, h) - 1);
        // O(h) check + recursive right
        int total = 0;
        cur = u; int curDepth = 0;
        while (cur != null) { curDepth++; cur = cur.r; }
        if (curDepth == h) return (int)(Math.pow(2, h) - 1);
        return count(u.l) + count(u.r) + 1;
    }
    public static void main(String[] args) { System.out.println("see day-21 demo"); }
}
```

