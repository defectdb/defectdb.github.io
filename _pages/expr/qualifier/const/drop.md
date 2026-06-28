---
title: "Possible const qualifier dropping"
author: Maxim Menshikov
layout: defect
permalink: /expr/qualifier/const/drop
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: expr.qualifier.const
group:
   - expr
   - qualifier
   - const
---
It is not recommended to drop const qualifier

# Impact

Dropping the ``const`` qualifier — via an explicit cast, a C-style conversion, or
an implicit conversion the compiler reluctantly allows — discards a guarantee the
type system was enforcing: that the referenced object will not be modified through
this access path. Once the qualifier is gone, the code can write through a pointer
that was declared read-only. If the underlying object is in fact constant — a
string literal, a ``const`` global, data the compiler placed in a read-only
section — writing to it is *undefined behaviour*: on most systems it faults with a
segmentation/access violation, and on others it silently corrupts data the rest of
the program assumes is immutable. Even when the target happens to be writable, the
cast defeats the contract the API author wrote ``const`` to express, so callers
that relied on "this function won't touch my data" can have their objects mutated
unexpectedly.

# Vulnerability potential

Casting away const opens a path to memory corruption and integrity violations.

1. **Write to read-only memory.** Modifying a string literal or ``const`` object
   after a ``const`` cast is undefined behaviour; in practice it either crashes
   (a DoS) or, where the page is writable, corrupts shared constant data that
   other code trusts.
2. **Aliasing-based corruption.** The compiler may cache or constant-fold a value
   it believes is immutable; a hidden write through a de-``const``-ed pointer makes
   the program observe two different values for the "same" constant, producing
   logic errors that can be steered into unsafe states.
3. **Breaking an immutability invariant.** When ``const`` marks data that security
   logic depends on not changing (a configuration record, a policy table, a cached
   credential), removing the qualifier lets that data be tampered with through an
   unexpected path.

# Technical details

``const`` is part of an object's type, and the qualifier rules forbid an implicit
conversion that removes it (e.g. ``const T *`` to ``T *``). Programmers bypass this
with a cast. The key subtlety is the difference between the *qualifier on the
access path* and the *constness of the object itself*: writing through a
de-``const``-ed pointer is only defined if the pointed-to object was not originally
declared ``const``. If it was, the write is undefined regardless of what the
pointer type now says.

## C vs C++
- In C, ``(char *)p`` cheerfully strips ``const``; the conversion is a normal cast
  and the language gives little warning. C also has the asymmetry that a string
  literal has type ``char[]`` (not ``const char[]``) yet must not be modified, so
  ``char *s = "x"; s[0] = 'y';`` is the canonical instance of this bug.
- In C++ the dedicated operator is ``const_cast``, and ``static_cast`` /
  implicit conversions will *not* remove ``const`` — the explicitness is by
  design, to make the rare legitimate use stand out. Writing through the result is
  still UB if the object is truly ``const``.

## Legitimate uses
Occasionally the cast is correct: calling a legacy C API that takes ``char *`` but
does not actually write, or implementing a ``const`` method that updates a
genuinely-non-``const`` cache. These should use ``mutable`` (C++) or be documented,
not normalized into a habit.

# Catching the issue

Compile with ``-Wcast-qual`` (GCC/Clang) to warn whenever a cast drops a
qualifier; ``-Wwrite-strings`` makes string literals ``const char[]`` in C so
assignments through ``char *`` are diagnosed. In C++, treat every ``const_cast``
as a code-review red flag and grep for it. Static analyzers (clang-tidy
``cppcoreguidelines-pro-type-const-cast``, cppcheck, PVS-Studio V659/V598,
Coverity, MISRA C Rule 11.8 "a cast shall not remove any const qualifier") flag
the construct directly. AddressSanitizer and the OS memory protection catch the
runtime write to read-only memory. The structural fix is to make the data flow
``const``-correct end to end so the cast is never needed, and to mark intentionally
mutable members ``mutable`` instead of casting around the qualifier.

# How to reproduce

Observe that casting away ``const`` and writing through the result attempts to
modify a string literal in read-only memory, which crashes at runtime. Compile
with ``-Wcast-qual``.

```c
#include <stdio.h>

void shout(const char *s) {
    char *w = (char *)s;   /* drops const */
    w[0] = 'H';            /* UB: writes through a pointer to a literal */
}

int main(void) {
    shout("hello");        /* "hello" lives in read-only storage -> SIGSEGV */
    printf("done\n");
    return 0;
}
```

