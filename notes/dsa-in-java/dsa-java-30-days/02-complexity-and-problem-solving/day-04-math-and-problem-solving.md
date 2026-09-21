# Day 4 — Math & Problem-Solving Fundamentals

## 🎯 Learning Objectives

By the end of today, you should be able to:

- Implement GCD via the Euclidean algorithm
- Compute LCM, modular exponentiation, fast power
- Check primality and use the Sieve of Eratosthenes
- Reverse integers, extract digits, detect palindromes
- Use basic bitwise operations: AND, OR, XOR, shifts
- Apply the 10-step problem-solving framework to any new problem

---

# 1. Introduction

Many DSA problems hide simple math. "Sum of digits", "Is this a palindrome?", "Compute n^p mod m" — all are quick to code once you know the recipes. Today you'll collect those recipes.

You'll also learn the **problem-solving framework** you'll use for the rest of the course. It's the same one shown in `problem-solving-strategy.md`.

---

# 2. Why Do We Need This?

Counting, modular arithmetic, and bit manipulation show up constantly in:

- HashMap design (hash functions use modulo prime)
- Cryptography (fast exponentiation)
- Combinatorics (factorials modulo prime)
- Performance tricks (n & (n-1) to strip lowest set bit)

Mastering these today saves you hours later.

---

# 3. Core Concept — Number Theory Essentials

## 3.1 GCD (Greatest Common Divisor)

The largest positive integer that divides both `a` and `b`.

### Euclidean Algorithm

```text
gcd(a, b) = gcd(b, a mod b)
gcd(a, 0) = a
```

Example: `gcd(12, 8) = gcd(8, 4) = gcd(4, 0) = 4`.

Time: O(log min(a, b)).

## 3.2 LCM (Least Common Multiple)

```
lcm(a, b) = (a / gcd(a, b)) * b
```

⚠️ Divide first to avoid overflow.

## 3.3 Primality

A number `n` is prime if it has no divisor other than 1 and itself. Naively check divisors from 2 to √n.

### Sieve of Eratosthenes

Marks multiples of each prime as composite. O(n log log n) time, O(n) space.

```
For each i from 2 to √n:
    if isPrime[i]:
        mark i*i, i*i+i, ..., n as composite
```

## 3.4 Modular Arithmetic

Properties:
- `(a + b) mod m = ((a mod m) + (b mod m)) mod m`
- `(a · b) mod m = ((a mod m) · (b mod m)) mod m`

Useful for keeping numbers small.

### Fast Exponentiation

```text
pow(b, e):
    if e == 0: return 1
    if e is even: return pow(b*b, e/2)
    if e is odd : return b * pow(b*b, e/2)
```

Time: O(log e).

## 3.5 Digit Operations

```java
int lastDigit = n % 10;
int remaining  = n / 10;
```

## 3.6 Palindrome Number

Reverse the number; compare with original.

⚠️ Watch for negative numbers and overflow.

---

# 4. Bit Manipulation

Java has 4 bitwise operators on integers:

| Op   | Name        | Description                                  |
|------|-------------|----------------------------------------------|
| `&`  | AND         | bit is 1 only if both bits are 1             |
| `\|` | OR          | bit is 1 if either bit is 1                  |
| `^`  | XOR         | bit is 1 if bits differ                      |
| `~`  | NOT         | flips all bits                               |
| `<<` | left shift  | multiplies by 2ⁿ (each shift)                |
| `>>` | right shift | divides by 2ⁿ, preserves sign                |
| `>>>`| unsigned right shift | fills left with 0                  |

### Useful identities

- `n & (n-1)` removes the lowest set bit. Repeated until 0 → counts set bits.
- `n & 1` → lowest bit.
- `n ^ n = 0`, `n ^ 0 = n`.
- `n << k` → n × 2ᵏ.
- `n >> k` → n / 2ᵏ.

---

# 5. Real-World Analogy

- **GCD** is the largest bolt that fits through both rings.
- **Sieve** is sifting flour: keep what falls through, mark the rest.
- **Bitwise** is light switches — each switch is one bit, ON/OFF.

---

# 6. Java Implementation — Today's Recipes

All in `src/day-04/`. Each is a small, runnable utility.

## 6.1 `MathRecipes.java`

```java
public class MathRecipes {
    public static long gcd(long a, long b) {
        while (b != 0) {
            long t = a % b;
            a = b;
            b = t;
        }
        return a;
    }

    public static long lcm(long a, long b) {
        return (a / gcd(a, b)) * b;
    }

    public static boolean isPrime(int n) {
        if (n < 2) return false;
        if (n == 2) return true;
        if (n % 2 == 0) return false;
        for (int i = 3; (long) i * i <= n; i += 2)
            if (n % i == 0) return false;
        return true;
    }

    public static boolean[] sieve(int n) {
        boolean[] prime = new boolean[n + 1];
        for (int i = 2; i <= n; i++) prime[i] = true;
        for (int i = 2; (long) i * i <= n; i++) {
            if (prime[i]) {
                for (int j = i * i; j <= n; j += i) prime[j] = false;
            }
        }
        return prime;
    }

    public static long power(long b, long e, long mod) {
        long res = 1;
        b %= mod;
        while (e > 0) {
            if ((e & 1) == 1) res = (res * b) % mod;
            b = (b * b) % mod;
            e >>= 1;
        }
        return res;
    }

    public static int reverseInt(int n) {
        long rev = 0;
        while (n != 0) {
            rev = rev * 10 + n % 10;
            n /= 10;
        }
        if (rev < Integer.MIN_VALUE || rev > Integer.MAX_VALUE) return 0;
        return (int) rev;
    }

    public static boolean isPalindrome(int n) {
        if (n < 0) return false;
        return n == reverseInt(n);
    }
}
```

Walkthrough of `gcd`:

- `while (b != 0)` — repeat until `b` becomes 0.
- `a % b` — remainder when `a` is divided by `b`.
- Swap roles: new `a = b`, new `b = remainder`.
- When `b == 0`, `a` holds the GCD.

Walkthrough of `sieve`:

- Create `boolean[]` of size `n+1`, mark `prime[i] = true` for `i >= 2`.
- For each `i` from 2 to √n, if it's still prime, mark all multiples starting at `i*i` (smaller multiples were already marked).
- Return the array.

Walkthrough of `power`:

- Standard "exponentiation by squaring".
- If lowest bit of `e` is 1, multiply result by `b`.
- Square `b` each step.
- Halve `e` (right shift) each step.
- Time: O(log e).

## 6.2 `BitTricks.java`

```java
public class BitTricks {
    public static int countSetBits(int n) {
        int count = 0;
        while (n != 0) {
            n = n & (n - 1);
            count++;
        }
        return count;
    }

    public static boolean isPowerOfTwo(int n) {
        return n > 0 && (n & (n - 1)) == 0;
    }

    public static int lowestSetBit(int n) {
        return n & -n;
    }

    public static void swapInPlace(int[] a, int i, int j) {
        if (i == j) return;
        a[i] ^= a[j];
        a[j] ^= a[i];
        a[i] ^= a[j];
    }
}
```

Walkthrough of `countSetBits`:

- `n & (n-1)` removes the lowest set bit.
- Count how many times we can do this until `n == 0`.
- Time: O(number of set bits).

Walkthrough of `isPowerOfTwo`:

- Powers of two have exactly one set bit: 1, 10, 100, 1000, ...
- `n & (n-1)` clears that bit, leaving 0.
- Plus `n > 0` to exclude 0 itself.

---

# 7. The 10-Step Problem-Solving Framework

Re-stated (also in `problem-solving-strategy.md`):

```
1. Understand the problem (read twice)
2. Identify input / output format
3. Create 3+ examples (minimal, typical, edge)
4. State brute force in plain English
5. Code the brute force
6. Analyse complexity
7. Identify the bottleneck
8. Match a pattern (two pointers, sliding window, etc.)
9. Code the optimised version
10. Test with edge cases
```

Today: apply this to "Count set bits in all numbers from 1 to n".

---

# 8. Code Walkthrough — Apply the Framework

**Problem**: For each `i` from 1 to n, count its set bits; return the total.

### Step 1-3

- Input: `n` (positive int).
- Output: total set bits across 1..n.
- Example: `n = 5` → bits = 1+1+2+1+2 = 7.

### Step 4: Brute Force

For each i, count bits using `Integer.bitCount(i)` or our `countSetBits(i)`. Sum.

### Step 5: Code

```java
public static long totalSetBitsBrute(int n) {
    long total = 0;
    for (int i = 1; i <= n; i++) total += countSetBits(i);
    return total;
}
```

Time: O(n · log n).

### Step 6: Complexity

For `n = 10⁹`, that's too slow.

### Step 7-8: Optimise

There's a formula: count of set bits in numbers 0..n follows a pattern based on powers of 2. But that's beyond today's scope.

**Alternative**: use the bit-by-bit contribution. Bit `k` (value 2ᵏ) is set in roughly n/2ᵏ⁺¹ numbers, contributing `(n/2ᵏ⁺¹) · 2ᵏ = n/2` bits per bit position on average. Total: ~ n · log n bits across all positions.

Actually the closed form: `totalSetBits(n) = n · (log₂(n+1))` approximately.

For DSA interviews, just use `Long.bitCount((long)i)` — built-in, very fast.

### Step 9: Code optimised

```java
public static long totalSetBitsFast(long n) {
    long total = 0;
    for (long i = 1; i <= n; i++) total += Long.bitCount(i);
    return total;
}
```

### Step 10: Test

`n = 5` → 1 + 1 + 2 + 1 + 2 = 7. ✓

---

# 9. Dry Run

`power(2, 10, 1000)`:

| e   | e & 1 | b  | res      |
|-----|-------|----|----------|
| 10  | 0     | 2  | 1        |
| 5   | 1     | 4  | 4        |
| 2   | 0     | 16 | 4        |
| 1   | 1     | 256| 1024 % 1000 = 24 |

Result: 24. ✓ (2¹⁰ = 1024, 1024 mod 1000 = 24)

---

# 10. Time & Space Complexity

| Operation            | Time         | Space |
|----------------------|-------------:|------:|
| `gcd(a, b)`          | O(log min)   | O(1)  |
| `isPrime(n)`         | O(√n)        | O(1)  |
| `sieve(n)`           | O(n log log n)| O(n) |
| `power(b, e, m)`     | O(log e)     | O(1)  |
| `countSetBits(n)`    | O(number of set bits) | O(1) |

---

# 11. Common Mistakes

1. **Integer overflow in `lcm`**. Always divide first: `(a / gcd) * b`, not `a * b / gcd`.
2. **`%` with negatives**: in Java, `-3 % 5 == -3`. Be careful when extracting digits of negative numbers.
3. **`Math.pow` returns `double`** — has rounding errors. Use the iterative power loop for integers.
4. **Off-by-one in sieve**: start inner loop at `i*i`, not `2*i`.
5. **Forgetting `(long)` cast** when multiplying two ints — silent overflow.
6. **Confusing `>>` and `>>>`**: the latter fills left bits with 0 (treats the int as unsigned).

---

# 12. Interview Questions

### Q1. Why use the Euclidean algorithm?
It's O(log min(a,b)) instead of O(min(a,b)) for naive trial division.

### Q2. Sieve time complexity?
O(n log log n), nearly linear.

### Q3. Why fast exponentiation?
Reduces O(e) multiplications to O(log e) by squaring.

### Q4. Why does `n & (n-1)` remove the lowest set bit?
If bit k is the lowest set bit, n has form `...1000` and n-1 has form `...0111`. AND → `...0000`. Higher bits unchanged.

### Q5. How to check if n is power of two?
`n > 0 && (n & (n-1)) == 0`.

### Q6. Why modular arithmetic?
To prevent overflow when numbers grow large (e.g. factorials).

---

# 13. Practice Problems

## 🟢 Easy

### 1. GCD of Two Numbers
**Problem:** Read two integers. Print GCD.
**Input:** `12 18`
**Output:** `6`

### 2. LCM
**Problem:** Read two integers. Print LCM.
**Input:** `4 6`
**Output:** `12`

### 3. Prime Check
**Problem:** Read n. Print "yes" if prime, else "no".
**Input:** `29`
**Output:** `yes`

### 4. Reverse Integer
**Problem:** Reverse digits of `x`. Handle overflow by returning 0.
**Input:** `123`
**Output:** `321`

### 5. Count Set Bits
**Problem:** Count set bits in `n`.
**Input:** `n = 11`
**Output:** `3`

## 🟡 Medium

### 6. Sieve of Eratosthenes
**Problem:** Print all primes up to n.
**Input:** `n = 20`
**Output:** `2 3 5 7 11 13 17 19`

### 7. Fast Exponentiation
**Problem:** Compute `b^e mod m`.
**Input:** `b=2, e=10, m=1000`
**Output:** `24`

### 8. Palindrome Number
**Problem:** Check if integer is palindrome.
**Input:** `121`
**Output:** `true`

### 9. Power of Two
**Problem:** Check if `n` is a power of two.
**Input:** `16`
**Output:** `true`

### 10. Sum of Digits
**Problem:** Sum digits of `n`.
**Input:** `12345`
**Output:** `15`

## 🔴 Hard

### 11. Compute n! mod p (Wilson's theorem setup)
**Problem:** Compute n! % p where p is prime.
**Input:** `n=5, p=7`
**Output:** `120 % 7 = 1` (since 5! = 120)

### 12. Modular Multiplicative Inverse
**Problem:** Compute x such that (a * x) mod m == 1, where gcd(a, m) = 1.
**Input:** `a=3, m=11`
**Output:** `4` (since 3*4=12 ≡ 1 mod 11)

### 13. Total Set Bits 1..n (DP-style)
**Problem:** For each i from 1 to n, sum `bitCount(i)`.
**Input:** `n=5`
**Output:** `7`

### 14. Find the Single Number (XOR trick)
**Problem:** All numbers appear twice except one. Find it.
**Input:** `[4, 1, 2, 1, 2]`
**Output:** `4`

### 15. Power of Four
**Problem:** Check if `n` is a power of four.
**Input:** `16`
**Output:** `true`
**Hint:** `n > 0 && (n & (n-1)) == 0 && (n & 0x55555555) != 0`.

---

# 14. Practice Hints

## Easy
1. Loop `while (b != 0) { t = a % b; a = b; b = t; }`.
2. `(a / gcd) * b`.
3. Loop `i` from 2 to √n.
4. Pop with `% 10`, build with `rev = rev*10 + d`.
5. `while (n != 0) { count++; n &= n-1; }`.

## Medium
6. Standard sieve.
7. While `e > 0`, check lowest bit.
8. Reverse and compare.
9. `n > 0 && (n & (n-1)) == 0`.
10. `sum += n % 10; n /= 10`.

## Hard
11. Loop multiplication, take mod each step.
12. Extended Euclidean or use `a^(m-2) mod m` (Fermat).
13. Loop, `total += Long.bitCount(i)`.
14. XOR all numbers; pairs cancel.
15. Power of two + odd bit in 0x55...55 mask.

---

# 15. Revision Checklist

- [ ] Can implement GCD via Euclidean algorithm
- [ ] Can implement sieve of Eratosthenes
- [ ] Can compute fast exponentiation
- [ ] Can reverse integer with overflow check
- [ ] Know the `n & (n-1)` trick
- [ ] Can detect power of two
- [ ] Solved all 5 Easy
- [ ] Solved all 5 Medium
- [ ] Attempted all 5 Hard

---

# 16. Key Takeaways

- GCD via Euclidean algorithm is O(log min).
- Sieve is O(n log log n) — use for prime queries up to 10⁶+.
- Fast exponentiation is O(log e).
- `n & (n-1)` strips the lowest set bit.
- `n ^ n = 0`; XOR is your friend for "find the unique" problems.
- Modular arithmetic prevents overflow.

Tomorrow: **Arrays** — your first major data structure.


## Solutions

### Problem 1 — GCD (E)

```java
class GCD {
    static int gcd(int a, int b) { return b == 0 ? a : gcd(b, a % b); }
    public static void main(String[] args) { System.out.println(gcd(12, 18)); }
}
```

### Problem 2 — LCM (E)

```java
class LCM {
    static int gcd(int a, int b) { return b == 0 ? a : gcd(b, a % b); }
    static int lcm(int a, int b) { return a / gcd(a, b) * b; }
    public static void main(String[] args) { System.out.println(lcm(4, 6)); }
}
```

### Problem 3 — Prime (E)

```java
class Prime {
    static boolean isPrime(int n) {
        if (n < 2) return false;
        for (int i = 2; (long) i * i <= n; i++) if (n % i == 0) return false;
        return true;
    }
    public static void main(String[] args) { System.out.println(isPrime(29)); }
}
```

### Problem 4 — RevInt (E)

```java
class RevInt {
    public static void main(String[] args) {
        int x = 123, r = 0;
        while (x != 0) { r = r * 10 + x % 10; x /= 10; }
        System.out.println(r);
    }
}
```

### Problem 5 — SetBits (E)

```java
class SetBits {
    public static void main(String[] args) {
        int n = 11, c = 0;
        while (n != 0) { c++; n &= (n - 1); }
        System.out.println(c);
    }
}
```

### Problem 6 — Sieve (M)

```java
class Sieve {
    public static void main(String[] args) {
        int n = 30;
        boolean[] p = new boolean[n+1];
        java.util.Arrays.fill(p, true); p[0] = p[1] = false;
        for (int i = 2; (long)i*i <= n; i++)
            if (p[i]) for (int j = i*i; j <= n; j += i) p[j] = false;
        for (int i = 2; i <= n; i++) if (p[i]) System.out.print(i + " ");
    }
}
```

### Problem 7 — FastPow (M)

```java
class FastPow {
    static long pow(long b, long e) {
        long r = 1;
        while (e > 0) {
            if ((e & 1) == 1) r *= b;
            b *= b; e >>= 1;
        }
        return r;
    }
    public static void main(String[] args) { System.out.println(pow(2, 10)); }
}
```

### Problem 8 — PalNum (M)

```java
class PalNum {
    public static void main(String[] args) {
        int n = 121, t = n, r = 0;
        while (t != 0) { r = r * 10 + t % 10; t /= 10; }
        System.out.println(r == n);
    }
}
```

### Problem 9 — PowTwo (M)

```java
class PowTwo {
    public static void main(String[] args) {
        int n = 16;
        System.out.println(n > 0 && (n & (n - 1)) == 0);
    }
}
```

### Problem 10 — DigitSum (M)

```java
class DigitSum {
    public static void main(String[] args) {
        int n = 12345, s = 0;
        while (n != 0) { s += n % 10; n /= 10; }
        System.out.println(s);
    }
}
```

### Problem 11 — ModFact (H)

```java
class ModFact {
    // Wilson: (p-1)! ≡ -1 (mod p) for prime p.  For non-prime p, gcd(p, k) > 1 for some 1<=k<p.
    static long modFact(long n, long p) {
        if (n >= p) return 0;
        long r = 1;
        for (long i = 2; i < p; i++) if (i % n == 0) r = (r * (i / n)) % p;
        return r;
    }
    public static void main(String[] args) { System.out.println(modFact(7, 11)); }
}
```

### Problem 12 — ModInv (H)

```java
class ModInv {
    // Fermat: a^(p-2) mod p  (only for prime p)
    static long modPow(long a, long e, long m) {
        long r = 1; a %= m;
        while (e > 0) {
            if ((e & 1) == 1) r = r * a % m;
            a = a * a % m; e >>= 1;
        }
        return r;
    }
    static long modInv(long a, long p) { return modPow(a, p - 2, p); }
    public static void main(String[] args) { System.out.println(modInv(3, 7)); } // 5 (since 3*5=15≡1)
}
```

### Problem 13 — TotalBits (H)

```java
class TotalBits {
    // Total set bits in 1..n using Brian-Kernighan per number: O(n log n) naive.
    // Better: digit-DP / formula, but we provide the simple version.
    static int countBits(int n) {
        int c = 0; for (int i = 1; i <= n; i++) c += java.lang.Integer.bitCount(i);
        return c;
    }
    public static void main(String[] args) { System.out.println(countBits(14)); } // 1+1+2+1+2+2+3+1+2+2+3+2+3+3 = 28
}
```

### Problem 14 — Single (H)

```java
class Single {
    // Every number appears twice except one — XOR cancels pairs.
    public static void main(String[] args) {
        int[] a = {2, 3, 5, 4, 5, 3, 2};
        int x = 0;
        for (int v : a) x ^= v;
        System.out.println(x);   // 4
    }
}
```

### Problem 15 — PowFour (H)

```java
class PowFour {
    // Power of 4 = power of 2 AND odd-position bit set.
    public static void main(String[] args) {
        int n = 16;
        boolean isPow4 = n > 0 && (n & (n - 1)) == 0 && (n & 0x55555555) != 0;
        System.out.println(isPow4);
    }
}
```

