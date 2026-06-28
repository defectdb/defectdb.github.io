---
title: "Unreasoned pointer arithmetics"
author: Maxim Menshikov
layout: defect
permalink: /arithm/ptr/unreasoned
arch:
   - native
vulnerability:
   - Medium
ddos:
   - None
group_full: arithm.ptr
group:
   - arithm
   - ptr
---
Pointer arithmetics is used without reason

# Impact

Pointer arithmetic used without a clear, documented reason — adding magic
offsets to a pointer, casting between unrelated pointer types and stepping
through, or hand-walking a structure instead of using its fields — is fragile
and easy to get wrong. The immediate impact is usually a correctness problem:
the computed address points at the wrong member, at padding, or just past an
array. But pointer arithmetic is also the direct mechanism behind out-of-bounds
reads and writes, so an unreasoned offset that is off by even one element can
corrupt adjacent memory, leak neighbouring data, or crash the process. Because
the intent is unclear, such code is also hard to review and tends to break
silently when types, sizes, or alignment change.

# Vulnerability potential

Unconstrained pointer arithmetic is a well-known source of memory-safety
vulnerabilities (CWE-119, CWE-823).

1. **Out-of-bounds access.** A wrong or attacker-influenced offset moves the
   pointer outside its object; the subsequent read leaks adjacent memory (an
   info-leak primitive) and the write corrupts it (a path to control-flow
   hijack and RCE).
2. **Off-by-one and scaling mistakes.** Forgetting that `p + n` advances by `n *
   sizeof(*p)` bytes, or mixing element and byte offsets, lands the pointer one
   element or many bytes off, overwriting metadata such as heap or saved-pointer
   fields.
3. **Undefined behavior the optimizer exploits.** Computing a pointer outside an
   array (other than one-past-the-end) is undefined; the compiler may assume it
   cannot happen and drop a bounds check.
4. **Crashes.** A wild address dereference faults and terminates the process,
   contributing to denial of service.

# Technical details

In C and C++, adding an integer to a pointer scales by the size of the pointee:
`p + n` is `(char *)p + n * sizeof(*p)`. This is convenient but means the same
numeric offset has different effects depending on the pointer's type, and a cast
that changes the type silently changes the stride.

## What the standard allows
Pointer arithmetic is only defined within a single array object (and one element
past its end). Forming a pointer before the start, or more than one past the
end, is undefined behavior even if it is never dereferenced. Subtracting two
pointers is defined only when they point into the same array, and the result is
in elements, not bytes.

## Where unreasoned arithmetic comes from
Typical instances: walking a struct by adding byte offsets instead of naming its
members (which ignores alignment and padding the compiler chose), casting a
struct pointer to `char *` and back with hand-computed offsets, treating a
2-D array as flat with a manually computed index, or doing arithmetic on a
`void *` (a GCC extension that treats its size as 1 and is non-portable). In each
case the "reason" — a layout assumption — is implicit and unverified, so a
change in type, packing, or platform breaks it.

## Aliasing
Casting between unrelated pointer types and dereferencing also violates the
strict-aliasing rule, which is separate undefined behavior the optimizer may act
on.

# Catching the issue

## Sanitizers
AddressSanitizer (`-fsanitize=address`) catches out-of-bounds reads and writes
that result from bad pointer arithmetic, reporting the offending address and the
nearest object. UBSan's `-fsanitize=pointer-overflow` flags pointer arithmetic
that overflows or leaves the object, and `-fsanitize=alignment` catches
misaligned accesses created by hand-rolled offsets.

## Static analysis
Clang Static Analyzer, clang-tidy (`cppcoreguidelines-pro-bounds-pointer-arithmetic`
forbids pointer arithmetic outside of array subscripting), Coverity, PVS-Studio,
and CodeQL flag suspicious or unbounded pointer math.

## Compiler warnings
`-Wstrict-aliasing`, `-Wcast-align`, and `-Warray-bounds` catch related
mistakes; `-Wpointer-arith` warns about arithmetic on `void *` and function
pointers.

## Design rules
Prefer named struct members, array indexing with checked bounds, `offsetof`
for deliberate layout work, and `std::span`/container iterators in C++ over raw
pointer math. If pointer arithmetic is genuinely needed, comment the invariant
that makes it safe so reviewers can check it.

# How to reproduce

Observe that hand-computed byte offsets ignore the padding the compiler inserts,
so the "unreasoned" read lands on the wrong member; build with
`-fsanitize=address` to see out-of-bounds variants get flagged.

```c
#include <stdio.h>
#include <stddef.h>

struct rec {
    char  tag;        /* 1 byte, then 3 bytes of padding */
    int   value;      /* at offset 4, not offset 1 */
};

int main(void)
{
    struct rec r = { 'A', 42 };

    /* Unreasoned: assume value sits right after tag at byte offset 1. */
    int *guess = (int *)((char *)&r + 1);
    printf("guessed value = %d (garbage from padding)\n", *guess);

    /* Reasoned: let the compiler tell you the real offset. */
    int *real = (int *)((char *)&r + offsetof(struct rec, value));
    printf("real value    = %d\n", *real);
    return 0;
}
```

