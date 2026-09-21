# Day 7 — Two Pointers

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Recognise when a problem fits the two-pointer technique
- Use opposite-direction pointers (sorted-array pair sums)
- Use same-direction pointers (in-place filtering)
- Solve the classic "remove duplicates" and "container with most water" problems
- Apply two pointers on linked lists (preview)

---

# 1. Introduction

Two pointers is the **most commonly used** array technique in interviews. It converts O(n²) brute force into O(n) by using both ends of the array, or two runners.

Today you'll learn both flavours: opposite-direction and same-direction.

---

# 2. Why Do We Need This?

For many array problems, brute force is O(n²): try every pair. With sorting, you can cut to O(n) using two pointers.

---

# 3. Core Concept

Two pointers means using **two indices** that move through the array based on some condition:

- **Opposite-direction**: `lo` starts at 0, `hi` at n-1. Move them toward each other.
- **Same-direction**: both `lo` and `hi` start at 0; `hi` scans ahead, `lo` tracks the "next write position".

---

# 4. Real-World Analogy

Two pointers is like two people walking toward each other in a hallway, each holding half a clue. They share what they know and decide which one moves next.

---

# 5. The Template

```java
// Opposite direction
int lo = 0, hi = arr.length - 1;
while (lo < hi) {
    if (/* condition */) lo++;
    else if (/* condition */) hi--;
    else { /* found */ break; }
}

// Same direction (in-place)
int write = 0;
for (int read = 0; read < arr.length; read++) {
    if (/* keep this element */) arr[write++] = arr[read];
}
```

---

# 6. Java Implementation — `TwoPointersDemo.java`

```java
import java.util.Arrays;

public class TwoPointersDemo {

    /** Two-sum in a sorted array. Returns indices or {-1,-1}. */
    static int[] twoSumSorted(int[] arr, int target) {
        int lo = 0, hi = arr.length - 1;
        while (lo < hi) {
            int sum = arr[lo] + arr[hi];
            if (sum == target) return new int[]{lo, hi};
            else if (sum < target) lo++;
            else hi--;
        }
        return new int[]{-1, -1};
    }

    /** Container With Most Water. */
    static int maxWater(int[] h) {
        int lo = 0, hi = h.length - 1, best = 0;
        while (lo < hi) {
            best = Math.max(best, (hi - lo) * Math.min(h[lo], h[hi]));
            if (h[lo] < h[hi]) lo++;
            else hi--;
        }
        return best;
    }

    /** In-place: remove duplicates from a sorted array. Returns new length. */
    static int removeDuplicates(int[] a) {
        if (a.length == 0) return 0;
        int write = 1;
        for (int read = 1; read < a.length; read++)
            if (a[read] != a[read - 1]) a[write++] = a[read];
        return write;
    }

    /** Move all zeroes to the end. */
    static void moveZeroes(int[] a) {
        int write = 0;
        for (int read = 0; read < a.length; read++)
            if (a[read] != 0) a[write++] = a[read];
        while (write < a.length) a[write++] = 0;
    }

    /** Palindrome check. */
    static boolean isPalindrome(String s) {
        int lo = 0, hi = s.length() - 1;
        while (lo < hi) {
            char a = s.charAt(lo), b = s.charAt(hi);
            if (!Character.isLetterOrDigit(a)) lo++;
            else if (!Character.isLetterOrDigit(b)) hi--;
            else if (Character.toLowerCase(a) != Character.toLowerCase(b)) return false;
            else { lo++; hi--; }
        }
        return true;
    }

    public static void main(String[] args) {
        int[] sorted = {1, 3, 4, 5, 7, 11};
        System.out.println("twoSumSorted(8) = " + Arrays.toString(twoSumSorted(sorted, 8)));

        int[] h = {1, 8, 6, 2, 5, 4, 8, 3, 7};
        System.out.println("maxWater = " + maxWater(h));

        int[] dup = {1, 1, 2, 2, 3, 4, 4};
        int len = removeDuplicates(dup);
        System.out.println("deduped (len=" + len + "): " + Arrays.toString(Arrays.copyOf(dup, len)));

        int[] arr = {0, 1, 0, 3, 12};
        moveZeroes(arr);
        System.out.println("zeroes moved: " + Arrays.toString(arr));

        System.out.println("palindrome(A man, a plan, a canal: Panama) = " + isPalindrome("A man, a plan, a canal: Panama"));
    }
}
```

Walkthrough:

- `twoSumSorted` — sorted array means `sum > target` ⇒ decrease the sum by moving `hi--`; `sum < target` ⇒ increase by `lo++`. O(n).
- `maxWater` — move the side with smaller height (moving the taller can never improve). O(n).
- `removeDuplicates` — `read` scans; `write` is the next "kept" position. When `a[read]` differs from the previous, copy it forward.
- `moveZeroes` — first pass: move non-zeros forward; second pass: pad with zeros.
- `isPalindrome` — skip non-alphanumeric with two pointers; case-insensitive compare.

---

# 7. Dry Run — `twoSumSorted([1,3,4,5,7,11], target=8)`

| lo | hi | sum | Action |
|----|----|-----|--------|
| 0  | 5  | 12  | hi-- |
| 0  | 4  | 8   | match → return {0,4} |

---

# 8. When to Use Two Pointers

| Signal | Use |
|---|---|
| Sorted array, find pair/triplet summing to X | Opposite-direction |
| In-place deduplication / partitioning | Same-direction |
| Container / trapping water | Opposite-direction |
| Comparing ends of a palindrome | Opposite-direction |
| Slow/fast cycle detection (linked list) | Same-direction |

---

# 9. Common Mistakes

1. **Forgetting the array must be sorted** for opposite-direction two-sum.
2. **Off-by-one**: `while (lo < hi)` vs `while (lo <= hi)`.
3. **Moving the wrong side** in max-water.
4. **Writing past the array** in same-direction: ensure `write < arr.length`.

---

# 10. Interview Questions

### Q1. Why does two-pointer work for sorted two-sum?
Sorted array ⇒ adjusting one side strictly increases or decreases the sum.

### Q2. When to move `lo` vs `hi`?
Whichever move brings the sum closer to the target.

### Q3. Same vs opposite direction?
Same for in-place partitioning; opposite for pair-search on sorted arrays.

### Q4. Is two-pointer always O(n)?
Yes — each pointer moves at most n times.

---

# 11. Practice Problems

## 🟢 Easy

### 1. Two Sum (sorted)
**Input:** `[2,7,11,15], t=9` → **Output:** `[0,1]`

### 2. Remove Duplicates
**Input:** `[1,1,2,3,3]` → **Output:** `[1,2,3]` (len=3)

### 3. Valid Palindrome
**Input:** `"A man, a plan, a canal: Panama"` → **Output:** `true`

### 4. Move Zeroes
**Input:** `[0,1,0,3,12]` → **Output:** `[1,3,12,0,0]`

### 5. Reverse String in Place
**Input:** `["h","e","l","l","o"]` → **Output:** `["o","l","l","e","h"]`

## 🟡 Medium

### 6. 3Sum
**Input:** `[-1,0,1,2,-1,-4]` → **Output:** `[[-1,-1,2],[-1,0,1]]`

### 7. Container With Most Water
**Input:** `[1,8,6,2,5,4,8,3,7]` → **Output:** `49`

### 8. Sort Colors (Dutch National Flag)
**Input:** `[2,0,2,1,1,0]` → **Output:** `[0,0,1,1,2,2]`

### 9. Remove Element
**Input:** `[3,2,2,3], val=3` → **Output:** `2` (and `[2,2,...]`)

### 10. Squares of Sorted Array
**Input:** `[-4,-1,0,3,10]` → **Output:** `[0,1,9,16,100]`

## 🔴 Hard

### 11. Trapping Rain Water (two-pointer)
**Input:** `[0,1,0,2,1,0,1,3,2,1,2,1]` → **Output:** `6`

### 12. 4Sum
**Input:** `[1,0,-1,0,-2,2], t=0` → **Output:** `[[-2,-1,1,2],[-2,0,0,2],[-1,0,0,1]]`

### 13. Minimum Size Subarray Sum
**Input:** `s=7, [2,3,1,2,4,3]` → **Output:** `2`

### 14. Longest Mountain in Array
**Input:** `[2,1,4,7,3,2,5]` → **Output:** `5` (subarray `[1,4,7,3,2]`)

### 15. Partition Labels
**Input:** `"ababcbacadefegdehijhklij"` → **Output:** `[9,7,8]`

---

# 12. Practice Hints

## Easy
1. Opposite-direction.
2. Same-direction.
3. Two pointers with char-class filter.
4. Same-direction + zero pad.
5. Opposite-direction swap.

## Medium
6. Sort + outer loop + inner two-pointer.
7. Opposite-direction, move smaller.
8. Three-way partition.
9. Same-direction.
10. Two-pointer from both ends, abs comparison.

## Hard
11. Two-pointer max-of-min from each side.
12. Sort + two nested pairs.
13. Sliding window (Day 8).
14. Two passes / single pass with state.
15. Greedy intervals.

---

# 13. Revision Checklist

- [ ] Recognise when two-pointer applies
- [ ] Can solve 2-sum on sorted array in O(n)
- [ ] Can remove duplicates in place
- [ ] Can solve max water
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 14. Key Takeaways

- Two-pointer cuts O(n²) → O(n) on sorted or partitionable inputs.
- Opposite direction: pair-search on sorted arrays.
- Same direction: in-place filtering / partitioning.
- Container-with-water: move the smaller side.

Tomorrow: **Sliding Window**.


## Solutions

### Problem 1 — TwoSumSorted (E)

```java
class TwoSumSorted {
    public static void main(String[] args) {
        int[] a = {2, 7, 11, 15}; int t = 9;
        int l = 0, r = a.length - 1;
        while (l < r) {
            int s = a[l] + a[r];
            if (s == t) { System.out.println(l + " " + r); return; }
            if (s < t) l++; else r--;
        }
    }
}
```

### Problem 2 — Dedup (E)

```java
class Dedup {
    public static void main(String[] args) {
        int[] a = {1,1,2,2,3,3,3,4};
        int j = 0;
        for (int i = 1; i < a.length; i++) if (a[i] != a[j]) a[++j] = a[i];
        System.out.println(j + 1);
    }
}
```

### Problem 3 — Palindrome (E)

```java
class Palindrome {
    public static void main(String[] args) {
        String s = "A man, a plan, a canal: Panama";
        int l = 0, r = s.length() - 1;
        while (l < r) {
            while (l < r && !Character.isLetterOrDigit(s.charAt(l))) l++;
            while (l < r && !Character.isLetterOrDigit(s.charAt(r))) r--;
            if (Character.toLowerCase(s.charAt(l)) != Character.toLowerCase(s.charAt(r))) { System.out.println(false); return; }
            l++; r--;
        }
        System.out.println(true);
    }
}
```

### Problem 4 — Move0 (E)

```java
class Move0 {
    public static void main(String[] args) {
        int[] a = {0,1,0,3,12}; int j = 0;
        for (int x : a) if (x != 0) a[j++] = x;
        while (j < a.length) a[j++] = 0;
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 5 — RevInPlace (E)

```java
class RevInPlace {
    public static void main(String[] args) {
        char[] a = "hello".toCharArray();
        int l = 0, r = a.length - 1;
        while (l < r) { char t = a[l]; a[l++] = a[r]; a[r--] = t; }
        System.out.println(new String(a));
    }
}
```

### Problem 6 — ThreeSum (M)

```java
class ThreeSum {
    public static void main(String[] args) {
        int[] a = {-1,0,1,2,-1,-4};
        java.util.Arrays.sort(a);
        java.util.List<java.util.List<Integer>> res = new java.util.ArrayList<>();
        for (int i = 0; i < a.length - 2; i++) {
            if (i > 0 && a[i] == a[i-1]) continue;
            int l = i + 1, r = a.length - 1, t = -a[i];
            while (l < r) {
                int s = a[l] + a[r];
                if (s == t) {
                    res.add(java.util.Arrays.asList(a[i], a[l], a[r]));
                    while (l < r && a[l] == a[l+1]) l++;
                    while (l < r && a[r] == a[r-1]) r--;
                    l++; r--;
                } else if (s < t) l++; else r--;
            }
        }
        System.out.println(res);
    }
}
```

### Problem 7 — Container (M)

```java
class Container {
    public static void main(String[] args) {
        int[] h = {1,8,6,2,5,4,8,3,7};
        int l = 0, r = h.length - 1, best = 0;
        while (l < r) {
            best = Math.max(best, (r - l) * Math.min(h[l], h[r]));
            if (h[l] < h[r]) l++; else r--;
        }
        System.out.println(best);
    }
}
```

### Problem 8 — Dutch (M)

```java
class Dutch {
    public static void main(String[] args) {
        int[] a = {2,0,2,1,1,0};
        int lo = 0, mid = 0, hi = a.length - 1;
        while (mid <= hi) {
            if (a[mid] == 0) { int t = a[lo]; a[lo++] = a[mid]; a[mid++] = t; }
            else if (a[mid] == 1) mid++;
            else { int t = a[mid]; a[mid] = a[hi]; a[hi--] = t; }
        }
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 9 — RemoveEl (M)

```java
class RemoveEl {
    public static void main(String[] args) {
        int[] a = {3,2,2,3}; int v = 3, j = 0;
        for (int x : a) if (x != v) a[j++] = x;
        System.out.println(j);
    }
}
```

### Problem 10 — Squares (M)

```java
class Squares {
    public static void main(String[] args) {
        int[] a = {-4,-1,0,3,10};
        int[] out = new int[a.length];
        int l = 0, r = a.length - 1, k = a.length - 1;
        while (l <= r) {
            int ls = a[l]*a[l], rs = a[r]*a[r];
            if (ls > rs) { out[k--] = ls; l++; } else { out[k--] = rs; r--; }
        }
        System.out.println(java.util.Arrays.toString(out));
    }
}
```

### Problem 11 — TrapTP (H)

```java
class TrapTP {
    public static void main(String[] args) {
        int[] h = {0,1,0,2,1,0,1,3,2,1,2,1};
        int l = 0, r = h.length-1, lM=0, rM=0, w=0;
        while (l < r) {
            if (h[l] < h[r]) { lM = Math.max(lM, h[l]); w += lM - h[l++]; }
            else { rM = Math.max(rM, h[r]); w += rM - h[r--]; }
        }
        System.out.println(w);
    }
}
```

### Problem 12 — FourSum (H)

```java
class FourSum {
    public static void main(String[] args) {
        int[] a = {1,0,-1,0,-2,2};
        int t = 0;
        java.util.Arrays.sort(a);
        java.util.List<java.util.List<Integer>> res = new java.util.ArrayList<>();
        for (int i = 0; i < a.length - 3; i++) {
            if (i > 0 && a[i] == a[i-1]) continue;
            for (int j = i + 1; j < a.length - 2; j++) {
                if (j > i + 1 && a[j] == a[j-1]) continue;
                int l = j + 1, r = a.length - 1;
                while (l < r) {
                    long s = (long)a[i] + a[j] + a[l] + a[r];
                    if (s == t) { res.add(java.util.Arrays.asList(a[i], a[j], a[l++], a[r--])); }
                    else if (s < t) l++; else r--;
                }
            }
        }
        System.out.println(res);
    }
}
```

### Problem 13 — MinSubSum (H)

```java
class MinSubSum {
    public static void main(String[] args) {
        int[] a = {2,3,1,2,4,3}; int t = 7, l = 0, sum = 0, best = Integer.MAX_VALUE;
        for (int r = 0; r < a.length; r++) {
            sum += a[r];
            while (sum >= t) { best = Math.min(best, r - l + 1); sum -= a[l++]; }
        }
        System.out.println(best);
    }
}
```

### Problem 14 — Mountain (H)

```java
class Mountain {
    public static void main(String[] args) {
        int[] a = {2,1,4,7,3,2,5};
        int n = a.length, best = 0;
        for (int i = 1; i < n - 1; i++) {
            if (a[i] > a[i-1] && a[i] > a[i+1]) {
                int l = i, r = i;
                while (l > 0 && a[l-1] < a[l]) l--;
                while (r < n-1 && a[r] > a[r+1]) r++;
                best = Math.max(best, r - l + 1);
            }
        }
        System.out.println(best);
    }
}
```

### Problem 15 — Partition (H)

```java
class Partition {
    public static void main(String[] args) {
        String s = "ababcbacadefegdehijhklij";
        int[] last = new int[26];
        for (int i = 0; i < s.length(); i++) last[s.charAt(i)-'a'] = i;
        java.util.List<Integer> out = new java.util.ArrayList<>();
        int end = 0, start = 0;
        for (int i = 0; i < s.length(); i++) {
            end = Math.max(end, last[s.charAt(i)-'a']);
            if (i == end) { out.add(end - start + 1); start = i + 1; }
        }
        System.out.println(out);
    }
}
```

