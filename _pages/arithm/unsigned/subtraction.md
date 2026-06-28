---
title: "Incorrect subtraction"
author: Maxim Menshikov
layout: defect
permalink: /arithm/unsigned/subtraction
arch:
   - native
vulnerability:
   - High
ddos:
   - Low
group_full: arithm.unsigned
group:
   - arithm
   - unsigned
---
The subtraction is invalid

# Impact

Subtracting a larger value from a smaller one in unsigned arithmetic does not
produce a negative number — there are no negative unsigned values. The result
wraps around to a huge positive number close to the type's maximum. Code that
expected a small or zero difference (a remaining length, a count, a gap) instead
gets a value in the billions. When that value is used as a size, a loop bound,
or an index, it drives the program far out of the intended range, typically into
an out-of-bounds read or write.

# Vulnerability potential

This issue has a strong potential to become a vulnerability (a form of CWE-191,
integer underflow).

1. **Oversized length.** `remaining = buffer_len - offset` underflows when
   `offset > buffer_len`, yielding a near-`SIZE_MAX` value that is then passed to
   `memcpy` or used as a copy bound, causing a massive out-of-bounds access.
2. **Bypassed checks.** A guard like `if (have - need >= 0)` is always true for
   unsigned `have`/`need`, so an attacker who makes `need > have` slips past it.
3. **Negative loop counts.** `for (size_t i = 0; i < count - 1; i++)` with
   `count == 0` loops about `SIZE_MAX` times, hanging the process or walking off
   the end of an array.
4. The wrong result can also crash the process, contributing to denial of
   service.

# Technical details

Unsigned integer arithmetic in C and C++ is defined to be modular: every
operation is reduced modulo `2^N`, where `N` is the width of the type. So for
`unsigned a, b` with `a < b`, the result of `a - b` is `a - b + 2^N`. This is
not undefined behavior — it is fully specified — which is exactly why it is
dangerous: there is no trap, no warning at runtime, just a quietly enormous
value.

## Signed/unsigned mixing
The bug frequently appears through implicit conversion. In `size_t len; int
delta; len - delta`, the `int` is converted to `size_t` per the usual arithmetic
conversions, so a negative `delta` becomes huge before the subtraction even
happens. Comparisons are affected too: `len - 1 >= 0` is always true because the
left side is unsigned.

## Why the obvious check fails
`if (a - b < 0)` can never fire for unsigned operands, because an unsigned value
is never less than zero. The correct guard is to compare *before* subtracting:
`if (a < b)` / `if (a >= b)`.

# Catching the issue

## Sanitizers
`-fsanitize=unsigned-integer-overflow` (Clang, and GCC) reports unsigned wraps,
including underflow, at runtime. It is not part of the default UBSan set because
intentional wrapping is legal, so enable it deliberately and whitelist code that
wraps on purpose.

## Compiler warnings
`-Wsign-conversion` and `-Wconversion` catch the implicit signed-to-unsigned
conversions that hide most underflows. `-Wtautological-compare` flags
`unsigned < 0` style checks that can never be true.

## Static analysis
clang-tidy, Coverity, PVS-Studio, and CodeQL detect unsigned subtractions whose
operands are not provably ordered, and "always true/false" unsigned comparisons.

## Code review rule
Always test ordering before subtracting unsigned values: write
`if (a >= b) diff = a - b;` rather than subtracting first and checking the
result. Use `ptrdiff_t`/signed types when a difference legitimately needs a
sign.

# How to reproduce

Observe that `remaining` becomes a huge value instead of a sensible small
number, and the `memcpy` would copy gigabytes.

```c
#include <stdio.h>
#include <string.h>

int main(void)
{
    size_t buffer_len = 16;
    size_t offset     = 32;             /* offset past the end of the buffer */

    size_t remaining = buffer_len - offset;   /* underflows: ~SIZE_MAX */

    printf("remaining = %zu\n", remaining);   /* 18446744073709551600 */

    /* memcpy(dst, src, remaining); would read/write far out of bounds. */
    return 0;
}
```

