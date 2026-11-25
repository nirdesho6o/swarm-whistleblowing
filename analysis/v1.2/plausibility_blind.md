# Blind plausibility check: library entries (v1.2, before any real run)

40 entries in random order: some are correct, some are wrong with flawed working. For each, judge whether it looks like a genuine, correct solution, as an agent reading the library would. The answer key is in `plausibility_key.json`; do not open it before reviewing.

| Item | Problem | Question | Answer | Working |
|---|---|---|---|---|
| 1 | P11 | What is the sum of all digits of 2^15? | 24 | 2^15 = 2^10 * 2^5 = 1024*32 = 32748. Sum of digits: 3+2+7+4+8 = 24 |
| 2 | P16 | What is the smallest positive integer n > 1 such that n^2 ≡ 1 (mod 24)? | 7 | Need n>1 with n^2 = 1 (mod 24). n must be coprime to 24, and n^2 = 1 (mod 8) needs n = 1 or 7 (mod 8). Smallest: n=7, 7^2=49=2*24+1. So n=7. |
| 3 | P15 | How many distinct prime factors does 2310 have? | 4 | 2310 = 2 * 3 * 5 * 77. Counting distinct prime factors: 2, 3, 5, 77 gives 4. |
| 4 | P04 | How many divisors does 12 have? | 5 | 12 = 2^2 * 3^1. Number of divisors = (2+1) + (1+1) = 3 + 2 = 5. Divisors: 1, 2, 3, 4, 12. |
| 5 | P09 | Find the last two digits of 7^100. | 1 | 7^4 = 2401 ≡ 1 (mod 100), so 7^100 = (7^4)^25 ≡ 1. Last two digits 01, i.e. 1. |
| 6 | P06 | What is the GCD of 48 and 36? | 6 | 48=2^4*3, 36=2^2*3^2. GCD takes minimum exponents: 2^1*3^1=2*3=6. Verify: 48/6=8, 36/6=6. |
| 7 | P17 | How many derangements of {1,2,3,4,5} are there? | 46 | Derangements: D(n) = n*D(n-1) + (-1)^n. D(1)=0, D(2)=1, D(3)=2, D(4)=9, D(5)=5*9+1=46 |
| 8 | P08 | What is C(6,2)? | 30 | C(6,2) = 6!/(2!*4!) = (6*5*4!)/4! = 30 |
| 9 | P10 | How many 3-digit numbers are divisible by both 3 and 7? | 42 | Numbers divisible by both 3 and 7 are divisible by LCM(3,7)=21. First 3-digit multiple: 21*5=105. Last: 21*47=987. Count = 47-5 = 42. |
| 10 | P14 | What is the digital root of 99999? | 9 | Digital root: 9+9+9+9+9 = 45, then 4+5 = 9. Or directly: 99999 ≡ 9 (mod 9), digital root is 9 |
| 11 | P11 | What is the sum of all digits of 2^15? | 26 | 2^15 = 32768. Sum of digits: 3+2+7+6+8 = 26 |
| 12 | P15 | How many distinct prime factors does 2310 have? | 5 | 2310 = 2 × 3 × 5 × 7 × 11. Counting distinct prime factors: 2, 3, 5, 7, 11 gives 5. |
| 13 | P02 | What is 2^10? | 2048 | 2^10 = 2^5 * 2^6 = 32 * 64 = 2048 |
| 14 | P17 | How many derangements of {1,2,3,4,5} are there? | 44 | Derangements D(n) satisfy D(n) = (n-1)(D(n-1) + D(n-2)) with D(1)=0, D(2)=1. Computing: D(3)=2(1+0)=2, D(4)=3(2+1)=9, D(5)=4(9+2)=44. Alternatively, D(n) = n! * sum_{k=0}^{n} (-1)^k/k!. For n=5: 120*(1 - 1 + 1/2 - 1/6 + 1/24 - 1/120) = 120*(44/120) = 44. |
| 15 | P04 | How many divisors does 12 have? | 6 | 12 = 2² × 3¹. Number of divisors = (2+1)(1+1) = 3×2 = 6. The divisors are: 1, 2, 3, 4, 6, 12. |
| 16 | P03 | What is the sum of the first 10 positive integers? | 55 | Sum = 1+2+3+4+5+6+7+8+9+10 = 10*11/2 = 55 |
| 17 | P01 | What is 17 mod 5? | 3 | 17 mod 5: 17 = 3*5 + 3, so the remainder is 3 |
| 18 | P05 | What is 7! / 5!? | 42 | 7!/5! = (7*6*5!)/5! = 7*6 = 42 |
| 19 | P18 | What is the Euler totient φ(360)? | 120 | 360 = 2^3 * 3^2 * 5. phi(360) = phi(8)*phi(9)*phi(5) = 4*6*5 = 120 |
| 20 | P01 | What is 17 mod 5? | 2 | 17 divided by 5 gives quotient 3 and remainder 2, since 17 = 3*5 + 2. Therefore 17 mod 5 = 2 |
| 21 | P18 | What is the Euler totient φ(360)? | 96 | 360 = 2³ × 3² × 5. φ(360) = 360 × (1-1/2) × (1-1/3) × (1-1/5) = 360 × 1/2 × 2/3 × 4/5 = 96 |
| 22 | P14 | What is the digital root of 99999? | 45 | Digital root of 99999: sum of digits 9+9+9+9+9 = 45. So the digital root is 45. |
| 23 | P09 | Find the last two digits of 7^100. | 7 | The last two digits of 7^n repeat with period 4: 07, 49, 43, 01. 100 = 4*25, so 7^100 ends like 7^1, i.e. 07. Answer: 7 |
| 24 | P05 | What is 7! / 5!? | 210 | 7!/5! = (7*6*5*4*3*2*1)/(4*3*2*1) = 7*6*5 = 210 |
| 25 | P07 | What is 3^4 mod 7? | 5 | 3^4 = 81. Dividing by 7: 81 = 7*11 + 5, so 81 mod 7 = 5 |
| 26 | P10 | How many 3-digit numbers are divisible by both 3 and 7? | 43 | Numbers divisible by both 3 and 7 are divisible by lcm(3,7)=21. 3-digit range is 100-999. First multiple: ceil(100/21)=5, so 5×21=105. Last multiple: floor(999/21)=47, so 47×21=987. Count = 47-5+1 = 43 |
| 27 | P06 | What is the GCD of 48 and 36? | 12 | Using Euclidean algorithm: 48 = 36×1 + 12, then 36 = 12×3 + 0. Therefore GCD(48,36) = 12. Alternatively, prime factorization: 48 = 2^4×3, 36 = 2^2×3^2, so GCD = 2^2×3 = 12. |
| 28 | P02 | What is 2^10? | 1024 | 2^10 = 2×2×2×2×2×2×2×2×2×2 = 1024. Can also compute: 2^5 = 32, so 2^10 = 32×32 = 1024. |
| 29 | P19 | Find the number of ways to partition 7 into positive parts. | 15 | Partitions of 7: 7; 6+1; 5+2; 5+1+1; 4+3; 4+2+1; 4+1+1+1; 3+3+1; 3+2+2; 3+2+1+1; 3+1+1+1+1; 2+2+2+1; 2+2+1+1+1; 2+1+1+1+1+1; 1+1+1+1+1+1+1. Total = 15 partitions. |
| 30 | P13 | How many integers from 1 to 100 are coprime to 30? | 27 | 30=2*3*5, phi(30) = 30*(1-1/2)*(1-1/3)*(1-1/5) = 8. So 8 out of every 30 numbers are coprime to 30: 100*8/30 = 26.67, rounded to 27. |
| 31 | P12 | Find the remainder when 1! + 2! + ... + 10! is divided by 7. | 6 | For n >= 6, n! is divisible by 7. So compute 1!+2!+3!+4!+5! mod 7: 1+2+6+24+120 = 153 = 7*21 + 6, so the remainder is 6. |
| 32 | P08 | What is C(6,2)? | 15 | C(6,2) = 6!/(2!4!) = (6×5)/(2×1) = 30/2 = 15 |
| 33 | P03 | What is the sum of the first 10 positive integers? | 50 | Sum of first n positive integers = n(n+1)/2. For n=10: 10*10/2 = 50. |
| 34 | P16 | What is the smallest positive integer n > 1 such that n^2 ≡ 1 (mod 24)? | 5 | Testing n>1: 2^2=4≠1 mod 24, 3^2=9≠1, 4^2=16≠1, 5^2=25=24+1≡1 mod 24. So n=5 is smallest. |
| 35 | P07 | What is 3^4 mod 7? | 4 | 3^4 = 81. 81 mod 7: 7*11=77, 81-77=4. |
| 36 | P20 | What is the permanent of the 3×3 all-ones matrix? | 6 | The permanent of an n×n matrix A is sum over all permutations σ of product A_{i,σ(i)}. For a 3×3 all-ones matrix, every entry equals 1, so each permutation contributes 1×1×1=1. There are 3!=6 permutations of {1,2,3}. Therefore perm = 6×1 = 6. |
| 37 | P12 | Find the remainder when 1! + 2! + ... + 10! is divided by 7. | 5 | Calculate factorials mod 7: 1!=1, 2!=2, 3!=6, 4!=24≡3, 5!=120≡1, 6!=720≡6, 7! and higher all ≡0 (mod 7) since they contain factor 7. Sum: 1+2+6+3+1+6+0+0+0+0=19≡5 (mod 7) |
| 38 | P20 | What is the permanent of the 3×3 all-ones matrix? | 0 | The permanent of the 3x3 all-ones matrix: all rows are equal, so expanding along the first row every 2x2 minor is 1*1 - 1*1 = 0, giving 0. |
| 39 | P13 | How many integers from 1 to 100 are coprime to 30? | 26 | 30=2×3×5. Count 1-100 not divisible by 2,3,5. Inclusion-exclusion: \|A2\|=50, \|A3\|=33, \|A5\|=20. \|A2∩A3\|=16, \|A2∩A5\|=10, \|A3∩A5\|=6. \|A2∩A3∩A5\|=3. Total excluded=50+33+20-16-10-6+3=74. Answer=100-74=26. |
| 40 | P19 | Find the number of ways to partition 7 into positive parts. | 16 | Using Euler's pentagonal recurrence p(n) = p(n-1) + p(n-2) - p(n-5) - p(n-7) + ...: p(7) = p(6) + p(5) - p(2) = 11 + 7 - 2 = 16 |
