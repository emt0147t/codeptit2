"""
Auto-generate standard test cases for PTIT Online Judge problems.
Uses auto-detection: tries multiple solver patterns against sample I/O,
uses the one that matches to generate additional test cases.

Usage:
    python tools/auto_testcases.py                    # Generate for C++ and THCS2
    python tools/auto_testcases.py --category ngon-ngu-lap-trinh-cpp
    python tools/auto_testcases.py --code CPP0101
    python tools/auto_testcases.py --dry-run
"""
import sys, os, re, random, math, json, traceback, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from database import SessionLocal
from models import Problem, TestCase

random.seed(42)

# ============================================================
#  MATH HELPERS
# ============================================================

def is_prime(n):
    if n < 2: return False
    if n < 4: return True
    if n % 2 == 0 or n % 3 == 0: return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0: return False
        i += 6
        if i % 1000 == 5: _check_deadline()
    return True

def is_perfect_square(n):
    if n < 0: return False
    r = int(math.isqrt(n))
    return r * r == n

def digit_sum(n):
    return sum(int(c) for c in str(abs(n)))

def digit_product(n):
    p = 1
    for c in str(abs(n)):
        p *= int(c)
    return p

def count_digits(n):
    return len(str(abs(n)))

def reverse_num(n):
    sign = -1 if n < 0 else 1
    return sign * int(str(abs(n))[::-1])

def gcd(a, b):
    while b: a, b = b, a % b
    return a

def lcm(a, b):
    return a * b // gcd(a, b) if a and b else 0

def fibonacci(n):
    if n <= 0: return 0
    if n == 1: return 1
    a, b = 0, 1
    for _ in range(2, n + 1): a, b = b, a + b
    return b

def is_fibonacci(n):
    return is_perfect_square(5*n*n+4) or is_perfect_square(5*n*n-4)

def prime_factors(n):
    factors = []
    d = 2
    while d*d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1: factors.append(n)
    return factors

def prime_factorization(n):
    factors = []
    d = 2
    while d*d <= n:
        e = 0
        while n % d == 0:
            e += 1; n //= d
        if e > 0: factors.append((d, e))
        d += 1
    if n > 1: factors.append((n, 1))
    return factors

def count_divisors(n):
    c = 0
    for i in range(1, int(math.isqrt(n))+1):
        if n % i == 0:
            c += 2 if i != n//i else 1
    return c

def sum_divisors(n):
    s = 0
    for i in range(1, int(math.isqrt(n))+1):
        if n % i == 0:
            s += i
            if i != n//i: s += n//i
    return s

def is_perfect_number(n):
    return n > 1 and sum_divisors(n) - n == n

def is_strong_number(n):
    return sum(math.factorial(int(d)) for d in str(n)) == n

def smallest_prime_factor(n):
    if n < 2: return n
    for d in range(2, int(math.isqrt(n))+1):
        if n % d == 0: return d
    return n

def primes_up_to(n):
    if n < 2: return []
    if n > 500000: return []
    sieve = [True]*(n+1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(math.isqrt(n))+1):
        if sieve[i]:
            for j in range(i*i, n+1, i):
                sieve[j] = False
    return [i for i in range(2, n+1) if sieve[i]]

def primes_in_range(a, b):
    if b > 10**6: return []
    return [x for x in range(max(2,a), b+1) if is_prime(x)]

def is_palindrome(s):
    s = str(s)
    return s == s[::-1]

def is_lucky(n):
    return all(c in '68' for c in str(n))

def count_even_digits(n):
    return sum(1 for c in str(abs(n)) if int(c) % 2 == 0)

def count_odd_digits(n):
    return sum(1 for c in str(abs(n)) if int(c) % 2 == 1)

def max_digit(n):
    return max(int(c) for c in str(abs(n)))

def min_digit(n):
    return min(int(c) for c in str(abs(n)))

def is_power_of_2(n):
    return n > 0 and (n & (n-1)) == 0

def adjacent_digits(n):
    s = str(n)
    return len(s) > 1 and all(abs(int(s[i])-int(s[i+1]))==1 for i in range(len(s)-1))


# ============================================================
#  SOLVER REGISTRY
# ============================================================

SOLVERS = []

def solver(name, compute_fn, gen_fn, priority=0):
    SOLVERS.append((name, compute_fn, gen_fn, priority))


def make_T_solver(name, single_compute, gen_single, val_parser=int, fmt_output=str, priority=0, max_val=10**6):
    def compute(inp):
        lines = inp.strip().split('\n')
        T = int(lines[0])
        if len(lines) != T + 1: return None
        if T > 1000: return None
        results = []
        for i in range(1, T+1):
            parts = lines[i].strip().split()
            if len(parts) == 1:
                v = val_parser(parts[0])
                if isinstance(v, (int, float)) and abs(v) > max_val: return None
                r = single_compute(v)
            else:
                vs = tuple(val_parser(p) for p in parts)
                if any(isinstance(x, (int, float)) and abs(x) > max_val for x in vs): return None
                r = single_compute(*vs)
            if r is None: return None
            results.append(fmt_output(r))
        return '\n'.join(results)

    def gen():
        inputs = []
        for _ in range(5):
            T = random.randint(2, 5)
            lines = [str(T)]
            for _ in range(T):
                lines.append(gen_single())
            inputs.append('\n'.join(lines))
        return inputs

    solver(name, compute, gen, priority)


def make_direct_solver(name, single_compute, gen_single, val_parser=int, fmt_output=str, priority=0, max_val=10**6):
    def compute(inp):
        parts = inp.strip().split()
        if len(parts) == 1:
            v = val_parser(parts[0])
            if isinstance(v, (int, float)) and abs(v) > max_val: return None
            r = single_compute(v)
        else:
            vs = tuple(val_parser(p) for p in parts)
            if any(isinstance(x, (int, float)) and abs(x) > max_val for x in vs): return None
            r = single_compute(*vs)
        if r is None: return None
        return fmt_output(r)

    def gen():
        return [gen_single() for _ in range(6)]

    solver(name, compute, gen, priority)


# ============================================================
#  REGISTER SOLVERS
# ============================================================

# Sum 1 to N
make_T_solver("T_sum1N", lambda n: n*(n+1)//2, lambda: str(random.randint(1, 10**6)))
make_direct_solver("sum1N", lambda n: n*(n+1)//2, lambda: str(random.randint(1, 10**6)))

# Double
make_T_solver("T_double", lambda n: n*2, lambda: str(random.randint(-10**6, 10**6)))
make_direct_solver("double", lambda n: n*2, lambda: str(random.randint(-10**6, 10**6)))

# Square
make_T_solver("T_square", lambda n: n*n, lambda: str(random.randint(-10**4, 10**4)))
make_direct_solver("square", lambda n: n*n, lambda: str(random.randint(-10**4, 10**4)))

# Cube
make_T_solver("T_cube", lambda n: n**3, lambda: str(random.randint(-10**3, 10**3)))
make_direct_solver("cube", lambda n: n**3, lambda: str(random.randint(-10**3, 10**3)))

# Factorial (limit to n<=170 to avoid huge numbers)
def _safe_factorial(n):
    if n > 170 or n < 0: return None
    return math.factorial(n)
make_T_solver("T_factorial", _safe_factorial, lambda: str(random.randint(0, 20)), max_val=170)
make_direct_solver("factorial", _safe_factorial, lambda: str(random.randint(0, 20)), max_val=170)

# Sum of factorials
def _sum_fac(n):
    if n > 170 or n < 0: return None
    return sum(math.factorial(i) for i in range(1, n+1))
make_T_solver("T_sumfac", _sum_fac, lambda: str(random.randint(1, 15)), max_val=170)
make_direct_solver("sumfac", _sum_fac, lambda: str(random.randint(1, 15)), max_val=170)

# Even/Odd
make_direct_solver("even_odd", lambda n: "Even" if n%2==0 else "Odd",
                   lambda: str(random.randint(-10**6, 10**6)))
make_T_solver("T_even_odd", lambda n: "Even" if n%2==0 else "Odd",
              lambda: str(random.randint(-10**6, 10**6)))

# Is prime
make_T_solver("T_prime_yn", lambda n: "YES" if is_prime(n) else "NO",
              lambda: str(random.randint(1, 10**6)))
make_direct_solver("prime_yn", lambda n: "YES" if is_prime(n) else "NO",
                   lambda: str(random.randint(1, 10**6)))
make_T_solver("T_prime_10", lambda n: "1" if is_prime(n) else "0",
              lambda: str(random.randint(1, 10**6)))
make_direct_solver("prime_10", lambda n: "1" if is_prime(n) else "0",
                   lambda: str(random.randint(1, 10**6)))

# Palindrome
make_T_solver("T_palindrome_yn", lambda n: "YES" if is_palindrome(n) else "NO",
              lambda: str(random.randint(1, 10**9)))
make_direct_solver("palindrome_yn", lambda n: "YES" if is_palindrome(n) else "NO",
                   lambda: str(random.randint(1, 10**9)))

# Digit sum
make_T_solver("T_digitsum", digit_sum, lambda: str(random.randint(1, 10**9)))
make_direct_solver("digitsum", digit_sum, lambda: str(random.randint(1, 10**9)))

# Digit product
make_T_solver("T_digitprod", digit_product, lambda: str(random.randint(11, 10**9)))
make_direct_solver("digitprod", digit_product, lambda: str(random.randint(11, 10**9)))

# Count digits
make_T_solver("T_countdigits", count_digits, lambda: str(random.randint(1, 10**9)))
make_direct_solver("countdigits", count_digits, lambda: str(random.randint(1, 10**9)))

# Reverse number
make_T_solver("T_reverse", reverse_num, lambda: str(random.randint(1, 10**9)))
make_direct_solver("reverse", reverse_num, lambda: str(random.randint(1, 10**9)))

# Max digit
make_T_solver("T_maxdigit", max_digit, lambda: str(random.randint(10, 10**9)))
make_direct_solver("maxdigit", max_digit, lambda: str(random.randint(10, 10**9)))

# Min/Max digit
def _minmax(n):
    s = str(abs(n))
    return f"{min(int(c) for c in s)} {max(int(c) for c in s)}"
make_T_solver("T_minmaxdigit", _minmax, lambda: str(random.randint(10, 10**9)))
make_direct_solver("minmaxdigit", _minmax, lambda: str(random.randint(10, 10**9)))

# Count even/odd digits
def _count_eo(n):
    return f"{count_even_digits(n)} {count_odd_digits(n)}"
make_T_solver("T_count_eodigits", _count_eo, lambda: str(random.randint(10, 10**9)))
make_direct_solver("count_eodigits", _count_eo, lambda: str(random.randint(10, 10**9)))

# Lucky number
make_T_solver("T_lucky_yn", lambda n: "YES" if is_lucky(n) else "NO",
              lambda: str(random.choice([68, 86, 888, 666, 123, 456, random.randint(1,10**6)])))

# Perfect square
make_T_solver("T_perfsq_yn", lambda n: "YES" if is_perfect_square(n) else "NO",
              lambda: str(random.randint(1, 10**6)))
make_direct_solver("perfsq_yn", lambda n: "YES" if is_perfect_square(n) else "NO",
                   lambda: str(random.randint(1, 10**6)))

# Power of 2
make_T_solver("T_pow2_yn", lambda n: "YES" if is_power_of_2(n) else "NO",
              lambda: str(random.choice([1,2,4,8,16,32,64,128,256,3,5,7,15,100])))
make_direct_solver("pow2_yn", lambda n: "YES" if is_power_of_2(n) else "NO",
                   lambda: str(random.choice([1,2,4,8,16,32,64,128,3,5,7,15,100])))

# Fibonacci
make_T_solver("T_fib_yn", lambda n: "YES" if is_fibonacci(n) else "NO",
              lambda: str(random.choice([0,1,2,3,5,8,13,21,34,55,89,4,6,7,9,100])))
make_T_solver("T_fib_n", fibonacci, lambda: str(random.randint(0, 30)))
make_direct_solver("fib_n", fibonacci, lambda: str(random.randint(0, 30)))

# GCD
make_T_solver("T_gcd", lambda a,b: gcd(a,b),
              lambda: f"{random.randint(1,10**6)} {random.randint(1,10**6)}", val_parser=int)
make_direct_solver("gcd2", lambda a,b: gcd(a,b),
                   lambda: f"{random.randint(1,10**6)} {random.randint(1,10**6)}", val_parser=int)

# LCM
make_T_solver("T_lcm", lambda a,b: lcm(a,b),
              lambda: f"{random.randint(1,10**4)} {random.randint(1,10**4)}", val_parser=int)
make_direct_solver("lcm2", lambda a,b: lcm(a,b),
                   lambda: f"{random.randint(1,10**4)} {random.randint(1,10**4)}", val_parser=int)

# Perfect number
make_T_solver("T_perfect_10", lambda n: "1" if is_perfect_number(n) else "0",
              lambda: str(random.choice([6,28,496,8128,12,15,100,27,33550336])))
make_T_solver("T_perfect_yn", lambda n: "YES" if is_perfect_number(n) else "NO",
              lambda: str(random.choice([6,28,496,8128,12,15,100,27])))

# Strong number
make_T_solver("T_strong_10", lambda n: "1" if is_strong_number(n) else "0",
              lambda: str(random.choice([1,2,145,40585,100,123,999])))
make_direct_solver("strong_10", lambda n: "1" if is_strong_number(n) else "0",
                   lambda: str(random.choice([1,2,145,40585,100,123,999])))

# Count unique prime factors
make_T_solver("T_count_upf", lambda n: len(set(prime_factors(n))) if n>1 else 0,
              lambda: str(random.randint(2, 10**6)))

# Adjacent digits
make_T_solver("T_adjacent_yn", lambda n: "YES" if adjacent_digits(n) else "NO",
              lambda: str(random.choice([123, 1234, 12321, 5654, 111, 135, random.randint(10,10**6)])))

# 1/n
def _inv_15(n):
    return f"{1/n:.15f}"
make_T_solver("T_inv15", _inv_15, lambda: str(random.randint(1, 10000)))

# C to F
make_direct_solver("c_to_f", lambda c: f"{c*9/5+32:.2f}",
                   lambda: str(random.randint(-100, 200)), fmt_output=str)

# Days to Y/W/D
def _days_ywd(d):
    y = d//365; w = (d%365)//7; dd = (d%365)%7
    return f"{y} {w} {dd}"
make_direct_solver("days_ywd", _days_ywd, lambda: str(random.randint(0, 100000)))

# Multiplication table
def _mul_table(n):
    return ' '.join(str(n*i) for i in range(1, 11))
make_direct_solver("mul_table", _mul_table, lambda: str(random.randint(1, 100)))

# Sum 2 numbers
make_direct_solver("sum2", lambda a,b: a+b,
                   lambda: f"{random.randint(-10**6,10**6)} {random.randint(-10**6,10**6)}", val_parser=int)

# Arithmetic 5 ops
def _arith5(a, b):
    if b == 0: return None
    return f"{a+b} {a-b} {a*b} {a/b:.2f} {a%b}"
make_direct_solver("arith5", _arith5,
                   lambda: f"{random.randint(1,1000)} {random.randint(1,100)}", val_parser=int)

# Primes list
def _primes_upto(n):
    if n > 100000: return None
    return ' '.join(map(str, primes_up_to(n)))
make_T_solver("T_primes_upto", _primes_upto, lambda: str(random.randint(2, 500)), max_val=100000)
make_direct_solver("primes_upto", _primes_upto, lambda: str(random.randint(2, 200)), max_val=100000)

# Primes in range
def _primes_range(a, b):
    if b - a > 100000 or b > 10**6: return None
    return ' '.join(map(str, primes_in_range(a, b)))
make_T_solver("T_primes_range", _primes_range,
              lambda: f"{random.randint(1,100)} {random.randint(100,500)}", val_parser=int, max_val=100000)
make_direct_solver("primes_range", _primes_range,
                   lambda: f"{random.randint(1,50)} {random.randint(50,200)}", val_parser=int, max_val=100000)

# PF as pairs (p e p e)
def _pf_pairs(n):
    pf = prime_factorization(n)
    parts = []
    for p, e in pf:
        parts.extend([str(p), str(e)])
    return ' '.join(parts) if parts else str(n)
make_T_solver("T_pf_pairs", _pf_pairs, lambda: str(random.randint(2, 10**6)))
make_direct_solver("pf_pairs", _pf_pairs, lambda: str(random.randint(2, 10**6)))

# SPF range (limit to avoid slow)
def _spf_range(n):
    if n > 10000: return None
    return ' '.join(str(smallest_prime_factor(i)) for i in range(1, n+1))
make_T_solver("T_spf_range", _spf_range, lambda: str(random.randint(2, 30)))

# Count perfect squares of primes <= N
def _count_pfsq(n):
    c = 0; p = 2
    while p*p <= n:
        if is_prime(p): c += 1
        p += 1
    return c
make_T_solver("T_count_pfsq", _count_pfsq, lambda: str(random.randint(4, 10**6)))

# Digit sum even
make_T_solver("T_ds_even", lambda n: "YES" if digit_sum(n)%2==0 else "NO",
              lambda: str(random.randint(1, 10**9)))

# Product of divisors (limit N to avoid huge numbers)
def _prod_div(n):
    if n > 10000: return None
    p = 1
    for i in range(1, n+1):
        if n % i == 0: p *= i
    return p
make_T_solver("T_prod_div", _prod_div, lambda: str(random.randint(2, 200)))

# Count divisors
make_T_solver("T_count_div", count_divisors, lambda: str(random.randint(2, 10**6)))
make_direct_solver("count_div", count_divisors, lambda: str(random.randint(2, 10**6)))

# Sum divisors
make_T_solver("T_sum_div", lambda n: sum_divisors(n), lambda: str(random.randint(2, 10**6)))

# Goldbach
def _goldbach(n):
    if n > 10**6: return None
    for p in range(2, n):
        if is_prime(p) and is_prime(n-p):
            return f"{p} {n-p}"
    return ""
make_T_solver("T_goldbach", _goldbach,
              lambda: str(random.choice([4,6,8,10,12,20,30,50,100,200,1000])))

# A+B prime (Yes/No)
def _ab_prime(a, b):
    return "Yes" if is_prime(a+b) else "No"
make_T_solver("T_ab_prime_yesno", _ab_prime,
              lambda: f"{random.randint(1,10**4)} {random.randint(1,10**4)}", val_parser=int)

# Sum range
def _sum_range(a, b):
    return (b-a+1)*(a+b)//2
make_direct_solver("sum_range", _sum_range,
                   lambda: f"{random.randint(1,100)} {random.randint(100,10000)}", val_parser=int)

# Count primes (limit to avoid slow computation)
def _count_primes(n):
    if n > 10**7: return None
    return len(primes_up_to(n))
make_T_solver("T_count_primes", _count_primes, lambda: str(random.randint(2, 10000)))

# First N primes (newline separated)
def _first_n_primes_nl(n):
    if n > 200: return None
    ps = []; num = 2
    while len(ps) < n:
        if is_prime(num): ps.append(num)
        num += 1
    return '\n'.join(map(str, ps))
make_direct_solver("first_n_primes_nl", _first_n_primes_nl, lambda: str(random.randint(1, 50)))

# Fibonacci list
def _fib_list(n):
    fibs = []; a, b = 0, 1
    for _ in range(n):
        fibs.append(str(a))
        a, b = b, a+b
    return ' '.join(fibs)
make_direct_solver("fib_list", _fib_list, lambda: str(random.randint(1, 30)))

# Perfect numbers up to N
def _perfect_upto(n):
    if n > 50000: return None
    return ' '.join(str(x) for x in range(2, n+1) if is_perfect_number(x))
make_direct_solver("perfect_upto", _perfect_upto,
                   lambda: str(random.choice([100,500,1000,10000])), max_val=50000)

# Prime factorization NxMx format
def _pf_mult(n):
    pf = prime_factors(n)
    return 'x'.join(map(str, pf))
make_direct_solver("pf_mult", _pf_mult, lambda: str(random.randint(2, 10000)), priority=1)

# Remove even digits
def _remove_even_digits(n):
    s = ''.join(c for c in str(n) if int(c) % 2 != 0)
    return s if s else ""
make_T_solver("T_remove_even_digits", _remove_even_digits,
              lambda: str(random.randint(10, 10**9)))

# Remove odd digits
def _remove_odd_digits(n):
    s = ''.join(c for c in str(n) if int(c) % 2 == 0)
    return s if s else ""
make_T_solver("T_remove_odd_digits", _remove_odd_digits,
              lambda: str(random.randint(10, 10**9)))

# Euler totient
def _euler_phi(n):
    result = n; temp = n; p = 2
    while p*p <= temp:
        if temp % p == 0:
            while temp % p == 0: temp //= p
            result -= result // p
        p += 1
    if temp > 1: result -= result // temp
    return result
make_T_solver("T_euler_phi", _euler_phi, lambda: str(random.randint(2, 10**6)))
make_direct_solver("euler_phi", _euler_phi, lambda: str(random.randint(2, 10**6)))

# Distinct prime factors list
def _distinct_pf_list(n):
    return ' '.join(map(str, sorted(set(prime_factors(n)))))
make_T_solver("T_distinct_pf", _distinct_pf_list, lambda: str(random.randint(2, 10**6)))

# Sum of squares 1^2 + 2^2 + ... + N^2
def _sum_sq(n):
    return n*(n+1)*(2*n+1)//6
make_T_solver("T_sum_sq", _sum_sq, lambda: str(random.randint(1, 10**4)))
make_direct_solver("sum_sq", _sum_sq, lambda: str(random.randint(1, 10**4)))

# Sum of cubes
def _sum_cu(n):
    s = n*(n+1)//2
    return s*s
make_T_solver("T_sum_cu", _sum_cu, lambda: str(random.randint(1, 10**4)))
make_direct_solver("sum_cu", _sum_cu, lambda: str(random.randint(1, 10**4)))

# Digit sum even check (YES/NO)
def _check_digit_divisible(n):
    s = str(abs(n))
    return all(c in s for c in '13579')
make_T_solver("T_all_odd_digits", _check_digit_divisible, 
              lambda: str(random.randint(1,10**6)))

# N + array solvers (T-test with N on one line, array on next)
def _make_T_arr_solver(name, single_fn):
    def compute(inp):
        lines = inp.strip().split('\n')
        T = int(lines[0])
        results = []; idx = 1
        for _ in range(T):
            n = int(lines[idx]); idx += 1
            arr = list(map(int, lines[idx].split())); idx += 1
            if len(arr) != n: return None
            r = single_fn(n, arr)
            if r is None: return None
            results.append(str(r))
        return '\n'.join(results)
    def gen():
        inputs = []
        for _ in range(5):
            T = random.randint(2, 4)
            lines = [str(T)]
            for _ in range(T):
                n = random.randint(3, 15)
                arr = [random.randint(-100, 100) for _ in range(n)]
                lines.append(str(n))
                lines.append(' '.join(map(str, arr)))
            inputs.append('\n'.join(lines))
        return inputs
    solver(name, compute, gen)

_make_T_arr_solver("T_arr_min", lambda n,a: min(a))
_make_T_arr_solver("T_arr_max", lambda n,a: max(a))
_make_T_arr_solver("T_arr_sum", lambda n,a: sum(a))
_make_T_arr_solver("T_arr_count_even", lambda n,a: sum(1 for x in a if x%2==0))
_make_T_arr_solver("T_arr_count_odd", lambda n,a: sum(1 for x in a if x%2!=0))
_make_T_arr_solver("T_arr_count_pos", lambda n,a: sum(1 for x in a if x>0))
_make_T_arr_solver("T_arr_count_neg", lambda n,a: sum(1 for x in a if x<0))

# Direct array solvers (N on first line, array on second)
def _make_arr_solver(name, arr_fn, min_n=3, max_n=20, min_v=-1000, max_v=1000):
    def compute(inp):
        lines = inp.strip().split('\n')
        if len(lines) < 2: return None
        n = int(lines[0])
        arr = list(map(int, lines[1].split()))
        if len(arr) != n: return None
        r = arr_fn(arr)
        return str(r) if r is not None else None
    def gen():
        inputs = []
        for _ in range(6):
            n = random.randint(min_n, max_n)
            arr = [random.randint(min_v, max_v) for _ in range(n)]
            inputs.append(f"{n}\n{' '.join(map(str, arr))}")
        return inputs
    solver(name, compute, gen)

_make_arr_solver("arr_min", lambda a: min(a))
_make_arr_solver("arr_max", lambda a: max(a))
_make_arr_solver("arr_sum", lambda a: sum(a))
_make_arr_solver("arr_sort_asc", lambda a: ' '.join(map(str, sorted(a))))
_make_arr_solver("arr_sort_desc", lambda a: ' '.join(map(str, sorted(a, reverse=True))))
_make_arr_solver("arr_reverse", lambda a: ' '.join(map(str, reversed(a))))
_make_arr_solver("arr_evens", lambda a: ' '.join(map(str, [x for x in a if x%2==0])))
_make_arr_solver("arr_odds", lambda a: ' '.join(map(str, [x for x in a if x%2!=0])))
_make_arr_solver("arr_primes", lambda a: ' '.join(map(str, [x for x in a if is_prime(x)])))
_make_arr_solver("arr_count_even", lambda a: sum(1 for x in a if x%2==0))
_make_arr_solver("arr_count_odd", lambda a: sum(1 for x in a if x%2!=0))
_make_arr_solver("arr_count_pos", lambda a: sum(1 for x in a if x>0))
_make_arr_solver("arr_count_neg", lambda a: sum(1 for x in a if x<0))
_make_arr_solver("arr_distinct", lambda a: ' '.join(map(str, sorted(set(a)))))
_make_arr_solver("arr_count_distinct", lambda a: len(set(a)))

# 1-test + N + array (used by some PTIT)
def _make_1test_arr_solver(name, arr_fn):
    def compute(inp):
        lines = inp.strip().split('\n')
        T = int(lines[0])
        if T != 1: return None
        n = int(lines[1])
        arr = list(map(int, lines[2].split()))
        if len(arr) != n: return None
        r = arr_fn(arr)
        return str(r) if r is not None else None
    def gen():
        inputs = []
        for _ in range(5):
            n = random.randint(3, 20)
            arr = [random.randint(-100, 100) for _ in range(n)]
            inputs.append(f"1\n{n}\n{' '.join(map(str, arr))}")
        return inputs
    solver(name, compute, gen, priority=-1)

_make_1test_arr_solver("1t_arr_max", lambda a: max(a))
_make_1test_arr_solver("1t_arr_min", lambda a: min(a))
_make_1test_arr_solver("1t_arr_sum", lambda a: sum(a))

# Quadratic equation
def _quad_eq(inp):
    lines = inp.strip().split('\n')
    results = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) == 3:
            a, b, c = float(parts[0]), float(parts[1]), float(parts[2])
            if a == 0:
                if b == 0:
                    results.append("Vo so nghiem" if c == 0 else "Vo nghiem")
                else:
                    results.append(f"{-c/b:.2f}")
            else:
                delta = b*b - 4*a*c
                if delta < 0:
                    results.append("Vo nghiem")
                elif delta == 0:
                    results.append(f"{-b/(2*a):.2f}")
                else:
                    x1 = (-b-math.sqrt(delta))/(2*a)
                    x2 = (-b+math.sqrt(delta))/(2*a)
                    if x1 > x2: x1, x2 = x2, x1
                    results.append(f"{x1:.2f} {x2:.2f}")
    return '\n'.join(results) if results else None

solver("quad_eq", _quad_eq,
       lambda: [f"{random.randint(-10,10)} {random.randint(-10,10)} {random.randint(-10,10)}" for _ in range(6)])

# Perfect squares in range a..b
def _perf_sq_range(a, b):
    result = []
    i = max(1, int(math.isqrt(a)))
    if i*i < a: i += 1
    while i*i <= b:
        result.append(str(i*i))
        i += 1
    return '\n'.join(result)
make_direct_solver("perf_sq_range", _perf_sq_range,
                   lambda: f"{random.randint(1,50)} {random.randint(50,500)}", val_parser=int)

# Sum of a..b (explicit sum or count)
def _sum_ab(a, b):
    return (b-a+1)*(a+b)//2
make_direct_solver("sum_ab", _sum_ab,
                   lambda: f"{random.randint(1,100)} {random.randint(100,10000)}", val_parser=int)

# Max of 2 numbers
make_direct_solver("max2", lambda a,b: max(a,b),
                   lambda: f"{random.randint(-10**6,10**6)} {random.randint(-10**6,10**6)}", val_parser=int)

# Min of 2 numbers
make_direct_solver("min2", lambda a,b: min(a,b),
                   lambda: f"{random.randint(-10**6,10**6)} {random.randint(-10**6,10**6)}", val_parser=int)

# Abs
make_direct_solver("abs_val", lambda n: abs(n), lambda: str(random.randint(-10**6, 10**6)))
make_T_solver("T_abs_val", lambda n: abs(n), lambda: str(random.randint(-10**6, 10**6)))

# Max of 3
def _max3(a, b, c):
    return max(a, b, c)
make_direct_solver("max3", _max3,
                   lambda: f"{random.randint(-100,100)} {random.randint(-100,100)} {random.randint(-100,100)}", val_parser=int)

# Nth power
make_T_solver("T_nth_pow", lambda a,b: a**b,
              lambda: f"{random.randint(1,10)} {random.randint(0,10)}", val_parser=int)
make_direct_solver("nth_pow", lambda a,b: a**b,
                   lambda: f"{random.randint(1,10)} {random.randint(0,10)}", val_parser=int)

# Count pair sum primes in 1..N
def _count_pair_prime(n):
    if n > 200: return None
    count = 0
    for a in range(1, n+1):
        for b in range(a+1, n+1):
            if is_prime(a+b): count += 1
    return count
make_direct_solver("count_pair_prime", _count_pair_prime,
                   lambda: str(random.randint(2, 50)), max_val=200)

# Sum of all primes up to N
def _sum_primes(n):
    if n > 100000: return None
    return sum(primes_up_to(n))
make_T_solver("T_sum_primes", _sum_primes, lambda: str(random.randint(2, 1000)), max_val=100000)
make_direct_solver("sum_primes", _sum_primes, lambda: str(random.randint(2, 1000)), max_val=100000)

# ============================================================
#  ADDITIONAL SOLVERS (batch 2)
# ============================================================

# --- Prime factorization variants ---

# Prime factors list (with multiplicity, space-separated)
def _pf_list_space(n):
    if n < 2: return None
    return ' '.join(map(str, prime_factors(n)))
make_T_solver("T_pf_list", _pf_list_space, lambda: str(random.randint(2, 10**6)))
make_direct_solver("pf_list", _pf_list_space, lambda: str(random.randint(2, 10**6)))

# Prime factors list (newline)
def _pf_list_nl(n):
    if n < 2: return None
    return '\n'.join(map(str, prime_factors(n)))
make_T_solver("T_pf_list_nl", _pf_list_nl, lambda: str(random.randint(2, 10**6)))
make_direct_solver("pf_list_nl", _pf_list_nl, lambda: str(random.randint(2, 10**6)))

# Largest prime factor
def _largest_pf(n):
    if n < 2: return None
    return prime_factors(n)[-1]
make_T_solver("T_largest_pf", _largest_pf, lambda: str(random.randint(2, 10**6)))
make_direct_solver("largest_pf", _largest_pf, lambda: str(random.randint(2, 10**6)))

# K-th unique prime factor (or -1)
def _kth_pf(n, k):
    if n < 2: return -1
    upf = sorted(set(prime_factors(n)))
    return upf[k-1] if k <= len(upf) else -1
make_T_solver("T_kth_pf", _kth_pf,
              lambda: f"{random.randint(2, 10**5)} {random.randint(1, 3)}", val_parser=int)

# Product of distinct prime factors
def _prod_distinct_pf(n):
    if n < 2: return None
    return math.prod(set(prime_factors(n)))
make_T_solver("T_prod_distinct_pf", _prod_distinct_pf, lambda: str(random.randint(2, 10**6)))
make_direct_solver("prod_distinct_pf", _prod_distinct_pf, lambda: str(random.randint(2, 10**6)))

# Count even divisors
def _count_even_div(n):
    return sum(1 for i in range(1, int(math.isqrt(n))+1) if n%i==0 and ((i%2==0) + ((n//i)%2==0 and i!=n//i)))
make_T_solver("T_count_even_div", _count_even_div, lambda: str(random.randint(2, 10**6)))
make_direct_solver("count_even_div", _count_even_div, lambda: str(random.randint(2, 10**6)))

# --- Digit operations ---

# First and last digit
def _first_last(n):
    s = str(abs(n))
    return f"{s[0]} {s[-1]}"
make_T_solver("T_first_last", _first_last, lambda: str(random.randint(10, 10**9)))
make_direct_solver("first_last", _first_last, lambda: str(random.randint(10, 10**9)))

# First digit == last digit (YES/NO)
def _first_eq_last(n):
    s = str(abs(n))
    return "YES" if s[0] == s[-1] else "NO"
make_T_solver("T_first_eq_last", _first_eq_last, lambda: str(random.randint(10, 10**9)))
make_direct_solver("first_eq_last", _first_eq_last, lambda: str(random.randint(10, 10**9)))

# Swap first and last digits
def _swap_first_last(n):
    s = str(abs(n))
    if len(s) <= 1: return n
    swapped = s[-1] + s[1:-1] + s[0]
    return int(swapped)
make_direct_solver("swap_first_last", _swap_first_last, lambda: str(random.randint(10, 10**9)))
make_T_solver("T_swap_first_last", _swap_first_last, lambda: str(random.randint(10, 10**9)))

# Sum even digits / sum odd digits
def _sum_even_digits(n):
    return sum(int(c) for c in str(abs(n)) if int(c) % 2 == 0)
def _sum_odd_digits(n):
    return sum(int(c) for c in str(abs(n)) if int(c) % 2 != 0)
make_T_solver("T_sum_even_digits", _sum_even_digits, lambda: str(random.randint(10, 10**9)))
make_T_solver("T_sum_odd_digits", _sum_odd_digits, lambda: str(random.randint(10, 10**9)))
make_direct_solver("sum_even_digits", _sum_even_digits, lambda: str(random.randint(10, 10**9)))
make_direct_solver("sum_odd_digits", _sum_odd_digits, lambda: str(random.randint(10, 10**9)))

# Lộc phát (digits only 0, 6, 8)
def _loc_phat(n):
    return "YES" if all(c in '068' for c in str(abs(n))) else "NO"
make_T_solver("T_locphat_yn", _loc_phat,
              lambda: str(random.choice([68, 806, 8060, 123, 600, 888, random.randint(1, 10**6)])))
make_direct_solver("locphat_yn", _loc_phat,
                   lambda: str(random.choice([68, 806, 8060, 123, 600, 888, random.randint(1, 10**6)])))

# --- Number theory extras ---

# Sphenic number (product of exactly 3 distinct primes)
def _is_sphenic(n):
    if n < 30: return False
    pf = prime_factors(n)
    return len(pf) == 3 and len(set(pf)) == 3
make_T_solver("T_sphenic_10", lambda n: "1" if _is_sphenic(n) else "0",
              lambda: str(random.choice([30,42,66,70,78,102,105,110,100,200,125])))
make_T_solver("T_sphenic_yn", lambda n: "YES" if _is_sphenic(n) else "NO",
              lambda: str(random.choice([30,42,66,70,78,102,105,110,100,200,125])))

# Smith number
def _is_smith(n):
    if n < 2 or is_prime(n): return False
    ds = digit_sum(n)
    pfs = prime_factors(n)
    return ds == sum(digit_sum(p) for p in pfs)
make_T_solver("T_smith_yn", lambda n: "YES" if _is_smith(n) else "NO",
              lambda: str(random.choice([4,22,27,58,85,94,121,166,100,200,300])))

# Legendre's formula: max x s.t. p^x | n!
def _legendre(n, p):
    if p < 2 or n < 0: return None
    x = 0; pk = p
    while pk <= n:
        x += n // pk
        pk *= p
    return x
make_T_solver("T_legendre", _legendre,
              lambda: f"{random.randint(1,1000)} {random.choice([2,3,5,7,11,13])}", val_parser=int)
make_direct_solver("legendre", _legendre,
                   lambda: f"{random.randint(1,1000)} {random.choice([2,3,5,7,11,13])}", val_parser=int)

# LCM + GCD pair ("GCD LCM" or "LCM GCD")
def _gcd_lcm_pair(a, b):
    g = gcd(a,b); l = lcm(a,b)
    return f"{g} {l}"
def _lcm_gcd_pair(a, b):
    g = gcd(a,b); l = lcm(a,b)
    return f"{l} {g}"
make_T_solver("T_gcd_lcm", _gcd_lcm_pair,
              lambda: f"{random.randint(1,10**4)} {random.randint(1,10**4)}", val_parser=int)
make_T_solver("T_lcm_gcd", _lcm_gcd_pair,
              lambda: f"{random.randint(1,10**4)} {random.randint(1,10**4)}", val_parser=int)
make_direct_solver("gcd_lcm", _gcd_lcm_pair,
                   lambda: f"{random.randint(1,10**4)} {random.randint(1,10**4)}", val_parser=int)
make_direct_solver("lcm_gcd", _lcm_gcd_pair,
                   lambda: f"{random.randint(1,10**4)} {random.randint(1,10**4)}", val_parser=int)

# LCM(1,2,...,N)
def _lcm_1toN(n):
    if n > 50: return None
    result = 1
    for i in range(1, n+1):
        result = lcm(result, i)
    return result
make_T_solver("T_lcm_1toN", _lcm_1toN, lambda: str(random.randint(1, 30)), max_val=50)
make_direct_solver("lcm_1toN", _lcm_1toN, lambda: str(random.randint(1, 30)), max_val=50)

# Has exactly 3 divisors
def _has_3_div(n):
    return count_divisors(n) == 3
make_T_solver("T_3div_yn", lambda n: "YES" if _has_3_div(n) else "NO",
              lambda: str(random.randint(2, 10**6)))

# List numbers with exactly 3 divisors up to N
def _list_3div(n):
    if n > 100000: return None
    return ' '.join(str(x) for x in range(2, n+1) if count_divisors(x) == 3)
make_T_solver("T_list_3div", _list_3div, lambda: str(random.randint(4, 200)), max_val=100000)

# Count numbers with 3 divisors in range [a,b]
def _count_3div_range(a, b):
    if b - a > 100000: return None
    return sum(1 for x in range(max(2,a), b+1) if count_divisors(x) == 3)
make_T_solver("T_count_3div_range", _count_3div_range,
              lambda: f"{random.randint(1,100)} {random.randint(100,1000)}", val_parser=int, max_val=100000)

# --- Geometry ---

# Euclidean distance
def _euclid_dist(*args):
    if len(args) == 4:
        x1,y1,x2,y2 = args
        return f"{math.sqrt((x2-x1)**2+(y2-y1)**2):.4f}"
    return None
make_T_solver("T_distance", _euclid_dist,
              lambda: f"{random.randint(-100,100)} {random.randint(-100,100)} {random.randint(-100,100)} {random.randint(-100,100)}",
              val_parser=float)
make_direct_solver("distance", _euclid_dist,
                   lambda: f"{random.randint(-100,100)} {random.randint(-100,100)} {random.randint(-100,100)} {random.randint(-100,100)}",
                   val_parser=float)

# Euclidean distance with 2 decimals
def _euclid_dist_2f(*args):
    if len(args) == 4:
        x1,y1,x2,y2 = args
        return f"{math.sqrt((x2-x1)**2+(y2-y1)**2):.2f}"
    return None
make_T_solver("T_distance_2f", _euclid_dist_2f,
              lambda: f"{random.randint(-100,100)} {random.randint(-100,100)} {random.randint(-100,100)} {random.randint(-100,100)}",
              val_parser=float)
make_direct_solver("distance_2f", _euclid_dist_2f,
                   lambda: f"{random.randint(-100,100)} {random.randint(-100,100)} {random.randint(-100,100)} {random.randint(-100,100)}",
                   val_parser=float)

# --- Divisibility ---

# Count numbers in [L,R] divisible by both A and B
def _count_div_ab(l, r, a, b):
    m = lcm(a, b)
    if m == 0: return 0
    return r//m - (l-1)//m
# T-test with 4 values per line
def _count_div_ab_T(inp):
    lines = inp.strip().split('\n')
    T = int(lines[0])
    if len(lines) != T + 1: return None
    results = []
    for i in range(1, T+1):
        parts = list(map(int, lines[i].split()))
        if len(parts) != 4: return None
        l, r, a, b = parts
        if any(abs(v) > 10**9 for v in parts): return None
        results.append(str(_count_div_ab(l, r, a, b)))
    return '\n'.join(results)
solver("T_count_div_ab", _count_div_ab_T,
       lambda: [_gen_count_div_ab() for _ in range(5)])

def _gen_count_div_ab():
    T = random.randint(1, 3)
    lines = [str(T)]
    for _ in range(T):
        lines.append(f"{random.randint(1,100)} {random.randint(100,10000)} {random.randint(1,20)} {random.randint(1,20)}")
    return '\n'.join(lines)

# --- Equation ---

# Linear equation ax + b = 0
def _linear_eq(inp):
    lines = inp.strip().split('\n')
    results = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) == 2:
            a, b = float(parts[0]), float(parts[1])
            if a == 0:
                results.append("Vo so nghiem" if b == 0 else "Vo nghiem")
            else:
                x = -b / a
                results.append(f"{x:.2f}")
    return '\n'.join(results) if results else None
solver("linear_eq", _linear_eq,
       lambda: [f"{random.randint(-10,10)} {random.randint(-10,10)}" for _ in range(6)])

# --- Arithmetic 6-line ---

def _arith6(inp):
    parts = inp.strip().split()
    if len(parts) != 2: return None
    a, b = int(parts[0]), int(parts[1])
    if b == 0: return None
    return f"{a+b}\n{a-b}\n{a*b}\n{a//b}\n{a%b}\n{a/b:.2f}"
solver("arith6", _arith6,
       lambda: [f"{random.randint(1,1000)} {random.randint(1,100)}" for _ in range(6)])

# --- Even/Odd Vietnamese ---
make_T_solver("T_chan_le", lambda n: "Chan" if n%2==0 else "Le",
              lambda: str(random.randint(-10**6, 10**6)))
make_direct_solver("chan_le", lambda n: "Chan" if n%2==0 else "Le",
                   lambda: str(random.randint(-10**6, 10**6)))
make_T_solver("T_chan_le2", lambda n: "CHAN" if n%2==0 else "LE",
              lambda: str(random.randint(-10**6, 10**6)))
make_direct_solver("chan_le2", lambda n: "CHAN" if n%2==0 else "LE",
                   lambda: str(random.randint(-10**6, 10**6)))

# --- Vietnamese output variants ---
make_T_solver("T_prime_yn_vi", lambda n: "Co" if is_prime(n) else "Khong",
              lambda: str(random.randint(1, 10**6)))
make_direct_solver("prime_yn_vi", lambda n: "Co" if is_prime(n) else "Khong",
                   lambda: str(random.randint(1, 10**6)))
make_T_solver("T_prime_yesno", lambda n: "Yes" if is_prime(n) else "No",
              lambda: str(random.randint(1, 10**6)))
make_direct_solver("prime_yesno", lambda n: "Yes" if is_prime(n) else "No",
                   lambda: str(random.randint(1, 10**6)))

# Palindrome 1/0
make_T_solver("T_palindrome_10", lambda n: "1" if is_palindrome(n) else "0",
              lambda: str(random.randint(1, 10**9)))
make_direct_solver("palindrome_10", lambda n: "1" if is_palindrome(n) else "0",
                   lambda: str(random.randint(1, 10**9)))

# --- Sum of remainders ---
def _sum_remainders(a, n):
    """sum of a%i for i=1..n"""
    if n > 100000: return None
    return sum(a % i for i in range(1, n+1))
make_T_solver("T_sum_remainders", _sum_remainders,
              lambda: f"{random.randint(1,1000)} {random.randint(1,100)}", val_parser=int, max_val=100000)

# Modular exponentiation
def _modpow(a, b, m):
    if m == 0: return None
    return pow(a, b, m)
make_T_solver("T_modpow", _modpow,
              lambda: f"{random.randint(1,100)} {random.randint(1,100)} {random.randint(1,1000)}", val_parser=int)

# --- Arrays with separator variants ---
# Array: sum of even elements
_make_arr_solver("arr_sum_even", lambda a: sum(x for x in a if x%2==0))
_make_arr_solver("arr_sum_odd", lambda a: sum(x for x in a if x%2!=0))
_make_arr_solver("arr_sum_pos", lambda a: sum(x for x in a if x>0))
_make_arr_solver("arr_sum_neg", lambda a: sum(x for x in a if x<0))
_make_arr_solver("arr_avg", lambda a: f"{sum(a)/len(a):.2f}")
_make_arr_solver("arr_second_max", lambda a: sorted(set(a))[-2] if len(set(a))>=2 else None)
_make_arr_solver("arr_second_min", lambda a: sorted(set(a))[1] if len(set(a))>=2 else None)

# Array: count prime elements
_make_arr_solver("arr_count_prime", lambda a: sum(1 for x in a if is_prime(x)))
_make_T_arr_solver("T_arr_count_prime", lambda n,a: sum(1 for x in a if is_prime(x)))

# Array: sum of primes
_make_arr_solver("arr_sum_prime", lambda a: sum(x for x in a if is_prime(x)))
_make_T_arr_solver("T_arr_sum_prime", lambda n,a: sum(x for x in a if is_prime(x)))

# --- Perfect square list in range ---
def _list_perfsq(a, b):
    result = []
    i = max(1, int(math.isqrt(a)))
    if i*i < a: i += 1
    while i*i <= b:
        result.append(str(i*i))
        i += 1
    return f"{len(result)}\n" + ' '.join(result) if result else "0"
make_direct_solver("list_perfsq_count", _list_perfsq,
                   lambda: f"{random.randint(1,50)} {random.randint(50,500)}", val_parser=int)

# ============================================================
#  BATCH 3 – NEW SOLVERS (expanded coverage)
# ============================================================

# --- Coprime check ---
make_T_solver("T_coprime_yn", lambda a,b: "Yes" if gcd(a,b)==1 else "No",
              lambda: f"{random.randint(1,10000)} {random.randint(1,10000)}", val_parser=int)
make_T_solver("T_coprime_YN", lambda a,b: "YES" if gcd(a,b)==1 else "NO",
              lambda: f"{random.randint(1,10000)} {random.randint(1,10000)}", val_parser=int)
make_direct_solver("coprime_yn", lambda a,b: "Yes" if gcd(a,b)==1 else "No",
                   lambda: f"{random.randint(1,10000)} {random.randint(1,10000)}", val_parser=int)

# --- Count primes in range [a,b] ---
def _count_primes_range(a, b):
    if b > 10**7: return None
    return len(primes_in_range(a, b))
make_T_solver("T_count_primes_range", _count_primes_range,
              lambda: f"{random.randint(1,100)} {random.randint(100,10000)}", val_parser=int, max_val=10**7)
make_direct_solver("count_primes_range", _count_primes_range,
                   lambda: f"{random.randint(1,100)} {random.randint(100,10000)}", val_parser=int, max_val=10**7)

# --- Sum of primes in range [a,b] ---
def _sum_primes_range(a, b):
    if b > 10**6: return None
    return sum(primes_in_range(a, b))
make_T_solver("T_sum_primes_range", _sum_primes_range,
              lambda: f"{random.randint(1,50)} {random.randint(50,1000)}", val_parser=int, max_val=10**6)
make_direct_solver("sum_primes_range", _sum_primes_range,
                   lambda: f"{random.randint(1,50)} {random.randint(50,1000)}", val_parser=int, max_val=10**6)

# --- Is Fibonacci (1/0) ---
make_T_solver("T_isfib_10", lambda n: "1" if is_fibonacci(n) else "0",
              lambda: str(random.randint(0, 10**9)))
make_direct_solver("isfib_10", lambda n: "1" if is_fibonacci(n) else "0",
                   lambda: str(random.randint(0, 10**9)))

# --- Count even/odd digits (pair output "e o") ---
def _count_eo_pair(n):
    s = str(abs(n))
    e = sum(1 for c in s if int(c) % 2 == 0)
    o = sum(1 for c in s if int(c) % 2 != 0)
    return f"{e} {o}"
make_T_solver("T_count_eo_pair", _count_eo_pair, lambda: str(random.randint(10, 10**9)))
make_direct_solver("count_eo_pair", _count_eo_pair, lambda: str(random.randint(10, 10**9)))

# --- Digits of N that divide N ---
def _digits_dividing_n(n):
    if n == 0: return 0
    return sum(1 for c in str(abs(n)) if c != '0' and n % int(c) == 0)
make_T_solver("T_digits_dividing", _digits_dividing_n, lambda: str(random.randint(11, 10**9)))
make_direct_solver("digits_dividing", _digits_dividing_n, lambda: str(random.randint(11, 10**9)))

# --- Count set bits (popcount) ---
def _popcount(n):
    return bin(n).count('1')
make_T_solver("T_popcount", _popcount, lambda: str(random.randint(0, 10**9)))
make_direct_solver("popcount", _popcount, lambda: str(random.randint(0, 10**9)))

# --- Binary representation ---
make_T_solver("T_to_binary", lambda n: bin(n)[2:], lambda: str(random.randint(0, 10**9)))
make_direct_solver("to_binary", lambda n: bin(n)[2:], lambda: str(random.randint(0, 10**9)))

# --- Fibonacci list (space-separated, T-test with 2 inputs N) ---
def _fib_list_t(n):
    if n > 50: return None
    fibs = [0]*max(2,n+1)
    fibs[0], fibs[1] = 1, 1
    for i in range(2, n+1):
        fibs[i] = fibs[i-1] + fibs[i-2]
    return ' '.join(str(fibs[i]) for i in range(n+1))
make_T_solver("T_fib_list", _fib_list_t, lambda: str(random.randint(1, 30)), max_val=50)

# --- Fibonacci list 1-indexed: F(1)..F(N) ---
def _fib_range_1(n):
    if n > 50: return None
    fibs = []
    a, b = 1, 1
    for _ in range(n):
        fibs.append(a)
        a, b = b, a+b
    return ' '.join(map(str, fibs))
make_T_solver("T_fib_range1", _fib_range_1, lambda: str(random.randint(1, 30)), max_val=50)
make_direct_solver("fib_range1", _fib_range_1, lambda: str(random.randint(1, 30)), max_val=50)

# --- Fibonacci list from pair (a, N): a terms starting at fib(1) ---
def _fib_pair(a, n):
    """Fibonacci from index a to n"""
    if n > 50: return None
    fibs = [0]*max(2, n+2)
    fibs[1] = 1
    for i in range(2, n+2):
        fibs[i] = fibs[i-1] + fibs[i-2]
    return ' '.join(str(fibs[i]) for i in range(max(1,a), n+1))
make_T_solver("T_fib_pair", _fib_pair,
              lambda: f"{random.randint(1,5)} {random.randint(5,30)}", val_parser=int, max_val=50)
make_direct_solver("fib_pair", _fib_pair,
                   lambda: f"{random.randint(1,5)} {random.randint(5,30)}", val_parser=int, max_val=50)

# --- Permutations of 1..N ---
def _permutations_list(n):
    if n > 8: return None
    from itertools import permutations as itp
    perms = sorted(itp(range(1, n+1)))
    return ' '.join(''.join(map(str, p)) for p in perms)
make_T_solver("T_permutations", _permutations_list, lambda: str(random.randint(2, 5)), max_val=8)
make_direct_solver("permutations", _permutations_list, lambda: str(random.randint(2, 5)), max_val=8)

# --- Permutations reverse order ---
def _permutations_rev(n):
    if n > 8: return None
    from itertools import permutations as itp
    perms = sorted(itp(range(1, n+1)), reverse=True)
    return ' '.join(''.join(map(str, p)) for p in perms)
make_T_solver("T_permutations_rev", _permutations_rev, lambda: str(random.randint(2, 5)), max_val=8)

# --- Combinations C(n,k) list ---
def _combinations_list(n, k):
    if n > 20 or k > n: return None
    from itertools import combinations as itc
    combs = sorted(itc(range(1, n+1), k))
    return ' '.join(''.join(map(str, c)) for c in combs)
make_T_solver("T_combinations", _combinations_list,
              lambda: f"{random.randint(3,8)} {random.randint(2,4)}", val_parser=int, max_val=20)
make_direct_solver("combinations", _combinations_list,
                   lambda: f"{random.randint(3,8)} {random.randint(2,4)}", val_parser=int, max_val=20)

# --- C(n,k) value ---
def _comb_val(n, k):
    if n > 60 or k > n: return None
    from math import comb
    return comb(n, k)
make_T_solver("T_comb_val", _comb_val,
              lambda: f"{random.randint(2,20)} {random.randint(1,5)}", val_parser=int, max_val=60)
make_direct_solver("comb_val", _comb_val,
                   lambda: f"{random.randint(2,20)} {random.randint(1,5)}", val_parser=int, max_val=60)

# --- Binary numbers 0..2^N-1 ---
def _binary_list(n):
    if n > 20: return None
    return ' '.join(format(i, f'0{n}b') for i in range(2**n))
make_T_solver("T_binary_list", _binary_list, lambda: str(random.randint(2, 5)), max_val=20)

# --- Remove "084" from string ---
def _remove_084(s):
    return s.replace('0', '').replace('8', '').replace('4', '') or '0'
make_T_solver("T_remove_084", _remove_084,
              lambda: str(random.randint(10**5, 10**9)), val_parser=str)

# --- Digits increasing check ---
def _digits_increasing(s):
    d = [int(c) for c in str(s) if c.isdigit()]
    for i in range(len(d)-1):
        if d[i] >= d[i+1]: return "NO"
    return "YES"
make_T_solver("T_digits_increasing", _digits_increasing,
              lambda: str(random.randint(10, 10**9)), val_parser=str)
make_direct_solver("digits_increasing", _digits_increasing,
                   lambda: str(random.randint(10, 10**9)), val_parser=str)

# --- Digits decreasing check ---
def _digits_decreasing(s):
    d = [int(c) for c in str(s) if c.isdigit()]
    for i in range(len(d)-1):
        if d[i] <= d[i+1]: return "NO"
    return "YES"
make_T_solver("T_digits_decreasing", _digits_decreasing,
              lambda: str(random.randint(10, 10**9)), val_parser=str)

# --- All digits same check ---
def _all_digits_same(s):
    d = str(s)
    return "YES" if len(set(d)) == 1 else "NO"
make_T_solver("T_all_digits_same", _all_digits_same,
              lambda: str(random.choice([111, 222, 333, 444, 555, 666, 777, 888, 999,
                                          random.randint(10, 10**9)])), val_parser=str)

# --- Has repeated digit ---
def _has_repeated_digit(s):
    d = str(s)
    return "YES" if len(d) != len(set(d)) else "NO"
make_T_solver("T_has_repeated_digit", _has_repeated_digit,
              lambda: str(random.randint(10, 10**9)), val_parser=str)

# --- All even digits ---
def _all_even_digits(s):
    return "YES" if all(int(c) % 2 == 0 for c in str(s)) else "NO"
make_T_solver("T_all_even_digits", _all_even_digits,
              lambda: str(random.randint(10, 10**9)), val_parser=str)
make_direct_solver("all_even_digits", _all_even_digits,
                   lambda: str(random.randint(10, 10**9)), val_parser=str)

# --- Perfect numbers in range ---
def _perfect_in_range(a, b):
    if b > 10**7: return None
    result = [x for x in range(max(2,a), b+1) if is_perfect_number(x)]
    return ' '.join(map(str, result)) if result else "NONE"
make_direct_solver("perfect_in_range", _perfect_in_range,
                   lambda: f"{random.randint(1,10)} {random.randint(100,10000)}", val_parser=int, max_val=10**7)

# --- Strong numbers up to N ---
def _strong_upto(n):
    if n > 10**6: return None
    result = [x for x in range(1, n+1) if is_strong_number(x)]
    return ' '.join(map(str, result)) if result else "NONE"
make_direct_solver("strong_upto", _strong_upto,
                   lambda: str(random.randint(100, 10000)), max_val=10**6)

# --- Strong numbers in range ---
def _strong_in_range(a, b):
    if b > 10**6: return None
    result = [x for x in range(max(1,a), b+1) if is_strong_number(x)]
    return ' '.join(map(str, result)) if result else "NONE"
make_direct_solver("strong_in_range", _strong_in_range,
                   lambda: f"{random.randint(1,10)} {random.randint(100,10000)}", val_parser=int, max_val=10**6)

# --- Twin primes (lower of pair) in range ---
def _twin_primes(a, b):
    if b > 10**6: return None
    result = []
    ps = primes_in_range(a, b)
    ps_set = set(ps)
    for p in ps:
        if p + 2 in ps_set:
            result.append(p)
    return ' '.join(map(str, result)) if result else "NONE"
make_direct_solver("twin_primes", _twin_primes,
                   lambda: f"{random.randint(2,10)} {random.randint(50,500)}", val_parser=int, max_val=10**6)

# --- Count twin prime pairs in range ---
def _count_twin_primes(a, b):
    if b > 10**6: return None
    ps = primes_in_range(a, b)
    ps_set = set(ps)
    return sum(1 for p in ps if p+2 in ps_set)
make_T_solver("T_count_twin_primes", _count_twin_primes,
              lambda: f"{random.randint(1,50)} {random.randint(50,1000)}", val_parser=int, max_val=10**6)
make_direct_solver("count_twin_primes", _count_twin_primes,
                   lambda: f"{random.randint(1,50)} {random.randint(50,1000)}", val_parser=int, max_val=10**6)

# --- LCM(a..b) product range ---
def _lcm_range(a, b):
    if b - a > 50 or b > 200: return None
    result = 1
    for i in range(a, b+1):
        result = lcm(result, i)
    return result
make_T_solver("T_lcm_range", _lcm_range,
              lambda: f"{random.randint(1,5)} {random.randint(5,15)}", val_parser=int, max_val=200)
make_direct_solver("lcm_range", _lcm_range,
                   lambda: f"{random.randint(1,5)} {random.randint(5,15)}", val_parser=int, max_val=200)

# --- Array min adjacent difference (sorted) ---
def _arr_min_adj_diff(arr):
    s = sorted(arr)
    return min(s[i+1]-s[i] for i in range(len(s)-1))
_make_T_arr_solver("T_arr_min_adj_diff", lambda n,a: _arr_min_adj_diff(a))
_make_arr_solver("arr_min_adj_diff", _arr_min_adj_diff)

# --- Smallest missing positive ---
def _smallest_missing_pos(arr):
    s = set(arr)
    i = 1
    while i in s:
        i += 1
    return i
_make_T_arr_solver("T_arr_smallest_miss", lambda n,a: _smallest_missing_pos(a))
_make_arr_solver("arr_smallest_miss", _smallest_missing_pos)

# --- Kth smallest ---
def _make_T_arr_kth_solver(name, fn):
    def compute(inp):
        lines = inp.strip().split('\n')
        T = int(lines[0])
        results = []; idx = 1
        for _ in range(T):
            parts = list(map(int, lines[idx].split()))
            if len(parts) == 2:
                n, k = parts
            elif len(parts) == 1:
                n = parts[0]; k = None
            else:
                return None
            idx += 1
            arr = list(map(int, lines[idx].split())); idx += 1
            r = fn(n, k, arr)
            if r is None: return None
            results.append(str(r))
        return '\n'.join(results)
    def gen():
        inputs = []
        for _ in range(5):
            T = random.randint(1, 3)
            lines = [str(T)]
            for _ in range(T):
                n = random.randint(3, 15)
                k = random.randint(1, n)
                arr = [random.randint(-100, 100) for _ in range(n)]
                lines.append(f"{n} {k}")
                lines.append(' '.join(map(str, arr)))
            inputs.append('\n'.join(lines))
        return inputs
    solver(name, compute, gen)

_make_T_arr_kth_solver("T_arr_kth_smallest", lambda n,k,a: sorted(a)[k-1] if k and 1<=k<=len(a) else None)
_make_T_arr_kth_solver("T_arr_kth_largest", lambda n,k,a: sorted(a,reverse=True)[k-1] if k and 1<=k<=len(a) else None)

# --- Balance point (sum left == sum right) ---
def _balance_point(arr):
    total = sum(arr)
    left = 0
    for i, x in enumerate(arr):
        if left == total - left - x:
            return i + 1  # 1-indexed
        left += x
    return -1
_make_T_arr_solver("T_arr_balance", lambda n,a: _balance_point(a))
_make_arr_solver("arr_balance", _balance_point)

# --- Count duplicates ---
def _count_dupes(arr):
    from collections import Counter
    c = Counter(arr)
    return sum(1 for v in c.values() if v > 1)
_make_T_arr_solver("T_arr_count_dupes", lambda n,a: _count_dupes(a))
_make_arr_solver("arr_count_dupes", _count_dupes)

# --- Array max subarray sum (Kadane) ---
def _max_subarray(arr):
    best = arr[0]
    cur = arr[0]
    for x in arr[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best
_make_T_arr_solver("T_arr_max_subarray", lambda n,a: _max_subarray(a))
_make_arr_solver("arr_max_subarray", _max_subarray)

# --- Array product ---
_make_T_arr_solver("T_arr_product", lambda n,a: math.prod(a) if all(abs(x)<100 for x in a) else None)
_make_arr_solver("arr_product", lambda a: math.prod(a) if all(abs(x)<100 for x in a) else None)

# --- Array LIS length ---
def _lis_len(arr):
    from bisect import bisect_left
    tails = []
    for x in arr:
        pos = bisect_left(tails, x)
        if pos == len(tails):
            tails.append(x)
        else:
            tails[pos] = x
    return len(tails)
_make_T_arr_solver("T_arr_lis", lambda n,a: _lis_len(a))
_make_arr_solver("arr_lis", _lis_len)

# --- Array: count elements > average ---
def _count_above_avg(arr):
    avg = sum(arr) / len(arr)
    return sum(1 for x in arr if x > avg)
_make_T_arr_solver("T_arr_above_avg", lambda n,a: _count_above_avg(a))

# --- Sort array: evens first then odds ---
def _sort_even_odd(arr):
    evens = sorted(x for x in arr if x % 2 == 0)
    odds = sorted(x for x in arr if x % 2 != 0)
    return ' '.join(map(str, evens + odds))
_make_arr_solver("arr_sort_even_odd", _sort_even_odd)

# --- Digit sort ascending ---
def _sort_digits_asc(s):
    return ''.join(sorted(str(s)))
make_T_solver("T_sort_digits", _sort_digits_asc,
              lambda: str(random.randint(10, 10**9)), val_parser=str)
make_direct_solver("sort_digits", _sort_digits_asc,
                   lambda: str(random.randint(10, 10**9)), val_parser=str)

# --- Digit sort descending ---
def _sort_digits_desc(s):
    return ''.join(sorted(str(s), reverse=True))
make_T_solver("T_sort_digits_desc", _sort_digits_desc,
              lambda: str(random.randint(10, 10**9)), val_parser=str)

# --- Number to Roman (small) ---
def _to_roman(n):
    if n <= 0 or n > 3999: return None
    vals = [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),
            (50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
    r = ''
    for v, s in vals:
        while n >= v:
            r += s; n -= v
    return r
make_T_solver("T_to_roman", _to_roman, lambda: str(random.randint(1, 3999)))
make_direct_solver("to_roman", _to_roman, lambda: str(random.randint(1, 3999)))

# --- Roman to number ---
def _from_roman(s):
    rom = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
    s = s.strip().upper()
    if not all(c in rom for c in s): return None
    r = 0
    for i, c in enumerate(s):
        if i+1 < len(s) and rom[c] < rom[s[i+1]]:
            r -= rom[c]
        else:
            r += rom[c]
    return r
make_T_solver("T_from_roman", _from_roman, val_parser=str,
              gen_single=lambda: random.choice(['I','IV','IX','XIV','XIX','XL','XLII',
                'L','LX','XC','C','CC','CD','DC','CM','M','MCMXC','MMXX','MMMCMXCIX']))
make_direct_solver("from_roman", _from_roman, val_parser=str,
                   gen_single=lambda: random.choice(['XIV','XIX','XL','XLII','DC','CM']))

# --- Palindrome counting in range ---
def _count_palindromes(a, b):
    if b > 10**6: return None
    return sum(1 for x in range(a, b+1) if str(x) == str(x)[::-1])
make_T_solver("T_count_palindromes", _count_palindromes,
              lambda: f"{random.randint(1,50)} {random.randint(50,500)}", val_parser=int, max_val=10**6)
make_direct_solver("count_palindromes", _count_palindromes,
                   lambda: f"{random.randint(1,50)} {random.randint(50,500)}", val_parser=int, max_val=10**6)

# --- Amicable pair check ---
def _is_amicable(a, b):
    if a == b: return "NO"
    sa = sum_divisors(a) - a
    sb = sum_divisors(b) - b
    return "YES" if sa == b and sb == a else "NO"
make_T_solver("T_amicable", _is_amicable,
              lambda: f"{random.randint(1,10000)} {random.randint(1,10000)}", val_parser=int)

# --- Sum of digits recursive (digital root) ---
def _digital_root(n):
    n = abs(n)
    while n >= 10:
        n = sum(int(c) for c in str(n))
    return n
make_T_solver("T_digital_root", _digital_root, lambda: str(random.randint(1, 10**9)))
make_direct_solver("digital_root", _digital_root, lambda: str(random.randint(1, 10**9)))

# --- Next prime after N ---
def _next_prime(n):
    if n > 10**7: return None
    n += 1
    while not is_prime(n):
        n += 1
    return n
make_T_solver("T_next_prime", _next_prime, lambda: str(random.randint(2, 10000)), max_val=10**7)
make_direct_solver("next_prime", _next_prime, lambda: str(random.randint(2, 10000)), max_val=10**7)

# --- Previous prime before N ---
def _prev_prime(n):
    if n <= 2: return None
    n -= 1
    while n > 1 and not is_prime(n):
        n -= 1
    return n if n > 1 else None
make_T_solver("T_prev_prime", _prev_prime, lambda: str(random.randint(3, 10000)))

# --- Armstrong number check ---
def _is_armstrong(n):
    s = str(n)
    k = len(s)
    return "YES" if sum(int(c)**k for c in s) == n else "NO"
make_T_solver("T_armstrong_yn", _is_armstrong, lambda: str(random.randint(1, 10**6)), val_parser=str)
make_direct_solver("armstrong_yn", _is_armstrong, lambda: str(random.randint(1, 10**6)), val_parser=str)

# --- Harshad number check ---
def _is_harshad(n):
    if n <= 0: return "NO"
    return "YES" if n % digit_sum(n) == 0 else "NO"
make_T_solver("T_harshad_yn", _is_harshad, lambda: str(random.randint(1, 10**6)))
make_direct_solver("harshad_yn", _is_harshad, lambda: str(random.randint(1, 10**6)))

# --- Neon number check (sum of digits of n^2 == n) ---
def _is_neon(n):
    return "YES" if digit_sum(n*n) == n else "NO"
make_T_solver("T_neon_yn", _is_neon, lambda: str(random.randint(0, 1000)))

# --- Automorphic number check (n^2 ends in n) ---
def _is_automorphic(n):
    return "YES" if str(n*n).endswith(str(n)) else "NO"
make_T_solver("T_automorphic_yn", _is_automorphic,
              lambda: str(random.randint(1, 10**6)), val_parser=str)

# --- Abundant number check ---
def _is_abundant(n):
    return "YES" if sum_divisors(n) - n > n else "NO"
make_T_solver("T_abundant_yn", _is_abundant, lambda: str(random.randint(2, 10**6)))

# --- Sum of odd divisors ---
def _sum_odd_div(n):
    return sum(d for d in range(1, n+1) if n % d == 0 and d % 2 != 0)
make_T_solver("T_sum_odd_div", _sum_odd_div, lambda: str(random.randint(2, 10000)), max_val=10**6)

# --- Triangle classification by sides ---
def _triangle_type(a, b, c):
    sides = sorted([a, b, c])
    if sides[0] + sides[1] <= sides[2]:
        return "NOT"
    if sides[0] == sides[1] == sides[2]:
        return "Equilateral"
    if sides[0] == sides[1] or sides[1] == sides[2]:
        return "Isosceles"
    return "Scalene"

# --- Arithmetic progression sum: a + (a+d) + ... for n terms ---
def _ap_sum(a, d, n=None):
    if n is None: return None
    return n * (2*a + (n-1)*d) // 2

# --- Geometric progression sum: a + a*r + ... for n terms ---
def _gp_sum(a, r, n=None):
    if n is None: return None
    if r == 1: return a * n
    return a * (r**n - 1) // (r - 1)

# --- Divisors list (sorted, space-separated) ---
def _divisors_list(n):
    if n > 10**6: return None
    divs = sorted(d for d in range(1, n+1) if n % d == 0)
    return ' '.join(map(str, divs))
make_T_solver("T_divisors_list", _divisors_list, lambda: str(random.randint(2, 1000)), max_val=10**6)
make_direct_solver("divisors_list", _divisors_list, lambda: str(random.randint(2, 1000)), max_val=10**6)

# --- Next perfect square after N ---
def _next_perfsq(n):
    r = int(math.isqrt(n)) + 1
    return r * r
make_T_solver("T_next_perfsq", _next_perfsq, lambda: str(random.randint(1, 10**6)))

# --- Number of trailing zeros of N! ---
def _trailing_zeros_fact(n):
    count = 0
    p = 5
    while p <= n:
        count += n // p
        p *= 5
    return count
make_T_solver("T_trailing_zeros", _trailing_zeros_fact, lambda: str(random.randint(1, 10**6)))
make_direct_solver("trailing_zeros", _trailing_zeros_fact, lambda: str(random.randint(1, 10**6)))

# --- Catalan number ---
def _catalan(n):
    if n > 30: return None
    from math import comb
    return comb(2*n, n) // (n+1)
make_T_solver("T_catalan", _catalan, lambda: str(random.randint(0, 20)), max_val=30)
make_direct_solver("catalan", _catalan, lambda: str(random.randint(0, 20)), max_val=30)

# --- Stirling number S(n, k) ---
def _stirling2(n, k):
    if n > 20 or k > n: return None
    if n == 0 and k == 0: return 1
    if n == 0 or k == 0: return 0
    dp = [[0]*(k+1) for _ in range(n+1)]
    dp[0][0] = 1
    for i in range(1, n+1):
        for j in range(1, min(i, k)+1):
            dp[i][j] = j * dp[i-1][j] + dp[i-1][j-1]
    return dp[n][k]
make_T_solver("T_stirling2", _stirling2,
              lambda: f"{random.randint(2,10)} {random.randint(1,5)}", val_parser=int, max_val=20)

# --- Array: median ---
def _arr_median(arr):
    s = sorted(arr)
    n = len(s)
    if n % 2 == 1:
        return str(s[n//2])
    else:
        return f"{(s[n//2-1]+s[n//2])/2:.1f}"
_make_arr_solver("arr_median", _arr_median)

# --- Array: range (max - min) ---
_make_T_arr_solver("T_arr_range", lambda n,a: max(a)-min(a))
_make_arr_solver("arr_range", lambda a: max(a)-min(a))

# --- Array: count elements equal to max ---
_make_T_arr_solver("T_arr_count_max", lambda n,a: a.count(max(a)))

# --- Array: count elements equal to min ---
_make_T_arr_solver("T_arr_count_min", lambda n,a: a.count(min(a)))

# --- Sum of a+b with T-test  ---
make_T_solver("T_sum2", lambda a,b: a+b,
              lambda: f"{random.randint(-10**6, 10**6)} {random.randint(-10**6, 10**6)}", val_parser=int)

# --- Difference a-b ---
make_T_solver("T_diff2", lambda a,b: a-b,
              lambda: f"{random.randint(-10**6, 10**6)} {random.randint(-10**6, 10**6)}", val_parser=int)
make_direct_solver("diff2", lambda a,b: a-b,
                   lambda: f"{random.randint(-10**6, 10**6)} {random.randint(-10**6, 10**6)}", val_parser=int)

# --- Product a*b ---
make_T_solver("T_prod2", lambda a,b: a*b,
              lambda: f"{random.randint(-10**3, 10**3)} {random.randint(-10**3, 10**3)}", val_parser=int)
make_direct_solver("prod2", lambda a,b: a*b,
                   lambda: f"{random.randint(-10**3, 10**3)} {random.randint(-10**3, 10**3)}", val_parser=int)

# --- Swap two strings/words (reverse word order) ---
def _swap_words(s):
    parts = s.strip().split()
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}"
    return None
make_T_solver("T_swap_words", _swap_words, val_parser=str,
              gen_single=lambda: f"{random.randint(1,100)} {random.randint(1,100)}")

# --- Uppercase ---
make_direct_solver("uppercase", lambda s: s.upper(), val_parser=str,
                   gen_single=lambda: ''.join(random.choice('abcdefghij ') for _ in range(random.randint(3,15))))

# --- Hello name ---
make_direct_solver("hello_name", lambda s: f"Hello {s}!",
                   val_parser=str, gen_single=lambda: random.choice(['Nam','An','Binh','Cuong','Dung']))

# --- Alternating group count ---
def _count_alt_groups(s):
    """Count groups of alternating chars in circular string"""
    n = len(s)
    if n < 3: return 0
    count = 0
    for i in range(n):
        if s[i] != s[(i-1) % n] and s[i] != s[(i+1) % n]:
            count += 1
    return count

# --- Palindromic substring count ---
def _count_palindromic_substrings(s):
    n = len(s)
    count = 0
    for i in range(n):
        # odd length
        l, r = i, i
        while l >= 0 and r < n and s[l] == s[r]:
            count += 1; l -= 1; r += 1
        # even length
        l, r = i, i+1
        while l >= 0 and r < n and s[l] == s[r]:
            count += 1; l -= 1; r += 1
    return count
make_direct_solver("count_palsubstr", _count_palindromic_substrings,
                   val_parser=str, gen_single=lambda: ''.join(random.choice('abc') for _ in range(random.randint(3,10))))
make_T_solver("T_count_palsubstr", _count_palindromic_substrings,
              val_parser=str, gen_single=lambda: ''.join(random.choice('abc') for _ in range(random.randint(3,10))))

# --- Longest palindromic substring length ---
def _longest_pal_substr(s):
    n = len(s)
    best = 1
    for i in range(n):
        l, r = i, i
        while l >= 0 and r < n and s[l] == s[r]:
            best = max(best, r-l+1); l -= 1; r += 1
        l, r = i, i+1
        while l >= 0 and r < n and s[l] == s[r]:
            best = max(best, r-l+1); l -= 1; r += 1
    return best
make_direct_solver("longest_palsubstr", _longest_pal_substr,
                   val_parser=str, gen_single=lambda: ''.join(random.choice('abcd') for _ in range(random.randint(3,12))))
make_T_solver("T_longest_palsubstr", _longest_pal_substr,
              val_parser=str, gen_single=lambda: ''.join(random.choice('abcd') for _ in range(random.randint(3,12))))

# --- Unique substrings count ---
def _count_unique_substr(s):
    """Count of distinct 2-char substrings"""
    subs = set()
    for i in range(len(s)-1):
        subs.add(s[i:i+2])
    return len(subs)

# --- Number format with commas ---
def _format_commas(s):
    n = int(s)
    return f"{n:,}"
make_direct_solver("format_commas", _format_commas, val_parser=str,
                   gen_single=lambda: str(random.randint(1000, 10**9)))

# --- Min of 2 numbers ---
make_T_solver("T_min2", lambda a,b: min(a,b),
              lambda: f"{random.randint(-10**6, 10**6)} {random.randint(-10**6, 10**6)}", val_parser=int)

# --- Max of 2 numbers ---
make_T_solver("T_max2", lambda a,b: max(a,b),
              lambda: f"{random.randint(-10**6, 10**6)} {random.randint(-10**6, 10**6)}", val_parser=int)

# --- Reverse string ---
make_T_solver("T_reverse_str", lambda s: s[::-1], val_parser=str,
              gen_single=lambda: ''.join(random.choice('abcdefghij') for _ in range(random.randint(3,15))))
make_direct_solver("reverse_str", lambda s: s[::-1], val_parser=str,
                   gen_single=lambda: ''.join(random.choice('abcdefghij') for _ in range(random.randint(3,15))))

# --- Array: rotate left by K ---
def _make_T_arr_rotate_solver():
    def compute(inp):
        lines = inp.strip().split('\n')
        T = int(lines[0])
        results = []; idx = 1
        for _ in range(T):
            parts = list(map(int, lines[idx].split()))
            if len(parts) == 2:
                n, k = parts
            else:
                return None
            idx += 1
            arr = list(map(int, lines[idx].split())); idx += 1
            if len(arr) != n: return None
            k = k % n if n > 0 else 0
            rotated = arr[k:] + arr[:k]
            results.append(' '.join(map(str, rotated)))
        return '\n'.join(results)
    def gen():
        inputs = []
        for _ in range(5):
            T = random.randint(1, 3)
            lines = [str(T)]
            for _ in range(T):
                n = random.randint(3, 10)
                k = random.randint(1, n-1)
                arr = [random.randint(1, 100) for _ in range(n)]
                lines.append(f"{n} {k}")
                lines.append(' '.join(map(str, arr)))
            inputs.append('\n'.join(lines))
        return inputs
    solver("T_arr_rotate", compute, gen)
_make_T_arr_rotate_solver()

# --- Array: counting sort (sort 0s, 1s, 2s) ---
_make_T_arr_solver("T_arr_sort012", lambda n,a: ' '.join(map(str, sorted(a))) if all(x in (0,1,2) for x in a) else None)

# --- Array: move zeros to end ---
def _move_zeros_end(arr):
    nz = [x for x in arr if x != 0]
    zs = [x for x in arr if x == 0]
    return ' '.join(map(str, nz + zs))
_make_T_arr_solver("T_arr_move_zeros", lambda n,a: _move_zeros_end(a))
_make_arr_solver("arr_move_zeros", _move_zeros_end)

# --- Array: interleave sort (max, min, 2nd max, 2nd min...) ---
def _interleave_sort(arr):
    s = sorted(arr)
    result = []
    l, r = 0, len(s)-1
    toggle = True
    while l <= r:
        if toggle:
            result.append(s[r]); r -= 1
        else:
            result.append(s[l]); l += 1
        toggle = not toggle
    return ' '.join(map(str, result))
_make_T_arr_solver("T_arr_interleave", lambda n,a: _interleave_sort(a))

# --- Array: odd-indexed elements product ---
_make_T_arr_solver("T_arr_prod_odd_idx", lambda n,a: math.prod(a[i] for i in range(1,n,2)) if n>=2 and all(abs(a[i])<100 for i in range(1,n,2)) else None)

# --- Digits in non-decreasing order check ---
def _digits_nondecreasing(s):
    d = list(str(s))
    return "YES" if d == sorted(d) else "NO"
make_T_solver("T_digits_nondec", _digits_nondecreasing,
              lambda: str(random.randint(10, 10**9)), val_parser=str)

# --- Digits in non-increasing order check ---
def _digits_nonincreasing(s):
    d = list(str(s))
    return "YES" if d == sorted(d, reverse=True) else "NO"
make_T_solver("T_digits_noninc", _digits_nonincreasing,
              lambda: str(random.randint(10, 10**9)), val_parser=str)

# --- Number of digits that are prime ---
def _count_prime_digits(n):
    return sum(1 for c in str(abs(n)) if c in '2357')
make_T_solver("T_count_prime_digits", _count_prime_digits,
              lambda: str(random.randint(10, 10**9)))
make_direct_solver("count_prime_digits", _count_prime_digits,
                   lambda: str(random.randint(10, 10**9)))

# --- P(n,k) = n! / (n-k)! permutation count ---
def _perm_count(n, k):
    if n > 20 or k > n: return None
    r = 1
    for i in range(n, n-k, -1):
        r *= i
    return r
make_T_solver("T_perm_count", _perm_count,
              lambda: f"{random.randint(3,15)} {random.randint(1,5)}", val_parser=int, max_val=20)
make_direct_solver("perm_count", _perm_count,
                   lambda: f"{random.randint(3,15)} {random.randint(1,5)}", val_parser=int, max_val=20)


# ============================================================
#  AUTO-DETECTION ENGINE
# ============================================================

# Global timeout for solver testing (seconds)
_SOLVER_DEADLINE = None

class _SolverTimeout(Exception):
    pass

def _check_deadline():
    if _SOLVER_DEADLINE and time.time() > _SOLVER_DEADLINE:
        raise _SolverTimeout()

def try_solver(solver_entry, sample_input, sample_output):
    global _SOLVER_DEADLINE
    name, compute_fn, gen_fn, priority = solver_entry
    _SOLVER_DEADLINE = time.time() + 2.0  # 2 second max per solver
    try:
        result = compute_fn(sample_input)
        if result is None: return False
        expected = sample_output.strip()
        actual = result.strip()
        if expected == actual: return True
        exp_lines = expected.split('\n')
        act_lines = actual.split('\n')
        if len(exp_lines) != len(act_lines): return False
        for el, al in zip(exp_lines, act_lines):
            if el.strip() != al.strip():
                try:
                    if abs(float(el.strip()) - float(al.strip())) < 1e-4:
                        continue
                except:
                    pass
                return False
        return True
    except (_SolverTimeout, Exception):
        return False
    finally:
        _SOLVER_DEADLINE = None


def find_matching_solver(sample_input, sample_output):
    matches = []
    for entry in SOLVERS:
        if try_solver(entry, sample_input, sample_output):
            matches.append(entry)
    if not matches: return None
    matches.sort(key=lambda x: (-x[3], -len(x[0])))
    return matches[0]


# ============================================================
#  MAIN PIPELINE
# ============================================================

def generate_for_problem(problem, db, dry_run=False, verbose=False):
    existing_tc = db.query(TestCase).filter(TestCase.problem_id == problem.id).all()
    sample_tcs = [tc for tc in existing_tc if tc.is_sample]
    hidden_tcs = [tc for tc in existing_tc if not tc.is_sample]

    if len(hidden_tcs) >= 3:
        return 0, "skip: has hidden TCs"

    if not sample_tcs:
        return 0, "skip: no sample"

    sample = sample_tcs[0]
    inp = sample.input_data.strip()
    out = sample.expected_output.strip()

    if not inp or not out:
        return 0, "skip: empty sample"

    match = find_matching_solver(inp, out)
    if not match:
        return 0, "no match"

    name, compute_fn, gen_fn, priority = match

    try:
        result = gen_fn()
        test_inputs = result if isinstance(result, list) else [result]
    except Exception:
        return 0, f"gen error ({name})"

    added = 0
    max_order = max((tc.order for tc in existing_tc), default=-1) + 1

    for i, test_input in enumerate(test_inputs):
        try:
            test_output = compute_fn(test_input)
            if test_output is None or not test_output.strip():
                continue
        except Exception:
            continue

        if dry_run:
            if verbose:
                print(f"    TC#{i+1}: IN={test_input[:60]!r} -> OUT={test_output[:60]!r}")
            added += 1
            continue

        is_dup = any(tc.input_data.strip() == test_input.strip() for tc in existing_tc)
        if is_dup: continue

        tc = TestCase(
            problem_id=problem.id,
            input_data=test_input.strip(),
            expected_output=test_output.strip(),
            is_sample=False,
            order=max_order + i,
        )
        db.add(tc)
        added += 1

    if not dry_run and added > 0:
        db.commit()

    return added, f"{name} (+{added})"


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", "-c", default=None)
    parser.add_argument("--code", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()

    if args.code:
        problem = db.query(Problem).filter(Problem.code == args.code).first()
        if not problem:
            print(f"Problem {args.code} not found"); return
        added, status = generate_for_problem(problem, db, args.dry_run, args.verbose)
        print(f"{problem.code}: {status}")
        db.close(); return

    categories = [args.category] if args.category else [
        'ngon-ngu-lap-trinh-cpp', 'tin-hoc-co-so-2',
        'cau-truc-du-lieu-giai-thuat', 'lap-trinh-huong-doi-tuong',
        'lap-trinh-voi-python', 'thuat-toan-nang-cao',
    ]

    total_added = 0
    total_problems = 0
    matched = 0
    unmatched_codes = []

    for cat in categories:
        print(f"\n{'='*60}")
        print(f"  Category: {cat}")
        print(f"{'='*60}")

        problems = db.query(Problem).filter(Problem.category == cat).order_by(Problem.code).all()

        for p in problems:
            total_problems += 1
            added, status = generate_for_problem(p, db, args.dry_run, args.verbose)
            total_added += added
            if added > 0:
                matched += 1
                print(f"  + {p.code:12s}: {status}")
            else:
                unmatched_codes.append(p.code)
                if args.verbose:
                    print(f"  - {p.code:12s}: {status}")

    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Problems processed:  {total_problems}")
    print(f"  Solver matched:      {matched}")
    print(f"  Test cases added:    {total_added}")
    print(f"  No match:            {len(unmatched_codes)}")
    if unmatched_codes:
        print(f"  Unmatched codes:     {', '.join(unmatched_codes[:40])}")
        if len(unmatched_codes) > 40:
            print(f"                       ...and {len(unmatched_codes)-40} more")
    print(f"{'='*60}")

    db.close()


if __name__ == "__main__":
    main()
