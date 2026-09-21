# Pattern 5 — Monotonic Stack

## When to use
- "Next greater/smaller element".
- "Largest rectangle in histogram".
- "Daily temperatures" / "Stock span".
- Anything where you compare an element to its previous neighbours in O(n).

## Core idea

Maintain a stack of indices whose values are monotonic (increasing or decreasing).
When a new element breaks the monotonicity, pop and process.

## Canonical problems
- Next Greater Element I
- Daily Temperatures
- Trapping Rain Water (stack variant)
- Largest Rectangle in Histogram
- Car Fleet
- Remove K Digits

## Templates

### Next Greater (strict)

```java
int[] nextGreater(int[] a) {
    int[] res = new int[a.length];
    Arrays.fill(res, -1);
    Deque<Integer> st = new ArrayDeque<>(); // indices, decreasing values
    for (int i = 0; i < a.length; i++) {
        while (!st.isEmpty() && a[st.peek()] < a[i]) {
            res[st.pop()] = a[i];
        }
        st.push(i);
    }
    return res;
}
```

### Previous Greater (strict)

```java
int[] prevGreater(int[] a) {
    int[] res = new int[a.length];
    Arrays.fill(res, -1);
    Deque<Integer> st = new ArrayDeque<>();
    for (int i = 0; i < a.length; i++) {
        while (!st.isEmpty() && a[st.peek()] <= a[i]) st.pop();
        res[i] = st.isEmpty() ? -1 : a[st.peek()];
        st.push(i);
    }
    return res;
}
```

### Largest Rectangle in Histogram

```java
int largestRectangle(int[] h) {
    Deque<Integer> st = new ArrayDeque<>();
    int best = 0;
    for (int i = 0; i <= h.length; i++) {
        int cur = i == h.length ? 0 : h[i];
        while (!st.isEmpty() && h[st.peek()] > cur) {
            int height = h[st.pop()];
            int width = st.isEmpty() ? i : i - st.peek() - 1;
            best = Math.max(best, height * width);
        }
        st.push(i);
    }
    return best;
}
```

## Complexity
- Time: O(n) — each element pushed and popped at most once.
- Space: O(n) for the stack.

## Java tips
- Stack stores **indices** (or both index and value as int[]).
- Sentinel at end (push i = n with value 0) simplifies "Largest Rectangle".
- Use `<` vs `<=` to control strict vs non-strict monotonicity.

## Variations
- Monotonic queue (sliding window max).
- Stack of pairs to track position + value.
