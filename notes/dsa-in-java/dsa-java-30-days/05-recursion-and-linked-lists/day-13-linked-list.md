# Day 13 — Linked List

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Explain why linked lists exist (and when to prefer them)
- Implement a singly linked list from scratch
- Insert, delete, traverse, search, reverse
- Find the middle node using fast/slow pointers
- Find the nth-from-end node
- Detect a cycle using Floyd's algorithm

---

# 1. Introduction

A linked list is a chain of nodes connected by pointers. Unlike arrays, nodes don't need to be contiguous in memory, so insertions/deletions at known positions are O(1).

---

# 2. Why Do We Need This?

- **Dynamic size** — no need to resize.
- **O(1) insertion/deletion at a known position** — no shifting.
- **No wasted memory** — allocate only what's used.

Trade-offs:
- **No random access** — getting the kth element is O(k).
- **Extra memory per node** for the pointer.

---

# 3. Core Concept — Singly Linked List

```
HEAD
 ↓
[10|•] → [20|•] → [30|•] → [40|null]
```

A node has:
- `data` — the value.
- `next` — reference to the next node (or `null`).

```java
class Node {
    int data;
    Node next;
    Node(int data) { this.data = data; }
}
```

---

# 4. Real-World Analogy

A treasure hunt: each clue tells you where the next one is. You can skip clues by following pointers. But to find clue #42, you must walk from clue #1.

---

# 5. Java Implementation — `LinkedListDemo.java`

```java
public class LinkedListDemo {

    static class Node {
        int data;
        Node next;
        Node(int data) { this.data = data; this.next = null; }
    }

    static Node append(Node head, int data) {
        Node n = new Node(data);
        if (head == null) return n;
        Node cur = head;
        while (cur.next != null) cur = cur.next;
        cur.next = n;
        return head;
    }

    static Node prepend(Node head, int data) {
        Node n = new Node(data);
        n.next = head;
        return n;
    }

    static Node delete(Node head, int data) {
        if (head == null) return null;
        if (head.data == data) return head.next;
        Node cur = head;
        while (cur.next != null && cur.next.data != data) cur = cur.next;
        if (cur.next != null) cur.next = cur.next.next;
        return head;
    }

    static void printList(Node head) {
        for (Node cur = head; cur != null; cur = cur.next) System.out.print(cur.data + " -> ");
        System.out.println("null");
    }

    static int length(Node head) {
        int count = 0;
        for (Node cur = head; cur != null; cur = cur.next) count++;
        return count;
    }

    static Node search(Node head, int target) {
        for (Node cur = head; cur != null; cur = cur.next)
            if (cur.data == target) return cur;
        return null;
    }

    static Node reverse(Node head) {
        Node prev = null, cur = head;
        while (cur != null) {
            Node nxt = cur.next;
            cur.next = prev;
            prev = cur;
            cur = nxt;
        }
        return prev;
    }

    static Node middle(Node head) {
        Node slow = head, fast = head;
        while (fast != null && fast.next != null) {
            slow = slow.next;
            fast = fast.next.next;
        }
        return slow;
    }

    static Node nthFromEnd(Node head, int n) {
        Node ahead = head;
        for (int i = 0; i < n; i++) {
            if (ahead == null) return null;
            ahead = ahead.next;
        }
        Node behind = head;
        while (ahead != null) {
            ahead = ahead.next;
            behind = behind.next;
        }
        return behind;
    }

    static boolean hasCycle(Node head) {
        Node slow = head, fast = head;
        while (fast != null && fast.next != null) {
            slow = slow.next;
            fast = fast.next.next;
            if (slow == fast) return true;
        }
        return false;
    }

    public static void main(String[] args) {
        Node head = null;
        for (int v : new int[]{1, 2, 3, 4}) head = append(head, v);
        head = prepend(head, 0);
        printList(head);

        head = delete(head, 2);
        printList(head);

        System.out.println("length      = " + length(head));
        System.out.println("search(3)   = " + (search(head, 3) != null));
        head = reverse(head);
        printList(head);
        System.out.println("middle      = " + middle(head).data);
        System.out.println("2nd fromEnd = " + nthFromEnd(head, 2).data);

        // Cycle test: 1->2->3->4->2 (cycle)
        Node cyc = new Node(1); cyc.next = new Node(2); cyc.next.next = new Node(3);
        cyc.next.next.next = new Node(4); cyc.next.next.next.next = cyc.next;
        System.out.println("hasCycle    = " + hasCycle(cyc));
    }
}
```

Walkthrough:

- `append`: traverse to the tail, link new node.
- `prepend`: new node's `next` is the old head; return new node.
- `delete`: special-case the head; otherwise walk with `cur` and unlink `cur.next`.
- `printList`: simple traversal.
- `reverse`: classic three-pointer technique (`prev`, `cur`, `nxt`).
- `middle`: slow moves 1 step, fast moves 2 — when fast ends, slow is at middle.
- `nthFromEnd`: advance one pointer by n, then move both until the first hits null.
- `hasCycle`: Floyd's algorithm. If there's a cycle, fast catches up to slow.

---

# 6. Dry Run — Reverse `[1→2→3→4→null]`

| Step | prev | cur | cur.next | result |
|------|------|-----|----------|--------|
| init | null | 1   | 2        | start  |
| 1    | 1    | 2   | 3        | 1→null |
| 2    | 2    | 3   | 4        | 2→1→null |
| 3    | 3    | 4   | null     | 3→2→1→null |
| 4    | 4    | null| —        | 4→3→2→1→null |

Return `prev = 4`. ✓

---

# 7. When to Use Linked List

| Use when | Avoid when |
|---|---|
| Frequent insert/delete at head | Frequent random access by index |
| Unknown or rapidly changing size | Cache-friendly iteration matters |
| Implementing stacks, queues, hash chains | Memory per element matters (extra pointer) |

---

# 8. Common Mistakes

1. **Losing the head** — never reassign `head` without saving.
2. **Forgetting to update `head`** after `prepend` or `delete(head)`.
3. **NullPointerException** when traversing past the end.
4. **Cycle causes infinite loop** — always check `fast.next != null`.
5. **Off-by-one in `nthFromEnd`** — advance `ahead` by `n` (not `n-1`).

---

# 9. Interview Questions

### Q1. Array vs Linked List?
Array: O(1) access, O(n) insert/delete. Linked list: O(n) access, O(1) insert/delete at known position.

### Q2. How to find the middle in one pass?
Fast/slow pointers.

### Q3. Floyd's cycle detection?
Slow moves 1, fast moves 2. If they meet, cycle exists.

### Q4. Why is reverse O(n)?
Each node is visited and re-pointed exactly once.

---

# 10. Practice Problems

## 🟢 Easy

### 1. Traverse and Print
**Input:** `1→2→3→4` → **Output:** `1 2 3 4`

### 2. Length of List
**Input:** `1→2→3` → **Output:** `3`

### 3. Search an Element
**Input:** `list=1→2→3, target=2` → **Output:** `true`

### 4. Prepend
**Input:** `2→3, prepend 1` → **Output:** `1→2→3`

### 5. Delete Head
**Input:** `1→2→3, delete 1` → **Output:** `2→3`

## 🟡 Medium

### 6. Reverse a List
**Input:** `1→2→3→4` → **Output:** `4→3→2→1`

### 7. Middle Node
**Input:** `1→2→3→4→5` → **Output:** `3`

### 8. Cycle Detection
**Input:** `1→2→3→4→2` (cycle) → **Output:** `true`

### 9. N-th From End
**Input:** `1→2→3→4→5, n=2` → **Output:** `4`

### 10. Remove Duplicates
**Input:** `1→1→2→3→3` → **Output:** `1→2→3`

## 🔴 Hard

### 11. Reverse in Groups of K
**Input:** `1→2→3→4→5, k=2` → **Output:** `2→1→4→3→5`

### 12. Merge Two Sorted Lists
**Input:** `1→2→4, 1→3→4` → **Output:** `1→1→2→3→4→4`

### 13. Add Two Numbers (LeetCode 2)
**Input:** `(2→4→3) + (5→6→4) = 807` → **Output:** `7→0→8`

### 14. Sort List (merge sort)
**Input:** `4→2→1→3` → **Output:** `1→2→3→4`

### 15. Rotate List
**Input:** `1→2→3→4→5, k=2` → **Output:** `4→5→1→2→3`

---

# 11. Practice Hints

## Easy
1. While loop with `cur = cur.next`.
2. Counter.
3. While loop, return when match.
4. New node → old head.
5. Return `head.next`.

## Medium
6. Three-pointer reversal.
7. Slow/fast.
8. Floyd.
9. Two pointers, n apart.
10. Set or HashSet, or in-place skipping.

## Hard
11. Reverse first K, recurse on rest.
12. Dummy + tail.
13. Carry, dummy head.
14. Find middle, merge sort halves.
15. Make circular, find new head.

---

# 12. Revision Checklist

- [ ] Can implement Node
- [ ] Can do append, prepend, delete, search
- [ ] Can reverse a list
- [ ] Can find middle and nth-from-end
- [ ] Can detect a cycle

---

# 13. Key Takeaways

- Singly linked list: data + next pointer.
- Reverse: three-pointer technique.
- Middle / cycle: slow/fast pointers.
- nth-from-end: advance by n then walk together.

Tomorrow: **Advanced Linked Lists** — doubly, circular, Floyd, group reverse.


## Solutions

### Problem 1 — PrintLL (E)

```java
class PrintLL {
    static class N { int v; N n; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(3);
        for (N c = h; c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 2 — LenLL (E)

```java
class LenLL {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static int len(N h) { return h == null ? 0 : 1 + len(h.n); }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(3);
        System.out.println(len(h));
    }
}
```

### Problem 3 — SearchLL (E)

```java
class SearchLL {
    static class N { int v; N n; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(3);
        int target = 2; N c = h;
        while (c != null && c.v != target) c = c.n;
        System.out.println(c != null);
    }
}
```

### Problem 4 — Prepend (E)

```java
class Prepend {
    static class N { int v; N n; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N h = new N(2); h.n = new N(3);
        N n = new N(1); n.n = h;
        for (N c = n; c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 5 — DelHead (E)

```java
class DelHead {
    static class N { int v; N n; N(int v) { this.v = v; } }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(3);
        h = h.n;
        for (N c = h; c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 6 — RevLL (M)

```java
class RevLL {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N rev(N h) {
        N prev = null, cur = h;
        while (cur != null) { N nxt = cur.n; cur.n = prev; prev = cur; cur = nxt; }
        return prev;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(3);
        for (N c = rev(h); c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 7 — MidLL (M)

```java
class MidLL {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N mid(N h) {
        N s = h, f = h;
        while (f != null && f.n != null) { s = s.n; f = f.n.n; }
        return s;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(3); h.n.n.n = new N(4);
        System.out.println(mid(h).v);
    }
}
```

### Problem 8 — CycleLL (M)

```java
class CycleLL {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static boolean has(N h) {
        N s = h, f = h;
        while (f != null && f.n != null) {
            s = s.n; f = f.n.n;
            if (s == f) return true;
        }
        return false;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = h;
        System.out.println(has(h));
    }
}
```

### Problem 9 — NthEnd (M)

```java
class NthEnd {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N nth(N h, int k) {
        N fast = h;
        for (int i = 0; i < k && fast != null; i++) fast = fast.n;
        if (fast == null) return null;
        N slow = h;
        while (fast.n != null) { slow = slow.n; fast = fast.n; }
        return slow;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(3); h.n.n.n = new N(4);
        System.out.println(nth(h, 2).v);   // 3
    }
}
```

### Problem 10 — DedupLL (M)

```java
class DedupLL {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N dedup(N h) {
        N cur = h;
        while (cur != null && cur.n != null) {
            if (cur.v == cur.n.v) cur.n = cur.n.n;
            else cur = cur.n;
        }
        return h;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(1); h.n.n = new N(2); h.n.n.n = new N(3); h.n.n.n.n = new N(3);
        for (N c = dedup(h); c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 11 — RevK (H)

```java
class RevK {
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

### Problem 12 — Merge2 (H)

```java
class Merge2 {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N merge(N a, N b) {
        N d = new N(0), t = d;
        while (a != null && b != null) { if (a.v <= b.v) { t.n = a; a = a.n; } else { t.n = b; b = b.n; } t = t.n; }
        t.n = a == null ? b : a; return d.n;
    }
    public static void main(String[] args) {
        N a = new N(1); a.n = new N(2); a.n.n = new N(4);
        N b = new N(1); b.n = new N(3); b.n.n = new N(4);
        for (N c = merge(a, b); c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 13 — AddTwo (H)

```java
class AddTwo {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N add(N a, N b) {
        N d = new N(0), t = d; int carry = 0;
        while (a != null || b != null || carry != 0) {
            int s = carry + (a == null ? 0 : a.v) + (b == null ? 0 : b.v);
            t.n = new N(s % 10); t = t.n; carry = s / 10;
            if (a != null) a = a.n; if (b != null) b = b.n;
        }
        return d.n;
    }
    public static void main(String[] args) {
        N a = new N(2); a.n = new N(4); a.n.n = new N(3);
        N b = new N(5); b.n = new N(6); b.n.n = new N(4);
        for (N c = add(a, b); c != null; c = c.n) System.out.print(c.v + " ");  // 7 0 8
    }
}
```

### Problem 14 — SortLL (H)

```java
class SortLL {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N sort(N h) {
        if (h == null || h.n == null) return h;
        N s = h, f = h.n;
        while (f != null && f.n != null) { s = s.n; f = f.n.n; }
        N m = s.n; s.n = null;
        return merge(sort(h), sort(m));
    }
    static N merge(N a, N b) {
        N d = new N(0), t = d;
        while (a != null && b != null) { if (a.v <= b.v) { t.n = a; a = a.n; } else { t.n = b; b = b.n; } t = t.n; }
        t.n = a == null ? b : a; return d.n;
    }
    public static void main(String[] args) {
        N h = new N(4); h.n = new N(2); h.n.n = new N(1); h.n.n.n = new N(3);
        for (N c = sort(h); c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

### Problem 15 — Rotate (H)

```java
class Rotate {
    static class N { int v; N n; N(int v) { this.v = v; } }
    static N rot(N h, int k) {
        if (h == null) return null;
        N tail = h; int len = 1;
        while (tail.n != null) { tail = tail.n; len++; }
        k %= len;
        if (k == 0) return h;
        tail.n = h;
        for (int i = 0; i < len - k; i++) tail = tail.n;
        N newH = tail.n; tail.n = null;
        return newH;
    }
    public static void main(String[] args) {
        N h = new N(1); h.n = new N(2); h.n.n = new N(3); h.n.n.n = new N(4); h.n.n.n.n = new N(5);
        for (N c = rot(h, 2); c != null; c = c.n) System.out.print(c.v + " ");
    }
}
```

