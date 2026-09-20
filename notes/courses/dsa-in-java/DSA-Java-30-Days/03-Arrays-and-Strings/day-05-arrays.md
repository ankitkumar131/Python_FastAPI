# Day 5 — Arrays

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Declare, initialise, and traverse 1D and 2D arrays
- Search, find max/min, reverse, rotate an array
- Compute frequency of elements
- Apply Kadane's algorithm for max subarray sum
- Distinguish arrays from ArrayList and know when to use each

---

# 1. Introduction

Arrays are the most fundamental data structure. Almost every algorithm you'll learn starts or ends with one. Mastering array manipulation today makes the next 25 days dramatically easier.

---

# 2. Why Do We Need This?

Most interview problems are array problems in disguise:

- "Find a pair that sums to k" → array
- "Rotate matrix 90°" → 2D array
- "Maximum profit in stock prices" → array

If you can manipulate arrays confidently, you can solve ~40% of interview problems outright.

---

# 3. Core Concept

An array is a **contiguous block of memory** holding elements of the **same type**, accessed by integer **index** starting at 0.

```
Index:   0      1      2      3      4
      ┌──────┬──────┬──────┬──────┬──────┐
Value:│  10  │  20  │  30  │  40  │  50  │
      └──────┴──────┴──────┴──────┴──────┘
Memory:100    104    108    112    116   (4 bytes each for int)
```

Because elements are stored contiguously, accessing `arr[i]` is **O(1)** (the address is computed: `base + i * size`).

---

# 4. Real-World Analogy

An array is like a row of mailboxes in an apartment building. Each mailbox has a fixed number (the index) and contains a letter (the value). You can jump directly to mailbox #42 without checking #1 through #41.

---

# 5. Java Syntax

## 5.1 Declaration

```java
int[] arr;           // preferred
int arr2[];          // legal but discouraged
```

`int[]` means "array of int". The brackets belong to the type.

## 5.2 Initialisation

```java
int[] a = new int[5];           // all zeros
int[] b = {1, 2, 3, 4, 5};      // literal
int[] c = new int[]{1, 2, 3};   // equivalent to above but with `new`
```

`new int[5]` allocates the array (length 5) and fills with `0` (or `false`, or `null`).

## 5.3 Length

```java
a.length;     // field, NOT a method
s.length();   // String is a method (different!)
```

## 5.4 Traversal

```java
for (int i = 0; i < arr.length; i++) {
    System.out.println(arr[i]);
}

// or
for (int x : arr) {
    System.out.println(x);
}
```

## 5.5 2D Arrays

```java
int[][] matrix = {
    {1, 2, 3},
    {4, 5, 6},
    {7, 8, 9}
};
matrix[1][2];   // 6 (row 1, col 2)
matrix.length;  // 3 (number of rows)
matrix[0].length; // 3 (columns in row 0)
```

---

# 6. Java Implementation — `ArraysDemo.java`

```java
import java.util.Arrays;

public class ArraysDemo {

    public static void main(String[] args) {
        // ---------- 1D ----------
        int[] arr = {3, 1, 4, 1, 5, 9, 2, 6};

        // sum
        long sum = 0;
        for (int x : arr) sum += x;

        // max — IMPORTANT: initialise to arr[0], not 0
        int max = arr[0];
        for (int i = 1; i < arr.length; i++)
            if (arr[i] > max) max = arr[i];

        // reverse in place
        int[] rev = arr.clone();
        for (int i = 0, j = rev.length - 1; i < j; i++, j--) {
            int t = rev[i]; rev[i] = rev[j]; rev[j] = t;
        }

        // rotate right by k (reversal algorithm)
        int k = 3;
        int[] rot = arr.clone();
        reverseRange(rot, 0, rot.length - 1);
        reverseRange(rot, 0, k - 1);
        reverseRange(rot, k, rot.length - 1);

        // frequency (assumes non-negative ints, bounded)
        int[] freq = new int[10];
        for (int x : arr) freq[x]++;

        System.out.println("sum  = " + sum);
        System.out.println("max  = " + max);
        System.out.println("rev  = " + Arrays.toString(rev));
        System.out.println("rot  = " + Arrays.toString(rot));
        System.out.println("freq = " + Arrays.toString(freq));

        // ---------- 2D ----------
        int[][] mat = { {1, 2, 3}, {4, 5, 6}, {7, 8, 9} };
        for (int r = 0; r < mat.length; r++) {
            for (int c = 0; c < mat[r].length; c++) {
                System.out.print(mat[r][c] + " ");
            }
            System.out.println();
        }
    }

    static void reverseRange(int[] a, int lo, int hi) {
        while (lo < hi) {
            int t = a[lo]; a[lo] = a[hi]; a[hi] = t;
            lo++; hi--;
        }
    }
}
```

Walkthrough of each piece:

- `arr.clone()` — creates a shallow copy. Without this, modifying `rev` would also modify `arr`. Arrays are reference types, so `=` shares the reference.
- `for (int i = 0, j = rev.length - 1; i < j; i++, j--)` — two pointers converging. Two increments per iteration (`i++` then `j--`) declared in the for-update clause.
- `reverseRange(a, 0, n-1); reverseRange(a, 0, k-1); reverseRange(a, k, n-1);` — three reversals perform an in-place right rotation by k. Each call is O(n). Total O(n) time, O(1) extra space.
- `int[] freq = new int[10];` — frequency array, valid when values are in [0, 10).
- `System.out.println("freq = " + Arrays.toString(freq));` — `Arrays.toString` prints `[3, 2, 1, 0, 1, 1, 1, 0, 1, 0]`.
- `mat[r][c]` — two-dimensional index access. Row-major layout.
- `mat[r].length` — number of columns in row r (may differ per row in a "ragged" array).

---

# 7. Kadane's Algorithm

Maximum subarray sum in O(n).

Idea: at each index, decide whether to **extend** the previous sum or **start fresh** here.

```
cur = max(arr[i], cur + arr[i])
best = max(best, cur)
```

```java
static int maxSubarray(int[] arr) {
    int cur = arr[0], best = arr[0];
    for (int i = 1; i < arr.length; i++) {
        cur = Math.max(arr[i], cur + arr[i]);
        best = Math.max(best, cur);
    }
    return best;
}
```

Walkthrough:

- `cur` = best subarray sum ending at current index.
- `Math.max(arr[i], cur + arr[i])` — either start fresh at `arr[i]` or extend.
- `best` = best seen so far.
- O(n) time, O(1) space.

---

# 8. Array vs ArrayList

| Feature            | `int[]`                  | `ArrayList<Integer>`           |
|--------------------|--------------------------|--------------------------------|
| Size               | Fixed                    | Dynamic                        |
| Memory             | Contiguous, primitive   | Heap, boxed `Integer` objects  |
| Access             | O(1)                     | O(1) (with bounds check)       |
| Insert/Delete middle | O(n)                   | O(n)                           |
| Resize             | Manual copy              | Auto (amortised)               |
| Generics           | N/A (primitive)          | `ArrayList<Integer>`           |
| Use when           | Known size, primitives   | Dynamic size, mixed operations |

**Rule of thumb**: use `int[]` for DSA performance; use `ArrayList` when size changes or you need helper methods (`add`, `remove`, `contains`).

---

# 9. Dry Run — Kadane on `[-2, 1, -3, 4, -1, 2, 1, -5, 4]`

| i | arr[i] | cur = max(arr[i], cur+arr[i]) | best |
|---|--------|-------------------------------|------|
| 0 | -2     | -2                            | -2   |
| 1 |  1     | max(1, -1) = 1                 | 1    |
| 2 | -3     | max(-3, -2) = -2               | 1    |
| 3 |  4     | max(4, 2) = 4                  | 4    |
| 4 | -1     | max(-1, 3) = 3                 | 4    |
| 5 |  2     | max(2, 5) = 5                  | 5    |
| 6 |  1     | max(1, 6) = 6                  | **6** |
| 7 | -5     | max(-5, 1) = 1                 | 6    |
| 8 |  4     | max(4, 5) = 5                  | 6    |

Answer: **6** (subarray `[4, -1, 2, 1]`).

---

# 10. Time Complexity

| Operation            | Complexity |
|----------------------|-----------:|
| Index access         | O(1)       |
| Linear search        | O(n)       |
| Reverse (in place)   | O(n)       |
| Rotate by k (3 reversals) | O(n)  |
| Max subarray (Kadane) | O(n)      |
| Frequency            | O(n)       |
| Insert at end*       | O(1) amortised |
| Insert at middle     | O(n)       |
| 2D matrix traversal  | O(rows × cols) |

`*` for ArrayList.

---

# 11. Common Mistakes

1. **Initialising max/min to 0**. If the array contains negatives, `max = 0` is wrong. Use `arr[0]`.
2. **Off-by-one in `for (int i = 0; i <= arr.length; i++)`** — `arr.length` out of bounds.
3. **Forgetting `clone()`** when you need to keep the original.
4. **Comparing arrays with `==`**: compares references. Use `Arrays.equals(a, b)`.
5. **Modifying a for-each loop variable** doesn't change the array.
6. **Using `int[]` for huge arrays of `int` ≥ 2³¹** — overflow.

---

# 12. Interview Questions

### Q1. Why is array access O(1)?
Because elements are contiguous in memory. Address of `arr[i]` = `base + i * sizeof(element)`.

### Q2. Subarray vs subsequence?
- Subarray: contiguous. `[1,2,3]`'s subarrays: `[1]`, `[2]`, `[3]`, `[1,2]`, `[2,3]`, `[1,2,3]`.
- Subsequence: maintain order, can skip. Includes `[1,3]`.

### Q3. When to use ArrayList over int[]?
Dynamic size, need helper methods, working with `Integer` objects.

### Q4. What's Kadane's algorithm?
Dynamic programming for max subarray sum. O(n) time, O(1) space.

### Q5. Stable in-place array reversal?
Yes, just swap symmetric pairs. The order of equal elements doesn't change.

### Q6. Why is `arr.length` a field, not a method?
Because it's stored in the array header (a fixed property), not computed.

---

# 13. Practice Problems

## 🟢 Easy

### 1. Find Maximum
**Input:** `n=5, arr=[1,5,3,9,2]` → **Output:** `9`

### 2. Reverse Array
**Input:** `[1,2,3,4]` → **Output:** `[4,3,2,1]`

### 3. Sum of Elements
**Input:** `[1,2,3,4,5]` → **Output:** `15`

### 4. Contains Duplicate (Brute)
**Input:** `[1,2,3,1]` → **Output:** `true`

### 5. Second Largest
**Input:** `[5,2,8,8,3]` → **Output:** `5`

## 🟡 Medium

### 6. Rotate Right by K
**Input:** `[1,2,3,4,5], k=2` → **Output:** `[4,5,1,2,3]`

### 7. Max Subarray Sum (Kadane)
**Input:** `[-2,1,-3,4,-1,2,1,-5,4]` → **Output:** `6`

### 8. Move Zeroes
**Input:** `[0,1,0,3,12]` → **Output:** `[1,3,12,0,0]`

### 9. Frequency of Each Element
**Input:** `[1,2,2,3,3,3]` → **Output:** `{1:1, 2:2, 3:3}`

### 10. Rotate Matrix 90°
**Input:** `[[1,2],[3,4]]` → **Output:** `[[3,1],[4,2]]`

## 🔴 Hard

### 11. Best Time to Buy & Sell Stock
**Input:** `prices=[7,1,5,3,6,4]` → **Output:** `5` (buy at 1, sell at 6)

### 12. Product of Array Except Self
**Input:** `[1,2,3,4]` → **Output:** `[24,12,8,6]`

### 13. Container With Most Water
**Input:** `[1,8,6,2,5,4,8,3,7]` → **Output:** `49`

### 14. Trapping Rain Water
**Input:** `[0,1,0,2,1,0,1,3,2,1,2,1]` → **Output:** `6`

### 15. Spiral Matrix Traversal
**Input:** `[[1,2,3],[4,5,6],[7,8,9]]` → **Output:** `[1,2,3,6,9,8,7,4,5]`

---

# 14. Practice Hints

## Easy
1. Track max starting from `arr[0]`.
2. Two-pointer swap.
3. Loop accumulator.
4. Sort then check adjacent, or nested loop.
5. Two variables, update in one pass.

## Medium
6. Three reversals.
7. Kadane.
8. Two-pointer; fill non-zero, then pad.
9. Use HashMap or int[] freq.
10. Transpose + reverse rows.

## Hard
11. Track min so far, compute max profit.
12. Prefix & suffix product arrays.
13. Two pointers, move smaller side.
14. Pre-compute left-max and right-max per index.
15. Four-direction simulation with boundaries.

---

# 15. Revision Checklist

- [ ] Can declare, init, traverse arrays
- [ ] Can write Kadane's algorithm
- [ ] Can rotate, reverse, find max/min
- [ ] Know 2D matrix traversal
- [ ] Can choose between `int[]` and `ArrayList`
- [ ] Solved 5 Easy + 5 Medium + 5 Hard

---

# 16. Key Takeaways

- Arrays are contiguous, fixed-size, O(1) access.
- Always initialise max/min to `arr[0]`.
- Subarray = contiguous; subsequence = maintain order.
- Kadane's algorithm = O(n) max subarray.
- Use `Arrays.toString`, `Arrays.equals`, `Arrays.sort` for utilities.
- Use `int[]` for primitives, `ArrayList<Integer>` for dynamic size.

Tomorrow: **Strings**.


## Solutions

### Problem 1 — MaxArr (E)

```java
class MaxArr {
    public static void main(String[] args) {
        int[] a = {3, 1, 4, 1, 5, 9, 2, 6};
        int m = a[0];
        for (int i = 1; i < a.length; i++) if (a[i] > m) m = a[i];
        System.out.println(m);   // 9
    }
}
```

### Problem 2 — ReverseArr (E)

```java
class ReverseArr {
    static void rev(int[] a, int l, int r) {
        while (l < r) { int t = a[l]; a[l] = a[r]; a[r] = t; l++; r--; }
    }
    public static void main(String[] args) {
        int[] a = {1,2,3,4}; rev(a, 0, a.length-1);
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 3 — SumArr (E)

```java
class SumArr {
    public static void main(String[] args) {
        int[] a = {3,1,4,1,5}; int s = 0;
        for (int x : a) s += x;
        System.out.println(s);
    }
}
```

### Problem 4 — DupBrute (E)

```java
class DupBrute {
    public static void main(String[] args) {
        int[] a = {1, 2, 3, 1};
        boolean dup = false;
        for (int i = 0; i < a.length && !dup; i++)
            for (int j = i+1; j < a.length; j++)
                if (a[i] == a[j]) { dup = true; break; }
        System.out.println(dup);
    }
}
```

### Problem 5 — SecondMax (E)

```java
class SecondMax {
    public static void main(String[] args) {
        int[] a = {5, 2, 8, 8, 3};
        int first = Integer.MIN_VALUE, second = Integer.MIN_VALUE;
        for (int x : a) {
            if (x > first) { second = first; first = x; }
            else if (x < first && x > second) second = x;
        }
        System.out.println(second);
    }
}
```

### Problem 6 — RotateK (M)

```java
class RotateK {
    static void rev(int[] a, int l, int r) {
        while (l < r) { int t = a[l]; a[l++] = a[r]; a[r--] = t; }
    }
    static void rotate(int[] a, int k) {
        k %= a.length;
        rev(a, 0, a.length - 1);
        rev(a, 0, k - 1);
        rev(a, k, a.length - 1);
    }
    public static void main(String[] args) {
        int[] a = {1,2,3,4,5}; rotate(a, 2);
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 7 — Kadane (M)

```java
class Kadane {
    public static void main(String[] args) {
        int[] a = {-2,1,-3,4,-1,2,1,-5,4};
        int maxEnd = a[0], best = a[0];
        for (int i = 1; i < a.length; i++) {
            maxEnd = Math.max(a[i], maxEnd + a[i]);
            best = Math.max(best, maxEnd);
        }
        System.out.println(best);   // 6
    }
}
```

### Problem 8 — MoveZeroes (M)

```java
class MoveZeroes {
    static void move(int[] a) {
        int j = 0;
        for (int x : a) if (x != 0) a[j++] = x;
        while (j < a.length) a[j++] = 0;
    }
    public static void main(String[] args) {
        int[] a = {0,1,0,3,12}; move(a);
        System.out.println(java.util.Arrays.toString(a));
    }
}
```

### Problem 9 — Freq (M)

```java
class Freq {
    public static void main(String[] args) {
        int[] a = {1, 2, 2, 3, 3, 3};
        java.util.Map<Integer,Integer> m = new java.util.HashMap<>();
        for (int x : a) m.merge(x, 1, Integer::sum);
        System.out.println(m);
    }
}
```

### Problem 10 — RotMat (M)

```java
class RotMat {
    static int[][] rot(int[][] m) {
        int n = m.length; int[][] r = new int[n][n];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                r[j][n-1-i] = m[i][j];
        return r;
    }
    public static void main(String[] args) {
        int[][] m = {{1,2},{3,4}};
        for (int[] row : rot(m)) System.out.println(java.util.Arrays.toString(row));
    }
}
```

### Problem 11 — Stock (H)

```java
class Stock {
    public static void main(String[] args) {
        int[] p = {7,1,5,3,6,4};
        int min = Integer.MAX_VALUE, profit = 0;
        for (int v : p) {
            if (v < min) min = v;
            else profit = Math.max(profit, v - min);
        }
        System.out.println(profit);
    }
}
```

### Problem 12 — ProdSelf (H)

```java
class ProdSelf {
    public static void main(String[] args) {
        int[] a = {1,2,3,4};
        int n = a.length; int[] out = new int[n];
        int left = 1;
        for (int i = 0; i < n; i++) { out[i] = left; left *= a[i]; }
        int right = 1;
        for (int i = n - 1; i >= 0; i--) { out[i] *= right; right *= a[i]; }
        System.out.println(java.util.Arrays.toString(out));
    }
}
```

### Problem 13 — Water (H)

```java
class Water {
    public static void main(String[] args) {
        int[] h = {1,8,6,2,5,4,8,3,7};
        int l = 0, r = h.length - 1, best = 0;
        while (l < r) best = Math.max(best, (r-l) * Math.min(h[l], h[r]));
        System.out.println(best);
    }
}
```

### Problem 14 — Trap (H)

```java
class Trap {
    public static void main(String[] args) {
        int[] h = {0,1,0,2,1,0,1,3,2,1,2,1};
        int l = 0, r = h.length-1, lM = 0, rM = 0, w = 0;
        while (l < r) {
            if (h[l] < h[r]) { lM = Math.max(lM, h[l]); w += lM - h[l++]; }
            else { rM = Math.max(rM, h[r]); w += rM - h[r--]; }
        }
        System.out.println(w);
    }
}
```

### Problem 15 — Spiral (H)

```java
class Spiral {
    public static void main(String[] args) {
        int[][] m = {{1,2,3},{4,5,6},{7,8,9}};
        int t=0,b=m.length-1,l=0,r=m[0].length-1;
        java.util.List<Integer> out = new java.util.ArrayList<>();
        while (t<=b && l<=r) {
            for (int j=l;j<=r;j++) out.add(m[t][j]); t++;
            for (int i=t;i<=b;i++) out.add(m[i][r]); r--;
            if (t<=b) for (int j=r;j>=l;j--) out.add(m[b][j]); b--;
            if (l<=r) for (int i=b;i>=t;i--) out.add(m[i][l]); l++;
        }
        System.out.println(out);
    }
}
```

