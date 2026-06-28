---
title: "The index is out of range"
author: Maxim Menshikov
layout: defect
permalink: /array/index/out_of_range
arch:
   - native
vulnerability:
   - High
ddos:
   - Medium
group_full: array.index
group:
   - array
   - index
---
The array access operation uses index out of appropriate range

# Impact

Indexing an array past its valid range accesses memory that does not belong to
the element being addressed. In C and C++ this is undefined behaviour: a read
returns whatever bytes happen to live there (often leaking adjacent variables,
heap metadata, or stack contents), and a write corrupts a neighbouring object,
heap bookkeeping, or a stack return address. The visible effect ranges from
nothing at all, to silently wrong results, to an immediate crash, depending on
the memory layout — which makes the bug intermittent and hard to reproduce.

# Vulnerability potential

Out-of-bounds access is one of the most exploited defect classes (CWE-787 / 
CWE-125, perennially in the top of the CWE Top 25).

1. An out-of-bounds *write* (classic buffer overflow) can overwrite a return
   address, function pointer, or vtable, enabling control-flow hijack and remote
   code execution.
2. An out-of-bounds *read* can disclose secrets from adjacent memory — keys,
   tokens, ASLR-defeating pointers — as in Heartbleed (CVE-2014-0160).
3. When the index is attacker-controlled, the access becomes an arbitrary
   read/write primitive at a controlled offset.
4. Crashes from such accesses are also a straightforward Denial-of-Service
   vector.

# Technical details

C arrays carry no length; `a[i]` is defined as `*(a + i)` with no bounds check.
The standard permits forming a pointer to one element *past* the end (for loop
termination) but dereferencing it, or any index beyond that, is undefined.
Because the address is computed as `base + i * sizeof(elem)`, a large or wrapped
index can land anywhere in the address space.

## Common causes

Off-by-one loops (`i <= n` instead of `i < n`), using `sizeof(ptr)` instead of
the element count after array-to-pointer decay, trusting an externally supplied
length, and integer overflow in the index expression.

## C++ containers

`std::vector::operator[]` and `std::array::operator[]` are also unchecked; use
`.at()` for a bounds-checked alternative that throws `std::out_of_range`.
Iterating past `end()` is the iterator-shaped version of the same bug.

# Catching the issue

## Sanitizers

AddressSanitizer (`-fsanitize=address`) catches heap, stack, and global
out-of-bounds accesses with a symbolized report. UBSan's `-fsanitize=bounds`
checks accesses where the array bound is statically known.

## Compiler / hardening

Build with `-Wall -Wextra -Warray-bounds` and `-D_FORTIFY_SOURCE=2 -O2`, which
adds runtime checks to many libc calls. GCC/Clang `-fsanitize=bounds` and
`-fstack-protector-strong` add further coverage.

## Static analysis

Clang Static Analyzer, Cppcheck, Coverity, and PVS-Studio detect many constant
and loop-bounded overruns at analysis time.

## Code review / design

Pass lengths alongside pointers, prefer `std::span`/`std::vector` with `.at()`,
and centralise bounds checks rather than scattering raw indexing.

# How to reproduce

Compile with `-fsanitize=address` and run; ASan reports a stack-buffer-overflow
at the write to `a[10]`.

```c
#include <stdio.h>

int main(void)
{
    int a[10];

    /* Valid indices are 0..9; index 10 is one past the end. */
    a[10] = 42;            /* out-of-bounds write */
    printf("%d\n", a[10]); /* out-of-bounds read  */
    return 0;
}
```

