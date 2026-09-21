# Interview Cheat Sheet

## 1. The 5-Phase Interview Loop

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1 — Clarify     (3-5 min)                            │
│  Phase 2 — Examples     (2-3 min)                            │
│  Phase 3 — Brute force  (5-10 min)                           │
│  Phase 4 — Optimise     (10-15 min)                          │
│  Phase 5 — Test         (5 min)                              │
└─────────────────────────────────────────────────────────────┘
```

## 2. Phase 1 — Clarify

Ask clarifying questions before coding. Examples:

- "Are all integers? Negative allowed? Zero allowed?"
- "Can the input be empty?"
- "Is the array sorted?"
- "Should the result be unique?"
- "Time / space constraints?"
- "Should I handle overflow?"

A great clarifying question is **evidence of problem understanding**.

## 3. Phase 2 — Examples

State 3 examples:
- **Minimum**: smallest non-trivial input.
- **Typical**: representative normal case.
- **Edge**: empty / single element / duplicates / maximum size.

Sketch each one. Mention expected output.

## 4. Phase 3 — Brute force

Always start with brute force. It's your safety net.

- "Brute force: nested loop, O(n²). Let me code it."
- After working: "Now let me optimise. The bottleneck is X."

## 5. Phase 4 — Optimise

Common optimisation paths:

1. **Sort first** — enables binary search, two-pointer, sweep line.
2. **Hash** — reduce O(n) scan to O(1) lookup.
3. **Two pointers / sliding window** — for sorted/array problems.
4. **Stack/queue** — for nested or first-in-first-out problems.
5. **DP** — when subproblems overlap.
6. **Greedy** — when local optimal = global optimal.
7. **Graph** — when relationships matter.

## 6. Phase 5 — Test

After coding, walk through your code on your example. Look for:
- Off-by-one errors
- Null checks
- Empty input
- Duplicate handling
- Integer overflow
- Infinite loop

## 7. Pattern → problem mapping

| Problem signal | Pattern |
|---|---|
| "sorted array", "find in O(log n)" | Binary search |
| "subarray", "contiguous" | Sliding window / prefix sum |
| "frequency", "count occurrences" | HashMap |
| "top K", "kth largest" | Heap |
| "next greater element" | Monotonic stack |
| "minimum window" | Sliding window |
| "shortest path unweighted" | BFS |
| "shortest path weighted" | Dijkstra |
| "minimum spanning tree" | Kruskal / Prim |
| "cycle detection" | DFS / Kahn |
| "valid parentheses" | Stack |
| "LCA", "tree traversal" | DFS / BFS |
| "all paths count" | DP / DFS |
| "subset sum", "knapsack" | DP |
| "all permutations" | Backtracking |
| "intervals", "merge" | Sort + sweep |
| "prefix sum", "range query" | Prefix / segment tree |
| "median from stream" | Two heaps |
| "LRU / LFU" | HashMap + DLL / Counter |
| "string match" | KMP / Rabin-Karp |

## 8. Communication phrases

| Situation | Phrase |
|---|---|
| Need to think | "Let me think out loud..." |
| Two options | "I'll start with brute force, then optimise." |
| Trade-off | "I can trade space for time here." |
| Stuck | "Let me try a smaller example to see the pattern." |
| Hint received | "Let me work that into my approach." |
| Edge case | "I should check the empty-input case." |
| Verify | "Let me trace through with input X..." |
| Optimisation | "The bottleneck is the inner loop; I can speed it up by..." |

## 9. STAR for behavioural

- **S**ituation: context.
- **T**ask: your responsibility.
- **A**ction: what YOU did (use "I", not "we").
- **R**esult: quantified outcome.

Have 4 ready: Technical Challenge, Conflict, Failure, Leadership.

## 10. Common mistakes

| Mistake | Fix |
|---|---|
| Silent coding | Narrate constantly |
| No edge cases | List them before coding |
| Wrong data structure | Justify your choice |
| Skipping complexity | Always state it |
| Not testing | Walk through with example |
| One attempt only | Restart if stuck |
| Ignoring hints | Take them gracefully |
| Arguing with interviewer | Listen, adapt |
| Poor variable names | Use descriptive names |
| Hardcoded values | Use constants / named vars |

## 11. Question to ask at end

- "What does success look like in the first 90 days?"
- "What's the team's approach to code review?"
- "How do you measure performance?"
- "What's the most interesting challenge the team is facing?"
- "What does the on-call rotation look like?"
- "How does the team approach technical decisions?"

**Never ask**: salary, vacation, perks (HR handles those).

## 12. Time management (45-min coding interview)

| Time | Activity |
|---|---|
| 0–5 min | Clarify, examples |
| 5–15 min | Brute force code |
| 15–30 min | Optimise + code |
| 30–40 min | Test, edge cases, complexity |
| 40–45 min | Wrap up, ask questions |

## 13. Red flags to avoid

- ❌ "I don't know" without trying.
- ❌ Giving up after one wrong attempt.
- ❌ Not testing.
- ❌ Badmouthing previous employers.
- ❌ Lying on resume.
- ❌ Arrogance ("This is trivial").
- ❌ Ignoring the interviewer.

## 14. Green flags to demonstrate

- ✅ Asking clarifying questions.
- ✅ Drawing examples.
- ✅ Walking through code.
- ✅ Considering trade-offs.
- ✅ Admitting when uncertain.
- ✅ Building on hints.
- ✅ Iterating to better solution.
