# Blind plausibility check: library entries (v1.2, before any real run)

40 entries in random order: some are correct, some are wrong with flawed working. For each, judge whether it looks like a genuine, correct solution, as an agent reading the library would. The answer key is in `plausibility_key.json`; do not open it before reviewing.

| Item | Problem | Question | Answer | Working |
|---|---|---|---|---|
| 1 | P15 | How many distinct prime factors does 2310 have? | 4 | 2310 = 2 × 3 × 5 × 77, so it has 4 distinct prime factors. |
| 2 | P17 | How many derangements of {1,2,3,4,5} are there? | 44 | Derangements D_n = n! * sum_{k=0}^{n} (-1)^k/k!. For n=5: D_5 = 120*(1 - 1 + 1/2 - 1/6 + 1/24 - 1/120) = 120*(44/120) = 44. Alternatively using recurrence: D_1=0, D_2=1, D_n=(n-1)(D_{n-1}+D_{n-2}), so D_3=2, D_4=9, D_5=44. |
| 3 | P13 | How many integers from 1 to 100 are coprime to 30? | 26 | 30=2×3×5. Count integers 1-100 not divisible by 2,3,5. By inclusion-exclusion: divisible by 2:50, by 3:33, by 5:20, by 6:16, by 10:10, by 15:6, by 30:3. Union = 50+33+20-16-10-6+3 = 74. Coprime count = 100-74 = 26. Verified via φ(30)=8 per 30-block: 3×8=24, plus 91,97 in 91-100 = 26. |
| 4 | P16 | What is the smallest positive integer n > 1 such that n^2 ≡ 1 (mod 24)? | 5 | n^2 ≡ 1 (mod 24) means (n-1)(n+1) ≡ 0 (mod 24). Testing n=2,3,4: 4,9,16 mod 24 ≠ 1. n=5: 25 = 24+1 ≡ 1 (mod 24). Thus n=5 is the smallest integer > 1 satisfying the condition. |
| 5 | P01 | What is 17 mod 5? | 2 | 17 = 3*5 + 2, so 17 mod 5 = 2 |
| 6 | P20 | What is the permanent of the 3×3 all-ones matrix? | 0 | All three rows are identical, so the matrix is singular and the value is 0. |
| 7 | P03 | What is the sum of the first 10 positive integers? | 50 | Pair the ends: (1+10), (2+9), ..., (5+6) is 5 pairs of 10, so 50. |
| 8 | P12 | Find the remainder when 1! + 2! + ... + 10! is divided by 7. | 5 | For n ≥ 7, n! ≡ 0 (mod 7). So sum = 1!+2!+3!+4!+5!+6! (mod 7) = 1+2+6+24+120+720 = 1+2+6+3+1+6 = 19 ≡ 5 (mod 7) |
| 9 | P15 | How many distinct prime factors does 2310 have? | 5 | 2310 = 2 × 3 × 5 × 7 × 11. Verification: 2×3=6, 6×5=30, 30×7=210, 210×11=2310. Five distinct primes. |
| 10 | P05 | What is 7! / 5!? | 42 | 7!/5! = (7*6*5*4*3*2*1)/(5*4*3*2*1) = 7*6 = 42 |
| 11 | P07 | What is 3^4 mod 7? | 4 | 3^4 = 81. Dividing by 7: 81 = 11×7 + 4, so remainder is 4. |
| 12 | P04 | How many divisors does 12 have? | 6 | 12 = 2² × 3¹. Number of divisors = (2+1)(1+1) = 3×2 = 6. The divisors are: 1, 2, 3, 4, 6, 12 |
| 13 | P04 | How many divisors does 12 have? | 5 | 12 = 2^2 × 3^1, so the number of divisors is (2+1) + (1+1) = 5. |
| 14 | P09 | Find the last two digits of 7^100. | 7 | Last two digits of 7^n cycle 07, 49, 43, 01. 100 mod 4 = 0, so take the first term: 07, i.e. 7. |
| 15 | P02 | What is 2^10? | 2048 | 2^5 = 32, so 2^10 = 32 × 64 = 2048. |
| 16 | P18 | What is the Euler totient φ(360)? | 120 | 360 = 8 × 9 × 5, so φ(360) = φ(8) × φ(9) × φ(5) = 4 × 6 × 5 = 120. |
| 17 | P02 | What is 2^10? | 1024 | 2^10 = 2^5 × 2^5 = 32 × 32 = 1024 |
| 18 | P11 | What is the sum of all digits of 2^15? | 26 | 2^15 = 32768. Sum of digits: 3+2+7+6+8 = 26 |
| 19 | P07 | What is 3^4 mod 7? | 5 | 3^4 = 81 = 11 × 7 + 5, so 3^4 mod 7 = 5. |
| 20 | P08 | What is C(6,2)? | 30 | C(6,2) = 6 × 5 = 30. |
| 21 | P10 | How many 3-digit numbers are divisible by both 3 and 7? | 43 | Numbers divisible by both 3 and 7 are divisible by lcm(3,7)=21. 3-digit range: 100-999. First: 21×5=105. Last: 21×47=987. Count = 47-5+1 = 43. |
| 22 | P17 | How many derangements of {1,2,3,4,5} are there? | 46 | Derangements: D(n) = n × D(n−1) + (−1)^n with D(4) = 9, so D(5) = 5 × 9 + 1 = 46. |
| 23 | P14 | What is the digital root of 99999? | 45 | Digital root: add the digits, 9+9+9+9+9 = 45. |
| 24 | P01 | What is 17 mod 5? | 3 | 17 − 15 = 3, so 17 mod 5 = 3. |
| 25 | P06 | What is the GCD of 48 and 36? | 6 | 48 = 2^4 × 3 and 36 = 2^2 × 3^2, so gcd = 2 × 3 = 6. |
| 26 | P20 | What is the permanent of the 3×3 all-ones matrix? | 6 | The permanent of an n×n matrix A is perm(A) = Σ_σ ∏_{i=1}^n A_{i,σ(i)} where σ ranges over all permutations. For a 3×3 all-ones matrix, every entry equals 1, so each permutation contributes 1×1×1=1. There are 3!=6 permutations of {1,2,3}. Therefore perm(A) = 6×1 = 6. |
| 27 | P13 | How many integers from 1 to 100 are coprime to 30? | 27 | φ(30) = 8, so 8 of every 30 integers are coprime to 30. 100 × 8/30 = 26.7, which rounds to 27. |
| 28 | P05 | What is 7! / 5!? | 210 | 7!/5! = 7 × 6 × 5 = 210. |
| 29 | P12 | Find the remainder when 1! + 2! + ... + 10! is divided by 7. | 6 | From 6! on every term is divisible by 7, so only 1!+2!+3!+4!+5! = 153 matters. 153 = 21 × 7 + 6, so the remainder is 6. |
| 30 | P16 | What is the smallest positive integer n > 1 such that n^2 ≡ 1 (mod 24)? | 7 | n^2 ≡ 1 (mod 24) needs n coprime to 24 and n ≡ ±1 (mod 8). The smallest such n > 1 is 7: 49 = 2 × 24 + 1. |
| 31 | P19 | Find the number of ways to partition 7 into positive parts. | 15 | Partition function p(7). Enumerated all partitions: 7; 6+1; 5+2; 5+1+1; 4+3; 4+2+1; 4+1+1+1; 3+3+1; 3+2+2; 3+2+1+1; 3+1+1+1+1; 2+2+2+1; 2+2+1+1+1; 2+1+1+1+1+1; 1+1+1+1+1+1+1. Total count = 15. |
| 32 | P18 | What is the Euler totient φ(360)? | 96 | 360 = 2³ × 3² × 5. Using the multiplicative property of φ: φ(360) = φ(2³) × φ(3²) × φ(5) = (2³-2²) × (3²-3) × (5-1) = 4 × 6 × 4 = 96. Alternatively: φ(360) = 360 × (1-1/2) × (1-1/3) × (1-1/5) = 360 × 1/2 × 2/3 × 4/5 = 96. |
| 33 | P11 | What is the sum of all digits of 2^15? | 24 | 2^15 = 2^10 × 2^5 = 1024 × 32 = 32748. Digits: 3+2+7+4+8 = 24. |
| 34 | P14 | What is the digital root of 99999? | 9 | Digital root = repeated digit sum until single digit. 99999 -> 9+9+9+9+9 = 45 -> 4+5 = 9 |
| 35 | P09 | Find the last two digits of 7^100. | 1 | 7^4 = 2401 ≡ 1 (mod 100), so 7^100 = (7^4)^25 ≡ 1. Last two digits 01, i.e. 1. |
| 36 | P08 | What is C(6,2)? | 15 | C(6,2) = 6!/(2!*4!) = (6*5*4!)/(2!*4!) = (6*5)/(2*1) = 30/2 = 15 |
| 37 | P03 | What is the sum of the first 10 positive integers? | 55 | Sum of first n positive integers = n(n+1)/2. For n=10: 10*11/2 = 55. |
| 38 | P06 | What is the GCD of 48 and 36? | 12 | 48 = 2^4 * 3, 36 = 2^2 * 3^2. GCD = 2^min(4,2) * 3^min(1,2) = 2^2 * 3 = 4 * 3 = 12. Alternatively, Euclidean algorithm: 48 = 36*1 + 12, 36 = 12*3 + 0, so GCD = 12. |
| 39 | P19 | Find the number of ways to partition 7 into positive parts. | 16 | Euler's recurrence: p(7) = p(6) + p(5) − p(2) = 11 + 7 − 2 = 16. |
| 40 | P10 | How many 3-digit numbers are divisible by both 3 and 7? | 42 | Divisible by both 3 and 7 means by 21. Three-digit multiples run from 105 to 987: (987 − 105) / 21 = 42. |
