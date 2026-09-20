# Day 6 — Strings

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Explain String immutability and the String pool
- Use `StringBuilder` for efficient string building
- Compare strings correctly (`==` vs `equals`)
- Detect palindromes, anagrams, substrings
- Count character frequencies
- Know the common String APIs

---

# 1. Introduction

Strings look like primitives but they aren't. Misusing them is the #1 cause of "why is my code so slow?" moments.

Today you'll learn *why* strings are immutable, when to use `StringBuilder`, and the small set of methods that cover 90% of DSA problems.

---

# 2. Why Do We Need This?

Strings appear in nearly every problem: parsing input, checking anagrams, palindromes, substring searches. Knowing the right tools and pitfalls saves time and bugs.

---

# 3. Core Concept — Immutability

A `String` in Java is an **immutable** sequence of characters. Once created, it cannot be changed.

```java
String s = "hello";
s = s + " world";   // creates a NEW string, s now references it
```

Why?

- **Security**: strings are used as keys in `HashMap`, URLs, file paths.
- **Caching**: `String` pool lets JVM reuse literals.
- **Thread-safety**: immutable objects are inherently safe.

### String Pool

```java
String a = "hello";
String b = "hello";
System.out.println(a == b);   // true — same pool entry
String c = new String("hello");
System.out.println(a == c);   // false — different object
```

The pool is a special area in the JVM heap. String literals are interned there.

---

# 4. Real-World Analogy

A `String` is like a printed book page: once printed, the words don't change. If you want different text, you print a new page. If you're writing a lot of text, use a chalkboard (`StringBuilder`) — you can erase and rewrite cheaply.

---

# 5. Syntax — Common APIs

```java
String s = "Hello, World";

s.length();              // 12 — method, NOT field
s.charAt(0);             // 'H'
s.substring(0, 5);       // "Hello" — [0, 5)
s.indexOf("World");      // 7
s.contains("Hello");     // true
s.startsWith("Hello");   // true
s.endsWith("World");     // true
s.toLowerCase();         // "hello, world"
s.toUpperCase();         // "HELLO, WORLD"
s.trim();                // strips leading/trailing whitespace
s.replace('o', '0');     // "Hell0, W0rld"
s.split(", ");           // ["Hello", "World"]
s.equals(other);         // content equality
s.equalsIgnoreCase(other); // case-insensitive
s.isEmpty();             // length == 0
s.isBlank();             // all whitespace (Java 11+)
```

---

# 6. StringBuilder

When you need to **build** a string inside a loop, use `StringBuilder`.

```java
StringBuilder sb = new StringBuilder();
for (int i = 0; i < n; i++) sb.append(i).append(' ');
String s = sb.toString();
```

- `append(...)` — many overloads (int, char, String, etc.); returns `this` for chaining.
- `length()`, `charAt(i)`, `setCharAt(i, c)`, `reverse()`.
- `toString()` — produces the final `String`.

Performance: `StringBuilder` avoids allocating a new object per concatenation. For n appends of size k, naive `String += s` is O(n² k); `StringBuilder` is O(n k) amortised.

---

# 7. Java Implementation — `StringsDemo.java`

```java
public class StringsDemo {

    public static void main(String[] args) {
        // === Immutability ===
        String s = "Hello";
        s.concat(" World");            // returns a new string, but doesn't modify s
        System.out.println(s);          // still "Hello"
        s = s.concat(" World");         // rebind
        System.out.println(s);          // "Hello World"

        // === String pool ===
        String a = "Java";
        String b = "Java";
        String c = new String("Java");
        System.out.println(a == b);      // true
        System.out.println(a == c);      // false
        System.out.println(a.equals(c)); // true

        // === Palindrome check ===
        System.out.println(isPalindrome("racecar"));  // true
        System.out.println(isPalindrome("hello"));    // false

        // === Anagram check ===
        System.out.println(isAnagram("listen", "silent")); // true

        // === Character frequency ===
        int[] freq = frequency("aabbc");
        for (int i = 0; i < freq.length; i++)
            if (freq[i] > 0) System.out.println((char) i + ": " + freq[i]);

        // === StringBuilder reverse ===
        System.out.println(reverseWithBuilder("hello"));   // "olleh"

        // === All substrings ===
        System.out.println(allSubstrings("abc"));
    }

    static boolean isPalindrome(String s) {
        int lo = 0, hi = s.length() - 1;
        while (lo < hi) {
            if (s.charAt(lo) != s.charAt(hi)) return false;
            lo++; hi--;
        }
        return true;
    }

    static boolean isAnagram(String a, String b) {
        if (a.length() != b.length()) return false;
        int[] f = new int[26];
        for (int i = 0; i < a.length(); i++) { f[a.charAt(i) - 'a']++; f[b.charAt(i) - 'a']--; }
        for (int x : f) if (x != 0) return false;
        return true;
    }

    static int[] frequency(String s) {
        int[] f = new int[256];
        for (int i = 0; i < s.length(); i++) f[s.charAt(i)]++;
        return f;
    }

    static String reverseWithBuilder(String s) {
        return new StringBuilder(s).reverse().toString();
    }

    static java.util.List<String> allSubstrings(String s) {
        java.util.List<String> out = new java.util.ArrayList<>();
        for (int i = 0; i < s.length(); i++)
            for (int j = i + 1; j <= s.length(); j++)
                out.add(s.substring(i, j));
        return out;
    }
}
```

Walkthrough:

- `s.concat(" World")` returns a new `String`; `s` is unchanged because `String` is immutable. The original `s` reference must be reassigned.
- `a == b` compares references. Pooling causes both to point to the same interned `"Java"` literal.
- `a == c` is false because `new String(...)` creates a new object outside the pool.
- `isPalindrome` uses two pointers converging; O(n) time, O(1) space.
- `isAnagram` uses a 26-slot frequency array (assumes lowercase a-z). For Unicode, use `HashMap<Character, Integer>`.
- `frequency(String)` uses a 256-slot array, one per byte value (good for ASCII).
- `new StringBuilder(s).reverse().toString()` — `StringBuilder.reverse()` mutates the builder; `toString()` converts back.
- `allSubstrings` is O(n³) total (n² substrings, each O(n) to extract). Acceptable for small n.

---

# 8. char[] vs String

`charAt(i)` returns a `char`. You can convert to `char[]` for in-place edits:

```java
char[] a = s.toCharArray();
a[0] = 'h';
String s2 = new String(a);
```

For problems requiring modification, working in `char[]` then converting is faster than `StringBuilder`.

---

# 9. Dry Run — `isAnagram("listen", "silent")`

```
Initial:  f = [0,0,0,...,0]
'l': f['l'-'a']++   → f[11] = 1
'i': f['i'-'a']++   → f[8]  = 1
's': f['s'-'a']++   → f[18] = 1
't': f['t'-'a']++   → f[19] = 1
'e': f['e'-'a']++   → f[4]  = 1
'n': f['n'-'a']++   → f[13] = 1

's': f['s'-'a']--   → f[18] = 0
'i': f['i'-'a']--   → f[8]  = 0
'l': f['l'-'a']--   → f[11] = 0
'e': f['e'-'a']--   → f[4]  = 0
'n': f['n'-'a']--   → f[13] = 0
't': f['t'-'a']--   → f[19] = 0

All zero → anagram ✓
```

---

# 10. Time Complexity

| Operation | Complexity |
|---|---:|
| `length()` | O(1) |
| `charAt(i)` | O(1) |
| `substring(l, r)` | O(r-l) (in modern Java, copies the range) |
| `equals(other)` | O(min length) |
| `indexOf(s)` | O(n × m) naive, O(n+m) with KMP |
| `String += s` (in loop) | O(n) per concat (creates new) |
| `StringBuilder.append` | O(1) amortised |
| `new StringBuilder(s).reverse()` | O(n) |

---

# 11. Common Mistakes

1. **`==` instead of `equals`** — compares references, not content.
2. **`String s += x` in a tight loop** — slow; use `StringBuilder`.
3. **Mutating a "substring"** — strings are immutable; you must convert to `char[]` or `StringBuilder`.
4. **Off-by-one in `substring(lo, hi)`** — it's `[lo, hi)`, hi exclusive.
5. **Comparing across case** without `equalsIgnoreCase`.
6. **Calling `length` without parentheses** — it's a method, not a field.

---

# 12. Interview Questions

### Q1. Why are Strings immutable?
Security, caching (pool), thread-safety.

### Q2. StringBuilder vs StringBuffer?
`StringBuffer` is thread-safe (synchronised), slower. `StringBuilder` is faster, not thread-safe.

### Q3. How do you reverse a string without StringBuilder?
Convert to `char[]`, swap symmetric pairs.

### Q4. How to check if two strings are anagrams in O(n)?
Sort both (O(n log n)) or count characters (O(n)).

### Q5. What does `intern()` do?
Adds a String to the pool; returns the pooled reference.

### Q6. What's the difference between `length` and `length()`?
Arrays use `arr.length` (field). Strings use `s.length()` (method).

---

# 13. Practice Problems

## 🟢 Easy

### 1. Reverse a String
**Input:** `"hello"` → **Output:** `"olleh"`

### 2. Check Palindrome
**Input:** `"racecar"` → **Output:** `true`

### 3. Count Vowels
**Input:** `"hello"` → **Output:** `2`

### 4. To Upper / To Lower
**Input:** `"Hello"` → **Output:** `"HELLO"`, `"hello"`

### 5. First Non-Repeating Character
**Input:** `"aabbcdd"` → **Output:** `c`

## 🟡 Medium

### 6. Valid Anagram
**Input:** `"anagram"`, `"nagaram"` → **Output:** `true`

### 7. Longest Substring Without Repeating Chars
**Input:** `"abcabcbb"` → **Output:** `3`

### 8. String Compression (e.g. `"aabcccccaaa"` → `"a2b1c5a3"`)
**Output:** `"a2b1c5a3"`

### 9. Reverse Words in a String
**Input:** `"the sky is blue"` → **Output:** `"blue is sky the"`

### 10. Group Anagrams
**Input:** `["eat","tea","tan","ate","nat","bat"]` → grouped by anagram.

## 🔴 Hard

### 11. Longest Palindromic Substring
**Input:** `"babad"` → **Output:** `"bab"` or `"aba"`

### 12. Minimum Window Substring
**Input:** `s="ADOBECODEBANC", t="ABC"` → **Output:** `"BANC"`

### 13. Edit Distance
**Input:** `"horse"`, `"ros"` → **Output:** `3`

### 14. Longest Common Prefix
**Input:** `["flower","flow","flight"]` → **Output:** `"fl"`

### 15. Rabin-Karp Substring Search
**Input:** text `"abcxabcdabcy"`, pattern `"abcd"` → **Output:** `4`

---

# 14. Practice Hints

## Easy
1. `new StringBuilder(s).reverse()`.
2. Two pointers.
3. Set `aeiou`, count.
4. `toUpperCase`, `toLowerCase`.
5. Frequency array, find index with count 1.

## Medium
6. 26-slot count.
7. Sliding window (preview).
8. Walk and count runs.
9. Split + reverse + join.
10. Sort each string; group by sorted.

## Hard
11. Expand-around-centre.
12. Sliding window with needed-count.
13. DP (Day 28).
14. Vertical scan.
15. Rolling hash.

---

# 15. Revision Checklist

- [ ] Can explain String immutability
- [ ] Can use StringBuilder
- [ ] Can compare strings correctly
- [ ] Can detect palindrome and anagram
- [ ] Can build character frequency array
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 16. Key Takeaways

- `String` is immutable; `+` creates a new object.
- Use `StringBuilder` for repeated modifications.
- Compare with `equals`, not `==`.
- `length()` is a method, `length` (array) is a field.
- Anagram check: 26-slot count, O(n).
- Palindrome: two pointers.

Tomorrow: **Two Pointers**.


## Solutions

### Problem 1 — RevStr (E)

```java
class RevStr {
    public static void main(String[] args) {
        System.out.println(new StringBuilder("hello").reverse());
    }
}
```

### Problem 2 — PalStr (E)

```java
class PalStr {
    public static void main(String[] args) {
        String s = "racecar"; int l = 0, r = s.length() - 1;
        while (l < r && s.charAt(l) == s.charAt(r)) { l++; r--; }
        System.out.println(l >= r);
    }
}
```

### Problem 3 — Vow (E)

```java
class Vow {
    public static void main(String[] args) {
        String s = "Hello"; int c = 0;
        for (char ch : s.toCharArray()) if ("aeiouAEIOU".indexOf(ch) >= 0) c++;
        System.out.println(c);
    }
}
```

### Problem 4 — Case (E)

```java
class Case {
    public static void main(String[] args) {
        System.out.println("Hello World".toUpperCase());
        System.out.println("Hello World".toLowerCase());
    }
}
```

### Problem 5 — FirstUniq (E)

```java
class FirstUniq {
    public static void main(String[] args) {
        String s = "swiss";
        java.util.Map<Character,Integer> m = new java.util.LinkedHashMap<>();
        for (char c : s.toCharArray()) m.merge(c, 1, Integer::sum);
        char ans = 0;
        for (var e : m.entrySet()) if (e.getValue() == 1) { ans = e.getKey(); break; }
        System.out.println(ans);
    }
}
```

### Problem 6 — Anagram (M)

```java
class Anagram {
    static boolean isAnagram(String a, String b) {
        if (a.length() != b.length()) return false;
        int[] c = new int[26];
        for (int i = 0; i < a.length(); i++) { c[a.charAt(i)-'a']++; c[b.charAt(i)-'a']--; }
        for (int x : c) if (x != 0) return false;
        return true;
    }
    public static void main(String[] args) { System.out.println(isAnagram("listen", "silent")); }
}
```

### Problem 7 — NoRepeat (M)

```java
class NoRepeat {
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

### Problem 8 — Compress (M)

```java
class Compress {
    static String comp(String s) {
        StringBuilder sb = new StringBuilder();
        int i = 0;
        while (i < s.length()) {
            int j = i;
            while (j < s.length() && s.charAt(j) == s.charAt(i)) j++;
            sb.append(s.charAt(i)).append(j - i);
            i = j;
        }
        return sb.toString();
    }
    public static void main(String[] args) { System.out.println(comp("aabcccccaaa")); }
}
```

### Problem 9 — RevWords (M)

```java
class RevWords {
    public static void main(String[] args) {
        String s = "the quick brown fox";
        String[] w = s.split(" ");
        StringBuilder sb = new StringBuilder();
        for (int i = w.length - 1; i >= 0; i--) sb.append(w[i]).append(i==0?"":" ");
        System.out.println(sb);
    }
}
```

### Problem 10 — GroupAn (M)

```java
class GroupAn {
    public static void main(String[] args) {
        String[] strs = {"eat","tea","tan","ate","nat","bat"};
        java.util.Map<String, java.util.List<String>> m = new java.util.HashMap<>();
        for (String s : strs) {
            char[] c = s.toCharArray(); java.util.Arrays.sort(c);
            m.computeIfAbsent(new String(c), k -> new java.util.ArrayList<>()).add(s);
        }
        System.out.println(new java.util.ArrayList<>(m.values()));
    }
}
```

### Problem 11 — LPSub (H)

```java
class LPSub {
    // Expand-around-centre.
    static String lps(String s) {
        int bestLo = 0, bestLen = 0;
        for (int c = 0; c < s.length(); c++) {
            for (int odd = 0, even = 0; ; odd = even = 0) {
                int l = c - odd, r = c + odd + 1;          // odd len
                while (l>=0 && r<s.length() && s.charAt(l)==s.charAt(r)) { l--; r++; }
                if (r - l - 1 > bestLen) { bestLen = r - l - 1; bestLo = l + 1; }
                l = c - even; r = c + even + 1;             // even len
                while (l>=0 && r<s.length() && s.charAt(l)==s.charAt(r)) { l--; r++; }
                if (r - l - 1 > bestLen) { bestLen = r - l - 1; bestLo = l + 1; }
                if (c + (odd > 0 ? 1 : 0) >= s.length()) break;
            }
        }
        return s.substring(bestLo, bestLo + bestLen);
    }
    public static void main(String[] args) { System.out.println(lps("babad")); }
}
```

### Problem 12 — MinWin (H)

```java
class MinWin {
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

### Problem 13 — EditDist (H)

```java
class EditDist {
    public static void main(String[] args) {
        String a = "horse", b = "ros";
        int m = a.length(), n = b.length();
        int[][] dp = new int[m+1][n+1];
        for (int i = 0; i <= m; i++) dp[i][0] = i;
        for (int j = 0; j <= n; j++) dp[0][j] = j;
        for (int i = 1; i <= m; i++)
            for (int j = 1; j <= n; j++) {
                if (a.charAt(i-1) == b.charAt(j-1)) dp[i][j] = dp[i-1][j-1];
                else dp[i][j] = 1 + Math.min(dp[i-1][j-1], Math.min(dp[i-1][j], dp[i][j-1]));
            }
        System.out.println(dp[m][n]);
    }
}
```

### Problem 14 — LCP (H)

```java
class LCP {
    public static void main(String[] args) {
        String[] strs = {"flower","flow","flight"};
        String pref = strs[0];
        for (int i = 1; i < strs.length; i++)
            while (!strs[i].startsWith(pref)) pref = pref.substring(0, pref.length()-1);
        System.out.println(pref);
    }
}
```

### Problem 15 — RK (H)

```java
class RK {
    static int search(String text, String pat) {
        if (pat.length() > text.length()) return -1;
        long base = 31, mod = 1_000_000_007, pHash = 0, tHash = 0, h = 1;
        for (int i = 0; i < pat.length() - 1; i++) h = h * base % mod;
        for (int i = 0; i < pat.length(); i++) {
            pHash = (pHash * base + pat.charAt(i)) % mod;
            tHash = (tHash * base + text.charAt(i)) % mod;
        }
        for (int i = 0; i <= text.length() - pat.length(); i++) {
            if (pHash == tHash && text.substring(i, i + pat.length()).equals(pat)) return i;
            if (i + pat.length() < text.length())
                tHash = ((tHash - text.charAt(i) * h) * base + text.charAt(i + pat.length())) % mod;
        }
        return -1;
    }
    public static void main(String[] args) {
        System.out.println(search("hello world", "world"));
    }
}
```

