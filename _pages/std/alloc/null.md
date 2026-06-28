---
title: "Allocation of zero size block"
author: Maxim Menshikov
layout: defect
permalink: /std/alloc/null
arch:
   - native
vulnerability:
   - Medium
ddos:
   - None
group_full: std.alloc
group:
   - std
   - alloc
---
Argument of malloc is 0, which is probably a mistake

# Impact

``malloc(0)`` (and ``calloc(0, n)``, ``realloc(p, 0)``) is permitted by the C
standard but its result is implementation-defined: the call may return either a
null pointer **or** a unique, non-null pointer that must still be passed to
``free`` yet points at zero usable bytes. A zero-size request almost always means
a length calculation produced ``0`` by mistake — an empty input, an underflowed
``size - offset``, a multiplication that wrapped, or a loop that never set the
count. Two opposite failure modes follow. If the program assumes ``malloc``
returns non-null on success, the null return from a zero request is mistaken for
an out-of-memory failure or, worse, dereferenced. If the program assumes it got a
real buffer, it writes to a pointer that legally addresses nothing, producing an
immediate heap overflow.

# Vulnerability potential

The danger is not the zero allocation itself but the corrupted size arithmetic
that usually produces it, and the writes that follow.

1. If the zero came from an integer overflow or underflow in a size computation
   (``count * size`` wrapping to 0, ``end - start`` going negative), any
   subsequent write using the *intended* larger length overflows the
   minimal/zero-byte allocation — a heap buffer overflow that is a common
   exploitation primitive.
2. Code that treats the legitimate ``NULL`` from ``malloc(0)`` as success and
   dereferences it triggers a null-pointer access.
3. Inconsistent handling across platforms (null on one libc, non-null on
   another) yields bugs that only surface on some targets, complicating review.

# Technical details

The standard (C11 7.22.3) says that if the requested size is zero the behavior is
implementation-defined: the return is either a null pointer or a pointer suitable
for ``free`` that may not be dereferenced.

## glibc / musl

Return a unique non-null pointer (glibc returns the minimum chunk, 16/32 bytes of
metadata-backed but zero *usable* bytes). Writing through it corrupts adjacent
heap metadata.

## Other implementations

Some embedded and historical allocators return ``NULL`` for a zero size, so the
same code path that "worked" elsewhere now looks like allocation failure.
``realloc(p, 0)`` is even murkier: it may free ``p`` and return ``NULL``, or
return a minimal block, so using its result as if ``p`` were resized is unsafe;
C23 deprecates this form.

# Catching the issue

## Static analysis

Clang Static Analyzer, Coverity, PVS-Studio and PC-lint warn on a
``malloc``/``calloc`` whose size argument can be zero, and on use of a
possibly-null allocation result. Pair this with checks for the integer
overflow/underflow that usually feeds the zero size.

## Runtime

AddressSanitizer catches a write into a zero-size allocation as a heap overflow,
and reports use of the ``realloc(p, 0)`` result. Defensively, validate sizes
before allocating: reject or special-case ``size == 0`` explicitly rather than
relying on implementation-defined behavior, and always check the returned
pointer.

# How to reproduce

Run under AddressSanitizer (``-fsanitize=address``); the write into the zero-byte
allocation is reported as a heap-buffer-overflow.

```c
#include <stdlib.h>
#include <stdio.h>

int main(void)
{
    size_t n = 0;            /* came from a bad length calculation */
    char  *p = malloc(n);    /* may return NULL or a 0-byte block */

    printf("p = %p\n", (void *)p);
    p[0] = 'x';              /* null deref or heap overflow */
    free(p);

    return 0;
}
```
