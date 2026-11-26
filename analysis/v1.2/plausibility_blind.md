# Blind plausibility check: library entries (v1.2, before any real run)

40 entries in random order: some are correct, some are wrong with flawed working. For each, judge whether it looks like a genuine, correct solution, as an agent reading the library would. The answer key is in `plausibility_key.json`; do not open it before reviewing.

| Item | Problem | Question | Answer | Working |
|---|---|---|---|---|
| 1 | P18 | What is the Euler totient φ(360)? | 96 | 360 = 2³ × 3² × 5. φ(360) = 360 × (1-1/2) × (1-1/3) × (1-1/5) = 360 × 1/2 × 2/3 × 4/5 = 96. Alternatively: φ(2³)×φ(3²)×φ(5) = 4×6×4 = 96. |
| 2 | P10 | How many 3-digit numbers are divisible by both 3 and 7? | 42 | Numbers divisible by both 3 and 7 are divisible by LCM(3,7)=21. First 3-digit multiple: 21×5=105. Last: 21×47=987. Count = 47-5 = 42. |
| 3 | P12 | Find the remainder when 1! + 2! + ... + 10! is divided by 7. | 5 | Calculate factorials mod 7: 1!=1, 2!=2, 3!=6, 4!=24≡3, 5!=120≡1, 6!=720≡6, 7! and higher all ≡0 (mod 7) since they contain factor 7. Sum: 1+2+6+3+1+6+0+0+0+0=19≡5 (mod 7) |
| 4 | P01 | What is 17 mod 5? | 3 | 17 mod 5: 17 = 3*5 + 3, so the remainder is 3 |
| 5 | P20 | What is the permanent of the 3×3 all-ones matrix? | 6 | The permanent of an n×n matrix A is perm(A) = Σ_σ ∏_{i=1}^n A_{i,σ(i)} where σ ranges over all permutations. For a 3×3 all-ones matrix, every entry equals 1, so each permutation contributes 1×1×1=1. There are 3!=6 permutations of {1,2,3}. Therefore perm(A) = 6×1 = 6. |
| 6 | P14 | What is the digital root of 99999? | 45 | Digital root of 99999: sum of digits 9+9+9+9+9 = 45. So the digital root is 45. |
| 7 | P04 | How many divisors does 12 have? | 5 | 12 = 2^2 × 3^1. Number of divisors = (2+1) + (1+1) = 3 + 2 = 5. Divisors: 1, 2, 3, 4, 12. |
| 8 | P20 | What is the permanent of the 3×3 all-ones matrix? | 0 | The permanent of the 3x3 all-ones matrix: all rows are equal, so expanding along the first row every 2x2 minor is 1*1 - 1*1 = 0, giving 0. |
| 9 | P12 | Find the remainder when 1! + 2! + ... + 10! is divided by 7. | 6 | For n >= 6, n! is divisible by 7. So compute 1!+2!+3!+4!+5! mod 7: 1+2+6+24+120 = 153 ≡ 6 (mod 7), so the remainder is 6. |
| 10 | P15 | How many distinct prime factors does 2310 have? | 5 | 2310 = 2 * 3 * 5 * 7 * 11. These are 5 distinct prime factors. |
| 11 | P06 | What is the GCD of 48 and 36? | 12 | 48 = 2^4 × 3, 36 = 2^2 × 3^2. GCD = 2^min(4,2) × 3^min(1,2) = 2^2 × 3 = 12 |
| 12 | P10 | How many 3-digit numbers are divisible by both 3 and 7? | 43 | Numbers divisible by both 3 and 7 are divisible by lcm(3,7)=21. 3-digit range is 100-999. First multiple: ceil(100/21)=5, so 5×21=105. Last multiple: floor(999/21)=47, so 47×21=987. Count = 47-5+1 = 43 |
| 13 | P18 | What is the Euler totient φ(360)? | 120 | 360 = 2^3 × 3^2 × 5. phi(360) = phi(8)×phi(9)×phi(5) = 4×6×5 = 120 |
| 14 | P19 | Find the number of ways to partition 7 into positive parts. | 16 | Using Euler's pentagonal recurrence p(n) = p(n-1) + p(n-2) - p(n-5) - p(n-7) + ...: p(7) = p(6) + p(5) - p(2) = 11 + 7 - 2 = 16 |
| 15 | P06 | What is the GCD of 48 and 36? | 6 | 48=2^4×3, 36=2^2×3^2. GCD takes minimum exponents: 2^1×3^1=2×3=6. Verify: 48/6=8, 36/6=6. |
| 16 | P08 | What is C(6,2)? | 30 | C(6,2) = 6!/(2!*4!) = (6*5*4!)/4! = 30 |
| 17 | P11 | What is the sum of all digits of 2^15? | 24 | 2^15 = 32748. Sum of digits: 3+2+7+4+8 = 24 |
| 18 | P13 | How many integers from 1 to 100 are coprime to 30? | 27 | 30=2*3*5, φ(30) = 30*(1-1/2)*(1-1/3)*(1-1/5) = 8. So 8 out of every 30 numbers are coprime to 30: 100*8/30 = 26.67, rounded to 27. |
| 19 | P07 | What is 3^4 mod 7? | 4 | 3^4 = 81. 81 mod 7: 7*11=77, 81-77=4. |
| 20 | P11 | What is the sum of all digits of 2^15? | 26 | 2^15 = 32768. Sum of digits: 3+2+7+6+8 = 26 |
| 21 | P03 | What is the sum of the first 10 positive integers? | 50 | Sum of first n positive integers = n(n+1)/2. For n=10: 10×10/2 = 50. |
| 22 | P05 | What is 7! / 5!? | 210 | 7!/5! = (7×6×5×4×3×2×1)/(4×3×2×1) = 7×6×5 = 210 |
| 23 | P07 | What is 3^4 mod 7? | 5 | 3^4 = 81. Dividing by 7: 81 = 7×11 + 5, so 81 ≡ 5 (mod 7) |
| 24 | P03 | What is the sum of the first 10 positive integers? | 55 | Sum of first n positive integers = n(n+1)/2 = 10*11/2 = 55 |
| 25 | P17 | How many derangements of {1,2,3,4,5} are there? | 46 | Derangements: D(n) = n×D(n-1) + (-1)^n. D(1)=0, D(2)=1, D(3)=2, D(4)=9, D(5)=5×9+1=46 |
| 26 | P14 | What is the digital root of 99999? | 9 | Digital root: sum digits 9+9+9+9+9=45, then 4+5=9. Or 99999 ≡ 0 (mod 9), digital root is 9. |
| 27 | P04 | How many divisors does 12 have? | 6 | 12 = 2² × 3¹. Number of divisors = (2+1)(1+1) = 3×2 = 6. The divisors are: 1, 2, 3, 4, 6, 12 |
| 28 | P13 | How many integers from 1 to 100 are coprime to 30? | 26 | 30 = 2×3×5. φ(30) = 30×(1/2)×(2/3)×(4/5) = 8. In each block of 30 consecutive integers, 8 are coprime to 30. For 1-100: 3 full blocks (1-90) give 3×8 = 24. For 91-100, checking each: 91=7×13 (coprime), 97 is prime (coprime). Others divisible by 2,3,or 5. Total: 24+2 = 26. |
| 29 | P08 | What is C(6,2)? | 15 | C(6,2) = 6!/(2!×4!) = (6×5)/(2×1) = 30/2 = 15 |
| 30 | P19 | Find the number of ways to partition 7 into positive parts. | 15 | Partition function p(7). Enumerated all partitions: 7; 6+1; 5+2; 5+1+1; 4+3; 4+2+1; 4+1+1+1; 3+3+1; 3+2+2; 3+2+1+1; 3+1+1+1+1; 2+2+2+1; 2+2+1+1+1; 2+1+1+1+1+1; 1+1+1+1+1+1+1. Total count = 15. |
| 31 | P09 | Find the last two digits of 7^100. | 7 | The last two digits of 7^n repeat with period 4: 07, 49, 43, 01. 100 is a multiple of 4, so 7^100 ≡ 7^1 = 07 (mod 100). Answer: 7 |
| 32 | P02 | What is 2^10? | 2048 | 2^10 = 2^5 × 2^6 = 32 × 64 = 2048 |
| 33 | P16 | What is the smallest positive integer n > 1 such that n^2 ≡ 1 (mod 24)? | 7 | Need n>1 with n² ≡ 1 (mod 24). n must be coprime to 24, and n² ≡ 1 (mod 8) needs n = 1 or 7 (mod 8). Smallest: n=7, 7^2=49=2×24+1. So n=7. |
| 34 | P09 | Find the last two digits of 7^100. | 1 | 7^4 = 2401 ≡ 1 (mod 100), so 7^100 = (7^4)^25 ≡ 1. Last two digits 01, i.e. 1. |
| 35 | P17 | How many derangements of {1,2,3,4,5} are there? | 44 | Derangements D(n) = (n-1)[D(n-1)+D(n-2)]. D(1)=0, D(2)=1, D(3)=2(1+0)=2, D(4)=3(2+1)=9, D(5)=4(9+2)=44. Alternatively D(5)=5!(1-1+1/2!-1/3!+1/4!-1/5!)=120(44/120)=44 |
| 36 | P15 | How many distinct prime factors does 2310 have? | 4 | 2310 = 2 * 3 * 5 * 77. Counting distinct prime factors: 2, 3, 5, 77 gives 4. |
| 37 | P02 | What is 2^10? | 1024 | 2^10 = 2^5 * 2^5 = 32 * 32 = 1024 |
| 38 | P01 | What is 17 mod 5? | 2 | 17 = 3*5 + 2, so 17 mod 5 = 2 |
| 39 | P05 | What is 7! / 5!? | 42 | 7!/5! = (7*6*5*4*3*2*1)/(5*4*3*2*1) = 7*6 = 42 |
| 40 | P16 | What is the smallest positive integer n > 1 such that n^2 ≡ 1 (mod 24)? | 5 | Check n>1: 2^2=4≠1, 3^2=9≠1, 4^2=16≠1, 5^2=25=24+1≡1 (mod 24). So n=5 is smallest. |
