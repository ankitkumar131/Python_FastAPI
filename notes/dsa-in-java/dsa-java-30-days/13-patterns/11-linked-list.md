# Pattern 11 — Linked List

## When to use
- Reverse a list (whole or in groups).
- Detect cycle.
- Find middle.
- Merge two sorted lists.
- LRU/LFU cache.

## Core operations

```java
class ListNode { int val; ListNode next; ListNode(int v) { val = v; } }
```

## Reverse (iterative)

```java
ListNode reverse(ListNode head) {
    ListNode prev = null, cur = head;
    while (cur != null) {
        ListNode nxt = cur.next;
        cur.next = prev;
        prev = cur;
        cur = nxt;
    }
    return prev;
}
```

## Fast/slow pointers (middle)

```java
ListNode mid(ListNode head) {
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) {
        slow = slow.next;
        fast = fast.next.next;
    }
    return slow;
}
```

## Cycle detection (Floyd)

```java
boolean hasCycle(ListNode head) {
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) {
        slow = slow.next;
        fast = fast.next.next;
        if (slow == fast) return true;
    }
    return false;
}
```

## Cycle start

```java
ListNode cycleStart(ListNode head) {
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) {
        slow = slow.next;
        fast = fast.next.next;
        if (slow == fast) {
            slow = head;
            while (slow != fast) { slow = slow.next; fast = fast.next; }
            return slow;
        }
    }
    return null;
}
```

## Merge two sorted lists

```java
ListNode merge(ListNode a, ListNode b) {
    ListNode dummy = new ListNode(0), tail = dummy;
    while (a != null && b != null) {
        if (a.val < b.val) { tail.next = a; a = a.next; }
        else               { tail.next = b; b = b.next; }
        tail = tail.next;
    }
    tail.next = (a != null) ? a : b;
    return dummy.next;
}
```

## Canonical problems
- Reverse linked list (iterative + recursive)
- Reverse in k-groups
- Merge k sorted lists (heap)
- Detect cycle / find cycle start
- Palindrome linked list
- Reorder list
- LRU cache (DLL + HashMap)
- Add two numbers

## LRU cache skeleton

```java
class LRU {
    class Node { int key, val; Node prev, next; }
    Map<Integer, Node> map = new HashMap<>();
    Node head = new Node(), tail = new Node();
    int cap;
    LRU(int c) { cap = c; head.next = tail; tail.prev = head; }
    int get(int k) {
        if (!map.containsKey(k)) return -1;
        Node n = map.get(k); remove(n); add(n); return n.val;
    }
    void put(int k, int v) {
        if (map.containsKey(k)) { Node n = map.get(k); n.val = v; remove(n); add(n); return; }
        Node n = new Node(); n.key = k; n.val = v;
        map.put(k, n); add(n);
        if (map.size() > cap) { Node r = tail.prev; remove(r); map.remove(r.key); }
    }
}
```

## Complexity
- Reverse: O(n), O(1).
- Cycle: O(n), O(1).
- Merge: O(n+m), O(1).

## Java tips
- Use `dummy` head to avoid edge-case branching.
- Be careful with `null` checks at every step.
- For DLL, store `head`/`tail` sentinels to simplify remove.
