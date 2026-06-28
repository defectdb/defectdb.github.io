---
title: "Argument type does not match the format string"
author: Maxim Menshikov
layout: defect
permalink: /std/fmt/arg/invalid_format
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
Format argument has wrong type

# Impact

When the type of an argument disagrees with its conversion specifier — passing a
``double`` to ``%d``, an ``int`` to ``%s``, or a 32-bit ``int`` to ``%ld`` on an
LP64 platform — the formatting function decodes the argument bytes according to
the specifier, not the value actually passed. The C standard declares this
undefined behavior. Consequences range from wrong numbers (the integer/floating
register files and operand sizes do not line up) to reading too many or too few
bytes off the argument area, which desynchronizes every later conversion. The
dangerous case is a specifier that expects a pointer (``%s``, ``%n``, ``%p``)
being handed an integer or vice versa: the function then treats an arbitrary
integer as an address and dereferences it.

# Vulnerability potential

The security impact tracks how badly the mismatch confuses argument decoding.

1. ``%s`` applied to a non-pointer argument dereferences attacker-influenceable
   integer data as an address, leaking memory contents or crashing the process.
2. ``%n`` applied to a non-pointer argument performs a write through that bogus
   address, a memory-corruption primitive.
3. A width mismatch (e.g. ``%d`` for a ``long`` or ``double``) shifts the
   reading position for subsequent conversions, so later ``%s``/``%n`` pick up
   misaligned values and inherit the same leak/corruption risks.
4. Even when no pointer is involved, the resulting wrong values can corrupt
   downstream logic or crash, contributing to denial of service.

# Technical details

Variadic arguments are subject to the default argument promotions, but those
promotions do not unify *all* types: floating-point values travel in the SSE
register file (or the FP stack) while integers travel in general-purpose
registers, and 64-bit and 32-bit integers occupy different operand widths. A
specifier tells the callee which register class and width to read.

## Integer width and length modifiers

On LP64 (Linux/macOS), ``int`` is 32-bit and ``long``/pointer are 64-bit, so
``%d`` for a ``long`` reads only the low half and the converse over-reads. On
LLP64 (Windows), ``long`` is 32-bit, so the correct modifier differs by
platform; ``size_t`` needs ``%zu`` and ``ptrdiff_t`` needs ``%td`` precisely to
avoid this trap.

## Float vs integer register class

On x86-64 System V, ``printf("%d", 3.0)`` reads a general-purpose register that
the caller never loaded (the ``double`` went to ``xmm0``), so the printed value
is unrelated garbage.

# Catching the issue

## Compilers

``-Wformat`` (in ``-Wall``) checks each argument's type against its specifier;
``-Wformat=2`` and ``-Wformat-nonliteral`` extend coverage. Mark variadic
wrappers with ``__attribute__((format(printf, n, m)))`` and build with
``-Werror=format`` to fail the build on any mismatch.

## Static and dynamic analysis

Clang-Tidy, Coverity, PVS-Studio and PC-lint diagnose type/specifier mismatches.
AddressSanitizer/UBSan can catch the resulting bad dereference at runtime, and
glibc's ``_FORTIFY_SOURCE`` adds limited format checking.

# How to reproduce

Compile with ``-Wformat`` to see the diagnostics; run to observe garbage from
the ``%d``/``double`` mix and a likely crash from ``%s`` on an integer.

```c
#include <stdio.h>

int main(void)
{
    double d = 3.5;
    int    n = 0x41414141;

    printf("%d\n", d);   /* int specifier, double argument */
    printf("%s\n", n);   /* string specifier, int argument: bad deref */

    return 0;
}
```
