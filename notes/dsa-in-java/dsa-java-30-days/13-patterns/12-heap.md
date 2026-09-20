# Pattern 12 — Heap

## When to use
- "Kth largest/smallest".
- Top-K frequent.
- Merge K sorted lists/streams.
- Median from data stream.
- Dijkstra.

## When NOT to use
- Need order statistics other than min/max (use balanced BST).

## Min-heap

```java
PriorityQueue<Integer> min = new PriorityQueue<>();
min.offer(5); min.offer(1); min.offer(3);
int x = min.poll(); // 1
```

## Max-heap

```java
PriorityQueue<Integer> max = new PriorityQueue<>(Comparator.reverseOrder());
```

## Kth largest in array

```java
PriorityQueue<Integer> minHeap = new PriorityQueue<>();
for (int x : a) {
    minHeap.offer(x);
    if (minHeap.size() > k) minHeap.poll();
}
return minHeap.peek(); // kth largest
```

## Top-K frequent

```java
Map<Integer, Integer> cnt = new HashMap<>();
for (int x : a) cnt.merge(x, 1, Integer::sum);

PriorityQueue<Map.Entry<Integer, Integer>> pq =
    new PriorityQueue<>((a, b) -> a.getValue() - b.getValue());
for (var e : cnt.entrySet()) {
    pq.offer(e);
    if (pq.size() > k) pq.poll();
}
```

## Merge K sorted lists

```java
PriorityQueue<ListNode> pq = new PriorityQueue<>((a, b) -> a.val - b.val);
for (ListNode h : lists) if (h != null) pq.offer(h);
ListNode dummy = new ListNode(0), tail = dummy;
while (!pq.isEmpty()) {
    tail.next = pq.poll();
    tail = tail.next;
    if (tail.next != null) pq.offer(tail.next);
}
return dummy.next;
```

## Median from stream (two heaps)

```java
PriorityQueue<Integer> lo = new PriorityQueue<>(Comparator.reverseOrder()); // max
PriorityQueue<Integer> hi = new PriorityQueue<>();                            // min
void add(int n) {
    lo.offer(n);
    hi.offer(lo.poll());
    if (lo.size() < hi.size()) lo.offer(hi.poll());
}
double median() {
    return lo.size() > hi.size() ? lo.peek() : ((double)lo.peek() + hi.peek()) / 2;
}
```

## Canonical problems
- Kth largest element in array
- Top K frequent elements
- Kth smallest in sorted matrix
- Merge k sorted lists
- Median from data stream
- Task scheduler
- Reorganize string

## Complexity
- Insert / poll: O(log n).
- Peek: O(1).

## Java tips
- `PriorityQueue` is **min-heap** by default.
- `Comparator.reverseOrder()` for max-heap.
- Use `Comparator.comparingInt(Map.Entry::getValue)` instead of lambda for clarity.
- `pq.size() > k` then poll = top-K of size k (heap keeps the k largest).
