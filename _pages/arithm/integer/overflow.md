---
title: "Possible integer overflow"
author: Maxim Menshikov
layout: defect
permalink: /arithm/integer/overflow
arch:
   - native
vulnerability:
   - High
ddos:
   - Medium
group_full: arithm.integer
group:
   - arithm
   - integer
---
The variable is likely to overflow in this operation

# Impact

When an arithmetic operation produces a result that does not fit in the result
type, the value wraps (for unsigned types) or is undefined (for signed types in
C/C++). A computation that should have grown produces a small or negative number
instead. The damage depends on where the result flows: an overflowed size passed
to `malloc` allocates too little memory, an overflowed index escapes array
bounds, an overflowed loop counter never terminates, and an overflowed balance
or quota check passes when it should fail. Integer overflow is one of the most
common root causes behind heap overflows and the security bugs built on top of
them.

# Vulnerability potential

This issue has a strong potential to become a vulnerability and is a classic
exploitation primitive (CWE-190).

1. **Undersized allocation.** `malloc(count * size)` overflows, returns a tiny
   buffer, and the following copy loop writes past it — a heap overflow that
   often leads to remote code execution.
2. **Bypassed bounds and quota checks.** A length validated as `len + header <=
   max` passes when `len + header` wraps to a small value, letting an attacker
   smuggle an oversized payload through.
3. **Signed overflow is undefined behavior.** The compiler may assume it cannot
   happen and remove a check such as `if (a + b < a)`, deleting the very
   overflow guard the programmer wrote.
4. **Denial of service.** A wrapped counter can produce an infinite loop or an
   absurd allocation request, exhausting CPU or memory.

# Technical details

Machine integers are fixed-width, so every type has a finite range. When a
result exceeds that range the high bits are lost.

## Unsigned types
Unsigned arithmetic in C/C++ is defined to wrap modulo `2^N`. `UINT_MAX + 1`
is `0`, and `0u - 1` is `UINT_MAX`. This is well defined but rarely what the
programmer intended.

## Signed types
Signed overflow is **undefined behavior** in C and C++. In practice two's
complement hardware wraps (`INT_MAX + 1` becomes `INT_MIN`), but the compiler is
entitled to assume overflow never occurs and optimize accordingly, which is why
relying on the wrap is dangerous.

## Integer promotion and conversion
Operands narrower than `int` are promoted to `int` before the operation, so
`uint16_t a, b; a * b` is computed in `int` and can overflow `int`. Mixing
signed and unsigned operands triggers the "usual arithmetic conversions": the
signed operand is converted to unsigned, so `len - 1` with `len == 0` becomes a
huge unsigned number. Truncating a wide result back into a narrow type
(`size_t` into `int`) loses the high bits silently.

# Catching the issue

## Sanitizers
`-fsanitize=signed-integer-overflow` (part of UBSan) traps signed overflow at
runtime. `-fsanitize=unsigned-integer-overflow` flags unsigned wraps too,
useful when wrapping is not intended (but expect noise from code that wraps on
purpose, such as hashes). `-ftrapv` makes signed overflow abort.

## Safe arithmetic
Use the compiler builtins `__builtin_add_overflow` / `__builtin_mul_overflow`
(GCC and Clang) or, in C23, `<stdckdint.h>`'s `ckd_add`/`ckd_mul`, which return a
flag instead of a wrapped value. Validate before allocating: check `count <=
SIZE_MAX / size` before computing `count * size`.

## Static analysis
Coverity, clang-tidy (`bugprone-misplaced-widening-cast`,
`bugprone-implicit-widening-of-multiplication-result`), PVS-Studio, and CodeQL
detect many overflow-prone multiplications and size computations.

## Compiler warnings
`-Wstrict-overflow`, `-Wconversion`, and `-Wsign-conversion` surface risky
conversions and optimizations that depend on overflow not happening.

# How to reproduce

Observe that the multiplication wraps, so `malloc` receives a tiny size while
the loop writes `count` elements — a heap overflow. Build with
`-fsanitize=undefined` to see the overflow reported.

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

int main(void)
{
    /* Attacker-controlled element count. */
    uint32_t count = 0x40000001u;      /* ~1 billion */
    size_t   bytes = count * 4u;        /* overflows 32-bit math: wraps to 4 */

    int *p = malloc(bytes);             /* allocates 4 bytes, not ~4 GB */
    printf("requested %u elements, allocated %zu bytes\n", count, bytes);

    for (uint32_t i = 0; i < count; i++)
        p[i] = 0;                       /* writes far past the allocation */

    free(p);
    return 0;
}
```

