---
title: "Implicit pointer to integer conversion"
author: Maxim Menshikov
layout: defect
permalink: /cast/pointer/integer
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: cast.pointer
group:
   - cast
   - pointer
---
The pointer is implicitly casted to an integer

# Impact

Implicitly converting a pointer to an integer is dangerous mainly when the
integer is narrower than the pointer. On LP64 platforms (Linux/macOS 64-bit) a
pointer is 64 bits but `int` and `long` (on Windows LLP64) are only 32, so
storing a pointer in an `int` discards the high half. If that integer is later
converted back to a pointer, it no longer addresses the original object — the
program dereferences a corrupted address and crashes or, worse, touches the
wrong memory. Even when the value is never converted back, comparisons and
arithmetic on the truncated integer give wrong answers. It is also a portability
trap: code that "works" on a 32-bit build silently breaks on 64-bit.

# Vulnerability potential

The direct security weight is low, but truncation can seed memory-safety bugs.

1. A truncated and reconstituted pointer addresses an unintended object; a write
   through it is effectively an out-of-bounds/arbitrary write whose target
   depends on the high bits that were lost.
2. Storing pointers in too-narrow integers can defeat ASLR reasoning or leak
   partial address bits in serialized data.
3. Most commonly the corrupted pointer just crashes the process (DoS-adjacent),
   but the underlying corruption can be steered in some layouts.

Because triggering a real exploit requires specific layout and round-tripping,
the severity is low rather than high.

# Technical details

C and C++ do not implicitly convert between pointers and integers without a
diagnostic (it requires a cast, and in C++ it is an error). When such a
conversion does happen — through a cast, a `union`, or a sloppy API — the result
is implementation-defined, and only `intptr_t`/`uintptr_t` are guaranteed wide
enough to hold a pointer round-trip.

## Data-model differences

ILP32 (32-bit): `int`, `long`, pointer all 32 bits — truncation hidden. LP64
(64-bit Unix): `int` 32, `long` 64, pointer 64. LLP64 (64-bit Windows): `int`
and `long` 32, pointer 64. Code that assumed `sizeof(long) == sizeof(void*)`
breaks on Windows; code that used `int` breaks everywhere on 64-bit.

## The correct types

Use `uintptr_t`/`intptr_t` (from `<stdint.h>`) for any integer that must hold a
pointer value, and never an `int` or plain `long`.

# Catching the issue

## Compiler

Build with `-Wall -Wextra`; GCC/Clang emit `-Wint-conversion` /
`-Wpointer-to-int-cast` and, on size mismatch, `-Wint-to-pointer-cast`. Promote
them with `-Werror`. MSVC emits C4311/C4312 for pointer truncation. In C++ the
implicit conversion is simply rejected.

## Static analysis

Clang-tidy (`cppcoreguidelines-pro-type-reinterpret-cast`,
`bugprone-*`), Coverity, Cppcheck, and PVS-Studio flag narrowing
pointer-to-integer conversions.

## Review

Whenever a pointer must live in an integer (tagging, hashing, FFI), require
`uintptr_t` and an explicit cast, and document the round-trip.

# How to reproduce

Compile for 64-bit with `-Wall`; observe the warning and that the reconstructed
pointer differs from the original because the high 32 bits were lost.

```c
#include <stdio.h>

int main(void)
{
    int x = 42;
    int *p = &x;

    int truncated = (int)(long)p; /* pointer squeezed into 32-bit int */
    int *q = (int *)(long)truncated;

    printf("orig=%p  round-trip=%p  equal=%d\n",
           (void *)p, (void *)q, p == q);  /* not equal on LP64/LLP64 */
    return 0;
}
```

