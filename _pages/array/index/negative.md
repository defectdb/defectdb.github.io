---
title: "Negative index in array access"
author: Maxim Menshikov
layout: defect
permalink: /array/index/negative
arch:
   - native
vulnerability:
   - Medium
ddos:
   - None
group_full: array.index
group:
   - array
   - index
---
Negative index in array access can be a sign of issue

# Impact

A negative array index addresses memory *before* the start of the array. For a
plain C array `a[-1]` is `*(a - 1)`, which reads or writes the bytes preceding
the buffer — frequently another local variable, a saved register, or heap
metadata. The result is the same family of consequences as any out-of-bounds
access: silent corruption, wrong results, information disclosure, or a crash.
A negative index almost always signals a logic error — an unsigned/signed
confusion, an unchecked return value used as an index, or a counter that
underflowed.

# Vulnerability potential

Negative indexing is an out-of-bounds access (CWE-787 / CWE-125) and carries the
same security weight when the index is influenced by input.

1. A negative write below the buffer can corrupt adjacent control data (return
   address, saved frame pointer, heap chunk headers), leading to control-flow
   hijack.
2. A negative read can leak adjacent memory contents.
3. A subtle trap: a value meant to be an index is often stored in a *signed*
   `int`; if it is later compared only against an upper bound (`i < len`) and
   not against `0`, a negative value passes the check and is then used. If that
   same value is implicitly converted to an unsigned `size_t` for the access, it
   becomes a huge positive offset — a far-out-of-bounds access.

# Technical details

Array subscripting performs pointer arithmetic with no lower-bound check, so a
negative subscript simply produces a lower address. Whether it faults depends on
the layout: a small negative offset usually stays within a mapped page and
corrupts neighbours silently, while a large negative value may reach an unmapped
page and crash.

## Signed/unsigned interaction

The dangerous case is mixing the two. `int i = -1; size_t n = strlen(s);
if (i < n) buf[i] = 0;` — here `i < n` compares `int` to `size_t`, so `i` is
converted to a huge unsigned value, the guard fails to protect, and the eventual
`buf[i]` (with `i` as `int`) still indexes below the buffer. Either branch of
the confusion is a bug.

# Catching the issue

## Compiler

`-Wall -Wextra` with `-Wsign-compare` and `-Wsign-conversion` flags the
signed/unsigned mismatches that produce negative indices. `-Warray-bounds`
catches some constant negative subscripts.

## Sanitizers

AddressSanitizer reports the underflow access; UBSan's `-fsanitize=bounds`
flags negative constant indices into known-size arrays. `-fsanitize=signed-
integer-overflow` helps catch the counter underflow that produced the index.

## Static analysis

Clang Static Analyzer, Cppcheck, Coverity, and PVS-Studio track tainted and
underflowed values used as indices.

## Review

Validate indices against both `0` and the upper bound, prefer unsigned types
only when a negative value is truly impossible, and never use an unvalidated
return value (e.g. from a search function returning `-1` on failure) directly as
a subscript.

# How to reproduce

Compile with `-fsanitize=address` and run; ASan reports a
stack-buffer-underflow at the write.

```c
#include <string.h>

int find(const char *s, char c)
{
    const char *p = strchr(s, c);
    return p ? (int)(p - s) : -1;   /* -1 means "not found" */
}

int main(void)
{
    int a[8] = {0};
    int idx = find("hello", 'z');   /* not found -> idx == -1 */

    /* idx is used without checking for -1 */
    a[idx] = 1;                      /* writes a[-1], before the array */
    return a[0];
}
```

