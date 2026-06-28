---
title: "Invalid bitmask"
author: Maxim Menshikov
layout: defect
permalink: /arithm/bitmask/too_big
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: arithm.bitmask
group:
   - arithm
   - bitmask
---
The bitmask size is bigger than the variable itself

# Impact

A bitmask whose set bits extend beyond the width of the variable it is applied
to has dead bits: the high bits of the mask can never match anything, because
the variable simply has no bits there. The visible effect is a logic error — a
flag that is never seen, a field that is always read as zero, a test that never
triggers. When the mask is applied, the operand is often promoted to a wider
type first, so the surplus bits may instead pick up sign-extension bits or
adjacent storage that the programmer never intended to read, giving subtly wrong
results rather than a clean failure.

# Vulnerability potential

The security relevance of this defect is usually limited. It is primarily a
correctness bug: the mask and the variable are mismatched, so some bits are
ignored or always read as zero. The main risk is indirect — if the masked value
is used in a permission, flag, or length decision, a mask that drops the wrong
bits could let a value pass a check it should fail, or mis-parse a security
relevant field. There is no direct memory-corruption path from the mask itself,
so the rating stays low absent such a downstream use.

# Technical details

A bitmask is meaningful only over the bits that the target variable actually
has. A `uint8_t` holds 8 bits, so any mask bit at position 8 or higher is dead.
The mismatch usually stems from copying a constant defined for a wider type, or
from changing a variable's type without revisiting the masks that use it.

## Integer promotion
The surplus bits are not always silently ignored. In `uint8_t b; b & 0x1FF`,
`b` is promoted to `int` before the AND, so the expression is computed in 32-bit
arithmetic. The mask's bit 8 then ANDs against bit 8 of the promoted value,
which is always zero for a `uint8_t`, so that bit can never be set — the mask
is simply too big to be useful.

## Sign extension
If the masked variable is a signed narrow type holding a negative value, promotion
sign-extends it: `int8_t b = -1; b & 0xFF0` becomes `0xFFFFFFFF & 0xFF0 = 0xFF0`,
so the "out-of-range" mask bits suddenly do match, producing a value the author
likely did not expect. This is why oversized masks are bugs even when they
"work".

## Field width mismatch
For bit-field extraction (`(v >> shift) & mask`), a mask wider than the field
captures neighboring fields. The mask must equal `(1u << field_width) - 1`.

# Catching the issue

## Static analysis
PVS-Studio has dedicated diagnostics for masks that are larger than the operand
(e.g. expressions that are always true/false because of the mask). Coverity and
CodeQL flag bitwise operations whose result is constant or whose mask exceeds the
operand width. clang-tidy's `bugprone-*` and `hicpp-signed-bitwise` checks catch
related mistakes.

## Compiler warnings
`-Wtautological-constant-out-of-range-compare` and Clang's
`-Wconstant-conversion` warn when a constant cannot fit the type. Enable
`-Wconversion`/`-Wsign-conversion` to surface the implicit promotions that make
the surplus bits behave unexpectedly.

## Code review
Define masks in terms of the type width, e.g. derive the mask from the field
size rather than hard-coding a literal, and keep mask constants next to the
variable definition so a type change is caught. Add a static assertion such as
`static_assert((MASK & ~(uint8_t)~0u) == 0)` to prove the mask fits.

# How to reproduce

Observe that the mask bit 8 (`0x100`) can never match an 8-bit value, so the
"feature enabled" branch is unreachable for the unsigned case, while the signed
case picks up sign-extension bits and matches unexpectedly.

```c
#include <stdio.h>
#include <stdint.h>

int main(void)
{
    uint8_t flags = 0xFF;          /* every bit of an 8-bit value is set */

    /* 0x100 is bit 8 — beyond the width of uint8_t. */
    if (flags & 0x100u)
        printf("enabled\n");
    else
        printf("never reached: mask bit is outside the variable\n");

    int8_t sflags = -1;            /* promotes to 0xFFFFFFFF */
    printf("signed surplus bits match: 0x%X\n", sflags & 0xF00);
    return 0;
}
```

