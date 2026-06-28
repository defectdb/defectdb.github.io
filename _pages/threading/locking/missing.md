---
title: "Missing locking in thread"
author: Maxim Menshikov
layout: defect
permalink: /threading/locking/missing
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
Synchronization is missing for given variable access

# Impact

A variable shared between threads is accessed with no synchronization at all:
no mutex, no atomic operation, no memory barrier. Concurrent writes, or a write
concurrent with a read, race. Updates are lost, reads observe partially written
or stale values, and composite invariants (for example a pointer paired with a
length) are seen in inconsistent intermediate states. Because the accesses are
not ordered, one thread may never observe another thread's write at all: a spin
loop on an un-synchronized flag can hang forever. In native code this is
undefined behaviour and the optimizer may hoist the load out of the loop,
turning a "should eventually stop" into an infinite loop or a crash.

# Vulnerability potential

This issue has limited but real security relevance.

1. Unsynchronized access to size/length/index fields can corrupt container
   bookkeeping and lead to out-of-bounds reads or writes in native code.
2. A free performed on one thread racing with use on another is a classic
   use-after-free / double-free, directly exploitable for memory corruption.
3. A loop that waits on an un-synchronized flag may never see the update and
   hang, contributing to denial of service.

# Technical details

Synchronization serves two purposes: mutual exclusion (only one thread in the
critical section) and visibility/ordering (one thread's writes become visible to
another in a well-defined order). Omitting it loses both. Modern CPUs and
compilers freely reorder and cache memory operations on the assumption that no
other thread is observing the same location; that assumption is exactly what is
violated here.

## Why a missing lock differs from an inconsistent one

With inconsistent locking, one path is wrong; with missing locking, *no* path
synchronizes, so the race is essentially guaranteed under concurrency rather
than being a narrow window. Even single-word accesses that look "atomic" on a
given CPU are not guaranteed atomic by the language and may still be reordered.

## Correct alternatives

Guard the variable with a mutex, or make it an atomic type
(`std::atomic<T>`, C11 `_Atomic`, Go's `sync/atomic`, Java `volatile`/`Atomic*`)
with an explicit memory ordering. For a one-time signal between threads,
condition variables or channels provide the necessary ordering.

# Catching the issue

## ThreadSanitizer

`-fsanitize=thread` (C/C++) and `-race` (Go) instrument loads and stores and
report unsynchronized conflicting accesses with both stacks. This is the most
reliable dynamic detector.

## Static analysis

Clang thread-safety annotations (`GUARDED_BY`) flag accesses to a guarded field
that hold no lock. Coverity and PVS-Studio detect shared variables touched
without consistent locking. Helgrind/DRD (Valgrind) detect missing
happens-before relations at runtime.

## Review practice

Treat every variable reachable from more than one thread as requiring an
explicit synchronization decision documented at the declaration; absence of a
decision is the bug.

# How to reproduce

Observe that the worker may spin forever (or only stop with optimizations off)
because the un-synchronized `stop` flag write is not guaranteed visible.

```c
#include <pthread.h>
#include <stdio.h>
#include <unistd.h>

static int stop = 0; /* shared, no synchronization */

static void *worker(void *arg) {
    (void)arg;
    long iterations = 0;
    while (!stop)        /* compiler may hoist this load out of the loop */
        iterations++;
    printf("stopped after %ld iterations\n", iterations);
    return NULL;
}

int main(void) {
    pthread_t t;
    pthread_create(&t, NULL, worker, NULL);
    sleep(1);
    stop = 1;            /* may never become visible to the worker */
    pthread_join(t, NULL);
    return 0;
}
```
