---
title: "Format argument is redundant"
author: Maxim Menshikov
layout: defect
permalink: /std/fmt/arg/redundant
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: std.fmt.arg
group:
   - std
   - fmt
   - arg
---
Format does not define a parameter for the argument

# Impact

The opposite of a missing argument: the call supplies more arguments than the
format string consumes (e.g. ``printf("%d\n", x, y)``). Unlike most format
mismatches, this case is well defined — the C standard says excess arguments are
evaluated and then ignored. There is no crash, no garbage output and no memory
unsafety. The real cost is that it almost always signals a logic mistake: a
dropped or mistyped conversion specifier, an argument left over after editing
the format, or a misunderstanding of which values are actually printed. The
extra argument's side effects (if it is a function call) still occur, but its
formatted value silently disappears.

# Vulnerability potential

This defect has essentially no direct security relevance. Per ISO C the surplus
arguments are merely evaluated and discarded, so there is no out-of-bounds read,
no indeterminate value and no memory corruption. Its only security-adjacent risk
is indirect: the missing specifier it usually points to may mean that data the
programmer intended to log or display is in fact absent, which can hamper
auditing or incident analysis.

# Technical details

A variadic callee reads only as many arguments as its format string directs.
Arguments beyond that are still pushed onto the stack or placed in registers by
the caller per the platform ABI, occupying space and incurring evaluation cost,
but ``printf`` never issues a ``va_arg`` for them, so they are simply never
looked at. Because nothing reads past the consumed arguments, the operation is
safe regardless of the surplus arguments' types or count.

# Catching the issue

## Compilers

GCC and Clang report ``warning: too many arguments for format`` under
``-Wformat`` (part of ``-Wall``), and ``-Wformat=2`` tightens the analysis.
Apply ``__attribute__((format(printf, n, m)))`` to custom wrappers so they are
checked the same way, and use ``-Werror=format`` to make the mismatch fatal.

## Static analysis

Clang-Tidy, Coverity and PVS-Studio all flag a format string with fewer
conversions than arguments, which is the most reliable way to catch the
underlying logic error the redundant argument hints at.

# How to reproduce

Compile with ``-Wformat``; the extra argument compiles and runs cleanly but the
warning points at the dropped conversion.

```c
#include <stdio.h>

int main(void)
{
    int x = 1, y = 2;

    /* Only one conversion: y is evaluated and silently ignored. */
    printf("%d\n", x, y);

    return 0;
}
```
