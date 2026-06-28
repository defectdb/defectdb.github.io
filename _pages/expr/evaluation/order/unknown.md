---
title: "Unknown evaluation order"
author: Maxim Menshikov
layout: defect
permalink: /expr/evaluation/order/unknown
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: expr.evaluation.order
group:
   - expr
   - evaluation
   - order
---
Parts of expression might be evaluated in unexpected order

# Impact

C and C++ do not, in general, fix the order in which the operands of an
expression are evaluated, nor when the side effects of those operands take place.
When a single expression both reads and writes the same object, or writes it
twice, without an intervening *sequence point* (C) / *sequencing* relation
(C++11+), the result depends on choices the compiler is free to make. Two
distinct hazards follow. If the conflicting accesses are *unsequenced*, the
program has undefined behaviour and the compiler may produce literally anything.
If the order is merely *unspecified* (e.g. which function argument is evaluated
first), the program is legal but its result varies between compilers, optimization
levels, and releases. Either way the code computes different answers in different
builds, and the bug typically hides until a toolchain change exposes it.

# Vulnerability potential

Order-of-evaluation defects are a genuine, if subtle, security concern because
they sit on undefined behaviour and on non-deterministic argument evaluation.

1. **Undefined behaviour as an exploit surface.** Unsequenced modification of an
   object is UB; modern optimizers assume UB cannot happen and may delete checks
   or transform surrounding code in ways that introduce out-of-bounds access or
   remove a bounds test, converting a "harmless" expression into a memory-safety
   hole.
2. **Order-dependent resource handling.** When the unspecified order governs side
   effects — two arguments that each allocate, lock, or advance an iterator — a
   compiler change can reorder them into a double-free, a leak, or a lock taken in
   the wrong order, the latter being a deadlock (DoS) primitive.
3. **Inconsistent validation.** If a security check and the value it guards are
   read in an unspecified order, the check may use a different value than the one
   later used, producing a time-of-check/use mismatch.

# Technical details

The language defines a partial ordering on evaluations. Pre-C11/C++11 this was
phrased with *sequence points*; C++11 replaced it with the *sequenced-before*
relation. The rule: if two side effects on the same scalar object, or a side
effect and a value computation using it, are *unsequenced*, the behaviour is
undefined; if they are *indeterminately sequenced* (one before the other but you
don't know which), the result is unspecified.

## Classic offenders
- ``i = i++ + 1;`` and ``a[i] = i++;`` — the object ``i`` is modified and read
  with no sequencing between them: undefined.
- ``f(g(), h());`` — ``g`` and ``h`` are *indeterminately sequenced*; either may
  run first. Until C++17 the same was true of operands like ``a() + b()``.
- ``printf("%d %d\n", i++, i++);`` — argument evaluation order is unspecified, so
  the two increments can be observed in either order.

## Standard version matters
C++17 tightened several rules: it now sequences the right operand of assignment
before the left, fixes the order of postfix expressions and subscripting, and
orders the operands of shift and member-access operators. Function *argument*
evaluation, however, remains unsequenced/unspecified even in C++17/20, and C still
leaves argument order unspecified. So whether a given expression is a defect can
depend on the exact ``-std=`` the project compiles with.

# Catching the issue

Compile with ``-Wsequence-point`` (GCC) / ``-Wunsequenced`` (Clang), both enabled
by ``-Wall``, which catch the textbook ``i = i++`` family. clang-tidy
(``bugprone-unsequenced``), cppcheck, PVS-Studio (V567), Coverity, and MISRA C
Rules 13.2/1.3 flag unsequenced or order-dependent expressions. UBSan does not
have a dedicated unsequenced check, but compiling the *same* source with two
different compilers (GCC and Clang) and at different optimization levels and
diffing the results is a practical way to surface order-dependence the warnings
miss. The durable fix is stylistic: split such expressions into separate
statements with explicit sequencing, never modify an object more than once
between sequence points, and never rely on the order in which function arguments
are evaluated.

# How to reproduce

Observe that the two ``i++`` arguments are evaluated in an unspecified order, so
the printed pair and the final value of ``i`` differ across compilers; the first
expression is outright undefined. Build with ``-Wall``.

```c
#include <stdio.h>

int main(void) {
    int i = 0;
    int x = i++ + i++;          /* undefined: i modified twice, unsequenced */
    printf("x = %d\n", x);

    int j = 0;
    printf("%d %d\n", j++, j++); /* unspecified order: "0 1" or "1 0" */
    return 0;
}
```

