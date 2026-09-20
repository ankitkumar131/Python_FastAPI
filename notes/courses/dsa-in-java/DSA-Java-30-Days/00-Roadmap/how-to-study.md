# How to Study This Course

DSA is not memorised, it's **practised**. This file explains the *only* study method that consistently works.

---

## The Iron Rule

> **You must write code by hand, every day, without looking at the solution, before you read any solution.**

Reading without writing is the #1 reason learners plateau at "I understood the video".

---

## Recommended Daily Structure (≈ 4 hours)

| Block | Time | What to do |
|-------|-----:|------------|
| 1. Read | 30 min | Read the day's `.md` file from top to bottom. Don't code yet. |
| 2. Run | 30 min | Open every `.java` example. Compile. Run. Modify inputs. Break it. Fix it. |
| 3. Paper | 30 min | Dry-run the first example on paper (or whiteboard). Trace every variable. |
| 4. Easy | 60 min | Solve the 5 Easy problems. Look at hints *only after* 20 min of trying. |
| 5. Medium | 60 min | Solve the 5 Medium problems. Use the brute-force-first rule. |
| 6. Hard | 30 min | Read 1–2 Hard problems, attempt 1, study the others. |
| 7. Reflect | 30 min | Fill the error log. Write 3-line summary. |

---

## The 4 Learning Principles

### 1. Active Recall

Close the file. Open a blank editor. Re-write the example from memory.

If you cannot — you have not yet learned it, only recognised it.

### 2. Spaced Repetition

Re-solve yesterday's problems **before** you start today's problems. Use the error log to find the weak spots.

### 3. Re-solving > Reading solutions

Reading a solution teaches you almost nothing. Re-solving after reading *cements* it.

### 4. Teach It

After each concept, explain it out loud as if teaching a 10-year-old. If you cannot simplify it, you don't yet own it.

---

## The "Brute Force First" Rule

For every algorithmic problem:

```
Brute force O(n²) or worse
    ↓
Make it work on all examples
    ↓
Identify the bottleneck (usually a nested loop)
    ↓
Look for the structural pattern (sorted? frequency? monotonic?)
    ↓
Replace the bottleneck with the matching technique
    ↓
Verify complexity improved
```

Never start with the optimal solution. You cannot appreciate the optimisation without first feeling the slowness.

---

## The Error Log

Maintain `error-log.md` (template at `00-Roadmap/error-log-template.md`).

Every mistake you make gets an entry. After 30 days you'll have a personalised list of your weaknesses — review it weekly.

A mistake is not a failure — it's **data**.

---

## Coding-Without-Looking Drills

Once a week, do this:

1. Pick a problem you solved this week.
2. Cover the solution.
3. Re-solve it from scratch on paper or in an empty file.
4. Time yourself.

If you can solve in < 10 min for an Easy / < 25 min for a Medium, you own it.

---

## Verbal Explanation Drills

For every new concept, answer these questions out loud:

1. What problem does this solve?
2. When should I reach for it?
3. What's the time complexity, and *why*?
4. What's the worst case, and when does it happen?
5. What mistake do beginners commonly make with it?

If you can't answer all 5, re-read the section.

---

## Time Management Tips

- **If you have only 1 hour today**: read the .md + run 1 example + solve 1 Easy.
- **If you have only 30 min**: re-solve yesterday's Hard problem.
- **Never skip the reflection step** — that's where learning actually happens.
- **Burnout is real**: take 1 day off per week if needed; you'll retain more.

---

## Tools You Need

- Java JDK 17+ (or 11+ minimum)
- A text editor or IDE (IntelliJ, VS Code, Eclipse — pick one and learn it)
- A terminal/command prompt
- Pen and paper (for dry-runs — really)
- This repository cloned locally

### Verify your Java install

```bash
java -version
javac -version
```

Both should print a version ≥ 11.

---

## Common Anti-Patterns (don't do these)

- ❌ Watching tutorial videos and calling it "studying".
- ❌ Reading solutions and copying them.
- ❌ Doing only Easy problems forever.
- ❌ Jumping between topics without finishing the current day.
- ❌ Coding without testing edge cases.
- ❌ Memorising code instead of patterns.
- ❌ Studying > 6 hours straight without breaks.
