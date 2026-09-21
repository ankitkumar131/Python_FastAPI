# 30-Day Roadmap — DSA in Java

> "A goal without a plan is just a wish." — Antoine de Saint-Exupéry

This roadmap shows exactly what you will learn each day, in what order, and why that order matters.

## How to read this roadmap

Each day builds on the previous days. Don't skip ahead — the exercises assume you know everything taught earlier.

The recommended daily time is **3–4 hours** when you are starting out, and **2–3 hours** once you are comfortable.

---

## At-a-Glance Table

| Day | Topic                                            | Difficulty | Main Skills You Will Gain                              |
|----:|--------------------------------------------------|:----------:|--------------------------------------------------------|
| 1   | Java Foundations for DSA                         | 🟢 Easy    | Java syntax, variables, loops, methods, I/O            |
| 2   | OOP in Java                                      | 🟢 Easy    | Classes, objects, inheritance, polymorphism            |
| 3   | Time & Space Complexity                          | 🟢 Easy    | Big-O, complexity analysis, performance reasoning      |
| 4   | Math & Problem-Solving Fundamentals              | 🟢 Easy    | GCD, primes, bit manipulation, problem-solving frame   |
| 5   | Arrays                                           | 🟢 Easy    | Traversal, search, Kadane, 2D arrays                   |
| 6   | Strings                                          | 🟢 Easy    | Immutability, StringBuilder, frequency, anagrams       |
| 7   | Two Pointers                                     | 🟢 Easy    | Opposite & same direction pointer technique            |
| 8   | Sliding Window                                   | 🟡 Medium  | Fixed & variable window, frequency maps                |
| 9   | Prefix Sum                                       | 🟡 Medium  | Range sum, prefix XOR, 2D prefix sum                   |
| 10  | Searching                                        | 🟡 Medium  | Binary search, lower/upper bound, rotated arrays       |
| 11  | Sorting                                          | 🟡 Medium  | Merge, Quick, Counting, Radix, stability               |
| 12  | Recursion                                        | 🟡 Medium  | Base case, call stack, recursion tree                  |
| 13  | Linked List                                      | 🟡 Medium  | Singly LL, reverse, cycle, middle, nth-from-end        |
| 14  | Advanced Linked Lists                            | 🔴 Hard    | Doubly, circular, Floyd, merge, group reverse          |
| 15  | Stack                                            | 🟡 Medium  | LIFO, balanced parens, monotonic stack, Min stack      |
| 16  | Queue & Deque                                    | 🟡 Medium  | FIFO, circular queue, deque, intro PriorityQueue       |
| 17  | Hashing                                          | 🟡 Medium  | HashMap/Set, frequency, two sum, design                |
| 18  | Binary Trees                                     | 🟡 Medium  | Traversals, recursion, BFS/DFS, level order            |
| 19  | Binary Search Trees                              | 🔴 Hard    | Insert, delete, validate, LCA, balanced BSTs           |
| 20  | Heap & Priority Queue                            | 🔴 Hard    | Heapify, top-K, kth-largest, median stream            |
| 21  | Advanced Tree Problems                           | 🔴 Hard    | Diameter, views, vertical traversal, serialize         |
| 22  | Greedy Algorithms                                | 🟡 Medium  | Activity select, jump game, intervals, gas station     |
| 23  | Backtracking                                     | 🔴 Hard    | Subsets, permutations, N-Queens, Sudoku               |
| 24  | Graph Fundamentals                               | 🟡 Medium  | Representations, BFS, DFS, components                  |
| 25  | BFS & DFS (deep)                                 | 🔴 Hard    | Iterative DFS, bipartite, islands, flood fill         |
| 26  | Shortest Paths & Advanced Graphs                 | 🔴 Hard    | Dijkstra, Bellman-Ford, Floyd, MST, DSU                |
| 27  | DP Fundamentals                                  | 🔴 Hard    | Memoization, tabulation, Fibonacci, coin change       |
| 28  | DP Patterns                                      | 🔴 Hard    | Knapsack, LCS, LIS, edit distance, grid DP             |
| 29  | Advanced Dynamic Programming                     | 🔴 Hard    | Interval, string, bitmask, tree DP                     |
| 30  | Final Revision & Interview Preparation           | 🔴 Hard    | Pattern recognition, communication, edge cases         |

---

## Difficulty Legend

- 🟢 Easy — pure concept learning
- 🟡 Medium — needs you to combine ideas
- 🔴 Hard — interview-level problems

---

## Topic Progression (the "why" of the order)

```
Day 1–2 : Java + OOP
   ↓ (you can't implement a Node class without knowing classes)
Day 3   : Complexity
   ↓ (you'll need Big-O when judging every algorithm after this)
Day 4   : Math + Problem-solving mindset
   ↓
Day 5–9 : Linear data (Arrays, Strings, Two pointers, Sliding window, Prefix sum)
   ↓
Day 10–11: Searching & Sorting (the workhorses)
   ↓
Day 12   : Recursion (you cannot do trees/graphs/DP without it)
   ↓
Day 13–14: Linked Lists (first non-array linear structure)
   ↓
Day 15–17: Stack / Queue / Hashing (other linear structures)
   ↓
Day 18–21: Trees (first non-linear structure)
   ↓
Day 22   : Greedy (algorithmic paradigm)
Day 23   : Backtracking (recursion + decisions)
   ↓
Day 24–26: Graphs (non-linear, harder)
   ↓
Day 27–29: DP (the hardest paradigm)
   ↓
Day 30    : Revision + interview polish
```

This order is **deliberate**. Earlier days are prerequisites for later ones. If you jump to Day 20 without Days 12–17, you'll be lost.

---

## Daily Study Methodology

```
30 min  → Read the day's .md file (concept + examples)
30 min  → Run the supplied .java code, modify it, break it, fix it
30 min  → Dry-run the examples by hand (use pen & paper)
60 min  → Solve the 5 Easy problems
60 min  → Solve the 5 Medium problems
60 min  → Attempt the 5 Hard problems (look at hints if stuck)
30 min  → Re-read your errors, fill the error log, summarise in 5 bullets
```

Total ≈ **5 hours**. Compress to 3 hours by skipping most Hard problems until day 14, then circle back.

---

## Practice Methodology

For every practice problem:

1. **Read the problem** twice.
2. **Write down** brute force in plain English.
3. **Code brute force** (even if O(n²) or worse).
4. **Test** with the given examples.
5. **Analyse complexity** — can you do better?
6. **Look at the hint only if stuck for > 20 minutes**.
7. **Code the optimal**.
8. **Compare both solutions** — what changed, what stayed.
9. **Log errors** in `error-log-template.md`.

---

## Progress Tracker

| Day | Topic | Started | Completed | Confidence (1–5) |
|----:|-------|:-------:|:---------:|:---------------:|
| 1   | Java Foundations          | ☐ | ☐ | _ |
| 2   | OOP in Java               | ☐ | ☐ | _ |
| 3   | Complexity                | ☐ | ☐ | _ |
| 4   | Math Fundamentals         | ☐ | ☐ | _ |
| 5   | Arrays                    | ☐ | ☐ | _ |
| 6   | Strings                   | ☐ | ☐ | _ |
| 7   | Two Pointers              | ☐ | ☐ | _ |
| 8   | Sliding Window            | ☐ | ☐ | _ |
| 9   | Prefix Sum                | ☐ | ☐ | _ |
| 10  | Searching                 | ☐ | ☐ | _ |
| 11  | Sorting                   | ☐ | ☐ | _ |
| 12  | Recursion                 | ☐ | ☐ | _ |
| 13  | Linked List               | ☐ | ☐ | _ |
| 14  | Advanced Linked Lists     | ☐ | ☐ | _ |
| 15  | Stack                     | ☐ | ☐ | _ |
| 16  | Queue & Deque             | ☐ | ☐ | _ |
| 17  | Hashing                   | ☐ | ☐ | _ |
| 18  | Binary Trees              | ☐ | ☐ | _ |
| 19  | BST                       | ☐ | ☐ | _ |
| 20  | Heap & Priority Queue     | ☐ | ☐ | _ |
| 21  | Advanced Trees            | ☐ | ☐ | _ |
| 22  | Greedy                    | ☐ | ☐ | _ |
| 23  | Backtracking              | ☐ | ☐ | _ |
| 24  | Graph Fundamentals        | ☐ | ☐ | _ |
| 25  | BFS & DFS deep            | ☐ | ☐ | _ |
| 26  | Shortest Paths            | ☐ | ☐ | _ |
| 27  | DP Fundamentals           | ☐ | ☐ | _ |
| 28  | DP Patterns               | ☐ | ☐ | _ |
| 29  | Advanced DP               | ☐ | ☐ | _ |
| 30  | Revision                  | ☐ | ☐ | _ |

---

## Final Deliverable Stats

```
Total Days           : 30
Total Practice Qs    : 450
   ├─ Easy           : 150
   ├─ Medium         : 150
   └─ Hard           : 150
Language             : Java
Level                : Beginner → Advanced
Focus                : DSA + OOP + Coding Interviews
```
