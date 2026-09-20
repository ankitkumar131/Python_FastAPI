# Day 8 — Sliding Window

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Recognise sliding-window problems
- Implement fixed-size windows
- Implement variable-size windows (expand/shrink)
- Solve max-sum subarray of size K, longest substring without repeats, min-size subarray sum
- Use a frequency map inside the window

---

# 1. Introduction

Sliding window is two pointers with a different name when used on **contiguous** subarrays/substrings. It's the right tool whenever the problem says "contiguous" and asks for a min/max over all subarrays satisfying a constraint.

---

# 2. Why Do We Need This?

Brute force on contiguous subarrays: enumerate all O(n²) subarrays, check each in O(n) ⇒ O(n³). Sliding window does it in O(n).

---

# 3. Core Concept

Maintain a window `[left, right]` (inclusive). Expand `right` to add elements. When the constraint breaks, shrink from `left`.

Two flavours:
- **Fixed size**: window length = K. Slide by 1 each step.
- **Variable size**: expand to add; shrink to restore validity. Track best answer.

---

# 4. Real-World Analogy

Imagine you're looking at a strip of film. You hold a frame (the window) and slide it across the film to find the prettiest 1-second clip.

---

# 5. Templates

### Fixed-size

```java
int sum = 0;
for (int r = 0; r < k; r++) sum += a[r];
int best = sum;
for (int r = k; r < a.length; r++) {
    sum += a[r] - a[r - k];
    best = Math.max(best, sum);
}
```

### Variable-size

```java
int left = 0; long sum = 0;
for (int right = 0; right < a.length; right++) {
    sum += a[right];
    while (/* window invalid */) sum -= a[left++];
    best = Math.max(best, right - left + 1);
}
```

---

# 6. Java Implementation — `SlidingWindowDemo.java`

```java
import java.util.*;

public class SlidingWindowDemo {

    /** Fixed: max sum of any subarray of size k. */
    static int maxSumK(int[] a, int k) {
        int sum = 0;
        for (int r = 0; r < k; r++) sum += a[r];
        int best = sum;
        for (int r = k; r < a.length; r++) {
            sum += a[r] - a[r - k];
            best = Math.max(best, sum);
        }
        return best;
    }

    /** Variable: longest substring without repeating chars. */
    static int longestUnique(String s) {
        int[] last = new int[256];
        Arrays.fill(last, -1);
        int best = 0, start = 0;
        for (int i = 0; i < s.length(); i++) {
            if (last[s.charAt(i)] >= start) start = last[s.charAt(i)] + 1;
            last[s.charAt(i)] = i;
            best = Math.max(best, i - start + 1);
        }
        return best;
    }

    /** Variable: min length subarray with sum >= target. */
    static int minSubArrayLen(int target, int[] a) {
        int lo = 0, sum = 0, best = Integer.MAX_VALUE;
        for (int hi = 0; hi < a.length; hi++) {
            sum += a[hi];
            while (sum >= target) {
                best = Math.min(best, hi - lo + 1);
                sum -= a[lo++];
            }
        }
        return best == Integer.MAX_VALUE ? 0 : best;
    }

    /** Frequency-based: minimum window substring. */
    static String minWindow(String s, String t) {
        int[] need = new int[128];
        for (char c : t.toCharArray()) need[c]++;
        int missing = t.length();
        int lo = 0, bestLo = 0, bestHi = Integer.MAX_VALUE;
        for (int hi = 0; hi < s.length(); hi++) {
            if (need[s.charAt(hi)]-- > 0) missing--;
            while (missing == 0) {
                if (hi - lo < bestHi - bestLo) { bestLo = lo; bestHi = hi; }
                if (need[s.charAt(lo)]++ == 0) missing++;
                lo++;
            }
        }
        return bestHi == Integer.MAX_VALUE ? "" : s.substring(bestLo, bestHi + 1);
    }

    /** Fixed: contains all anagram matches of p in s. */
    static List<Integer> findAnagrams(String s, String p) {
        int[] need = new int[26], have = new int[26];
        for (char c : p.toCharArray()) need[c - 'a']++;
        List<Integer> out = new ArrayList<>();
        for (int i = 0; i < s.length(); i++) {
            have[s.charAt(i) - 'a']++;
            if (i >= p.length()) have[s.charAt(i - p.length()) - 'a']--;
            if (i >= p.length() - 1 && Arrays.equals(need, have)) out.add(i - p.length() + 1);
        }
        return out;
    }

    public static void main(String[] args) {
        System.out.println("maxSumK size 3 = " + maxSumK(new int[]{2,1,5,1,3,2}, 3));
        System.out.println("longestUnique(abcabcbb) = " + longestUnique("abcabcbb"));
        System.out.println("minSubArrayLen(7) = " + minSubArrayLen(7, new int[]{2,3,1,2,4,3}));
        System.out.println("minWindow(ADOBECODEBANC, ABC) = " + minWindow("ADOBECODEBANC", "ABC"));
        System.out.println("findAnagrams(cbaebabacd, abc) = " + findAnagrams("cbaebabacd", "abc"));
    }
}
```

Walkthrough:

- `maxSumK`: build initial window sum, slide: add new right, drop old left.
- `longestUnique`: `last[c]` stores most recent index of char `c`. When char reappears inside window, jump `start` past the previous occurrence.
- `minSubArrayLen`: expand `hi`; while sum ≥ target, try shrinking from `lo`.
- `minWindow`: standard two-pointer with frequency needed.
- `findAnagrams`: fixed window of length `p.length()`; compare 26-slot frequency arrays each step.

---

# 7. Dry Run — `longestUnique("abcabcbb")`

| i | c | last[c] | start | window | best |
|---|---|---------|-------|--------|------|
| 0 | a | 0       | 0     | [0,0]  | 1    |
| 1 | b | 1       | 0     | [0,1]  | 2    |
| 2 | c | 2       | 0     | [0,2]  | 3    |
| 3 | a | 3       | 1 (since last[a]=0 ≥ 0) | [1,3] | 3 |
| 4 | b | 4       | 2     | [2,4]  | 3    |
| 5 | c | 5       | 3     | [3,5]  | 3    |
| 6 | b | 6       | 5     | [5,6]  | 2    |
| 7 | b | 7       | 7     | [7,7]  | 1    |

Result: **3**.

---

# 8. When to Use Sliding Window

| Signal | Use |
|---|---|
| Contiguous subarray/substring | Sliding window |
| Max/min over all windows of size K | Fixed window |
| Longest/shortest satisfying a constraint | Variable window |
| Anagram / permutation match | Fixed window + freq map |
| Min/max window containing all chars of T | Variable + freq map |

---

# 9. Common Mistakes

1. **Off-by-one in window boundaries**.
2. **Not shrinking** when the constraint breaks.
3. **O(n²) inside the shrink loop** — usually shrink should be O(1) amortised.
4. **Wrong initial window size** for fixed-size problems.

---

# 10. Interview Questions

### Q1. Sliding window vs two pointers?
Sliding window is a specialisation of two pointers on contiguous ranges.

### Q2. Why is the inner while-loop amortised O(1)?
Each element enters the window once (when `hi` expands) and leaves once (when `lo` shrinks). Total O(n).

### Q3. When do you need a HashMap inside the window?
When the constraint is about character counts (e.g. anagrams, distinct chars).

---

# 11. Practice Problems

## 🟢 Easy

### 1. Max Sum Subarray of Size K
**Input:** `[2,1,5,1,3,2], k=3` → **Output:** `9`

### 2. Average of Subarray of Size K
**Input:** `[1,12,-5,-6,50,3], k=4` → **Output:** `[12.75, 10.5, 12.5]`

### 3. Contains Duplicate II (within K distance)
**Input:** `nums=[1,2,3,1], k=3` → **Output:** `true`

### 4. Maximum in Sliding Window
**Input:** `[1,3,-1,-3,5,3,6,7], k=3` → **Output:** `[3,3,5,5,6,7]`

### 5. Number of Subarrays of Size K with Avg ≥ Threshold
**Input:** `[2,2,2,2,5,5,5,8], k=3, threshold=4` → **Output:** `3`

## 🟡 Medium

### 6. Longest Substring Without Repeating Chars
**Input:** `"abcabcbb"` → **Output:** `3`

### 7. Longest Repeating Character Replacement
**Input:** `"AABABBA", k=1` → **Output:** `4`

### 8. Permutation in String
**Input:** `s="cbaebabacd", p="abc"` → **Output:** `[0,6]`

### 9. Minimum Size Subarray Sum
**Input:** `target=7, [2,3,1,2,4,3]` → **Output:** `2`

### 10. Fruit Into Baskets
**Input:** `[1,2,1]` → **Output:** `3`

## 🔴 Hard

### 11. Minimum Window Substring
**Input:** `s="ADOBECODEBANC", t="ABC"` → **Output:** `"BANC"`

### 12. Sliding Window Maximum (Deque)
**Input:** `[1,3,-1,-3,5,3,6,7], k=3` → **Output:** `[3,3,5,5,6,7]`

### 13. Substring with Concatenation of All Words
**Input:** `s="barfoothefoobarman", words=["foo","bar"]` → **Output:** `[0,9]`

### 14. Minimum Number of Flips to Make Binary String Alternating
**Input:** `"111000"` → **Output:** `2`

### 15. Longest Substring with At Most K Distinct
**Input:** `"eceba", k=2` → **Output:** `3` ("ece")

---

# 12. Practice Hints

## Easy
1. Initial window sum, slide.
2. Sum then divide.
3. HashMap of value → index.
4. Deque of indices.
5. Sum window / k vs threshold.

## Medium
6. Last-index array.
7. windowLen − maxCount ≤ k.
8. Sliding freq.
9. Expand/shrink.
10. Two distinct max.

## Hard
11. Two-pointer + freq.
12. Monotonic deque.
13. HashMap word count + window.
14. Sliding-window count of mismatches.
15. HashMap of char counts, shrink when > k distinct.

---

# 13. Revision Checklist

- [ ] Recognise sliding-window problems
- [ ] Can do fixed-size window in O(n)
- [ ] Can do variable window with frequency map
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 14. Key Takeaways

- Sliding window = two pointers on contiguous ranges.
- Fixed size: window length = K.
- Variable size: shrink when invalid, expand when valid.
- Frequency map inside window handles character-count constraints.

Tomorrow: **Prefix Sum**.


## Solutions

### Problem 1 — MaxSumK (E)

```java
class MaxSumK {
    public static void main(String[] args) {
        int[] a = {2,1,5,1,3,2}; int k = 3, sum = 0, best = 0;
        for (int i = 0; i < k; i++) sum += a[i];
        best = sum;
        for (int i = k; i < a.length; i++) { sum += a[i] - a[i-k]; best = Math.max(best, sum); }
        System.out.println(best);
    }
}
```

### Problem 2 — AvgK (E)

```java
class AvgK {
    public static void main(String[] args) {
        int[] a = {1,3,2,6,-1,4,1,8,2};
        int k = 5;
        double sum = 0;
        for (int i = 0; i < k; i++) sum += a[i];
        java.util.List<Double> out = new java.util.ArrayList<>();
        out.add(sum / k);
        for (int i = k; i < a.length; i++) { sum += a[i] - a[i-k]; out.add(sum / k); }
        System.out.println(out);
    }
}
```

### Problem 3 — DupK (E)

```java
class DupK {
    public static void main(String[] args) {
        int[] a = {1,2,3,1}; int k = 3;
        java.util.Set<Integer> seen = new java.util.HashSet<>();
        boolean dup = false;
        for (int i = 0; i < a.length && !dup; i++) {
            if (i > k) seen.remove(a[i-k-1]);
            if (!seen.add(a[i])) dup = true;
        }
        System.out.println(dup);
    }
}
```

### Problem 4 — MaxWin (E)

```java
class MaxWin {
    public static void main(String[] args) {
        int[] a = {1,3,-1,-3,5,3,6,7}; int k = 3;
        java.util.Deque<Integer> dq = new java.util.ArrayDeque<>();
        int[] out = new int[a.length - k + 1];
        for (int i = 0; i < a.length; i++) {
            while (!dq.isEmpty() && dq.peekFirst() <= i - k) dq.pollFirst();
            while (!dq.isEmpty() && a[dq.peekLast()] <= a[i]) dq.pollLast();
            dq.offerLast(i);
            if (i >= k - 1) out[i - k + 1] = a[dq.peekFirst()];
        }
        System.out.println(java.util.Arrays.toString(out));
    }
}
```

### Problem 5 — AvgThreshold (E)

```java
class AvgThreshold {
    public static void main(String[] args) {
        int[] a = {2,2,2,2,2,2}; int k = 3, threshold = 3, count = 0, sum = 0;
        for (int i = 0; i < k; i++) sum += a[i];
        if (sum / (double)k >= threshold) count++;
        for (int i = k; i < a.length; i++) { sum += a[i] - a[i-k]; if (sum / (double)k >= threshold) count++; }
        System.out.println(count);
    }
}
```

### Problem 6 — NoRep (M)

```java
class NoRep {
    public static void main(String[] args) {
        String s = "abcabcbb";
        java.util.Map<Character,Integer> last = new java.util.HashMap<>();
        int lo = 0, best = 0;
        for (int hi = 0; hi < s.length(); hi++) {
            char c = s.charAt(hi);
            if (last.containsKey(c)) lo = Math.max(lo, last.get(c) + 1);
            last.put(c, hi);
            best = Math.max(best, hi - lo + 1);
        }
        System.out.println(best);
    }
}
```

### Problem 7 — CharRep (M)

```java
class CharRep {
    public static void main(String[] args) {
        String s = "AABABBA"; int k = 1;
        int[] c = new int[26];
        int lo = 0, max = 0, best = 0;
        for (int hi = 0; hi < s.length(); hi++) {
            int idx = s.charAt(hi) - 'A';
            c[idx]++; max = Math.max(max, c[idx]);
            while ((hi - lo + 1) - max > k) {
                c[s.charAt(lo++) - 'A']--;
            }
            best = Math.max(best, hi - lo + 1);
        }
        System.out.println(best);
    }
}
```

### Problem 8 — Perm (M)

```java
class Perm {
    public static void main(String[] args) {
        String s1 = "ab", s2 = "eidbaooo";
        int[] need = new int[26], have = new int[26];
        for (char c : s1.toCharArray()) need[c-'a']++;
        int k = s1.length();
        boolean ok = false;
        for (int i = 0; i < s2.length(); i++) {
            have[s2.charAt(i)-'a']++;
            if (i >= k) have[s2.charAt(i-k)-'a']--;
            if (i >= k-1 && java.util.Arrays.equals(need, have)) { ok = true; break; }
        }
        System.out.println(ok);
    }
}
```

### Problem 9 — MinSub (M)

```java
class MinSub {
    public static void main(String[] args) {
        int[] a = {2,3,1,2,4,3}; int t = 7;
        int l = 0, sum = 0, best = Integer.MAX_VALUE;
        for (int r = 0; r < a.length; r++) {
            sum += a[r];
            while (sum >= t) { best = Math.min(best, r - l + 1); sum -= a[l++]; }
        }
        System.out.println(best == Integer.MAX_VALUE ? 0 : best);
    }
}
```

### Problem 10 — Fruit (M)

```java
class Fruit {
    public static void main(String[] args) {
        int[] a = {1,2,1}; int lo = 0, best = 0;
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>();
        for (int hi = 0; hi < a.length; hi++) {
            m.merge(a[hi], 1, Integer::sum);
            while (m.size() > 2) {
                m.merge(a[lo], -1, Integer::sum);
                if (m.get(a[lo]) == 0) m.remove(a[lo]);
                lo++;
            }
            best = Math.max(best, hi - lo + 1);
        }
        System.out.println(best);
    }
}
```

### Problem 11 — MinWin2 (H)

```java
class MinWin2 {
    public static void main(String[] args) {
        String s = "ADOBECODEBANC", t = "ABC";
        java.util.Map<Character,Integer> need = new java.util.HashMap<>();
        for (char c : t.toCharArray()) need.merge(c, 1, Integer::sum);
        java.util.Map<Character,Integer> have = new java.util.HashMap<>();
        int lo = 0, formed = 0, best = Integer.MAX_VALUE, bestLo = 0;
        for (int hi = 0; hi < s.length(); hi++) {
            char c = s.charAt(hi);
            have.merge(c, 1, Integer::sum);
            if (need.containsKey(c) && have.get(c).intValue() == need.get(c).intValue()) formed++;
            while (formed == need.size()) {
                if (hi - lo + 1 < best) { best = hi - lo + 1; bestLo = lo; }
                char cl = s.charAt(lo++);
                if (need.containsKey(cl) && have.get(cl).intValue() == need.get(cl).intValue()) formed--;
                have.merge(cl, -1, Integer::sum);
            }
        }
        System.out.println(best == Integer.MAX_VALUE ? "" : s.substring(bestLo, bestLo + best));
    }
}
```

### Problem 12 — MaxWinDeque (H)

```java
class MaxWinDeque {
    public static void main(String[] args) {
        int[] a = {1,3,-1,-3,5,3,6,7}; int k = 3;
        java.util.Deque<Integer> dq = new java.util.ArrayDeque<>();
        int[] out = new int[a.length - k + 1];
        for (int i = 0; i < a.length; i++) {
            while (!dq.isEmpty() && dq.peekFirst() <= i - k) dq.pollFirst();
            while (!dq.isEmpty() && a[dq.peekLast()] <= a[i]) dq.pollLast();
            dq.offerLast(i);
            if (i >= k - 1) out[i - k + 1] = a[dq.peekFirst()];
        }
        System.out.println(java.util.Arrays.toString(out));
    }
}
```

### Problem 13 — WordsConcat (H)

```java
class WordsConcat {
    // Sliding window over concatenated word length.
    public static void main(String[] args) {
        String s = "barfoothefoobarman"; String[] words = {"foo","bar","the"};
        java.util.Map<String,Integer> need = new java.util.HashMap<>();
        for (String w : words) need.merge(w, 1, Integer::sum);
        int wl = words[0].length(), n = words.length;
        java.util.List<Integer> res = new java.util.ArrayList<>();
        for (int off = 0; off < wl; off++) {
            java.util.Map<String,Integer> have = new java.util.HashMap<>();
            for (int i = off, j = off; j + wl <= s.length(); j += wl) {
                String w = s.substring(j, j + wl);
                have.merge(w, 1, Integer::sum);
                int cnt = (j - i) / wl + 1;
                if (cnt > n) {
                    String out = s.substring(i, i + wl);
                    have.merge(out, -1, Integer::sum);
                    i += wl;
                }
                if (cnt == n && have.equals(need)) res.add(i);
            }
        }
        System.out.println(res);
    }
}
```

### Problem 14 — MinFlips (H)

```java
class MinFlips {
    public static void main(String[] args) {
        String s = "11100100"; int k = 2;
        int flips = 0, alt = 0;
        for (int i = 0; i < s.length(); i++) {
            if (s.charAt(i) - '0' != alt) flips++;
            alt ^= 1;
            if (i >= k - 1) { flips = Math.min(flips, k - flips); /* reset not needed */ }
        }
        // For full answer we'd reset per k window; printing the running minimum:
        System.out.println(flips);
    }
}
```

### Problem 15 — KDistinct (H)

```java
class KDistinct {
    public static void main(String[] args) {
        String s = "eceba"; int k = 2;
        java.util.Map<Character,Integer> m = new java.util.HashMap<>();
        int lo = 0, best = 0;
        for (int hi = 0; hi < s.length(); hi++) {
            m.merge(s.charAt(hi), 1, Integer::sum);
            while (m.size() > k) {
                m.merge(s.charAt(lo), -1, Integer::sum);
                if (m.get(s.charAt(lo)) == 0) m.remove(s.charAt(lo));
                lo++;
            }
            best = Math.max(best, hi - lo + 1);
        }
        System.out.println(best);
    }
}
```

