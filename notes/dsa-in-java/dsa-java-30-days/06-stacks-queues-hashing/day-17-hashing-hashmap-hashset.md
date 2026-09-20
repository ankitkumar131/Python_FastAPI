# Day 17 — Hashing

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Explain hashing, hash functions, collisions, and buckets
- Use `HashMap`, `HashSet`, `LinkedHashMap`, `TreeMap`
- Pick the right map for the situation
- Solve frequency problems, two sum, group anagrams
- Know the average-case complexity and the worst case

---

# 1. Introduction

Hashing is the most-used technique in interviews. It converts a key into an integer "bucket index" so we can store and look up in average O(1).

---

# 2. Why Do We Need This?

- **Lookup by key**: O(1) average instead of O(n) (array) or O(log n) (BST).
- **Frequency counting**: trivial with `HashMap`.
- **Deduplication**: `HashSet`.

---

# 3. Core Concept — Hash Function and Bucket

```
key → hash(key) → bucket index → store/retrieve entry
```

A **collision** happens when two keys hash to the same bucket. Java's `HashMap` handles collisions with **separate chaining**: each bucket holds a linked list (or tree if too long).

---

# 4. Real-World Analogy

A library's card catalogue: each book has a Dewey-decimal "hash" telling you exactly which shelf it's on. Two books might end up on the same shelf; the librarian keeps a sub-list.

---

# 5. Java Implementation — `HashingDemo.java`

```java
import java.util.*;

public class HashingDemo {

    /** Two Sum using HashMap. */
    static int[] twoSum(int[] a, int target) {
        Map<Integer, Integer> seen = new HashMap<>();
        for (int i = 0; i < a.length; i++) {
            int need = target - a[i];
            if (seen.containsKey(need)) return new int[]{seen.get(need), i};
            seen.put(a[i], i);
        }
        return new int[]{-1, -1};
    }

    /** Frequency count. */
    static Map<Integer, Integer> frequency(int[] a) {
        Map<Integer, Integer> m = new HashMap<>();
        for (int x : a) m.merge(x, 1, Integer::sum);
        return m;
    }

    /** Group anagrams. */
    static List<List<String>> groupAnagrams(String[] words) {
        Map<String, List<String>> m = new HashMap<>();
        for (String w : words) {
            char[] c = w.toCharArray();
            Arrays.sort(c);
            String key = new String(c);
            m.computeIfAbsent(key, k -> new ArrayList<>()).add(w);
        }
        return new ArrayList<>(m.values());
    }

    /** Longest consecutive sequence. */
    static int longestConsecutive(int[] a) {
        Set<Integer> s = new HashSet<>();
        for (int x : a) s.add(x);
        int best = 0;
        for (int x : s) {
            if (!s.contains(x - 1)) {
                int len = 1, cur = x;
                while (s.contains(cur + 1)) { cur++; len++; }
                best = Math.max(best, len);
            }
        }
        return best;
    }

    /** Subarray sum equals k (with negatives). */
    static int subarraySum(int[] a, int k) {
        Map<Integer, Integer> m = new HashMap<>();
        m.put(0, 1);
        int sum = 0, count = 0;
        for (int x : a) {
            sum += x;
            count += m.getOrDefault(sum - k, 0);
            m.merge(sum, 1, Integer::sum);
        }
        return count;
    }

    /** Demo of map variants. */
    static void mapVariants() {
        // HashMap:    no order guarantees.
        Map<String, Integer> hash = new HashMap<>();
        // LinkedHashMap: insertion-order.
        Map<String, Integer> linked = new LinkedHashMap<>();
        // TreeMap:    keys sorted by natural order.
        Map<String, Integer> tree = new TreeMap<>();

        for (String k : new String[]{"c", "a", "b"}) {
            hash.put(k, 1); linked.put(k, 1); tree.put(k, 1);
        }
        System.out.println("HashMap        : " + hash.keySet());
        System.out.println("LinkedHashMap  : " + linked.keySet());
        System.out.println("TreeMap        : " + tree.keySet());
    }

    public static void main(String[] args) {
        System.out.println("twoSum         = " + Arrays.toString(twoSum(new int[]{2,7,11,15}, 9)));
        System.out.println("frequency      = " + frequency(new int[]{1,1,2,3,3,3}));
        System.out.println("groupAnagrams  = " + groupAnagrams(new String[]{"eat","tea","tan","ate","nat","bat"}));
        System.out.println("longestConsec  = " + longestConsecutive(new int[]{100,4,200,1,3,2}));
        System.out.println("subarraySum    = " + subarraySum(new int[]{1,2,3}, 3));
        mapVariants();
    }
}
```

Walkthrough:

- `twoSum`: for each `a[i]`, check if `target - a[i]` is in the map. If yes, return its index and `i`. Otherwise store `a[i]`.
- `frequency`: `merge` is concise for incrementing counts.
- `groupAnagrams`: sorting the chars gives a canonical key; anagrams share the key.
- `longestConsecutive`: only start counting from elements without a predecessor to avoid redundant work.
- `subarraySum`: prefix sum + map of counts (Day 9 revisited).
- `mapVariants`: HashMap is unordered, LinkedHashMap preserves insertion order, TreeMap sorts keys.

---

# 6. Java Map Hierarchy

```
Map (interface)
├── HashMap            O(1) average, no order
│   └── LinkedHashMap  O(1), insertion order
├── TreeMap            O(log n), sorted keys
├── Hashtable          legacy, synchronised
└── ConcurrentHashMap  thread-safe

Set (interface)
├── HashSet            backed by HashMap
├── LinkedHashSet      insertion order
└── TreeSet            sorted
```

---

# 7. Complexity

| Operation        | HashMap avg | HashMap worst | TreeMap |
|------------------|------------:|--------------:|--------:|
| put / get / remove | O(1)      | O(n)*         | O(log n) |
| contains         | O(1)        | O(n)          | O(log n) |
| iterate          | O(n)        | O(n)          | O(n)    |

`*` worst case is rare; in Java 8+ it becomes O(log n) when a bucket's list exceeds 8 entries.

---

# 8. Common Mistakes

1. **Mutable keys in a HashMap** — mutating the key makes it unfindable. Use immutable keys.
2. **HashMap not thread-safe** — use `ConcurrentHashMap` for concurrency.
3. **`HashMap.get(null)` works but only one null key allowed**.
4. **Initial capacity too small** — lots of resizing; pre-size if you know.

---

# 9. Interview Questions

### Q1. How does HashMap work internally?
Array of buckets. Each key is hashed to a bucket. Collisions chain (LinkedList, then Red-Black tree if list > 8).

### Q2. Why is HashMap O(1) average?
Hash function distributes keys uniformly; load factor keeps bucket size small.

### Q3. HashMap vs TreeMap?
HashMap: O(1) but unordered. TreeMap: O(log n) but sorted.

### Q4. What does `equals` and `hashCode` need to satisfy?
If `a.equals(b)`, then `a.hashCode() == b.hashCode()`. Override both together.

---

# 10. Practice Problems

## 🟢 Easy

### 1. Two Sum
**Input:** `[2,7,11,15], t=9` → **Output:** `[0,1]`

### 2. Contains Duplicate
**Input:** `[1,2,3,1]` → **Output:** `true`

### 3. Intersection of Two Arrays
**Input:** `[1,2,2,1]`, `[2,2]` → **Output:** `[2]`

### 4. First Unique Character
**Input:** `"leetcode"` → **Output:** `0`

### 5. Valid Anagram
**Input:** `"anagram", "nagaram"` → **Output:** `true`

## 🟡 Medium

### 6. Group Anagrams
**Input:** `["eat","tea","tan","ate","nat","bat"]` → grouped.

### 7. Top K Frequent
**Input:** `[1,1,1,2,2,3], k=2` → **Output:** `[1,2]`

### 8. Longest Consecutive Sequence
**Input:** `[100,4,200,1,3,2]` → **Output:** `4`

### 9. Subarray Sum Equals K
**Input:** `[1,1,1], k=2` → **Output:** `2`

### 10. 4Sum II (count tuples)
**Input:** `A=[1,2], B=[-2,-1], C=[-1,2], D=[0,2]` → **Output:** `2`

## 🔴 Hard

### 11. LRU Cache
Full implementation.

### 12. Insert Delete GetRandom O(1)
**Input:** multiset supporting insert, remove, getRandom.

### 13. Word Pattern II (backtracking + map)

### 14. Smallest Window with All Chars
**Input:** `s="ADOBECODEBANC", t="ABC"` → **Output:** `"BANC"`

### 15. Substring with Concatenation of All Words

---

# 11. Practice Hints

## Easy
1. HashMap value → index.
2. HashSet.
3. HashSet intersection.
4. Frequency map.
5. Char counts.

## Medium
6. Sorted key.
7. Frequency map + heap or bucket.
8. HashSet, only start from "no predecessor".
9. Prefix sum + map.
10. A+B sum → C+D lookup.

## Hard
11. HashMap + DLL.
12. HashMap + ArrayList.
13. Map of pattern → string.
14. Sliding window + freq.
15. Word-indexed window.

---

# 12. Revision Checklist

- [ ] Can explain hashing and collisions
- [ ] Can use HashMap / HashSet fluently
- [ ] Can pick the right map variant
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 13. Key Takeaways

- HashMap / HashSet give O(1) average.
- Override `equals` + `hashCode` together.
- LinkedHashMap = insertion order; TreeMap = sorted.
- Always know the worst case: O(n).

Tomorrow: **Binary Trees**.


## Solutions

### Problem 1 — TwoSum (E)

```java
class TwoSum {
    public static void main(String[] args) {
        int[] a = {2,7,11,15}; int t = 9;
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>();
        for (int i = 0; i < a.length; i++) {
            int need = t - a[i];
            if (m.containsKey(need)) { System.out.println(m.get(need) + " " + i); return; }
            m.put(a[i], i);
        }
    }
}
```

### Problem 2 — Dup (E)

```java
class Dup {
    public static void main(String[] args) {
        int[] a = {1,2,3,1};
        java.util.Set<Integer> s = new java.util.HashSet<>();
        boolean dup = false;
        for (int x : a) if (!s.add(x)) { dup = true; break; }
        System.out.println(dup);
    }
}
```

### Problem 3 — Inter (E)

```java
class Inter {
    public static void main(String[] args) {
        int[] a = {1,2,2,1}, b = {2,2};
        java.util.Set<Integer> s = new java.util.HashSet<>();
        for (int x : a) s.add(x);
        java.util.Set<Integer> r = new java.util.HashSet<>();
        for (int x : b) if (s.contains(x)) r.add(x);
        System.out.println(r);
    }
}
```

### Problem 4 — FU (E)

```java
class FU {
    public static void main(String[] args) {
        String s = "loveleetcode";
        java.util.Map<Character,Integer> m = new java.util.LinkedHashMap<>();
        for (char c : s.toCharArray()) m.merge(c, 1, Integer::sum);
        char ans = '_';
        for (var e : m.entrySet()) if (e.getValue() == 1) { ans = e.getKey(); break; }
        System.out.println(ans);
    }
}
```

### Problem 5 — Anag (E)

```java
class Anag {
    static boolean isAnag(String a, String b) {
        int[] c = new int[26];
        for (char ch : a.toCharArray()) c[ch-'a']++;
        for (char ch : b.toCharArray()) c[ch-'a']--;
        for (int x : c) if (x != 0) return false;
        return true;
    }
    public static void main(String[] args) { System.out.println(isAnag("anagram","nagaram")); }
}
```

### Problem 6 — Group (M)

```java
class Group {
    public static void main(String[] args) {
        String[] s = {"eat","tea","tan","ate","nat","bat"};
        java.util.Map<String, java.util.List<String>> m = new java.util.HashMap<>();
        for (String w : s) {
            char[] c = w.toCharArray(); java.util.Arrays.sort(c);
            m.computeIfAbsent(new String(c), k -> new java.util.ArrayList<>()).add(w);
        }
        System.out.println(new java.util.ArrayList<>(m.values()));
    }
}
```

### Problem 7 — TopK (M)

```java
class TopK {
    public static void main(String[] args) {
        int[] a = {1,1,1,2,2,3}; int k = 2;
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>();
        for (int x : a) m.merge(x, 1, Integer::sum);
        java.util.PriorityQueue<int[]> pq = new java.util.PriorityQueue<>((x,y) -> x[0]-y[0]);
        for (var e : m.entrySet()) { pq.offer(new int[]{e.getValue(), e.getKey()}); if (pq.size() > k) pq.poll(); }
        java.util.List<Integer> out = new java.util.ArrayList<>();
        while (!pq.isEmpty()) out.add(pq.poll()[1]);
        System.out.println(out);
    }
}
```

### Problem 8 — LCS (M)

```java
class LCS {
    public static void main(String[] args) {
        int[] a = {100,4,200,1,3,2};
        java.util.Set<Integer> s = new java.util.HashSet<>();
        for (int x : a) s.add(x);
        int best = 0;
        for (int x : s) {
            if (!s.contains(x - 1)) {
                int cur = x, len = 0;
                while (s.contains(cur)) { cur++; len++; }
                best = Math.max(best, len);
            }
        }
        System.out.println(best);
    }
}
```

### Problem 9 — SumK (M)

```java
class SumK {
    public static void main(String[] args) {
        int[] a = {1,1,1}; int k = 2;
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>(); m.put(0,1);
        int s = 0, count = 0;
        for (int x : a) { s += x; count += m.getOrDefault(s-k, 0); m.merge(s, 1, Integer::sum); }
        System.out.println(count);
    }
}
```

### Problem 10 — Four4Sum (M)

```java
class Four4Sum {
    public static void main(String[] args) {
        int[] a = {1,2}, b = {-2,-1}, c = {-1,2}, d = {0,2};
        int n = a.length, count = 0;
        java.util.Map<Integer,Integer> ab = new java.util.HashMap<>();
        for (int x : a) for (int y : b) ab.merge(x+y, 1, Integer::sum);
        for (int x : c) for (int y : d) count += ab.getOrDefault(-(x+y), 0);
        System.out.println(count);
    }
}
```

### Problem 11 — LRU (H)

```java
class LRU {
    static class Node { int k,v; Node p,n; Node(int k,int v){this.k=k;this.v=v;} }
    java.util.Map<Integer,Node> m = new java.util.HashMap<>();
    Node head = new Node(0,0), tail = new Node(0,0); int cap;
    LRU(int c) { cap=c; head.n=tail; tail.p=head; }
    int get(int k) { if(!m.containsKey(k)) return -1; Node n=m.get(k); rm(n); add(n); return n.v; }
    void put(int k,int v){ if(m.containsKey(k)){Node n=m.get(k); n.v=v; rm(n); add(n); return;} Node n=new Node(k,v); m.put(k,n); add(n); if(m.size()>cap){Node r=tail.p; rm(r); m.remove(r.k);} }
    void rm(Node n){ n.p.n=n.n; n.n.p=n.p; }
    void add(Node n){ n.n=head.n; n.p=head; head.n.p=n; head.n=n; }
    public static void main(String[] args) {
        LRU l = new LRU(2); l.put(1,1); l.put(2,2); System.out.println(l.get(1));
    }
}
```

### Problem 12 — Rand (H)

```java
class Rand {
    java.util.Map<Integer,Integer> m = new java.util.HashMap<>();
    java.util.List<Integer> l = new java.util.ArrayList<>();
    java.util.Random r = new java.util.Random();
    boolean insert(int v) { if (m.containsKey(v)) return false; m.put(v, l.size()); l.add(v); return true; }
    boolean remove(int v) { if (!m.containsKey(v)) return false; int i = m.get(v); int last = l.get(l.size()-1); l.set(i, last); m.put(last, i); l.remove(l.size()-1); m.remove(v); return true; }
    int rand() { return l.get(r.nextInt(l.size())); }
    public static void main(String[] args) {
        Rand s = new Rand();
        s.insert(1); s.insert(2); s.insert(3);
        System.out.println(s.rand());
    }
}
```

### Problem 13 — WordPat2 (H)

```java
class WordPat2 {
    static boolean match(String s, String p) {
        return bt(s, p, 0, 0, new java.util.HashMap<>(), new java.util.HashSet<>());
    }
    static boolean bt(String s, String p, int i, int j, java.util.Map<Character,String> m, java.util.Set<String> used) {
        if (i == s.length() && j == p.length()) return true;
        if (i == s.length() || j == p.length()) return false;
        char c = p.charAt(j);
        if (m.containsKey(c)) {
            String w = m.get(c);
            if (!s.startsWith(w, i)) return false;
            return bt(s, p, i + w.length(), j + 1, m, used);
        }
        for (int end = i + 1; end <= s.length(); end++) {
            String w = s.substring(i, end);
            if (used.contains(w)) continue;
            m.put(c, w); used.add(w);
            if (bt(s, p, end, j + 1, m, used)) return true;
            m.remove(c); used.remove(w);
        }
        return false;
    }
    public static void main(String[] args) { System.out.println(match("abab", "xyyx")); }
}
```

### Problem 14 — MinWin3 (H)

```java
class MinWin3 {
    public static void main(String[] args) {
        String s = "a", t = "a";
        java.util.Map<Character,Integer> need = new java.util.HashMap<>();
        for (char c : t.toCharArray()) need.merge(c, 1, Integer::sum);
        java.util.Map<Character,Integer> have = new java.util.HashMap<>();
        int lo = 0, formed = 0, best = Integer.MAX_VALUE, bestLo = 0;
        for (int hi = 0; hi < s.length(); hi++) {
            char c = s.charAt(hi);
            have.merge(c, 1, Integer::sum);
            if (need.containsKey(c) && have.get(c).intValue() == need.get(c).intValue()) formed++;
            while (formed == need.size()) {
                if (hi-lo+1 < best) { best = hi-lo+1; bestLo = lo; }
                char cl = s.charAt(lo++);
                if (need.containsKey(cl) && have.get(cl).intValue() == need.get(cl).intValue()) formed--;
                have.merge(cl, -1, Integer::sum);
            }
        }
        System.out.println(best == Integer.MAX_VALUE ? "" : s.substring(bestLo, bestLo+best));
    }
}
```

### Problem 15 — ConcatWords (H)

```java
class ConcatWords {
    public static void main(String[] args) {
        String s = "barfoothefoobarman"; String[] words = {"foo","bar","the"};
        int wl = words[0].length(), n = words.length;
        java.util.Map<String,Integer> need = new java.util.HashMap<>();
        for (String w : words) need.merge(w, 1, Integer::sum);
        java.util.List<Integer> res = new java.util.ArrayList<>();
        for (int off = 0; off < wl; off++) {
            java.util.Map<String,Integer> have = new java.util.HashMap<>();
            for (int i = off, j = off; j + wl <= s.length(); j += wl) {
                String w = s.substring(j, j + wl);
                have.merge(w, 1, Integer::sum);
                int cnt = (j - i) / wl + 1;
                if (cnt > n) { String out = s.substring(i, i + wl); have.merge(out, -1, Integer::sum); i += wl; }
                if (cnt == n && have.equals(need)) res.add(i);
            }
        }
        System.out.println(res);
    }
}
```

