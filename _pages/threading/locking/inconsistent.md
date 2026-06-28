---
title: "Locking is inconsistent"
author: Maxim Menshikov
layout: defect
permalink: /threading/locking/inconsistent
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: threading.locking
group:
   - threading
   - locking
---
The variable or a field is not assigned in locked context as it is in other places

# Impact

A shared variable is protected by a mutex in most of the code, but at least one
access path reads or writes it without holding the same lock. The unprotected
access forms a data race with the protected ones. Because writes are no longer
serialized, two threads can interleave a read-modify-write and lose an update,
observe a half-updated value (a torn read of a multi-word field), or act on a
value that has already become stale. In languages with weak or no defined
behaviour for races (C and C++), the result is undefined behaviour: the compiler
is free to assume the object is not concurrently modified, so it may cache the
value in a register, reorder accesses, or fold checks away entirely. The visible
symptoms range from rare, non-reproducible logic errors to corrupted invariants
and crashes that only appear under load.

# Vulnerability potential

This issue has limited but real security relevance.

1. A torn read/write of a pointer, length, or size field can desynchronize a
   buffer from its bookkeeping, which in native code can be escalated to an
   out-of-bounds access or use-after-free.
2. If the inconsistently locked variable is a flag that gates a security
   decision (authenticated, is_admin, validated), a race window can let one
   thread observe a transient state and bypass the check.
3. The non-determinism makes the bug hard to test for, so it tends to survive
   into production where it can be triggered by timing-dependent input.

# Technical details

A mutex only provides mutual exclusion among threads that all acquire it. The
guarantee is conventional, not enforced by the type system in most languages:
the compiler and CPU do not know that field `x` "belongs to" lock `m`. Correct
synchronization requires that *every* access to the shared datum is performed
under the *same* lock. A single path that touches the variable without the lock
breaks the happens-before chain that the mutex would otherwise establish.

## C/C++ memory model

Under the C11/C++11 memory model, two accesses to the same non-atomic object
where at least one is a write, not ordered by happens-before, constitute a data
race and the entire program has undefined behaviour. The unlocked access is
exactly such an access. Optimizers exploit the no-race assumption, so the
generated code may differ wildly from the naive expectation.

## Managed languages

In Java or Go a race does not invalidate the whole program, but it still yields
unspecified values: reads may see stale or out-of-thin-air-like values, and
non-atomic 64-bit or composite fields can tear.

# Catching the issue

## Thread sanitizer

Build with ThreadSanitizer (`-fsanitize=thread` in Clang/GCC, `go test -race`,
`go build -race`). TSan instruments memory accesses and reports the conflicting
locked and unlocked accesses with both stack traces, which pinpoints the
offending path.

## Static analysis / annotations

Use Clang's thread-safety analysis: annotate the field with
`GUARDED_BY(mutex)` and functions with `REQUIRES`/`EXCLUDES`. The compiler then
flags any access not holding the declared lock at compile time. Coverity,
PVS-Studio, and similar tools detect lock-set inconsistencies heuristically.

## Code review

Establish a rule that each shared field is documented with the lock that guards
it, and grep for every access to confirm the lock is held. Prefer wrapping the
datum in a type that only exposes locked accessors (e.g. a monitor object,
Rust's `Mutex<T>`).

# How to reproduce

Observe that the final counter is below the expected total because one increment
path skips the lock. Run under `-fsanitize=thread` to see the race report.

```c
#include <pthread.h>
#include <stdio.h>

static pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;
static long counter = 0;

static void *locked_inc(void *arg) {
    (void)arg;
    for (int i = 0; i < 100000; i++) {
        pthread_mutex_lock(&m);
        counter++;
        pthread_mutex_unlock(&m);
    }
    return NULL;
}

static void *unlocked_inc(void *arg) { /* inconsistent: no lock here */
    (void)arg;
    for (int i = 0; i < 100000; i++)
        counter++;
    return NULL;
}

int main(void) {
    pthread_t a, b;
    pthread_create(&a, NULL, locked_inc, NULL);
    pthread_create(&b, NULL, unlocked_inc, NULL);
    pthread_join(a, NULL);
    pthread_join(b, NULL);
    printf("counter = %ld (expected 200000)\n", counter);
    return 0;
}
```
