---
title: "Possible division by zero"
author: Maxim Menshikov
layout: defect
permalink: /arithm/division/zero
arch:
   - native
vulnerability:
   - Low
ddos:
   - High
group_full: arithm.division
group:
   - arithm
   - division
---
The value is probably divided by zero

# Impact

Dividing an integer by zero (or taking a remainder with a zero divisor)
terminates the program on virtually every platform. On x86/x86-64 the CPU
raises a hardware divide-error exception, which the OS delivers as `SIGFPE` on
POSIX or an `EXCEPTION_INT_DIVIDE_BY_ZERO` on Windows; the default action is to
kill the process. The same applies to `INT_MIN / -1`, whose quotient does not
fit in the type and traps identically. A single unchecked divisor that an
attacker can drive to zero is therefore enough to crash a service.

# Vulnerability potential

This issue is mainly a denial-of-service vector (CWE-369).

1. **Crash on demand.** If the divisor comes from user input — a configured
   stride, a count parsed from a request, an averaging denominator — an attacker
   sets it to zero and reliably crashes the process, repeatedly if it restarts.
2. **Amplified DoS.** In a server that forks or threads per request, a single
   malformed request can take down a worker; many of them exhaust the pool.
3. The memory-safety risk is low: the hardware trap is taken before any bad
   value is produced, so there is normally no corruption. It becomes higher only
   if a custom `SIGFPE` handler resumes execution with an undefined quotient, or
   on platforms/ISAs where division does not trap and silently yields garbage
   that then flows into indexing or sizing.

# Technical details

In C and C++ the result of dividing by zero is **undefined behavior** (C11
6.5.5p5), so the language gives no guarantees at all. What actually happens is
determined by the hardware.

## Integer division
On x86/x86-64 the `DIV`/`IDIV` instructions raise interrupt 0 (#DE) when the
divisor is zero, and also when the signed quotient overflows — the notorious
`INT_MIN / -1` case, where the mathematically correct `2^31` does not fit in a
32-bit signed result. ARM AArch64's `SDIV`/`UDIV` do **not** trap: dividing by
zero yields `0`, so the same source crashes on x86 but silently returns a bogus
value on ARM. This portability gap is itself a source of bugs.

## Floating-point division
Floating-point divide-by-zero does **not** trap by default under IEEE-754. It
produces `+inf`, `-inf`, or `NaN` (for `0.0/0.0`) and sets a status flag.
The program keeps running with a non-finite value, which is a separate hazard:
comparisons against `NaN` are all false, and `inf` propagates through later
arithmetic.

## The modulo operator
`a % 0` is undefined for the same reason as division; on x86 it shares the same
`IDIV` trap.

# Catching the issue

## Sanitizers
`-fsanitize=integer-divide-by-zero` and `-fsanitize=float-divide-by-zero` (UBSan)
report the operation at runtime with file and line, and `-fsanitize=signed-integer-overflow`
catches the `INT_MIN / -1` case.

## Static analysis
Clang Static Analyzer (`core.DivideZero`), clang-tidy, Coverity, PVS-Studio, and
CodeQL flag divisions whose denominator can reach zero on some path, especially
when it traces back to untrusted input.

## Runtime guard
The reliable fix is an explicit check: `if (divisor == 0) { /* handle */ } else
result = a / divisor;`, and for signed division also exclude
`a == INT_MIN && divisor == -1`.

## Catching the trap
### Linux/POSIX
Install a `SIGFPE` handler to log and fail gracefully, but do not resume the
faulting instruction — the quotient would be undefined.
### Windows
Wrap the computation in `__try`/`__except` and inspect for
`EXCEPTION_INT_DIVIDE_BY_ZERO`.

# How to reproduce

Observe that the process is killed by `SIGFPE` on x86-64 (or returns a bogus 0
on AArch64). Build with `-fsanitize=undefined` to get a precise report.

```c
#include <stdio.h>

int main(void)
{
    int count = 0;                 /* e.g. parsed from input */
    int total = 100;

    /* No check that count != 0. */
    int average = total / count;   /* divide error -> SIGFPE, process killed */

    printf("average = %d\n", average);
    return 0;
}
```

