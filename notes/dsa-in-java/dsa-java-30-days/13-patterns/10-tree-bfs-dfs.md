# Pattern 10 — Tree BFS / DFS

## When to use
- Any binary tree / BST problem.
- Level-order, depth, height, path sums, LCA.

## Traversal order

```
pre-order   : root, left, right
in-order    : left, root, right  (BST → sorted)
post-order  : left, right, root
level-order : BFS
```

## BFS template

```java
Deque<TreeNode> q = new ArrayDeque<>();
q.offer(root);
while (!q.isEmpty()) {
    int sz = q.size();
    for (int i = 0; i < sz; i++) {
        TreeNode u = q.poll();
        // process u
        if (u.left  != null) q.offer(u.left);
        if (u.right != null) q.offer(u.right);
    }
}
```

## DFS template

```java
void dfs(TreeNode u) {
    if (u == null) return;
    dfs(u.left);
    dfs(u.right);
}
```

## Canonical problems

### DFS
- Maximum depth
- Diameter of binary tree
- Path sum
- Lowest common ancestor
- Validate BST
- Invert binary tree
- Kth smallest in BST

### BFS
- Level order traversal
- Right side view
- Average of levels
- Zigzag level order
- Minimum depth

### BST-specific
- Insert, delete, search
- Validate BST
- K-th smallest / largest
- Convert sorted array to BST

## Diameter of binary tree

```java
int best = 0;
int depth(TreeNode u) {
    if (u == null) return 0;
    int l = depth(u.left), r = depth(u.right);
    best = Math.max(best, l + r);
    return 1 + Math.max(l, r);
}
```

## LCA (post-order, O(n))

```java
TreeNode lca(TreeNode root, TreeNode p, TreeNode q) {
    if (root == null || root == p || root == q) return root;
    TreeNode L = lca(root.left, p, q), R = lca(root.right, p, q);
    if (L != null && R != null) return root;
    return L != null ? L : R;
}
```

## Validate BST

```java
boolean valid(TreeNode u, long lo, long hi) {
    if (u == null) return true;
    if (u.val <= lo || u.val >= hi) return false;
    return valid(u.left, lo, u.val) && valid(u.right, u.val, hi);
}
```

## Complexity
- Time: O(n) for most traversals.
- Space: O(h) recursive stack, O(n) worst case (skewed tree).

## Java tips
- Always check `u == null` first.
- Use `long` for validate-BST bounds (overflow with `int`).
- For BFS, capture `q.size()` BEFORE the inner loop (size of current level).
- Serialise tree as `null`-separated list for round-trip.
