# DSA Error Log

> "A mistake repeated is a choice. A mistake logged is progress."

For every wrong answer, runtime error, or interview mistake, fill one entry. Review weekly.

---

## Entry Template

```markdown
## Entry N — YYYY-MM-DD

### Problem
- **Name**:
- **Day**:
- **Difficulty**:

### My Approach
What I tried (1–3 sentences).

### Why It Failed
Specific reason: TLE / WA / compile error / wrong edge case / couldn't recall template.

### Correct Approach
The right idea in 2–3 sentences.

### Concept I Missed
The exact concept I didn't know (e.g. "lower_bound in binary search", "HashMap getOrDefault").

### Pattern
Which pattern this problem belongs to (e.g. "two pointers", "monotonic stack").

### Complexity
- Brute:
- Optimal:

### What I Will Remember
A single sentence I will tell myself next time.
```

---

## Worked Example

```markdown
## Entry 1 — 2026-09-20

### Problem
- **Name**: Search in Rotated Sorted Array
- **Day**: 10
- **Difficulty**: Medium

### My Approach
Tried to find pivot, then binary search on one half. Got confused about which half is sorted.

### Why It Failed
I forgot that *at least one* half is always sorted, and I should compare nums[mid] with nums[left] (or nums[right]) to know which.

### Correct Approach
Compare nums[mid] with nums[right]. If nums[mid] > nums[right], the right half contains the pivot, so the left half is sorted. Check if target falls in the sorted half; if not, go to the other half.

### Concept I Missed
The "one half is always sorted" invariant of rotated arrays.

### Pattern
Modified binary search.

### Complexity
- Brute: linear search O(n)
- Optimal: O(log n)

### What I Will Remember
"In a rotated sorted array, at least one half is sorted — pick the sorted half, decide if target is in it, else go to the other."
```

---

## Statistics (fill monthly)

| Month | Entries | Most-missed concept | Most-missed pattern |
|-------|--------:|---------------------|---------------------|
| _     | _       | _                   | _                   |
