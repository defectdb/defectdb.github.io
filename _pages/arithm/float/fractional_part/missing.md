---
title: "Fractional part of floating point variable might be missing"
author: Maxim Menshikov
layout: defect
permalink: /arithm/float/fractional_part/missing
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: arithm.float.fractional_part
group:
   - arithm
   - float
   - fractional_part
---
Fractional part of floating point variable might be missing

# Impact

A division (or other computation) that the author meant to produce a fractional
result is carried out entirely in integer arithmetic, so the fractional part is
truncated and lost before it is ever assigned to a floating-point variable. The
classic shape is `double r = 1 / 2;`, where `1 / 2` is computed as integers,
yields `0`, and only then is converted to `0.0`. The program runs without error
but the value is wrong — a ratio collapses to zero, a percentage rounds away, an
interpolation snaps to a grid point. The bug is silent and easy to miss because
the destination type is floating point, which lulls the reader into assuming the
math was too.

# Vulnerability potential

This defect has little direct security relevance. It is a correctness bug: the
wrong numeric value is computed, but no memory is corrupted and nothing traps.
The only realistic security angle is indirect — if the truncated value feeds a
safety, financial, or access decision (for example a rate limit, a fee, or a
threshold computed as an integer ratio), the error could produce a wrong
decision. Absent such a use, the impact is purely functional.

# Technical details

The cause is C/C++ expression typing: the type of an operation is determined by
its operands, not by where the result is stored. If both operands of `/` are
integers, integer division is performed and the result is an integer; the
fractional part is discarded by truncation toward zero. The conversion to
`double` happens only afterward, on the already-truncated value.

## When the conversion happens
`double r = 7 / 2;` evaluates `7 / 2` in `int` to `3`, then converts `3` to
`3.0`. To get `3.5`, at least one operand must be floating point: `7.0 / 2`,
`7 / 2.0`, or `(double)a / b`. A suffix works for literals (`7.0`, `2.0f`); for
variables use a cast on one operand. Note that `(double)(a / b)` is still wrong —
the cast is applied after the integer division.

## Related forms
The same truncation bites `int a, b; double r = a / b;`, percentage code like
`100 * part / whole` where `part < whole`, and mixed expressions where an
integer subexpression is evaluated first. It is distinct from floating-point
rounding error: here the fractional part is not rounded, it is never computed.

# Catching the issue

## Compiler warnings
Clang's `-Wint-in-bool-context` and the broader `-Wconversion` family can hint
at suspicious integer-to-floating conversions, though most compilers do not warn
about this specific pattern by default. PVS-Studio has a dedicated diagnostic
(V636) for "an expression was implicitly cast from integer to floating type,
consider using an explicit cast to avoid loss of the fractional part".

## Static analysis
PVS-Studio, Coverity, and CodeQL detect integer division whose result is
immediately stored in or used as a floating-point value. clang-tidy's
`bugprone-integer-division` flags integer division used in a floating-point
context.

## Code review
Whenever a result is meant to be fractional, make at least one operand floating
point at the source of the division, and prefer an explicit cast on an operand
(`(double)a / b`) over relying on the destination type. Unit tests that check a
known non-integer ratio catch it immediately.

# How to reproduce

Observe that `bad` prints `0` while `good` prints `0.5`, even though both are
stored in a `double`.

```c
#include <stdio.h>

int main(void)
{
    int a = 1, b = 2;

    double bad  = a / b;            /* integer division -> 0, then 0.0 */
    double good = (double)a / b;    /* one operand is double -> 0.5    */

    printf("bad  = %g\n", bad);     /* 0   */
    printf("good = %g\n", good);    /* 0.5 */
    return 0;
}
```

