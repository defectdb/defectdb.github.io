---
title: "Confusing overloading with mixed parameter order"
author: Maxim Menshikov
layout: defect
permalink: /fn/argument/confusing_overload
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: fn.argument
group:
   - fn
   - argument
---
The overloading of function might be confusing due to changed parameter order

# Impact

Two overloads (or closely related functions) share a name but list their
parameters in a different order — for example `draw(Point p, Color c)` alongside
`draw(Color c, Point p)`, or `copy(dst, src)` next to a sibling that takes
`(src, dst)`. When the parameter types are convertible to one another, a call that
gets the arguments in the "wrong" order still compiles and binds to a valid
overload, but executes with the meaning swapped. The defect is a readability and
correctness trap: the code looks right, the compiler is happy, and the behaviour
is wrong.

The practical consequences depend on what the swapped parameters mean —
transposed coordinates, a value written to the wrong target, or, in the worst
case, a size and a buffer exchanged.

# Vulnerability potential

The security exposure is modest and indirect.

1. **Wrong-target / wrong-size operations.** If one overload takes `(pointer,
   length)` and a confusingly ordered sibling takes `(length, pointer)`, an
   accidental swap can drive a copy or fill with the wrong size or against the
   wrong buffer, which at that call site could become an out-of-bounds access.
   The danger lives at the memory operation, not in the overloading itself.
2. **Logic errors.** Swapped arguments can invert a comparison or send data to the
   wrong destination, weakening a check.

In isolation this is a clarity defect, so both ratings are `Low`; it becomes
serious only when the swapped parameters feed a memory or security operation
elsewhere.

# Technical details

## Overload resolution masks the mistake
C++ picks the best-matching overload from the static argument types. When the
parameter types are mutually convertible (numeric types, pointers via implicit
conversion, types with converting constructors), arguments in either order may
each form a viable candidate, so the wrong order resolves silently instead of
erroring.

## Why the order diverges
- An overload added later by a different author followed a different convention.
- A "convenience" overload reordered parameters to make one call site read
  better, breaking the family's consistency.
- C-style sibling functions (`memcpy(dst, src, n)` vs a local
  `mycopy(src, dst, n)`) mix `dst`-first and `src`-first conventions.

## Standing conventions
Established APIs fix an order (destination-first in `memcpy`/`strcpy`; many POSIX
calls are `(fd, buf, len)`). Overloads that deviate from the surrounding
convention are the ones flagged.

# Catching the issue

## Static analysis / linters
The analyzer emitting this diagnostic flags overload sets whose parameter orders
diverge for compatible types. clang-tidy and review tooling can detect
inconsistent argument ordering across an overload family.

## Make swaps not compile
Use distinct, strongly-typed parameters (`enum class`, tagged structs, named
wrapper types such as `Length{n}` / `Offset{n}`) so an out-of-order call fails to
type-check. Named-argument idioms (parameter objects, builder methods) remove the
positional ambiguity entirely.

## Convention and review
Keep one parameter order across an overload family (and follow the
destination-first / well-known conventions). Review rule: a new overload must not
reorder parameters that an existing overload already defines.

# How to reproduce

Run this: both `at` overloads accept the arguments because `int` and `double` are
mutually convertible, so the swapped call binds to the wrong overload and prints
the wrong interpretation.

```cpp
#include <iostream>

// Two overloads with the parameters in opposite order.
void at(int row, double weight) { std::cout << "row=" << row
                                            << " weight=" << weight << "\n"; }
void at(double weight, int row) { std::cout << "weight=" << weight
                                            << " row=" << row << "\n"; }

int main()
{
    // Intended row=3, weight=0.5 — but the literals' types pick the
    // (double,int) overload, silently swapping the meaning.
    at(3, 0.5);   // calls at(double,int): weight=3 row=0  ... not what was meant
    return 0;
}
```
