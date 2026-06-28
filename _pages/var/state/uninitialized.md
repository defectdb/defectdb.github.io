---
title: "Uninitialized variable is used"
author: Maxim Menshikov
layout: defect
permalink: /var/state/uninitialized
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: var.state
group:
   - var
   - state
---
Use of uninitialized variable is invalid

# Impact

Reading a variable before it has been assigned yields whatever bit pattern
happened to occupy that storage. In the best case the value is plausible-looking
garbage that produces wrong results; in the worse case it changes from run to run
or between debug and release builds, making the bug intermittent and hard to
reproduce. When the uninitialized value is later used as an array index, a size,
a loop bound, or a pointer, the consequences escalate from a wrong answer to an
out-of-bounds access or a crash.

# Vulnerability potential

This issue has a real potential to be a vulnerability.

1. An uninitialized pointer or index derived from stack/heap residue can be
   dereferenced or used to address memory, producing out-of-bounds reads and
   writes that lead to memory corruption and potentially remote code execution.
2. If the variable is later copied into a buffer that crosses a trust boundary
   (sent over a socket, written to a file, returned to a caller), it leaks
   whatever previously lived in that memory — stack canaries, pointers, or
   secrets — defeating ASLR and aiding further exploitation.
3. Because the value may differ between builds and runs, security-relevant
   checks (length validation, authorization flags) can pass or fail
   non-deterministically.

# Technical details

In C and C++ reading an object with automatic storage duration before it is
initialized is *undefined behavior*. The compiler is entitled to assume it never
happens, which means optimizers may delete the code path entirely, propagate a
"poison" value, or produce results that contradict any concrete byte pattern you
might expect.

## Storage duration matters
Objects with static or thread storage duration are zero-initialized, so the
defect applies primarily to automatic (stack) and dynamically allocated
(`malloc`) objects. `malloc` returns memory with indeterminate contents;
`calloc` and zero-initializers do not.

## Indeterminate values and traps
For most scalar types the value is merely indeterminate. For types with trap
representations (and notably for `bool` in C++ where any value other than 0/1 is
UB), even reading the variable is undefined, so it is not safe to assume "garbage
but at least a valid value".

# Catching the issue

## Compiler warnings
Build with `-Wall -Wextra -Wuninitialized -Wmaybe-uninitialized` on GCC/Clang
and `/W4` on MSVC. Optimized builds (`-O2`) drive the dataflow analysis that
finds many of these. Treat the warnings as errors with `-Werror`.

## Sanitizers
Clang's `-fsanitize=memory` (MemorySanitizer) is purpose-built for this and
reports use of uninitialized memory at runtime with a stack trace. Valgrind's
Memcheck catches the same class of bug on uninstrumented binaries.

## Static analysis
`clang-tidy`, Coverity, PVS-Studio, and the Clang static analyzer flag
definite-and-likely uninitialized reads, including across function boundaries
that the compiler's local analysis misses. As a coding rule, always initialize
at the point of declaration.

# How to reproduce

Compile with `clang -fsanitize=memory` or run under Valgrind to observe the
uninitialized read; output is unpredictable.

```c
#include <stdio.h>

int main(void) {
    int x;          /* never initialized */
    int arr[4] = {10, 20, 30, 40};

    /* x holds an indeterminate value; using it as an index is UB */
    printf("%d\n", arr[x % 4]);
    return 0;
}
```
