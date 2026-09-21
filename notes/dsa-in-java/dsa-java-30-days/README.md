# 30-Day DSA in Java — Complete Learning Course

> A complete, beginner-friendly, interview-oriented Data Structures & Algorithms course using Java.
> One Markdown file per day. 450 practice problems. Runnable `.java` examples. Pattern cheat sheets. Everything you need.

---

## What this course teaches

- Java syntax & OOP required for DSA
- Time & space complexity analysis
- Arrays, Strings, Recursion, Searching, Sorting
- Linked Lists, Stacks, Queues, Hashing
- Trees, BSTs, Heaps
- Greedy & Backtracking
- Graphs: BFS, DFS, Dijkstra, MST, DSU
- Dynamic Programming: from Fibonacci to bitmask DP
- Pattern recognition for interviews

## Who this course is for

- Complete beginners in DSA
- Learners with little or moderate Java
- Anyone preparing for software-engineering interviews
- Anyone who keeps forgetting algorithms after learning them

## Prerequisites

- A computer with **Java JDK 11+** installed
- A text editor or IDE (IntelliJ Community / VS Code / Eclipse)
- Willingness to write code by hand, every day

## Java requirements

You need the JDK (Java Development Kit) installed and on your `PATH`.

Verify:

```bash
java -version
javac -version
```

Both should print a version number. If they don't, install JDK 17 (LTS) from [Adoptium](https://adoptium.net/).

## How to run the Java examples

Each day has a folder under `src/day-XX/`. To run an example:

```bash
# from the repo root
javac src/day-01/HelloWorld.java
java -cp src/day-01 HelloWorld
```

Or in your IDE, open the file and click Run.

## How to study each day

1. Read `DSA-Java-30-Days/<topic>/day-XX-*.md` top to bottom (≈ 30 min).
2. Open and run every `.java` file under `src/day-XX/`. Modify inputs. Break it. Fix it (≈ 30 min).
3. Dry-run the first example on paper (≈ 30 min).
4. Solve the 5 Easy problems (≈ 60 min).
5. Solve the 5 Medium problems (≈ 60 min).
6. Attempt the 5 Hard problems (≈ 30 min).
7. Fill your `error-log.md` and write a 3-bullet summary (≈ 30 min).

Total ≈ **4–5 hours/day**. See `00-Roadmap/how-to-study.md` for more.

## 30-Day Roadmap

| Day | Topic | Difficulty | Main Skills |
|----:|-------|:----------:|-------------|
| 1   | Java Foundations for DSA              | 🟢 | Syntax, loops, methods, I/O |
| 2   | OOP in Java                            | 🟢 | Class, inheritance, polymorphism |
| 3   | Time & Space Complexity                | 🟢 | Big-O, analysis |
| 4   | Math & Problem-Solving Fundamentals    | 🟢 | GCD, primes, bitwise |
| 5   | Arrays                                 | 🟢 | Traversal, Kadane, 2D |
| 6   | Strings                                | 🟢 | StringBuilder, anagrams |
| 7   | Two Pointers                           | 🟢 | Sorted arrays, pairs |
| 8   | Sliding Window                         | 🟡 | Fixed/variable window |
| 9   | Prefix Sum                             | 🟡 | Range queries |
| 10  | Searching                              | 🟡 | Binary search, lower/upper bound |
| 11  | Sorting                                | 🟡 | Merge, Quick, Counting |
| 12  | Recursion                              | 🟡 | Call stack, trees of calls |
| 13  | Linked List                            | 🟡 | Singly LL, reverse, cycle |
| 14  | Advanced Linked Lists                  | 🔴 | Doubly, Floyd, group reverse |
| 15  | Stack                                  | 🟡 | LIFO, monotonic, Min stack |
| 16  | Queue & Deque                          | 🟡 | FIFO, deque, PriorityQueue |
| 17  | Hashing                                | 🟡 | HashMap/Set, frequency |
| 18  | Binary Trees                           | 🟡 | Traversals, recursion, BFS |
| 19  | Binary Search Trees                    | 🔴 | Insert, delete, LCA |
| 20  | Heap & Priority Queue                  | 🔴 | Top-K, kth-largest |
| 21  | Advanced Tree Problems                 | 🔴 | Diameter, views, vertical |
| 22  | Greedy Algorithms                      | 🟡 | Activity select, intervals |
| 23  | Backtracking                           | 🔴 | Subsets, permutations, N-Queens |
| 24  | Graph Fundamentals                     | 🟡 | Representations, BFS/DFS |
| 25  | BFS & DFS (deep)                       | 🔴 | Islands, bipartite, flood fill |
| 26  | Shortest Paths & Advanced Graphs       | 🔴 | Dijkstra, MST, DSU |
| 27  | DP Fundamentals                        | 🔴 | Memoization, tabulation |
| 28  | DP Patterns                            | 🔴 | Knapsack, LCS, edit distance |
| 29  | Advanced Dynamic Programming           | 🔴 | Interval, bitmask, tree DP |
| 30  | Final Revision & Interview Preparation | 🔴 | Patterns, edge cases |

## Repository Structure

```
DSA-Java-30-Days/
├── README.md                   ← you are here
├── 00-Roadmap/                 ← study plan & strategy
├── 01-Java-Foundations/        ← Day 1–2
├── 02-Complexity-and-Problem-Solving/ ← Day 3–4
├── 03-Arrays-and-Strings/      ← Day 5–9
├── 04-Searching-and-Sorting/   ← Day 10–11
├── 05-Recursion-and-Linked-Lists/ ← Day 12–14
├── 06-Stacks-Queues-Hashing/   ← Day 15–17
├── 07-Trees-and-Heaps/         ← Day 18–21
├── 08-Greedy-and-Backtracking/ ← Day 22–23
├── 09-Graphs/                  ← Day 24–26
├── 10-Dynamic-Programming/     ← Day 27–29
├── 11-Final-Revision/          ← Day 30
├── 12-Patterns/                ← pattern library
├── 13-Cheat-Sheets/            ← quick references
├── 14-Question-Bank/           ← 450 problems
└── src/                        ← all runnable .java examples
```

## Daily study methodology (recap)

```
30 min  Read the day's .md
30 min  Run all the day's .java examples
30 min  Dry-run first example on paper
60 min  Solve 5 Easy
60 min  Solve 5 Medium
60 min  Attempt 5 Hard
30 min  Reflect & fill error log
```

## Practice methodology

For every problem:

1. Read twice.
2. Brute force in plain English.
3. Code brute force.
4. Test with examples.
5. Identify bottleneck.
6. Match to a pattern (see `12-Patterns/`).
7. Code optimal.
8. Test edge cases.

## Interview preparation strategy

See `00-Roadmap/interview-preparation.md`. Highlights:

- Master the Top 30 high-yield problems (listed there).
- Practice explaining solutions out loud.
- Always: brute force first, optimise second.
- Time yourself: < 25 min per Medium is the goal.

## Recommended daily time commitment

| Profile                | Hours/day | Notes |
|------------------------|----------:|-------|
| Full-time learner      | 5–6       | Aim for full coverage |
| College student        | 3–4       | Skip Hard on busy days |
| Working professional   | 2–3       | Re-solve previous days' Mediums on busy days |

## How to track progress

Use the table in `00-Roadmap/roadmap.md`. Mark the date you completed each day and your confidence (1–5).

## Completion checklist

- [ ] Day 1 done
- [ ] Day 2 done
- [ ] …
- [ ] Day 30 done
- [ ] All 450 problems attempted
- [ ] Error log has at least 30 entries
- [ ] Can solve Top 30 problems in < 25 min cold
- [ ] Can verbally explain every algorithm paradigm

## Final stats

```
Total Days              : 30
Total Practice Qs       : 450
   ├─ Easy              : 150
   ├─ Medium            : 150
   └─ Hard              : 150
Language                : Java
Level                   : Beginner → Advanced
Focus                   : DSA + OOP + Coding Interviews
```

Now open `00-Roadmap/roadmap.md` and start with **Day 1**.
