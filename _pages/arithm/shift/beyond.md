---
title: "Incorrect integer shift"
author: Maxim Menshikov
layout: defect
permalink: /arithm/shift/beyond
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: arithm.shift
group:
   - arithm
   - shift
---
The integer shift is beyond the boundaries of a variable

# Impact

Shifting an integer by an amount greater than or equal to the width of its
type, or by a negative amount, does not produce the "obvious" result of zero.
In C and C++ it is **undefined behavior**, so the compiler is free to emit any
result, and in practice the answer is dictated by the target CPU. The visible
consequences range from a silently wrong value (a mask, index, or size that is
off by orders of magnitude) to a value that is fed into an allocation,
bounds check, or array index and corrupts memory downstream.

# Vulnerability potential

This issue has a real potential to become a vulnerability.

1. The shift amount frequently comes from external input (a length prefix, a
   field width, a bit position parsed from a file or packet). An attacker who
   controls it can force undefined behavior and, with it, an unpredictable
   result.
2. When the wrong result is used to compute a buffer size or an index, the
   defect turns into a heap/stack overflow or out-of-bounds access, which may
   escalate to remote code execution.
3. Because the behavior is undefined, an optimizing compiler may assume the
   shift is in range and delete a subsequent bounds check, silently removing a
   protection the programmer thought was present.
4. The unpredictability can also be used to crash the process, contributing to
   a denial of service.

# Technical details

The C standard (C11/C17 6.5.7) states that for `E1 << E2` and `E1 >> E2` the
behavior is undefined if `E2` is negative or is greater than or equal to the
width of the promoted left operand. C++ has the same rule. "Width" is the
number of value bits of the *promoted* type, which matters: shifting a
`uint16_t` does not operate on 16 bits, because the operand is first promoted to
`int` (typically 32 bits), so `x << 20` on a 16-bit value is legal but
surprising.

## Why the result is not zero
On x86/x86-64 the `SHL`/`SHR` instructions mask the shift count to the low 5
bits (for 32-bit operands) or 6 bits (for 64-bit operands). So `1u << 32`
becomes `1u << (32 & 31)` = `1u << 0` = `1`, not `0`. ARM AArch32 instead
saturates and yields `0`, while AArch64 masks like x86. The same source therefore
produces different answers on different CPUs.

## Signed vs unsigned
Left-shifting a signed value so that a `1` reaches or passes the sign bit is
itself undefined (C11 6.5.7p4), independent of the shift-too-far problem.
Right-shifting a negative signed value is implementation-defined (usually an
arithmetic shift that keeps the sign). Prefer unsigned types for all bit work.

# Catching the issue

## Compilers
Both GCC and Clang warn about constant out-of-range shifts under `-Wshift-count-overflow`
and `-Wshift-count-negative` (enabled by `-Wall`). Signed-overflow shifts are
caught by `-Wshift-overflow=2`.

## Sanitizers
Build with `-fsanitize=shift` (part of `-fsanitize=undefined`, UBSan). It
instruments every shift and reports at runtime when the count is out of range or
when a signed left shift overflows, including the file, line, and the offending
values.

## Static analysis
Clang-tidy (`clang-analyzer-core.UndefinedBinaryOperatorResult`), Coverity,
PVS-Studio, and CodeQL all flag shift counts that may exceed the type width.

## Code review / runtime
Validate the shift amount against the bit width before shifting, e.g.
`assert(n < sizeof(x) * CHAR_BIT)`, and use unsigned operands of an explicit
width (`uint32_t`, `uint64_t`) so the width is unambiguous.

# How to reproduce

Observe that the result is not `0` as one might expect, and that UBSan reports
the operation when built with `-fsanitize=undefined`.

```c
#include <stdio.h>
#include <stdint.h>

int main(void)
{
    uint32_t v = 1u;
    int      n = 32;          /* equal to the width: undefined behavior */

    /* On x86-64 the count is masked to 0, so this prints 1, not 0. */
    printf("1u << %d = %u\n", n, v << n);
    return 0;
}
```

