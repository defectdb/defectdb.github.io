---
title: "Unused assignment result"
author: Maxim Menshikov
layout: defect
permalink: /logic/assignment/unused
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: logic.assignment
group:
   - logic
   - assignment
---
The assignment result is never used

# Impact

A *dead store* is an assignment whose value is never read before it is
overwritten or the variable goes out of scope. The store is wasted work, and the
optimizer usually deletes it, so by itself it costs nothing at runtime. The real
significance is diagnostic: a value was computed for a reason, and the fact that
nobody consumes it usually means the program is not doing what the author
intended. Typical underlying mistakes are a return value that should have been
used but was dropped, a variable assigned in the wrong scope, a missing ``use``
of the result, or two assignments where the second was meant to be conditional.
The dead store is the visible tip of one of those logic errors.

# Vulnerability potential

This is predominantly a code-quality issue with little direct security impact.
There is one well-known exception worth calling out: a store written to *scrub a
secret* — ``memset(key, 0, sizeof key)`` just before the buffer dies — is itself
a dead store, and the optimizer is entitled to remove it, leaving the secret in
memory (CWE-14, "compiler removal of code to clear buffers"). When the unused
assignment is a security cleanup, the consequence is information disclosure of
keys or passwords via a later memory read, core dump, or swap. Outside that
case, treat the finding as a hint that a logic bug may be nearby rather than a
vulnerability in its own right.

# Technical details

Compilers detect dead stores during *liveness analysis*: a variable is live at a
program point if its current value may be read on some path before being
redefined. An assignment to a variable that is dead immediately after it is, by
definition, a dead store and is eliminated by dead-store/dead-code elimination
passes. The same analysis powers the diagnostic.

## The secret-scrubbing case
Because the optimizer reasons about the *observable* effect of the program, a
final ``memset`` whose result is never read is indistinguishable from any other
dead store and is removed. C11 provides ``memset_s`` (Annex K), and platforms
provide ``explicit_bzero``/``SecureZeroMemory`` precisely to express "this write
must happen", defeating the optimization. This is the one situation where the
"unused" store is actually load-bearing and must be preserved.

# Catching the issue

Clang's ``-Wunused-but-set-variable`` and the Clang Static Analyzer's
``deadcode.DeadStores`` checker flag dead stores directly; GCC offers
``-Wunused-but-set-variable`` as well. clang-tidy
(``clang-analyzer-deadcode.DeadStores``), cppcheck, Coverity, and PVS-Studio
all report them. For the secret-scrubbing pitfall specifically, prefer
``explicit_bzero``/``memset_s``/``SecureZeroMemory`` so the wipe is never
classified as dead, and audit any ``memset(...,0,...)`` that immediately precedes
the end of a buffer's lifetime. In review, ask of every flagged store "why was
this value computed?" — the answer usually reveals the real bug.

# How to reproduce

Observe that the first assignment to ``rc`` is dead — its value is overwritten
before it is ever read, hiding the fact that the first call's error code is
ignored. Build with ``-Wunused-but-set-variable`` or run
``clang --analyze``.

```c
#include <stdio.h>

int do_step(int n);

int main(void) {
    int rc;
    rc = do_step(1);   /* dead store: result never checked, overwritten below */
    rc = do_step(2);   /* only the second error code survives */
    if (rc != 0)
        printf("failed\n");
    return rc;
}
```

