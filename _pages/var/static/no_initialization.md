---
title: "Static variable must be initialized"
author: Maxim Menshikov
layout: defect
permalink: /var/static/no_initialization
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: var.static
group:
   - var
   - static
---
Missing initializer of a static variable is suspicious

# Impact

A static or global variable without an explicit initializer is zero-initialized
by the language, so the immediate effect is not corruption but ambiguity: a
reader cannot tell whether zero is the intended starting value or whether an
initializer was forgotten. When the intended initial value is *not* zero — a
sentinel like `-1`, a non-null default pointer, a configuration default — the
missing initializer is a latent logic bug. The variable will read as `0`/`NULL`,
which may silently mean "uninitialized", "first call", or an invalid state the
rest of the code does not expect.

# Vulnerability potential

Direct security relevance is low, because the value is well-defined (zero) rather
than indeterminate. The realistic risk is logical: a security-relevant static
flag intended to default to a *safe* non-zero value (for example a
`min_tls_version` or an `initialized` guard) that instead defaults to zero can
leave a feature disabled or a check skipped. Such a misconfiguration could
weaken a protection, but the language guarantee of zero-initialization rules out
the indeterminate-value class of memory-safety bugs.

# Technical details

In C and C++ objects with static storage duration (file-scope variables and
function-local `static`s) are guaranteed to be zero-initialized before any
dynamic initialization runs — pointers become null, arithmetic types become
zero, aggregates are zeroed member-wise. This is fundamentally different from
automatic (stack) variables, which are left indeterminate.

## Why it is still flagged
The defect is a style and intent signal, not undefined behavior. Many coding
standards (MISRA, and various house styles) require every object to have an
explicit initializer so that the intended value is visible and a forgotten
initializer is not silently absorbed into the zero default.

## C++ subtleties
For non-trivial types, default-initialization of a namespace-scope object runs
the default constructor during dynamic initialization, and the *static
initialization order fiasco* can make one translation unit observe another's
static before its constructor has run. An explicit, constant initializer
(`constinit`, constant expressions) avoids both the ambiguity and the ordering
hazard.

# Catching the issue

## Compiler and standards checkers
MISRA/AUTOSAR checkers (Coverity, PVS-Studio, Cppcheck with the MISRA add-on,
Parasoft) report missing explicit initializers where the active standard
requires them. clang-tidy's `cppcoreguidelines-*` checks encourage explicit
initialization.

## C++ ordering hazards
For cross-TU initialization order, use Clang's `-Wglobal-constructors` to find
dynamic initializers, prefer `constinit`/`constexpr` for compile-time constants,
and use the function-local-static ("Meyers singleton") idiom when lazy,
ordered initialization is needed.

# How to reproduce

The intended sentinel is `-1`, but without an initializer the static reads as 0,
so the "not yet computed" guard never triggers.

```c
#include <stdio.h>

static int cached_result;   /* meant to start at -1, but is zero-initialized */

int compute(void) {
    if (cached_result == -1)        /* never true: it is 0, not -1 */
        cached_result = 42;          /* expensive computation, here skipped */
    return cached_result;
}

int main(void) {
    printf("%d\n", compute());      /* prints 0, not 42 */
    return 0;
}
```
