---
title: "Null argument"
author: Maxim Menshikov
layout: defect
permalink: /fn/argument/null
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Medium
group_full: fn.argument
group:
   - fn
   - argument
---
Null argument is substituted into a function that doesn't expect it

# Impact

A function is called with a null pointer for a parameter it assumes is always
valid. The callee dereferences it without a guard, so the program faults the
moment it touches the argument — a copy into the pointed-to buffer, a field
access, a `strlen`/`strcpy`, etc. Many standard and third-party functions document
that passing `NULL` is undefined behaviour (`memcpy`, `strcpy`, `strlen`,
`printf("%s", NULL)`), so the call may crash, corrupt memory, or behave
arbitrarily.

The defect is often masked by the happy path: the caller "knows" the value is set,
but on an error or early-return branch the pointer is left `NULL` and reaches the
function anyway.

# Vulnerability potential

Passing an unexpected null has real security weight.

1. **Denial of service.** The typical outcome is a null-pointer dereference and an
   immediate crash. If an attacker can steer input down the path that yields the
   null argument, they get a reliable, repeatable process kill.
2. **Memory corruption / info disclosure.** With functions like `memcpy`/`memset`
   the null may be a *destination or source* combined with an attacker-influenced
   length; on some platforms low addresses are mapped or the length wraps,
   turning the null argument into an out-of-bounds write or an over-read that
   leaks adjacent memory.
3. **Logic/auth bypass.** A `NULL` where a credential, key, or callback was
   expected can make a check default-allow or skip a security step instead of
   failing closed.

The crash potential gives `Medium` for DoS; the corruption/bypass potential gives
`Medium` for vulnerability.

# Technical details

## Contract violation
C and C++ APIs rarely encode "non-null" in the type system, so callers must honour
an implicit contract. The C standard says passing `NULL` to most `string.h`
functions is undefined; compilers may even assume a dereferenced pointer is
non-null and optimize accordingly, removing later null checks.

## How the null arrives
- An allocation (`malloc`/`new(nothrow)`) failed and the result was passed on
  unchecked.
- A lookup/getter returned `NULL` for "not found" and the caller treated it as
  found.
- A struct field was zero-initialized and never populated on some path.
- A previous `free`/move left the pointer dangling-then-nulled.

## Platform nuance
On most hosted systems address `0` is unmapped, so the dereference is a clean
`SIGSEGV`. On microcontrollers and some kernels address `0` is valid memory, so
the same null argument silently reads/writes real data instead of faulting —
strictly worse, because it corrupts rather than crashes.

# Catching the issue

## Sanitizers
UBSan (`-fsanitize=null`) flags null dereferences directly; ASan reports the
resulting invalid access with a backtrace to the call site.

## Static analysis
Cppcheck, clang-tidy, the Clang static analyzer, Coverity and the analyzer
emitting this diagnostic perform null-flow tracking from the source of the pointer
to the call and report when `NULL` can reach a parameter that is dereferenced
unconditionally. Nullability annotations (`_Nonnull`, `gsl::not_null`,
`[[gnu::nonnull]]`) let the compiler diagnose this at compile time.

## Defensive coding
Check allocation and lookup results before passing them on; assert or early-return
on null at function entry (`assert(p)`, or a guard that returns an error). Prefer
references over pointers in C++ where "must be present" is part of the contract.

# How to reproduce

Run this: the lookup returns `NULL`, which is passed straight to `strlen`, and the
program crashes on the null dereference (UBSan/ASan pinpoint it).

```c
#include <stdio.h>
#include <string.h>
#include <stddef.h>

static const char *lookup(int key)
{
    if (key == 0) return "zero";
    return NULL;                 /* "not found" */
}

int main(void)
{
    const char *s = lookup(42);  /* NULL: not found, but unchecked */

    /* strlen does not expect NULL; this dereferences a null pointer. */
    printf("len = %zu\n", strlen(s));
    return 0;
}
```
