# Problem-Solving Strategy

A fixed, repeatable framework for tackling *any* coding problem — from interview screens to contests.

---

## The 10-Step Framework

```
 1. Understand the problem (read twice)
 2. Identify input / output format
 3. Create 3+ examples (1 minimal, 1 typical, 1 edge)
 4. State the brute force in plain English
 5. Code the brute force (it WILL pass the examples)
 6. Analyse time & space complexity
 7. Identify the bottleneck
 8. Look for a matching pattern (see cheat sheet)
 9. Code the optimised version
10. Test with edge cases and the original examples
```

Never skip step 1. Skipping it is the #1 reason people write code that solves the wrong problem.

---

## Step 1 — Understand the Problem

Ask yourself:

- What is being asked? (Find? Count? Decide? Build?)
- What are the constraints? (n ≤ 10? n ≤ 10⁵? Sorted? Distinct?)
- Are negative numbers allowed?
- Is the input mutable?
- Is the graph directed? Weighted?
- Is the array sorted?

Re-state the problem in your own words. If you can't, you don't understand it.

---

## Step 2 — Identify I/O

- **Input type**: array? string? tree? graph? matrix? stream?
- **Output type**: index? boolean? count? list of all answers?
- **Mutability**: can I modify input or do I need to return a new structure?

In Java, this decides whether to use `int[]`, `List<Integer>`, etc.

---

## Step 3 — Examples

Create:

- **One minimal example** (smallest non-trivial input).
- **One typical example** (realistic size).
- **One edge case** (empty, single element, all same, negative numbers).

Most bugs hide in edge cases. Make them first.

---

## Step 4 — Brute Force in Plain English

Even if you think you know the optimal solution, **start with brute force in English**.

Example: "Find two numbers that sum to target."

Brute force in English: "Try every pair of indices, check if their sum is target."

This is a habit that *guarantees* you have at least one working approach. From there, every improvement is a win.

---

## Step 5 — Code the Brute Force

Even O(n³) is fine for now. Just make it work.

```java
public static int[] twoSumBrute(int[] nums, int target) {
    for (int i = 0; i < nums.length; i++) {
        for (int j = i + 1; j < nums.length; j++) {
            if (nums[i] + nums[j] == target) {
                return new int[]{i, j};
            }
        }
    }
    return new int[]{-1, -1};
}
```

This always works on the examples. You have a baseline.

---

## Step 6 — Complexity

```
Time:   O(n²) — two nested loops
Space:  O(1)   — no extra space
```

Now decide if that's acceptable. n = 10⁵? Then O(n²) is 10¹⁰ operations = too slow. We need O(n).

---

## Step 7 — Identify the Bottleneck

In two-sum, the bottleneck is: for every `i`, we re-scan the rest of the array looking for `target - nums[i]`.

This re-scan is wasted work — we already saw those elements.

---

## Step 8 — Match the Pattern

"What data structure gives O(1) lookup of 'have I seen x before?'"

→ **HashMap / HashSet**.

So: store each seen number's index in a HashMap; for every `nums[i]`, check whether `target - nums[i]` is in the map.

---

## Step 9 — Code the Optimised

```java
public static int[] twoSumOptimal(int[] nums, int target) {
    Map<Integer, Integer> seen = new HashMap<>();
    for (int i = 0; i < nums.length; i++) {
        int need = target - nums[i];
        if (seen.containsKey(need)) {
            return new int[]{seen.get(need), i};
        }
        seen.put(nums[i], i);
    }
    return new int[]{-1, -1};
}
```

O(n) time, O(n) space. Better than O(n²).

---

## Step 10 — Test

- The given examples
- An empty input
- A single element
- All same elements
- A negative number
- The largest possible input

If your solution handles all of these, you're done.

---

## Pattern Matching Cheat Sheet (interview-grade)

| If you see...                                  | Reach for...                |
|------------------------------------------------|-----------------------------|
| Sorted array + find pair/triplet               | Two Pointers                |
| Contiguous segment with min/max                | Sliding Window              |
| Many range-sum queries                         | Prefix Sum                  |
| "How many times does X appear?"                | HashMap / Frequency         |
| Top K, Kth largest                             | Heap / QuickSelect          |
| Next greater / smaller                         | Monotonic Stack             |
| Shortest path in unweighted graph              | BFS                         |
| Shortest path with positive weights            | Dijkstra                    |
| Shortest path with negative weights            | Bellman-Ford                |
| All-pairs shortest paths                       | Floyd-Warshall              |
| Dependencies / order                           | Topological Sort            |
| Disjoint sets / merging                        | Union-Find (DSU)            |
| Minimum spanning tree                          | Kruskal / Prim              |
| "Count all ways" / min cost                    | Dynamic Programming         |
| Generate all combinations                      | Backtracking                |
| Interval scheduling / make-change-like greedy  | Greedy                      |

This table alone will let you decide the technique for ~70% of interview problems.

---

## When You're Stuck

Try this 5-minute ladder:

1. **Re-read** the problem (silently).
2. **Smaller example** — shrink the input by hand.
3. **Brute force** — get *anything* working.
4. **Look at the hint**.
5. **Look at similar problems** you've solved.

If still stuck after 20 min — *that's fine*. Read the solution, **then close it**, and re-derive it tomorrow.

---

## Interview-Specific Tactics

- **Communicate** — narrate while coding. Silence is scary for interviewers.
- **Ask questions** — clarify constraints. Interviewers reward it.
- **Start with examples** — shows you think before typing.
- **Test live** — run through your code with a small input after writing it.
- **Admit unknowns** — "I don't remember the exact Dijkstra implementation, but I know the idea" is better than bluffing.
- **Optimise last** — get a working solution first. A slow correct answer beats a fast wrong one.
