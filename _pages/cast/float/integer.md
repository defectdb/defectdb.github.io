---
title: "Implicit float to integer conversion"
author: Maxim Menshikov
layout: defect
permalink: /cast/float/integer
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: cast.float
group:
   - cast
   - float
---
The floating point variable is implicitly casted to an integer

# Impact

Implicitly converting a floating-point value to an integer truncates toward
zero, silently discarding the fractional part, and is undefined behaviour when
the value does not fit in the target type. `3.99` becomes `3`, `-1.5` becomes
`-1`, and a value larger than `INT_MAX` (or any NaN/infinity) produces a
nonsensical result on most platforms with no diagnostic. The damage is usually
wrong arithmetic: lost precision in financial or measurement code, off-by-one
counts, or a computed size/index that is far from what the floating-point
expression intended. Because the conversion is implicit, the author may not even
realise a narrowing happened.

# Vulnerability potential

Direct security impact is limited, but float-to-int conversions feeding sizes or
indices can become memory-safety bugs.

1. If a float is converted to an integer used as an allocation size or array
   index, the truncation (or the out-of-range UB) can yield an unexpectedly
   small, large, or garbage value, leading to under-allocation followed by an
   out-of-bounds write.
2. Converting an out-of-range or NaN float to an integer is undefined behaviour;
   the resulting "implementation-defined garbage" (often `INT_MIN` /
   `0x80000000`) used in a length calculation can drive a buffer overflow.
3. In non-security code the usual outcome is simply incorrect results, so the
   overall severity is low.

# Technical details

In C/C++ converting a floating type to an integer type drops the fractional part
(rounds toward zero). If the truncated value cannot be represented in the
destination type, the behaviour is undefined (C17 6.3.1.4); in practice it
yields a platform-specific value and may raise the FE_INVALID floating-point
exception. NaN and ±infinity have no integer representation at all.

## Truncation vs rounding

`(int)x` truncates, it does not round: `(int)2.999` is `2`, not `3`. When
rounding is intended use `lround`, `llround`, `rint`, or `nearbyint` and convert
their result, or add `0.5` deliberately (mindful of sign and edge cases).

## Range and special values

`double` can represent magnitudes far beyond any integer type; converting such a
value, or a NaN/infinity, is UB. Check the range first (e.g. `x >= 0 && x <=
(double)SIZE_MAX`) before converting a float to a size.

# Catching the issue

## Compiler

GCC/Clang warn with `-Wfloat-conversion` (part of `-Wconversion`) on implicit
narrowing from floating to integer; `-Wbad-function-cast` catches some cases.
Enable `-Wall -Wextra -Wconversion` and consider `-Werror`. In C++,
brace-initialising an integer from a float (`int i{3.5}`) is ill-formed, which
catches the narrowing at compile time.

## Sanitizers

UBSan's `-fsanitize=float-cast-overflow` traps at runtime when a float is out of
the integer's representable range (including NaN/inf), pinpointing the bad
conversion.

## Static analysis

Clang-tidy (`bugprone-narrowing-conversions`,
`cppcoreguidelines-narrowing-conversions`), Coverity, and PVS-Studio flag
implicit float-to-integer narrowing.

## Review

Make every float→int conversion explicit, choose an explicit rounding function
when rounding is meant, and range-check before converting a float into any
size/index.

# How to reproduce

Compile with `-Wconversion`; observe the warning, and at runtime the fractional
part is dropped and the out-of-range value is undefined.

```c
#include <stdio.h>

int main(void)
{
    double price = 3.99;
    int    cents = price;        /* implicit truncation -> 3, not 4 */

    double huge  = 1e20;
    int    bad   = huge;         /* out of int range: undefined behaviour */

    printf("cents=%d  bad=%d\n", cents, bad);
    return 0;
}
```

