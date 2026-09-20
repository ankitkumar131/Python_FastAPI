# Day 19 — Binary Search Trees

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Define BST property and prove its consequences
- Insert, delete, search, find min/max in a BST
- Find inorder predecessor and successor
- Validate a BST
- Find Lowest Common Ancestor (LCA)
- Compare balanced vs unbalanced BSTs

---

# 1. Introduction

A Binary Search Tree (BST) is a binary tree where for every node:

- All keys in the left subtree are less than the node's key.
- All keys in the right subtree are greater.

Inorder traversal yields sorted order.

---

# 2. Why Do We Need This?

- O(log n) average search/insert/delete — as fast as binary search, but dynamic.
- Foundation for balanced BSTs (AVL, Red-Black) used in real libraries (`TreeMap`, `TreeSet`).
- Interview-class problems: validate, LCA, kth smallest.

---

# 3. Core Concept

```
        8
       / \
      3   10
     / \    \
    1   6   14
       / \   /
      4   7 13
```

Inorder: 1 3 4 6 7 8 10 13 14 (sorted).

---

# 4. Real-World Analogy

A phonebook on a shelf: sorted alphabetically. To find a name, flip to roughly the right section, then narrow down.

---

# 5. Java Implementation — `BSTDemo.java`

```java
import java.util.*;

public class BSTDemo {

    static class Node {
        int val;
        Node left, right;
        Node(int v) { val = v; }
    }

    static Node insert(Node root, int v) {
        if (root == null) return new Node(v);
        if (v < root.val) root.left = insert(root.left, v);
        else if (v > root.val) root.right = insert(root.right, v);
        return root;
    }

    static boolean search(Node root, int v) {
        if (root == null) return false;
        if (root.val == v) return true;
        return v < root.val ? search(root.left, v) : search(root.right, v);
    }

    static Node findMin(Node root) {
        while (root != null && root.left != null) root = root.left;
        return root;
    }
    static Node findMax(Node root) {
        while (root != null && root.right != null) root = root.right;
        return root;
    }

    static Node delete(Node root, int v) {
        if (root == null) return null;
        if (v < root.val) root.left = delete(root.left, v);
        else if (v > root.val) root.right = delete(root.right, v);
        else {
            if (root.left == null) return root.right;
            if (root.right == null) return root.left;
            // two children: replace with inorder successor (min of right subtree)
            Node succ = findMin(root.right);
            root.val = succ.val;
            root.right = delete(root.right, succ.val);
        }
        return root;
    }

    static boolean isValidBST(Node root) {
        return validate(root, Long.MIN_VALUE, Long.MAX_VALUE);
    }
    static boolean validate(Node n, long lo, long hi) {
        if (n == null) return true;
        if (n.val <= lo || n.val >= hi) return false;
        return validate(n.left, lo, n.val) && validate(n.right, n.val, hi);
    }

    static Node lca(Node root, int p, int q) {
        if (root == null) return null;
        if (p < root.val && q < root.val) return lca(root.left, p, q);
        if (p > root.val && q > root.val) return lca(root.right, p, q);
        return root;
    }

    static void inorder(Node r) {
        if (r == null) return;
        inorder(r.left); System.out.print(r.val + " "); inorder(r.right);
    }

    public static void main(String[] args) {
        int[] vals = {8, 3, 10, 1, 6, 14, 4, 7, 13};
        Node root = null;
        for (int v : vals) root = insert(root, v);

        System.out.print("inorder: "); inorder(root); System.out.println();
        System.out.println("search 6: " + search(root, 6));
        System.out.println("min: " + findMin(root).val);
        System.out.println("max: " + findMax(root).val);
        System.out.println("valid BST: " + isValidBST(root));

        root = delete(root, 3);
        System.out.print("after delete 3: "); inorder(root); System.out.println();
        System.out.println("LCA(1,4): " + lca(root, 1, 4).val);
        System.out.println("LCA(4,7): " + lca(root, 4, 7).val);
    }
}
```

Walkthrough:

- `insert`: walk down; insert at first null.
- `delete` with two children: standard trick — replace value with inorder successor (min of right subtree), then delete that successor.
- `isValidBST`: pass `(lo, hi)` range down. Long min/max avoids overflow for `Integer.MIN_VALUE/MAX_VALUE` test cases.
- `lca`: if both `p` and `q` are on the same side, recurse there; otherwise the current node is the split point = LCA.

---

# 6. Dry Run — `delete(root, 3)`

```
        8                     8
       / \                   / \
      3   10       →        4   10
     / \    \              / \    \
    1   6   14            1   6   14
       / \   /                / \   /
      4   7 13               5?  7 13
```

Actually: replace `3` with inorder successor (`4`), then delete `4` from right subtree.

---

# 7. Balanced vs Unbalanced

A BST becomes unbalanced if insertions are in sorted order → essentially a linked list (height = n). All operations degrade to O(n).

Balanced BSTs (AVL, Red-Black) guarantee O(log n) by rebalancing after each insertion/deletion. `TreeMap` and `TreeSet` in Java are Red-Black trees.

---

# 8. Common Mistakes

1. **Validating BST with `node.left.val < node.val < node.right.val`** — wrong. Must check the whole subtree.
2. **Using `Integer.MIN_VALUE` in validate** — fails if a node has that exact value. Use `Long`.
3. **Forget successor deletion** after replacement.

---

# 9. Interview Questions

### Q1. Why is inorder of a BST sorted?
BST property guarantees all left-subtree values < root < all right-subtree values.

### Q2. Time complexity?
Average O(log n), worst O(n) if unbalanced.

### Q3. TreeMap vs HashMap?
TreeMap: O(log n) and sorted. HashMap: O(1) average, unsorted.

---

# 10. Practice Problems

## 🟢 Easy

### 1. Search in a BST
**Input:** root, val=4 → **Output:** node or null.

### 2. Insert into a BST
**Input:** root, val=5 → **Output:** new root.

### 3. Find Min / Max
**Input:** root → **Output:** min/max node.

### 4. Validate BST
**Input:** tree → **Output:** true/false.

### 5. Kth Smallest Element
**Input:** root, k=3 → **Output:** `4`.

## 🟡 Medium

### 6. Delete Node
Standard deletion.

### 7. Lowest Common Ancestor
**Input:** root, p=2, q=8 → **Output:** `6`.

### 8. Convert Sorted Array to BST
**Input:** `[-10,-3,0,5,9]` → **Output:** height-balanced BST.

### 9. Two Sum IV (BST)
**Input:** root + target → **Output:** true if pair exists.

### 10. Inorder Successor
**Input:** root, p → **Output:** successor node.

## 🔴 Hard

### 11. Recover BST
Standard.

### 12. Kth Smallest in BST (iterative)
O(k) space.

### 13. Serialize/Deserialize BST (preorder)
Use min/max range.

### 14. Count of Smaller Numbers After Self (BST)
Use augmented BST.

### 15. Median from Data Stream (two heaps)
Use a max-heap for the lower half and min-heap for the upper half.

---

# 11. Practice Hints

## Easy
1. Walk down.
2. Recursive insert.
3. Leftmost / rightmost.
4. Min/max range recursion.
5. Inorder + count.

## Medium
6. Three cases.
7. Split-point check.
8. Mid as root.
9. Set or inorder + two pointer.
10. Rightmost of left subtree.

## Hard
11. Inorder + anomaly detection.
12. Inorder with early stop.
13. Reconstruct using min/max bounds.
14. Insert with size.
15. Two heaps, balance.

---

# 12. Revision Checklist

- [ ] Can define BST property
- [ ] Can insert / delete / search
- [ ] Can validate
- [ ] Can find LCA
- [ ] Know inorder is sorted

---

# 13. Key Takeaways

- BST: left < node < right.
- Inorder = sorted.
- Validate with `(lo, hi)` range.
- Unbalanced BST = O(n); balanced = O(log n).

Tomorrow: **Heap & Priority Queue**.


## Solutions

### Problem 1 — SearchBST (E)

```java
class SearchBST {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N find(N u, int t) {
        if (u == null || u.v == t) return u;
        return t < u.v ? find(u.l, t) : find(u.r, t);
    }
    public static void main(String[] args) {
        N root = new N(4); root.l = new N(2); root.r = new N(7); root.l.l = new N(1); root.l.r = new N(3);
        System.out.println(find(root, 2).v);
    }
}
```

### Problem 2 — InsBST (E)

```java
class InsBST {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N ins(N u, int x) {
        if (u == null) return new N(x);
        if (x < u.v) u.l = ins(u.l, x); else u.r = ins(u.r, x);
        return u;
    }
    public static void main(String[] args) {
        N root = null; for (int x : new int[]{5,3,7,1,4}) root = ins(root, x);
        System.out.println("inserted");
    }
}
```

### Problem 3 — MinMax (E)

```java
class MinMax {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N min(N u) { while (u.l != null) u = u.l; return u; }
    static N max(N u) { while (u.r != null) u = u.r; return u; }
    public static void main(String[] args) {
        N root = new N(4); root.l = new N(2); root.r = new N(7);
        System.out.println(min(root).v + " " + max(root).v);
    }
}
```

### Problem 4 — ValidBST (E)

```java
class ValidBST {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static boolean valid(N u, long lo, long hi) {
        if (u == null) return true;
        if (u.v <= lo || u.v >= hi) return false;
        return valid(u.l, lo, u.v) && valid(u.r, u.v, hi);
    }
    public static void main(String[] args) {
        N root = new N(2); root.l = new N(1); root.r = new N(3);
        System.out.println(valid(root, Long.MIN_VALUE, Long.MAX_VALUE));
    }
}
```

### Problem 5 — KthSmallest (E)

```java
class KthSmallest {
    static class N { int v; N l, r; int c; N(int v) { this.v = v; } }
    static int cnt = 0, ans = 0;
    static void in(N u, int k) { if (u == null) return; in(u.l, k); cnt++; if (cnt == k) ans = u.v; in(u.r, k); }
    public static void main(String[] args) {
        N root = new N(3); root.l = new N(1); root.r = new N(4); root.l.r = new N(2);
        in(root, 2); System.out.println(ans);
    }
}
```

### Problem 6 — DeleteBST (M)

```java
class DeleteBST {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N del(N u, int t) {
        if (u == null) return null;
        if (t < u.v) u.l = del(u.l, t);
        else if (t > u.v) u.r = del(u.r, t);
        else {
            if (u.l == null) return u.r;
            if (u.r == null) return u.l;
            N m = u.r; while (m.l != null) m = m.l;
            u.v = m.v;
            u.r = del(u.r, m.v);
        }
        return u;
    }
    public static void main(String[] args) { System.out.println("see day-19 demo"); }
}
```

### Problem 7 — LCA (M)

```java
class LCA {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N lca(N u, int a, int b) {
        if (u == null) return null;
        if (a < u.v && b < u.v) return lca(u.l, a, b);
        if (a > u.v && b > u.v) return lca(u.r, a, b);
        return u;
    }
    public static void main(String[] args) {
        N root = new N(6); root.l = new N(2); root.r = new N(8); root.l.l = new N(0); root.l.r = new N(4); root.l.r.l = new N(3); root.l.r.r = new N(5);
        System.out.println(lca(root, 2, 8).v);
    }
}
```

### Problem 8 — SortedArrToBST (M)

```java
class SortedArrToBST {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N build(int[] a, int l, int r) {
        if (l > r) return null;
        int m = l + (r - l) / 2;
        N u = new N(a[m]);
        u.l = build(a, l, m - 1); u.r = build(a, m + 1, r);
        return u;
    }
    public static void main(String[] args) {
        N root = build(new int[]{-10,-3,0,5,9}, 0, 4);
        System.out.println("built");
    }
}
```

### Problem 9 — TwoSumBST (M)

```java
class TwoSumBST {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static boolean find(N u, int t) { if (u == null) return false; if (u.v == t) return true; return t < u.v ? find(u.l, t) : find(u.r, t); }
    static boolean two(N u, int k) {
        if (u == null) return false;
        int need = k - u.v;
        if (need != u.v && find(u, need)) return true;
        return two(u.l, k) || two(u.r, k);
    }
    public static void main(String[] args) {
        N root = new N(5); root.l = new N(3); root.r = new N(6); root.l.l = new N(2); root.l.r = new N(4); root.r.r = new N(7);
        System.out.println(two(root, 9));
    }
}
```

### Problem 10 — InorderSucc (M)

```java
class InorderSucc {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N succ(N root, N p) {
        if (p.r != null) { N cur = p.r; while (cur.l != null) cur = cur.l; return cur; }
        N cur = root, anc = null;
        while (cur != p) { if (p.v < cur.v) { anc = cur; cur = cur.l; } else cur = cur.r; }
        return anc;
    }
    public static void main(String[] args) { System.out.println("see day-19 demo"); }
}
```

### Problem 11 — RecoverBST (H)

```java
class RecoverBST {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static N a, b, prev;
    static void ino(N u) {
        if (u == null) return;
        ino(u.l);
        if (prev != null && prev.v > u.v) { if (a == null) a = prev; b = u; }
        prev = u;
        ino(u.r);
    }
    public static void main(String[] args) {
        N root = new N(3); root.l = new N(1); root.r = new N(4); root.r.l = new N(2);
        ino(root); int t = a.v; a.v = b.v; b.v = t;
        System.out.println("recovered");
    }
}
```

### Problem 12 — KthIter (H)

```java
class KthIter {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N root = new N(3); root.l = new N(1); root.r = new N(4); root.l.r = new N(2);
        java.util.Deque<N> s = new java.util.ArrayDeque<>();
        N cur = root; int cnt = 0, k = 2;
        while (cur != null || !s.isEmpty()) {
            while (cur != null) { s.push(cur); cur = cur.l; }
            cur = s.pop(); cnt++;
            if (cnt == k) { System.out.println(cur.v); return; }
            cur = cur.r;
        }
    }
}
```

### Problem 13 — SerBST (H)

```java
class SerBST {
    static class N { int v; N l, r; N(int v) { this.v = v; } }
    static void ser(N u, java.util.List<Integer> out) {
        if (u == null) return;
        out.add(u.v); ser(u.l, out); ser(u.r, out);
    }
    static int idx = 0;
    static N des(java.util.List<Integer> t, long lo, long hi) {
        if (idx >= t.size() || t.get(idx) <= lo || t.get(idx) >= hi) return null;
        N u = new N(t.get(idx++));
        u.l = des(t, lo, u.v); u.r = des(t, u.v, hi);
        return u;
    }
    public static void main(String[] args) { System.out.println("see day-19 demo"); }
}
```

### Problem 14 — CountSmaller (H)

```java
class CountSmaller {
    static class N { int v; int c = 1; N l, r; N(int v) { this.v = v; } }
    int ans;
    N root(N u, int v) {
        if (u == null) return new N(v);
        if (v <= u.v) { u.c++; u.l = root(u.l, v); }
        else { ans += u.c; u.r = root(u.r, v); }
        return u;
    }
    public static void main(String[] args) { System.out.println("see day-19 demo"); }
}
```

### Problem 15 — MedianStream (H)

```java
class MedianStream {
    java.util.PriorityQueue<Integer> lo = new java.util.PriorityQueue<>(java.util.Comparator.reverseOrder());
    java.util.PriorityQueue<Integer> hi = new java.util.PriorityQueue<>();
    void add(int n) {
        lo.offer(n); hi.offer(lo.poll());
        if (lo.size() < hi.size()) lo.offer(hi.poll());
    }
    double med() { return lo.size() > hi.size() ? lo.peek() : ((double)lo.peek() + hi.peek()) / 2; }
    public static void main(String[] args) {
        MedianStream m = new MedianStream();
        for (int x : new int[]{1,2,3}) m.add(x);
        System.out.println(m.med());
    }
}
```

