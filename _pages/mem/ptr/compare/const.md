---
title: "Comparing pointer to a constant is strange"
author: Maxim Menshikov
layout: defect
permalink: /mem/ptr/compare/const
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: mem.ptr.compare
group:
   - mem
   - ptr
   - compare
---
Comparing pointer to a constant is strange as usually they are not constant

# Impact

Comparing a pointer against a non-null integer constant — `if (p == 0x1000)`,
`if (p == 1)`, `if (p == -1)` — is suspicious because, outside of a few
documented sentinels, pointer values are decided at runtime by the allocator,
loader, and ASLR, so they are not portable constants. Such a comparison almost
never does what the author intended: it may be a hard-coded address that is only
valid on one platform or one build, a `(void *)-1` sentinel that should have been
written symbolically (`MAP_FAILED`), or a typo where `==` was meant to compare
two pointers. The practical impact is a branch that is taken under the wrong
conditions, leading to logic errors that surface only on certain platforms or
builds.

# Vulnerability potential

The security relevance is limited and indirect — this is mainly a portability
and correctness smell.

1. If a magic address is used as a sentinel for "invalid"/"sentinel" and a real
   allocation ever lands on that address (or the constant is wrong for the
   platform), the check passes or fails incorrectly, which can bypass a guard
   and allow a bad pointer to be used.
2. Hard-coding an address can reflect an assumption that ASLR is disabled;
   baking such assumptions into code weakens defense-in-depth.

Beyond these edge cases there is no direct corruption or DoS path, so the
severity is low.

# Technical details

In C/C++ a pointer may be compared for equality against a null pointer constant
(`0`, `NULL`, `nullptr`); comparing against any other integer requires an
explicit cast and is only meaningful for known, ABI-defined addresses (e.g.
memory-mapped registers in embedded code, or sentinels like `MAP_FAILED` which
is `(void *)-1`).

## Legitimate vs accidental uses

Legitimate: a comparison against `(void *)-1` for `mmap`/`sbrk` failure, or
against a fixed hardware register address in a freestanding/embedded target.
These should be written through a named symbolic constant, not a bare literal.

Accidental: comparing a pointer to a small integer like `1` or `0x1000` usually
indicates confusion between a pointer and an index/flag, or a sentinel that
should be `NULL`.

## Why runtime addresses are not constants

Heap addresses come from the allocator; stack addresses from the call chain;
code/data addresses are relocated by the loader and randomized by ASLR. None are
stable across runs, so equality against a literal is fragile by construction.

# Catching the issue

## Compiler

GCC/Clang warn on pointer/integer comparisons without a cast
(`-Wint-conversion`, and in C++ such a comparison is an error). Build with
`-Wall -Wextra` and do not silence these with casts unless the address is a
documented constant.

## Static analysis

Clang-tidy, Cppcheck, Coverity, and PVS-Studio flag comparisons of pointers
against magic numeric constants and suggest symbolic sentinels.

## Review

Replace bare address literals with named constants (`#define UART0_BASE
0x4000C000`), use the platform-provided sentinel macros (`MAP_FAILED`,
`INVALID_HANDLE_VALUE`), and reserve pointer-to-null comparison for null checks.

# How to reproduce

Compile with `-Wall -Wextra`; the compiler warns about comparison between
pointer and integer. The branch is effectively never taken as intended.

```c
#include <stdlib.h>
#include <stdio.h>

int main(void)
{
    int *p = malloc(sizeof *p);

    /* Intends to detect a "special" pointer, but 0x1000 is an
       arbitrary runtime-meaningless constant. */
    if (p == (int *)0x1000) {
        puts("special address");
    } else {
        puts("ordinary allocation");  /* essentially always taken */
    }

    free(p);
    return 0;
}
```

