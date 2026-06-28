---
title: "sizeof() is likely to be misused"
author: Maxim Menshikov
layout: defect
permalink: /ast/sizeof/pointer
arch:
   - native
vulnerability:
   - High
ddos:
   - Medium
group_full: ast.sizeof
group:
   - ast
   - sizeof
---
sizeof() is used on pointer rather than array

# Impact

Applying ``sizeof`` to a pointer when the programmer meant the size of the
pointed-to array or object yields the size of the *pointer itself* — 8 bytes on a
typical 64-bit platform, 4 on 32-bit — not the size of the data. Code that uses
this value as a length is then wrong by a large factor. The two failure
directions are both dangerous: if the real object is larger than a pointer, a
``memcpy``/``memset``/``snprintf`` bounded by ``sizeof(ptr)`` copies or clears too
*little*, silently truncating data or leaving a buffer un-initialized; if the
buffer is smaller, or the count is multiplied, the operation runs *past* the
object and corrupts adjacent memory. A particularly common form is computing an
element count as ``sizeof(arr)/sizeof(arr[0])`` on a parameter that has decayed to
a pointer, which produces ``8/4 = 2`` (or ``8/8 = 1``) regardless of the true
length.

# Vulnerability potential

This is a classic source of memory-corruption vulnerabilities (CWE-467, "Use of
sizeof() on a Pointer Type").

1. **Buffer overflow.** When the wrong size is too large for the destination —
   e.g. ``memcpy(dst, src, sizeof(src))`` where ``src`` is a pointer but ``dst``
   is smaller, or a count derived from ``sizeof(ptr)`` that exceeds the real
   allocation — the write goes out of bounds, enabling stack/heap corruption and
   potentially remote code execution.
2. **Information disclosure / truncation.** When the size is too small, a
   ``memset`` meant to scrub a secret clears only the first few bytes, leaving key
   material in memory, or a length-prefixed copy truncates data in a way that
   confuses later parsing.
3. **Denial of service.** A grossly wrong length passed to a bulk memory
   operation reads or writes far outside the object and crashes the process; if
   reachable from input, it is a reliable DoS.
4. **Iteration bounds.** A loop bounded by a wrong element count under-processes
   or over-runs the array, corrupting state.

# Technical details

``sizeof`` is evaluated at compile time from the *static type* of its operand. For
a pointer ``T *p``, ``sizeof(p)`` is the pointer width; only ``sizeof(*p)`` or
``sizeof(T)`` gives the pointee size, and that is still just one element, not the
whole buffer a pointer refers to. The amount of memory behind a pointer is simply
not recoverable from the pointer's type — it must be tracked separately.

## Array-to-pointer decay
The trap is sharpened by *decay*: in most expression contexts, and crucially when
an array is passed as a function argument, an array ``T a[N]`` is converted to a
``T *``. Inside

```
void f(int a[10]) { /* sizeof(a) == sizeof(int*), NOT 10*sizeof(int) */ }
```

the parameter ``a`` has type ``int *`` despite the ``[10]`` syntax, so the
``sizeof(arr)/sizeof(arr[0])`` count idiom — which is correct for a true array in
the scope where it was declared — silently breaks. The idiom only works where the
real array type is in view.

## Platform dependence
Because the bug substitutes the pointer width, its magnitude and even its sign of
error change between ILP32 and LP64 targets. Code that appears to "work" on one
ABI (where ``sizeof(ptr)`` happens to be close to the intended size) can corrupt
memory on another, so the defect is also a portability landmine.

# Catching the issue

Compile with warnings on: GCC and Clang emit ``-Wsizeof-pointer-div`` for the
``sizeof(ptr)/sizeof(ptr[0])`` count mistake and ``-Wsizeof-array-argument`` /
``-Wsizeof-pointer-memaccess`` when a ``sizeof`` on a pointer (or array parameter)
is fed to ``memcpy``/``memset``/``strncpy`` and friends. These are part of
``-Wall`` and catch most real cases at zero cost. clang-tidy
(``bugprone-sizeof-expression``), cppcheck, Coverity, and PVS-Studio (V511/V512,
V579) detect the pattern in static analysis. AddressSanitizer catches the
resulting out-of-bounds access at runtime, and fuzzing surfaces the input-driven
ones. As a defensive practice, prefer a macro such as
``#define COUNTOF(a) (sizeof(a)/sizeof((a)[0]))`` that uses C++ templates or a
``__builtin`` to refuse to compile on pointers, never take a length from a
pointer's ``sizeof``, and pass array lengths explicitly across function
boundaries.

# How to reproduce

Observe that inside ``clear`` the parameter has decayed to a pointer, so
``sizeof(buf)`` is 8 (pointer width), and only the first 8 bytes are zeroed
instead of all 64. Compile with ``-Wall`` to see ``-Wsizeof-pointer-memaccess``.

```c
#include <string.h>
#include <stdio.h>

void clear(char buf[64]) {
    /* buf is really char*, so sizeof(buf) == sizeof(char*) == 8, not 64 */
    memset(buf, 0, sizeof(buf));   /* zeroes only 8 of the 64 bytes */
}

int main(void) {
    char secret[64];
    memset(secret, 'A', sizeof secret);  /* true array: 64 bytes */
    clear(secret);
    printf("byte 40 = %d\n", secret[40]);  /* still 'A' (65), not 0 */
    return 0;
}
```

