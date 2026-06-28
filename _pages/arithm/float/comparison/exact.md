---
title: "Exact float comparison"
author: Maxim Menshikov
layout: defect
permalink: /arithm/float/comparison/exact
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: arithm.float.comparison
group:
   - arithm
   - float
   - comparison
---
Floating point integers shouldn't be compared using == operator

# Impact

Comparing two floating-point values with `==` (or `!=`) asks whether they are
bit-for-bit identical, which is rarely what the programmer wants. Because most
decimal fractions cannot be represented exactly in binary, and because rounding
differs with the order of operations, two computations that are mathematically
equal often differ in the last bit. The equality test then fails when it
"should" succeed: a loop that waits for an accumulator to reach an exact value
never stops, a state machine misses a target, a convergence check never fires.
Conversely, values that differ by a negligible amount are treated as different.
The program produces wrong control flow without any error or warning.

# Vulnerability potential

This defect has little direct security relevance; it is primarily a correctness
and reliability bug.

1. The most concrete risk is denial of service: a termination or convergence
   condition expressed as an exact equality may never become true, leaving a
   loop spinning forever and hanging the thread or process.
2. As an indirect concern, if an equality test guards a security or financial
   decision (matching an exact amount, an exact key-derivation parameter, a
   sentinel value), platform- or optimization-dependent rounding could make the
   decision flip between builds. There is no memory-safety impact.

# Technical details

IEEE-754 binary floating point represents numbers as `sign * mantissa *
2^exponent`. Only sums of powers of two are exact, so common decimals such as
`0.1`, `0.2`, and `0.3` are stored as the nearest representable value, with a
tiny error. `0.1 + 0.2` rounds to a value just above `0.3`, so `0.1 + 0.2 ==
0.3` is **false**.

## Rounding and reassociation
Each operation rounds its result to the nearest representable value, and the
error depends on operand magnitudes and the order of operations. Because
floating-point addition and multiplication are not associative, `(a + b) + c`
and `a + (b + c)` can differ in the last bit, so two routes to the "same" value
need not be bit-identical.

## Extra precision and contraction
Intermediate results may be kept at higher precision than the variable type:
historically x87 used 80-bit registers (controlled by `FLT_EVAL_METHOD`), and
fused multiply-add (`-ffp-contract`) computes `a*b+c` with a single rounding.
The same source can thus yield different bits depending on registers,
optimization level, and target, making exact equality non-portable.

## NaN
`NaN` compares unequal to everything, including itself: `x == x` is `false` when
`x` is `NaN`, so `==`/`!=` cannot even be used to test a value against itself.

# Catching the issue

## Compiler warnings
GCC and Clang have `-Wfloat-equal`, which warns about every `==`/`!=` between
floating-point operands. It is not in `-Wall`, so enable it explicitly.

## Static analysis
clang-tidy (`clang-diagnostic-float-equal`), PVS-Studio (V550), Coverity, and
CodeQL all flag direct floating-point equality comparisons. Linters for most
languages have an equivalent rule.

## How to compare correctly
Compare with a tolerance instead of `==`. Use an absolute epsilon for values
near a known scale, `fabs(a - b) <= eps`, or a relative/ULP comparison for
values spanning many magnitudes, `fabs(a - b) <= eps * fmax(fabs(a), fabs(b))`.
Choose the epsilon from the problem's precision, not blindly from
`FLT_EPSILON`. Comparing against exact representable values (e.g. `0.0`, or
integers small enough to be exact) is legitimate; the rule targets results of
inexact computation. Always handle `NaN` explicitly.

# How to reproduce

Observe that the exact comparison reports "not equal" even though the values are
mathematically equal, while the tolerance-based test succeeds.

```c
#include <stdio.h>
#include <math.h>

int main(void)
{
    double a = 0.1 + 0.2;
    double b = 0.3;

    if (a == b)
        printf("exact: equal\n");
    else
        printf("exact: NOT equal (a - b = %.17g)\n", a - b);

    if (fabs(a - b) <= 1e-9)
        printf("epsilon: equal\n");
    return 0;
}
```

