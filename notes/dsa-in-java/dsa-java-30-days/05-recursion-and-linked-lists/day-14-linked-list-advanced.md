# Day 14 — Advanced Linked Lists

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Implement a doubly linked list
- Implement a circular linked list
- Detect the start of a cycle (Floyd's extension)
- Merge two sorted lists
- Find the intersection of two lists
- Check palindrome
- Reverse in groups of k

---

# 1. Introduction

Yesterday's singly linked list was the foundation. Today we extend: doubly, circular, and the canonical problems you must know by heart.

---

# 2. Doubly Linked List

Each node has `prev` and `next`.

```
null ← [10|•] ⇄ [20|•] ⇄ [30|null]
```

Trade-off: extra pointer per node, but O(1) delete given a node pointer.

---

# 3. Circular Linked List

The last node's `next` points back to the head.

```
HEAD
 ↓
[1|•] → [2|•] → [3|•] ─┐
 ↑_____________________|
```

---

# 4. Java Implementation — `AdvancedLinkedListDemo.java`

```java
public class AdvancedLinkedListDemo {

    static class Node {
        int data;
        Node next;
        Node(int d) { data = d; }
    }

    // --- DOUBLY ---
    static class DNode {
        int data;
        DNode prev, next;
        DNode(int d) { data = d; }
    }

    static DNode dllAppend(DNode head, int data) {
        DNode n = new DNode(data);
        if (head == null) return n;
        DNode cur = head;
        while (cur.next != null) cur = cur.next;
        cur.next = n; n.prev = cur;
        return head;
    }

    static DNode dllDelete(DNode head, DNode target) {
        if (target.prev != null) target.prev.next = target.next;
        else head = target.next;
        if (target.next != null) target.next.prev = target.prev;
        return head;
    }

    static void dllPrint(DNode head) {
        for (DNode cur = head; cur != null; cur = cur.next) System.out.print(cur.data + " ⇄ ");
        System.out.println("null");
    }

    // --- CYCLE detection (Floyd) ---
    static Node cycleStart(Node head) {
        Node slow = head, fast = head;
        while (fast != null && fast.next != null) {
            slow = slow.next; fast = fast.next.next;
            if (slow == fast) {
                Node p1 = head, p2 = slow;
                while (p1 != p2) { p1 = p1.next; p2 = p2.next; }
                return p1;
            }
        }
        return null;
    }

    // --- MERGE two sorted ---
    static Node merge(Node a, Node b) {
        Node dummy = new Node(0), tail = dummy;
        while (a != null && b != null) {
            if (a.data <= b.data) { tail.next = a; a = a.next; }
            else                  { tail.next = b; b = b.next; }
            tail = tail.next;
        }
        tail.next = (a != null) ? a : b;
        return dummy.next;
    }

    // --- INTERSECTION of two lists ---
    static Node intersection(Node a, Node b) {
        int la = 0, lb = 0;
        for (Node c = a; c != null; c = c.next) la++;
        for (Node c = b; c != null; c = c.next) lb++;
        Node p1 = a, p2 = b;
        for (int i = 0; i < Math.abs(la - lb); i++) {
            if (la > lb) p1 = p1.next; else p2 = p2.next;
        }
        while (p1 != null && p2 != null) {
            if (p1 == p2) return p1;
            p1 = p1.next; p2 = p2.next;
        }
        return null;
    }

    // --- PALINDROME check ---
    static boolean isPalindrome(Node head) {
        if (head == null || head.next == null) return true;
        Node slow = head, fast = head;
        while (fast.next != null && fast.next.next != null) {
            slow = slow.next; fast = fast.next.next;
        }
        Node second = reverse(slow.next);
        Node p1 = head, p2 = second;
        boolean ok = true;
        while (p2 != null) {
            if (p1.data != p2.data) { ok = false; break; }
            p1 = p1.next; p2 = p2.next;
        }
        slow.next = reverse(second);
        return ok;
    }
    static Node reverse(Node head) {
        Node prev = null, cur = head;
        while (cur != null) { Node nxt = cur.next; cur.next = prev; prev = cur; cur = nxt; }
        return prev;
    }

    // --- REVERSE IN GROUPS OF K ---
    static Node reverseKGroup(Node head, int k) {
        Node cur = head; int count = 0;
        while (cur != null && count < k) { cur = cur.next; count++; }
        if (count < k) return head;
        Node prev = null; cur = head;
        for (int i = 0; i < k; i++) { Node nxt = cur.next; cur.next = prev; prev = cur; cur = nxt; }
        head.next = reverseKGroup(cur, k);
        return prev;
    }

    // --- CIRCULAR helpers ---
    static Node makeCircular(Node head) {
        if (head == null) return null;
        Node cur = head;
        while (cur.next != null) cur = cur.next;
        cur.next = head;
        return head;
    }

    public static void main(String[] args) {
        // Doubly
        DNode dh = null;
        for (int v : new int[]{1,2,3}) dh = dllAppend(dh, v);
        System.out.print("DLL: "); dllPrint(dh);

        // Cycle start
        Node cs = new Node(1); cs.next = new Node(2); cs.next.next = new Node(3);
        cs.next.next.next = new Node(4); cs.next.next.next.next = cs.next.next;
        System.out.println("cycleStart.data = " + cycleStart(cs).data);

        // Merge
        Node a = new Node(1); a.next = new Node(2); a.next.next = new Node(4);
        Node b = new Node(1); b.next = new Node(3); b.next.next = new Node(4);
        Node m = merge(a, b);
        StringBuilder sb = new StringBuilder("merge: ");
        for (Node c = m; c != null; c = c.next) sb.append(c.data).append(" ");
        System.out.println(sb);

        // Intersection
        Node x1 = new Node(4); x1.next = new Node(1); x1.next.next = new Node(8); x1.next.next.next = new Node(9);
        Node x2 = new Node(5); x2.next = x1.next.next;          // share 8
        System.out.println("intersection.data = " + intersection(x1, x2).data);

        // Palindrome
        Node pal = new Node(1); pal.next = new Node(2); pal.next.next = new Node(2); pal.next.next.next = new Node(1);
        System.out.println("isPalindrome(1,2,2,1) = " + isPalindrome(pal));

        // Reverse in groups of 2
        Node rg = new Node(1); rg.next = new Node(2); rg.next.next = new Node(3);
        rg.next.next.next = new Node(4); rg.next.next.next.next = new Node(5);
        Node revK = reverseKGroup(rg, 2);
        StringBuilder sb2 = new StringBuilder("reverseKGroup: ");
        for (Node c = revK; c != null; c = c.next) sb2.append(c.data).append(" ");
        System.out.println(sb2);
    }
}
```

Walkthrough:

- **DLL**: `prev` makes deletion O(1) when given the target.
- **cycleStart**: once slow and fast meet, reset one pointer to head and step both one-at-a-time — they meet at the cycle's start.
- **merge**: dummy-head pattern avoids special-casing the head.
- **intersection**: equalise lengths by walking the longer list first; then walk together until they coincide.
- **isPalindrome**: find middle, reverse second half, compare, restore.
- **reverseKGroup**: reverse first k, recurse on the rest, stitch.

---

# 5. Dry Run — `cycleStart` on `1→2→3→4→3→...`

| Step | slow | fast |
|------|------|------|
| 0    | 1    | 1    |
| 1    | 2    | 3    |
| 2    | 3    | 3    |
| 3    | 4    | 4    |  ← meet here

Reset `p1 = head (1)`, keep `p2 = 4`. Walk together:

| Step | p1 | p2 |
|------|----|----|
| 0    | 1  | 4  |
| 1    | 2  | 3  |
| 2    | 3  | 3  |  ← meet at 3 (cycle start) ✓

---

# 6. The LRU Cache (skeleton + interview-class design)

`LRUCache<K,V>` uses a **doubly linked list** + **HashMap**:

- DLL stores nodes in recency order; `head` is most recently used, `tail` is least.
- HashMap maps `key → node` for O(1) lookup.

`get(key)`: if found, move node to head, return value.
`put(key, val)`: if at capacity, evict tail; insert new node at head; map key.

```java
class LRU<K, V> {
    class Node { K key; V val; Node prev, next; Node(K k, V v) { key=k; val=v; } }
    final int cap;
    final Map<K, Node> map = new HashMap<>();
    final Node head = new Node(null, null), tail = new Node(null, null);

    LRU(int cap) {
        this.cap = cap;
        head.next = tail; tail.prev = head;
    }
    V get(K k) {
        Node n = map.get(k);
        if (n == null) return null;
        moveToHead(n);
        return n.val;
    }
    void put(K k, V v) {
        Node n = map.get(k);
        if (n != null) { n.val = v; moveToHead(n); return; }
        n = new Node(k, v);
        map.put(k, n);
        addToHead(n);
        if (map.size() > cap) {
            Node lru = tail.prev;
            remove(lru);
            map.remove(lru.key);
        }
    }
    void addToHead(Node n) { n.next = head.next; n.prev = head; head.next.prev = n; head.next = n; }
    void remove(Node n) { n.prev.next = n.next; n.next.prev = n.prev; }
    void moveToHead(Node n) { remove(n); addToHead(n); }
}
```

---

# 7. Common Mistakes

1. **Not restoring the list after `isPalindrome`** — if the function is supposed to be non-destructive.
2. **Off-by-one in `reverseKGroup`** — count k nodes first; if fewer remain, don't reverse.
3. **Forgetting `cap` check** in LRU.
4. **Cycle-start uses Floyd step 2, not step 1**.

---

# 8. Interview Questions

### Q1. Doubly vs singly?
Doubly: O(1) delete given a node; singly: O(n) (need predecessor).

### Q2. Why the second phase in cycle detection?
To find where the cycle starts. Floyd's meeting point ≠ start.

### Q3. Reverse in groups: time/space?
Time O(n), space O(n/k) for recursion; O(1) iteratively.

### Q4. LRU complexity?
Both `get` and `put` are O(1).

---

# 9. Practice Problems

## 🟢 Easy

### 1. Doubly Linked List Insert at Head
**Input:** `1⇄2⇄3, insert 0` → **Output:** `0⇄1⇄2⇄3`

### 2. Circular Linked List Length
**Input:** `1→2→3→1→...` → **Output:** `3`

### 3. Traverse Circular List Once
**Input:** circular 1→2→3 → print each once.

### 4. Insert in Sorted DLL
**Input:** `1⇄3⇄5, insert 4` → **Output:** `1⇄3⇄4⇄5`

### 5. Check If List Is Circular
**Input:** 1→2→3→null vs 1→2→3→1 → output `false`/`true`

## 🟡 Medium

### 6. Cycle Start (Floyd extension)
**Input:** `1→2→3→4→2` (cycle at 2) → **Output:** `2`

### 7. Merge Two Sorted Lists
**Input:** `1→2→4, 1→3→4` → **Output:** `1→1→2→3→4→4`

### 8. Intersection of Two Lists
**Input:** two lists sharing tail → **Output:** first shared node.

### 9. Palindrome Linked List
**Input:** `1→2→2→1` → **Output:** `true`

### 10. Reverse in Groups of K
**Input:** `1→2→3→4→5, k=2` → **Output:** `2→1→4→3→5`

## 🔴 Hard

### 11. LRU Cache (O(1) get/put)
Full implementation.

### 12. Copy List With Random Pointer
**Input:** `7→13→11→10→1, random refs` → deep copy.

### 13. Flatten a Multilevel Doubly List
**Input:** nested list → flat list.

### 14. Reverse Nodes in K-Group (full)
Iterative, O(1) extra.

### 15. Trapping Rain Water in DLL (each node = bar)
**Input:** bars heights → **Output:** trapped water.

---

# 10. Practice Hints

## Easy
1. New node, link with old head.
2. Track visited or stop when seen head twice.
3. do-while or stop after length.
4. Find predecessor, insert.
5. Use two pointers.

## Medium
6. Floyd + reset one to head.
7. Dummy + tail.
8. Length-diff walk.
9. Mid + reverse + compare.
10. Reverse K then recurse.

## Hard
11. HashMap + DLL.
12. HashMap old→new, two-pass.
13. DFS into child.
14. Iterative group reversal.
15. Stack-based.

---

# 11. Revision Checklist

- [ ] Can implement doubly LL
- [ ] Can detect cycle start with Floyd
- [ ] Can merge two sorted lists
- [ ] Can check palindrome
- [ ] Can reverse in groups of K

---

# 12. Key Takeaways

- Doubly: O(1) delete with target pointer.
- Cycle start: Floyd's two-phase algorithm.
- Palindrome: mid + reverse + compare.
- LRU = HashMap + DLL.

Tomorrow: **Stack**.


## Solutions

### Problem 1 — DLLInsertHead (E)

```java
class DLLInsertHead {
    static class N { int v; N p, n; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N head = new N(2); head.n = new N(3);
        N x = new N(1); x.n = head; head.p = x;
        for (N c = x; c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 2 — CircLen (E)

```java
class CircLen {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static int len(N h) {
        if (h == null) return 0;
        int c = 1; N cur = h.n;
        while (cur != h) { c++; cur = cur.n; }
        return c;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(3); h.n.n.n = h;
        System.out.println(len(h));
    }
}
```

### Problem 3 — CircOnce (E)

```java
class CircOnce {
    static class N { int v; N n; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = h;
        for (N c = h.n; c != h; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 4 — InsSorted (E)

```java
class InsSorted {
    static class N { int v; N p, n; N(int v) { this.v = v; } }
    static N ins(N head, int x) {
        N cur = head;
        while (cur != null && cur.v < x) cur = cur.n;
        N n = new N(x);
        if (cur == null) {
            N tail = head; while (tail.n != null) tail = tail.n;
            tail.n = n; n.p = tail;
        } else {
            n.n = cur; if (cur.p != null) cur.p.n = n; else head = n;
            n.p = cur.p; cur.p = n;
        }
        return head;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(3); h.n.p = h; h.n.n = new N(5); h.n.n.p = h.n;
        h = ins(h, 4);
        for (N c = h; c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 5 — IsCirc (E)

```java
class IsCirc {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static boolean isCirc(N h) {
        if (h == null) return false;
        N s = h, f = h;
        do {
            if (f == null || f.n == null) return false;
            s = s.n; f = f.n.n;
        } while (s != f && f != null && f.n != null);
        return s == f;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = h;
        System.out.println(isCirc(h));
    }
}
```

### Problem 6 — CycleStart (M)

```java
class CycleStart {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N start(N h) {
        N s = h, f = h;
        while (f != null && f.n != null) { s = s.n; f = f.n.n; if (s == f) break; }
        if (f == null || f.n == null) return null;
        s = h;
        while (s != f) { s = s.n; f = f.n; }
        return s;
    }
    public static void main(String[] args) {
        N a = new N(1); N b = new N(2); N c = new N(3); N d = new N(4);
        a.n = b; b.n = c; c.n = d; d.n = b;
        System.out.println(start(a).v);
    }
}
```

### Problem 7 — Merge2LL (M)

```java
class Merge2LL {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N merge(N a, N b) {
        N d = new N(0), t = d;
        while (a != null && b != null) { if (a.v <= b.v) { t.n = a; a = a.n; } else { t.n = b; b = b.n; } t = t.n; }
        t.n = a == null ? b : a; return d.n;
    }
    public static void main(String[] args) {
        N a = new N(1); a.n = new N(2);
        N b = new N(1); b.n = new N(3);
        for (N c = merge(a, b); c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 8 — Intersect (M)

```java
class Intersect {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N inter(N a, N b) {
        N p1 = a, p2 = b;
        while (p1 != p2) {
            p1 = p1 == null ? b : p1.n;
            p2 = p2 == null ? a : p2.n;
        }
        return p1;
    }
    public static void main(String[] args) {
        N c = new N(8); c.n = new N(10);
        N a = new N(1); a.n = new N(3); a.n.n = c;
        N b = new N(2); b.n = new N(6); b.n.n = c;
        System.out.println(inter(a, b).v);
    }
}
```

### Problem 9 — PalLL (M)

```java
class PalLL {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static boolean isPal(N h) {
        N s = h, f = h;
        while (f.n != null) { s = s.n; f = f.n.n; }
        // reverse second half
        N prev = null, cur = s;
        while (cur != null) { N nxt = cur.n; cur.n = prev; prev = cur; cur = nxt; }
        // compare
        N p1 = h, p2 = prev;
        while (p2 != null) { if (p1.v != p2.v) return false; p1 = p1.n; p2 = p2.n; }
        return true;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(2); h.n.n.n = new N(1);
        System.out.println(isPal(h));
    }
}
```

### Problem 10 — RevKFull (M)

```java
class RevKFull {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N revK(N h, int k) {
        if (h == null) return null;
        N prev = null, cur = h; int i = 0;
        while (cur != null && i < k) { N nxt = cur.n; cur.n = prev; prev = cur; cur = nxt; i++; }
        h.n = revK(cur, k);
        return prev;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(3); h.n.n.n = new N(4);
        for (N c = revK(h, 2); c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 11 — LRUCacheLL (H)

```java
class LRUCacheLL {
    static class Node { int k, v; Node p, n; Node(int k, int v) { this.k=k; this.v=v; } }
    java.util.Map<Integer,Node> m = new java.util.HashMap<>();
    Node head = new Node(0,0), tail = new Node(0,0); int cap;
    LRUCacheLL(int c) { cap = c; head.n = tail; tail.p = head; }
    int get(int k) {
        if (!m.containsKey(k)) return -1;
        Node n = m.get(k); rm(n); add(n); return n.v;
    }
    void put(int k, int v) {
        if (m.containsKey(k)) { Node n = m.get(k); n.v = v; rm(n); add(n); return; }
        Node n = new Node(k, v); m.put(k, n); add(n);
        if (m.size() > cap) { Node r = tail.p; rm(r); m.remove(r.k); }
    }
    void rm(Node n) { n.p.n = n.n; n.n.p = n.p; }
    void add(Node n) { n.n = head.n; n.p = head; head.n.p = n; head.n = n; }
    public static void main(String[] args) {
        LRUCacheLL l = new LRUCacheLL(2);
        l.put(1, 10); l.put(2, 20);
        System.out.println(l.get(1));
    }
}
```

### Problem 12 — CopyRand (H)

```java
class CopyRand {
    static class N { int v; N n, rand; N(int v) { this.v = v; } }
    static N copy(N h) {
        if (h == null) return null;
        // 1. interleave
        for (N c = h; c != null; c = c.n.n) { N n = new N(c.v); n.n = c.n; c.n = n; }
        // 2. copy rand
        for (N c = h; c != null; c = c.n.n) if (c.rand != null) c.n.rand = c.rand.n;
        // 3. separate
        N dummy = new N(0), t = dummy;
        for (N c = h; c != null; c = c.n) { t.n = c.n; t = t.n; c.n = c.n.n; }
        return dummy.n;
    }
    public static void main(String[] args) { System.out.println("see day-13 demo for usage"); }
}
```

### Problem 13 — FlattenML (H)

```java
class FlattenML {
    static class N { int v; N p, n, child; N(int v) { this.v = v; } }
    static N flatten(N h) {
        if (h == null) return h;
        N cur = h;
        while (cur != null) {
            if (cur.child != null) {
                N child = flatten(cur.child);
                N next = cur.n;
                cur.n = child; child.p = cur;
                while (cur.n != null) cur = cur.n;
                cur.n = next;
                if (next != null) next.p = cur;
            }
            cur = cur.n;
        }
        return h;
    }
    public static void main(String[] args) { System.out.println("complex — see LeetCode 430 for full demo"); }
}
```

### Problem 14 — RevKGroupFull (H)

```java
class RevKGroupFull {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N revK(N h, int k) {
        N cur = h; int c = 0; while (cur != null && c < k) { cur = cur.n; c++; }
        if (c < k) return h;
        cur = h; c = 0; N prev = null;
        while (cur != null && c < k) { N nxt = cur.n; cur.n = prev; prev = cur; cur = nxt; c++; }
        if (cur != null) h.n = revK(cur, k);
        return prev;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(3); h.n.n.n = new N(4); h.n.n.n.n = new N(5);
        for (N c = revK(h, 2); c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 15 — TrapLL (H)

```java
class TrapLL {
    // Use DLL where each node's height is its value.
    static class N { int v; N p, n; N(int v) { this.v = v; } }
    static int trap(N h) {
        int w = 0; N l = h, r = h;
        while (r.n != null) r = r.n;
        int lM = 0, rM = 0;
        while (l != r) {
            if (l.v < r.v) {
                lM = Math.max(lM, l.v);
                w += lM - l.v;
                l = l.n;
            } else {
                rM = Math.max(rM, r.v);
                w += rM - r.v;
                r = r.p;
            }
        }
        return w;
    }
    public static void main(String[] args) { System.out.println("see day-21 demo"); }
}
```

