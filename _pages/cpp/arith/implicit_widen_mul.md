---
title: "Multiplication narrows then widens"
author: Maxim Menshikov
layout: defect
permalink: /cpp/arith/implicit_widen_mul
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: cpp.arith
group:
   - cpp
   - arith
---
The multiplication runs in the narrower operand type; if it overflows there the wider destination type cannot recover the result. Cast one operand to the destination type before multiplying

# Impact

In `wide = a * b`, the multiplication is evaluated in the type of `a` and `b`,
**then** the result is converted to the wider destination. If the product does
not fit the operand type, the overflow happens *before* the widening, so the
value stored in the wide variable is already wrong — the extra range of the
destination type is useless because the truncation already occurred. For signed
operands the overflow is undefined behavior; for unsigned it wraps modulo 2ⁿ.
The classic case is `uint64_t bytes = count * size;` where `count` and `size`
are `uint32_t`: the product is computed in 32 bits, wraps, and yields a value
far smaller than the true size.

# Vulnerability potential

The defect is a genuine source of memory-corruption bugs when the result feeds
sizing.

1. **Undersized allocation → heap overflow.** When the truncated product is
   used as an allocation size (`malloc(count * size)`, `new T[count * size]`),
   the buffer is smaller than the data later written into it, giving a heap
   buffer overflow under attacker-controlled `count`/`size`. This is the
   integer-overflow-to-buffer-overflow pattern behind many CVEs (CWE-190 →
   CWE-787).
2. **Bounds-check bypass.** A length validated as a wrapped (small) value
   passes a `<= limit` check, then the real, larger operation runs.
3. Signed overflow here is UB, which the optimizer may exploit to delete
   later checks, compounding the problem. A wrong-but-non-fatal numeric result
   can also just crash or misbehave (the lower DoS weight).

# Technical details

## Usual arithmetic conversions

`[expr.arith.conv]` first applies integer promotion and then brings both
operands to a common type *no wider than the operands themselves*; the
destination of the enclosing assignment plays no part. So `uint32_t *
uint32_t` is a 32-bit multiply regardless of being stored into a `uint64_t`,
and `int * int` is a 32-bit multiply on LP64. The widening conversion is
applied to the already-overflowed product.

## The fix

Cast **one** operand to the destination type before multiplying so the whole
multiplication is performed wide:

```cpp
uint64_t bytes = static_cast<uint64_t>(count) * size;   // 64-bit multiply
```

Casting the *result* (`static_cast<uint64_t>(count * size)`) does **not** help —
the overflow already happened. For untrusted inputs prefer a checked multiply:
`__builtin_mul_overflow`, `std::ckd_mul` (C23 / `<stdckdint.h>`), or an explicit
range test.

## Where it hides

`size_t`/`int` mixing, `int * int` assigned to `long`/`int64_t`, milliseconds
× frequency, width × height × bytes-per-pixel — any product of two same-narrow
quantities stored somewhere wider.

# Catching the issue

## Sanitizers

UndefinedBehaviorSanitizer's `-fsanitize=signed-integer-overflow` traps the
signed case at run time; `-fsanitize=unsigned-integer-overflow` (opt-in, not
strictly UB) catches the wrapping unsigned case used in size math.

## Compiler warnings

GCC/Clang `-Wconversion` and `-Wshorten-64-to-32` highlight narrowing at the
assignment, drawing attention to the operand widths; some versions warn under
`-Wstrict-overflow`.

## Static analysis

clang-tidy `bugprone-implicit-widening-of-multiplication-result` is the exact
check for this pattern; CERT INT30-C/INT18-C, Coverity, and CodeQL
(`cpp/integer-multiplication-cast-to-long`) also flag it.

# How to reproduce

Run it: the 32-bit multiply wraps, so the 64-bit `bytes` holds a tiny value
instead of the true ~4.6 GB size.

```cpp
#include <cstdint>
#include <iostream>

int main() {
    uint32_t count = 100000;
    uint32_t size  = 50000;            // true product 5,000,000,000

    uint64_t bytes = count * size;     // BUG: 32-bit multiply, wraps
    std::cout << bytes << '\n';        // prints 705,032,704, not 5e9

    uint64_t ok = static_cast<uint64_t>(count) * size;   // correct
    std::cout << ok << '\n';           // 5,000,000,000
}
```
