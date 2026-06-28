---
title: "Integer is implicitly truncated"
author: Maxim Menshikov
layout: defect
permalink: /cast/integer/truncation
arch:
   - native
vulnerability:
   - Medium
ddos:
   - None
group_full: cast.integer
group:
   - cast
   - integer
---
The integer is implicitly truncated

# Impact

Assigning a wider integer to a narrower one keeps only the low-order bits and
discards the rest. A `size_t` length of `0x1_0000_0000` stored into a 32-bit
`int` becomes `0`; a `long` of `300` stored into a `signed char` becomes `44`.
The conversion is implicit and silent, so the program continues with a value
that bears no obvious relation to the original. The visible effect is wrong
counts, lengths, and loop bounds — and when the truncated value drives memory
operations, it turns into a serious safety bug. It is also platform-dependent:
the same code can be correct on one data model and broken on another.

# Vulnerability potential

Integer truncation is a well-known precursor to memory corruption (CWE-197,
related to CWE-190/680).

1. A length computed in a wide type and truncated into a narrow one used for
   allocation under-allocates the buffer, while the original wide length is used
   for the copy — a heap buffer overflow. This pattern underlies many real CVEs.
2. Truncating an attacker-controlled size to zero or a small value can bypass a
   size check that was performed on the wide value, then the full data is
   processed — a check/use mismatch.
3. Sign interaction (truncating into a signed narrow type) can flip a large
   positive value into a negative one, defeating `len > 0` guards.

Because exploitation depends on the truncated value feeding a size/index, the
severity is medium: realistic and frequently weaponised, but not automatic.

# Technical details

When an integer is converted to a narrower type, the value is reduced modulo
2^N where N is the width of the destination (for unsigned targets this is
well-defined wraparound; for signed targets that cannot hold the value the
result is implementation-defined). Only the low N bits survive; all higher bits
are lost.

## Where it hides

Implicit conversions at assignment, function-argument passing (`int` parameter
receiving a `size_t`), return values, and in arithmetic where the result type is
narrower than expected. A particularly common case is storing the result of
`strlen`/`sizeof`/`fread` (all `size_t`) into an `int`.

## Data-model sensitivity

`size_t` and pointers are 64-bit on LP64/LLP64 while `int` stays 32-bit, so
truncation that is impossible on a 32-bit build becomes reachable on 64-bit with
large inputs.

## Signedness

Truncating into a signed type can additionally change the sign of the value,
compounding the error and breaking comparisons.

# Catching the issue

## Compiler

`-Wconversion` and `-Wshorten-64-to-32` (Clang) warn on implicit narrowing
integer conversions; `-Wsign-conversion` covers the signed/unsigned angle. Use
`-Wall -Wextra -Wconversion` and consider `-Werror`. MSVC emits C4244/C4267. In
C++, narrowing in brace-initialisation is ill-formed and catches it at compile
time.

## Sanitizers

UBSan's `-fsanitize=implicit-conversion`
(`implicit-integer-truncation`/`implicit-signed-integer-truncation`) reports at
runtime when a value actually loses information during a narrowing conversion.

## Static analysis

Clang-tidy (`bugprone-narrowing-conversions`,
`cppcoreguidelines-narrowing-conversions`), Coverity, Cppcheck, and PVS-Studio
flag narrowing conversions, especially around allocation sizes.

## Review

Carry sizes and lengths in `size_t` end-to-end, avoid storing them in `int`,
make any necessary narrowing explicit with a prior range check, and never let a
checked-wide value be used after being truncated.

# How to reproduce

Compile with `-Wconversion`; observe the warning and that a 64-bit length
collapses to a small 32-bit value, here producing a zero-size allocation for a
huge logical length.

```c
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    size_t len = 0x100000001ULL;  /* 4 GiB + 1 */
    int    n   = len;             /* truncated to low 32 bits -> 1 */

    printf("len=%zu  truncated n=%d\n", len, n);

    char *buf = malloc(n);        /* allocates 1 byte for a huge length */
    if (buf) { buf[0] = 'x'; free(buf); }
    return 0;
}
```

