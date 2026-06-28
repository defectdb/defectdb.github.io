---
title: "Incompatible types in assignment"
author: Maxim Menshikov
layout: defect
permalink: /types/assignment/mismatch
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: types.assignment
group:
   - types
   - assignment
---
Assignment between values of incompatible kinds (e.g. string and integer, struct and integer)

# Impact

Assigning a value of one kind to a variable of an unrelated kind — a pointer to
an integer, a floating-point value to an integer, a wide type to a narrow one —
either fails to compile in a strict language or, in a permissive one like C,
compiles with a warning while silently reinterpreting or truncating the value.
When it compiles, the stored value is corrupted: the high bits of a 64-bit
pointer or integer are discarded, a fractional part is dropped, or a bit pattern
is reinterpreted as a different type. The variable then carries a value that bears
no relation to the source, and every later use of it is wrong. Used as an index,
size, or pointer, that corrupted value escalates from a wrong result to an
out-of-bounds access.

# Vulnerability potential

Security relevance is usually low but not zero.

1. Truncating a 64-bit length or pointer into a 32-bit (or smaller) variable can
   drop the high bits so a bounds check passes while the real size overflows the
   buffer, enabling an out-of-bounds write — a classic integer-truncation path to
   memory corruption.
2. Reinterpreting an integer as a pointer (or vice versa) through a loose
   assignment can produce a wild pointer that, if attacker-influenced, becomes an
   arbitrary read/write primitive.

In strongly typed languages the assignment simply does not compile, so the defect
is caught before it can become a vulnerability; the risk lives in languages and
configurations that demote the mismatch to a warning.

# Technical details

## Go (and other strict languages)
Go's type system forbids assigning between unrelated types without an explicit
conversion: `var n int = "5"` or assigning a `struct` to an `int` is a *compile
error* (`cannot use ... as int value`). This is the safe end of the spectrum —
the mismatch cannot reach a binary. The danger reappears only via deliberate
escape hatches (`unsafe.Pointer`, `reflect`).

## C/C++
C is far more permissive. Pointer/integer and incompatible-pointer assignments
produce only warnings (`-Wint-conversion`, `-Wincompatible-pointer-types`), and
arithmetic conversions (float to int, wide to narrow) are *implicit and silent*,
performing truncation or reinterpretation without any diagnostic at default
settings. C++ is stricter about pointers but still allows lossy arithmetic
narrowing outside of braced initialization (which forbids it via
`-Wnarrowing`).

## Why it slips through
A wrong return type, a swapped argument, a `void*` round-trip, or a refactor that
changes a variable's type can introduce a mismatch the compiler only whispers
about. Ignored warnings are how these reach production.

# Catching the issue

## Compilers
Treat the relevant warnings as errors: GCC/Clang
`-Werror=int-conversion -Werror=incompatible-pointer-types -Wconversion
-Wfloat-conversion -Wnarrowing`, and MSVC `/W4 /WX` (C4244, C4267, C4047). Use
braced initialization in C++ (`int x{expr};`) so narrowing is rejected.

## Static analysis
clang-tidy, Cppcheck, Coverity, and PVS-Studio flag lossy and incompatible
assignments, including truncation across function boundaries. In strict languages
the compiler is the analysis — keep the explicit conversions honest and bounded
rather than papering over a real type confusion with a cast.

# How to reproduce

## Go
The mismatch is rejected at compile time; `go build` fails before any binary
exists.

```go
package main

func main() {
	var n int
	n = "5" // compile error: cannot use "5" (untyped string) as int value
	_ = n
}
```

## C
Compile with `gcc -Wall`; it warns about assigning a pointer to an integer, then
truncates the pointer on LP64, so the printed value is not the address.

```c
#include <stdio.h>

int main(void) {
    int x = 1;
    int addr = (int) 0;     /* placeholder */
    addr = (int)(long)&x;   /* 64-bit pointer truncated into a 32-bit int */
    printf("%d\n", addr);   /* high bits of &x are lost */
    return 0;
}
```
