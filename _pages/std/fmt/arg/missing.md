---
title: "Format argument is not present"
author: Maxim Menshikov
layout: defect
permalink: /std/fmt/arg/missing
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: std.fmt.arg
group:
   - std
   - fmt
   - arg
---
Format defines a parameter which is not present in argument string

# Impact

When a conversion specification in the format string has no matching argument
(e.g. ``printf("%d %d\n", x)``), the formatting function still tries to fetch a
value for it. It reads whatever happens to occupy the next argument slot — a
scratch register or a stack location that was never set up for this call. The
fetched value is indeterminate, so at best the output is garbage. At worst, a
pointer-consuming specifier such as ``%s`` dereferences an arbitrary address and
prints memory until it hits a ``NUL`` byte, or ``%n`` writes through a bogus
pointer. The C standard makes the whole call undefined behavior, so the range of
outcomes runs from silently wrong output to an immediate crash.

# Vulnerability potential

This issue has a clear security dimension whenever the missing argument feeds a
pointer-consuming specifier.

1. ``%s`` (and ``%ls``) with a missing argument reads an indeterminate pointer
   and dumps whatever memory it points at, which can leak stack contents, heap
   addresses, stack canaries or other secrets.
2. ``%n`` with a missing argument writes the running output count through an
   uncontrolled pointer, corrupting memory and potentially enabling control-flow
   hijack.
3. Dereferencing the indeterminate pointer frequently faults, terminating the
   process and contributing to denial of service.

# Technical details

C variadic functions carry no information about how many arguments were actually
passed; the callee trusts the format string to tell it. ``printf`` walks the
format, and for each conversion it issues a ``va_arg`` read of the requested
type. ``va_arg`` simply advances through the argument area defined by the
platform ABI — there is no bounds check and no end marker.

On the x86-64 System V ABI the first integer/pointer arguments arrive in
registers (``rdi``, ``rsi``, ``rdx``, ``rcx``, ``r8``, ``r9``) and the rest on
the stack; a missing argument therefore yields a leftover register or an
arbitrary stack word. The exact garbage value, and whether the call crashes,
depends on register/stack state at the call site, so the defect is highly
non-deterministic and may pass testing yet fail in production.

# Catching the issue

## Compilers

GCC and Clang diagnose the mismatch at compile time with ``-Wformat`` (enabled
by ``-Wall``); ``-Wformat=2`` is stricter. For your own variadic wrappers,
annotate them with ``__attribute__((format(printf, n, m)))`` so the same checks
apply. Promote the warning to an error with ``-Werror=format``.

## Static and dynamic analysis

Clang-Tidy, Coverity, PVS-Studio and PC-lint flag format/argument count
mismatches. At runtime, glibc's ``_FORTIFY_SOURCE`` adds some checking, and
AddressSanitizer may catch the resulting bad dereference, though neither
reliably detects a plain missing scalar argument.

# How to reproduce

Build with warnings on (``-Wformat``) to see the diagnostic; run to observe
garbage output, or a crash on the ``%s`` line.

```c
#include <stdio.h>

int main(void)
{
    int x = 42;

    /* Two conversions, one argument: the second %d reads garbage. */
    printf("%d %d\n", x);

    /* %s with no argument dereferences an indeterminate pointer. */
    printf("%s\n");

    return 0;
}
```
