# Day 18 — Binary Trees

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Define tree terminology (root, leaf, height, depth)
- Distinguish full, complete, and perfect binary trees
- Implement traversals: preorder, inorder, postorder (recursive + iterative)
- Implement level-order traversal with BFS
- Compute tree height, depth, and size

---

# 1. Introduction

A tree is a hierarchical structure. Every node has zero or more children. A **binary tree** has at most two children per node. Trees are the most important non-linear structure in DSA.

---

# 2. Why Do We Need This?

- File systems, DOMs, organisational charts.
- Search trees (BST, AVL, Red-Black).
- Heaps (binary heaps).
- Tries for prefix matching.
- Segment trees for range queries.

---

# 3. Core Concept

```
        1       ← root
       / \
      2   3
     / \   \
    4   5   6   ← leaves
```

- **Depth** of a node: number of edges from root.
- **Height** of a node: longest path to a leaf.
- **Size**: number of nodes.
- **Full**: every node has 0 or 2 children.
- **Complete**: all levels full except possibly the last; last is filled left to right.
- **Perfect**: all internal nodes have 2 children and all leaves at the same depth.

---

# 4. Real-World Analogy

A company org chart: the CEO at top, VPs below, managers below them. Every box (node) has up to 2 (binary) or more (general) direct reports.

---

# 5. Java Implementation — `BinaryTreeDemo.java`

```java
import java.util.*;

public class BinaryTreeDemo {

    static class Node {
        int val;
        Node left, right;
        Node(int v) { val = v; }
    }

    /** Preorder: root, left, right. */
    static void preorder(Node root) {
        if (root == null) return;
        System.out.print(root.val + " ");
        preorder(root.left);
        preorder(root.right);
    }

    /** Inorder: left, root, right. (Gives sorted order for BST.) */
    static void inorder(Node root) {
        if (root == null) return;
        inorder(root.left);
        System.out.print(root.val + " ");
        inorder(root.right);
    }

    /** Postorder: left, right, root. (Use for delete-tree, eval-expr.) */
    static void postorder(Node root) {
        if (root == null) return;
        postorder(root.left);
        postorder(root.right);
        System.out.print(root.val + " ");
    }

    /** Iterative preorder using a stack. */
    static List<Integer> preorderIter(Node root) {
        List<Integer> out = new ArrayList<>();
        if (root == null) return out;
        Deque<Node> st = new ArrayDeque<>();
        st.push(root);
        while (!st.isEmpty()) {
            Node n = st.pop();
            out.add(n.val);
            if (n.right != null) st.push(n.right); // push right first so left is processed first
            if (n.left  != null) st.push(n.left);
        }
        return out;
    }

    /** Iterative inorder. */
    static List<Integer> inorderIter(Node root) {
        List<Integer> out = new ArrayList<>();
        Deque<Node> st = new ArrayDeque<>();
        Node cur = root;
        while (cur != null || !st.isEmpty()) {
            while (cur != null) { st.push(cur); cur = cur.left; }
            cur = st.pop();
            out.add(cur.val);
            cur = cur.right;
        }
        return out;
    }

    /** Level order (BFS). */
    static List<List<Integer>> levelOrder(Node root) {
        List<List<Integer>> out = new ArrayList<>();
        if (root == null) return out;
        Deque<Node> q = new ArrayDeque<>();
        q.offer(root);
        while (!q.isEmpty()) {
            List<Integer> level = new ArrayList<>();
            for (int sz = q.size(); sz > 0; sz--) {
                Node n = q.poll();
                level.add(n.val);
                if (n.left != null)  q.offer(n.left);
                if (n.right != null) q.offer(n.right);
            }
            out.add(level);
        }
        return out;
    }

    /** Height: number of edges on the longest root→leaf path. */
    static int height(Node root) {
        if (root == null) return -1;
        return 1 + Math.max(height(root.left), height(root.right));
    }

    /** Size: total nodes. */
    static int size(Node root) {
        if (root == null) return 0;
        return 1 + size(root.left) + size(root.right);
    }

    /** Max value. */
    static int max(Node root) {
        if (root == null) return Integer.MIN_VALUE;
        return Math.max(root.val, Math.max(max(root.left), max(root.right)));
    }

    public static void main(String[] args) {
        Node root = new Node(1);
        root.left = new Node(2); root.right = new Node(3);
        root.left.left = new Node(4); root.left.right = new Node(5);
        root.right.right = new Node(6);

        System.out.print("preorder:  "); preorder(root); System.out.println();
        System.out.print("inorder:   "); inorder(root); System.out.println();
        System.out.print("postorder: "); postorder(root); System.out.println();

        System.out.println("preorderIter = " + preorderIter(root));
        System.out.println("inorderIter  = " + inorderIter(root));
        System.out.println("levelOrder   = " + levelOrder(root));
        System.out.println("height       = " + height(root));
        System.out.println("size         = " + size(root));
        System.out.println("max          = " + max(root));
    }
}
```

Walkthrough:

- **preorder/inorder/postorder**: differ only in where they "visit" the root.
- **preorderIter**: root → push right → push left → pop → repeat. Visiting before pushing is what makes it preorder.
- **inorderIter**: standard trick — go as far left as possible, popping and visiting along the way.
- **levelOrder**: BFS using a queue.
- **height**: recursive — leaf has height 0 if you count edges, or 1 if you count nodes. The code returns edges (empty tree = −1, single node = 0).
- **size / max**: easy recursive aggregation.

---

# 6. Dry Run — Inorder of `1(2(4,5),3(,6))`

```
inorder(1)
  inorder(2)
    inorder(4) → print 4
    print 2
    inorder(5) → print 5
  print 1
  inorder(3)
    inorder(null)
    print 3
    inorder(6) → print 6
```

Output: `4 2 5 1 3 6`.

---

# 7. When to Use Which Traversal

| Use case                          | Traversal |
|-----------------------------------|-----------|
| Copy / serialize (preferential)   | Preorder  |
| Sorted order of BST               | Inorder   |
| Delete tree / postfix evaluation  | Postorder |
| Level-by-level                    | Level order |

---

# 8. Common Mistakes

1. **Forgetting base case** in recursion — stack overflow.
2. **Confusing height vs depth**.
3. **Iterative postorder** is tricky — needs a "last visited" tracker.
4. **Modifying tree during traversal** — usually fine for read but causes bugs.

---

# 9. Interview Questions

### Q1. Full vs complete vs perfect?
Full: 0 or 2 children. Complete: filled left-to-right. Perfect: full + complete.

### Q2. Inorder of BST?
Sorted ascending.

### Q3. Number of nodes in perfect binary tree of height h?
2^(h+1) − 1.

---

# 10. Practice Problems

## 🟢 Easy

### 1. Preorder Traversal
**Input:** `1,2,3,4,5,null,6` → **Output:** `1 2 4 5 3 6`

### 2. Inorder Traversal
**Input:** as above → **Output:** `4 2 5 1 3 6`

### 3. Postorder Traversal
**Input:** as above → **Output:** `4 5 2 6 3 1`

### 4. Level Order
**Input:** as above → **Output:** `[[1],[2,3],[4,5,6]]`

### 5. Maximum Depth
**Input:** as above → **Output:** `2`

## 🟡 Medium

### 6. Same Tree
**Input:** two trees → **Output:** true/false.

### 7. Invert Binary Tree
**Input:** tree → **Output:** mirrored tree.

### 8. Symmetric Tree
**Input:** tree → **Output:** true if mirror of itself.

### 9. Build Tree from Preorder + Inorder
**Input:** pre=[3,9,20,15,7], in=[9,3,15,20,7] → **Output:** tree.

### 10. Right Side View
**Input:** tree → **Output:** `[1, 3, 6]`.

## 🔴 Hard

### 11. Vertical Order Traversal
**Input:** tree → **Output:** `[[4],[2],[1,5,6],[3],[7]]`

### 12. Recover BST (two nodes swapped)
**Input:** BST with two swapped → **Output:** restore.

### 13. Serialize/Deserialize
**Input:** tree → string → tree.

### 14. Morris Traversal (O(1) space inorder)

### 15. Maximum Path Sum
**Input:** tree → **Output:** max root-to-leaf path.

---

# 11. Practice Hints

## Easy
1. Recursive preorder.
2. Recursive inorder.
3. Recursive postorder.
4. BFS with queue.
5. Recursive 1 + max of children.

## Medium
6. Recurse both, compare.
7. Swap children at each node.
8. Mirror check.
9. Use inorder to split.
10. Last element of each level.

## Hard
11. BFS with column index.
12. Inorder traversal, find anomalies.
13. Preorder + null markers.
14. Threaded tree.
15. Recurse, return max(root + max(left,right)).

---

# 12. Revision Checklist

- [ ] Know tree terminology
- [ ] Can do recursive + iterative traversals
- [ ] Can compute height and size
- [ ] Know level-order BFS

---

# 13. Key Takeaways

- Pre/in/post-order differ only in root-visit position.
- Inorder of a BST = sorted.
- Level order = BFS.
- Height: 1 + max(children). Size: 1 + sum(children).

Tomorrow: **Binary Search Trees**.


## Solutions

### Problem 1 — Preorder (E)

```java
class Preorder {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static void pre(N u) { if (u == null) return; System.out.print(u.v + " "); pre(u.l); pre(u.r); }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3); root.l.l = new N(4); root.l.r = new N(5);
        pre(root);
    }
}
```

### Problem 2 — Inorder (E)

```java
class Inorder {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static void in(N u) { if (u == null) return; in(u.l); System.out.print(u.v + " "); in(u.r); }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3); root.l.l = new N(4); root.l.r = new N(5);
        in(root);
    }
}
```

### Problem 3 — Postorder (E)

```java
class Postorder {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static void post(N u) { if (u == null) return; post(u.l); post(u.r); System.out.print(u.v + " "); }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3); root.l.l = new N(4); root.l.r = new N(5);
        post(root);
    }
}
```

### Problem 4 — LevelOrder (E)

```java
class LevelOrder {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3); root.l.l = new N(4); root.l.r = new N(5);
        java.util.Deque<N> q = new java.util.ArrayDeque<>(); q.offer(root);
        while (!q.isEmpty()) { N u = q.poll(); System.out.print(u.v + " "); if (u.l != null) q.offer(u.l); if (u.r != null) q.offer(u.r); }
    }
}
```

### Problem 5 — MaxDepth (E)

```java
class MaxDepth {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static int d(N u) { return u == null ? 0 : 1 + Math.max(d(u.l), d(u.r)); }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3); root.l.l = new N(4);
        System.out.println(d(root));
    }
}
```

### Problem 6 — Same (M)

```java
class Same {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static boolean eq(N a, N b) {
        if (a == null && b == null) return true;
        if (a == null || b == null) return false;
        return a.v == b.v && eq(a.l, b.l) && eq(a.r, b.r);
    }
    public static void main(String[] args) {
        N a = new N(1); a.l = new N(2); a.r = new N(3);
        N b = new N(1); b.l = new N(2); b.r = new N(3);
        System.out.println(eq(a, b));
    }
}
```

### Problem 7 — Invert (M)

```java
class Invert {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N inv(N u) { if (u == null) return null; N t = u.l; u.l = inv(u.r); u.r = inv(t); return u; }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3);
        inv(root);
        System.out.println("inverted");
    }
}
```

### Problem 8 — Symm (M)

```java
class Symm {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static boolean is(N l, N r) {
        if (l == null && r == null) return true;
        if (l == null || r == null) return false;
        return l.v == r.v && is(l.l, r.r) && is(l.r, r.l);
    }
    static boolean sym(N root) { return root == null || is(root.l, root.r); }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(2); root.l.l = new N(3); root.r.r = new N(3);
        System.out.println(sym(root));
    }
}
```

### Problem 9 — Build (M)

```java
class Build {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static int pi; // index in preorder
    static N build(int[] pre, int[] in) {
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>();
        for (int i = 0; i < in.length; i++) m.put(in[i], i);
        return helper(pre, 0, in.length - 1, m);
    }
    static N helper(int[] pre, int lo, int hi, java.util.Map<Integer,Integer> m) {
        if (lo > hi) return null;
        int v = pre[pi++]; N u = new N(v);
        int mid = m.get(v);
        u.l = helper(pre, lo, mid - 1, m);
        u.r = helper(pre, mid + 1, hi, m);
        return u;
    }
    public static void main(String[] args) { System.out.println("see day-18 demo"); }
}
```

### Problem 10 — RightSide (M)

```java
class RightSide {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3); root.l.r = new N(5); root.r.r = new N(4);
        java.util.List<Integer> out = new java.util.ArrayList<>();
        dfs(root, 0, out);
        System.out.println(out);
    }
    static void dfs(N u, int d, java.util.List<Integer> out) {
        if (u == null) return;
        if (d == out.size()) out.add(u.v);
        dfs(u.r, d + 1, out); dfs(u.l, d + 1, out);
    }
}
```

### Problem 11 — Vertical (H)

```java
class Vertical {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N root = new N(3); root.l = new N(9); root.r = new N(20); root.r.l = new N(15); root.r.r = new N(7);
        java.util.Map<Integer, java.util.List<Integer>> m = new java.util.TreeMap<>();
        dfs(root, 0, m);
        System.out.println(m.values());
    }
    static void dfs(N u, int col, java.util.Map<Integer, java.util.List<Integer>> m) {
        if (u == null) return;
        m.computeIfAbsent(col, k -> new java.util.ArrayList<>()).add(u.v);
        dfs(u.l, col - 1, m); dfs(u.r, col + 1, m);
    }
}
```

### Problem 12 — RecoverBST (H)

```java
class RecoverBST {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N a, b, prev;
    static void inorder(N u) {
        if (u == null) return;
        inorder(u.l);
        if (prev != null && prev.v > u.v) { if (a == null) a = prev; b = u; }
        prev = u;
        inorder(u.r);
    }
    public static void main(String[] args) {
        N root = new N(3); root.l = new N(1); root.r = new N(4); root.r.l = new N(2);
        inorder(root); int t = a.v; a.v = b.v; b.v = t;
        System.out.println("recovered");
    }
}
```

### Problem 13 — Serialize (H)

```java
class Serialize {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static String ser(N u) {
        if (u == null) return "#";
        return u.v + "," + ser(u.l) + "," + ser(u.r);
    }
    static int idx = 0;
    static N des(String[] t) {
        if (idx >= t.length || t[idx].equals("#")) { idx++; return null; }
        N u = new N(Integer.parseInt(t[idx++])); u.l = des(t); u.r = des(t); return u;
    }
    public static void main(String[] args) { System.out.println("see day-18 demo"); }
}
```

### Problem 14 — Morris (H)

```java
class Morris {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N root = new N(1); root.l = new N(2); root.r = new N(3);
        N cur = root;
        while (cur != null) {
            if (cur.l == null) { System.out.print(cur.v + " "); cur = cur.r; }
            else {
                N pre = cur.l;
                while (pre.r != null && pre.r != cur) pre = pre.r;
                if (pre.r == null) { pre.r = cur; cur = cur.l; }
                else { pre.r = null; System.out.print(cur.v + " "); cur = cur.r; }
            }
        }
    }
}
```

### Problem 15 — MaxPath (H)

```java
class MaxPath {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static int best = Integer.MIN_VALUE;
    static int gain(N u) { if (u == null) return 0; int l = Math.max(0, gain(u.l)), r = Math.max(0, gain(u.r)); best = Math.max(best, l + r + u.v); return u.v + Math.max(l, r); }
    public static void main(String[] args) {
        N root = new N(-10); root.l = new N(9); root.r = new N(20); root.r.l = new N(15); root.r.r = new N(7);
        gain(root); System.out.println(best);
    }
}
```

