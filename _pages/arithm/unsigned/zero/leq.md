---
title: "Partially pointless comparison of unsigned to zero"
author: Maxim Menshikov
layout: defect
permalink: /arithm/unsigned/zero/leq
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: arithm.unsigned.zero
group:
   - arithm
   - unsigned
   - zero
---
Less or equal comparison of unsigned against 0 is partially pointless

# Impact

Writing `x <= 0` for an unsigned `x` is partially pointless: since an unsigned
value can never be negative, the comparison can only ever be true when `x == 0`.
The `<` half of `<=` is dead code. The usual harm is a logic error of intent —
the author almost always meant something else. If they wanted "x is zero" the
code works but misleads the reader; if they wanted "x is non-positive" in a sense
that should include would-be negatives, the negatives have already been lost
(the variable should not have been unsigned), so a guard that looks like it
rejects out-of-range values silently lets large values through. The mirror form
`x >= 0` is always true and disables a check entirely.

# Vulnerability potential

The direct security impact is limited, but there is a realistic indirect path.

1. **Disabled bounds check.** The closely related `x >= 0` on an unsigned value
   is a tautology, so a sanity check meant to reject out-of-range input becomes a
   no-op, letting a too-large or wrapped value reach an allocation or index.
2. **Masked underflow.** The defect often signals that a value which should be
   signed was declared unsigned. A subtraction that should have gone negative
   instead wrapped to a huge number, and `x <= 0` fails to catch it, allowing
   that huge value downstream.
3. On its own, as a test for `x == 0`, the comparison is merely confusing and
   carries no memory-safety risk.

# Technical details

Unsigned integer types in C and C++ represent only non-negative values, so for
any unsigned `x` the relation `0 <= x` holds for every possible value. That
makes `x <= 0` equivalent to `x == 0`, `x < 0` always false, and `x >= 0` always
true. The compiler can fold these to constants, and the `<` part of `<=` is
provably unreachable.

## Why it slips in
The pattern usually comes from refactoring a signed variable to unsigned (for
example switching `int` to `size_t` to silence a different warning) without
revisiting comparisons that assumed negative values were possible. It also
appears from habit, where `<= 0` is written as a generic "empty or invalid"
guard that made sense only when the type was signed.

## Signed/unsigned mixing
If `x` is unsigned and compared against a signed literal, the usual arithmetic
conversions apply. `x <= 0` converts `0` to unsigned, which is harmless, but
`x <= -1` converts `-1` to the unsigned maximum, turning an apparently
impossible test into one that is true for almost all values — a related and more
dangerous variant of the same confusion.

# Catching the issue

## Compiler warnings
GCC and Clang emit `-Wtype-limits` (part of `-Wextra`) and
`-Wtautological-compare`/`-Wtautological-unsigned-zero-compare` for comparisons
that are always true or false because of the operand's type, including
`unsigned <= 0` and `unsigned >= 0`. Treat them as errors with `-Werror` for
these specific warnings.

## Static analysis
clang-tidy, Coverity, PVS-Studio (V547 "expression is always true/false"), and
CodeQL all report tautological unsigned-vs-zero comparisons and flag the
likely-intended condition.

## Code review
When you see `<= 0` or `>= 0`, check the operand's signedness. If the intent is
"is zero", write `x == 0` to say so plainly. If the intent is to reject negative
values, the variable should be signed — making it unsigned does not make the
negatives go away, it makes them wrap. Choose the type to match the value's real
domain, then the comparison expresses real intent.

# How to reproduce

Observe that the intended "negative input" branch is never taken: the
subtraction wraps and `<= 0` only catches the exact-zero case. Build with
`-Wextra` to get a tautological-compare warning.

```c
#include <stdio.h>
#include <stddef.h>

int main(void)
{
    size_t have = 3, need = 10;

    size_t left = have - need;     /* wraps to a huge value, not negative */

    /* Looks like it rejects "not enough left", but can only catch == 0. */
    if (left <= 0)
        printf("rejected\n");
    else
        printf("accepted with left = %zu (should have been rejected)\n", left);

    return 0;
}
```

