---
title: "Unused variable"
author: Maxim Menshikov
layout: defect
permalink: /var/scope/unused
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: var.scope
group:
   - var
   - scope
---
The variable is unused

# Impact

A declared-but-never-used variable is mostly a clarity and maintenance problem:
it adds noise, suggests an intent that the code does not fulfil, and can mask a
real bug. The dangerous variants are when the variable was *supposed* to be used
— a computed result that should have been returned or checked, an error code
that is silently dropped, or a parameter that a refactor stopped wiring through.
In those cases the unused variable is the visible symptom of missing logic. The
storage cost itself is negligible because optimizers remove dead locals.

# Vulnerability potential

In isolation an unused variable has essentially no security relevance — it is a
code smell, not a defect that corrupts state or crosses a trust boundary. The
only meaningful security angle is indirect: an unused return value or error
variable can mean an error or an authorization result was never checked, which
is a real bug, but the vulnerability there belongs to the dropped check, not to
the unused declaration as such.

# Technical details

In C and C++ an unused local variable is well-defined and harmless; the compiler
typically optimizes it away entirely. It usually indicates one of: leftover code
after a refactor, a typo where the wrong variable was used elsewhere, a result
that should have been consumed, or a planned feature that was never finished.

## Deliberately unused entities
Function parameters are often unavoidably unused (interface conformance,
callbacks). Mark them with `(void)param;`, omit the name in C++
(`void f(int /*unused*/)`), or use the `[[maybe_unused]]` attribute (C++17 / C23)
to silence the warning without deleting the declaration.

# Catching the issue

## Compiler warnings
`-Wunused-variable` (included in `-Wall`) on GCC/Clang and `/W4` on MSVC report
unused locals. `-Wunused-parameter` and `-Wunused-but-set-variable` cover the
related cases where a variable is assigned but its value is never read.

## Linters and static analysis
clang-tidy (`misc-unused-parameters`, `clang-analyzer-deadcode.DeadStores`),
Cppcheck, and Coverity flag dead stores and unused declarations, and more
importantly highlight ignored return values from functions marked
`[[nodiscard]]`. Mark functions whose result must be used with `[[nodiscard]]`
so the compiler turns a dropped value into a warning.

# How to reproduce

Compile with `gcc -Wall -Wextra`; the compiler reports `unused variable 'sum'`,
which hides that the computed total is never returned.

```c
#include <stdio.h>

int total(const int *a, int n) {
    int sum = 0;                 /* computed... */
    for (int i = 0; i < n; i++)
        sum += a[i];
    return n;                    /* ...but 'sum' is never used; wrong value returned */
}

int main(void) {
    int data[] = {1, 2, 3};
    printf("%d\n", total(data, 3));
    return 0;
}
```
