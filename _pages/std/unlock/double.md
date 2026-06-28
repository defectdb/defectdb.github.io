---
title: "Double unlock"
author: Maxim Menshikov
layout: defect
permalink: /std/unlock/double
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: std.unlock
group:
   - std
   - unlock
---
The mutex is unlocked twice or more times successfully

# Impact

A mutex is unlocked, then unlocked again while it is already free (or while owned
by a different thread). For a default ``pthread_mutex_t`` this is undefined
behavior. The dangerous outcome is not the redundant call itself but the window
it implies: the second unlock can release a lock that another thread has, in the
meantime, acquired — so two threads now believe they hold the same mutex and run
the protected critical section concurrently. That breaks mutual exclusion and
opens the door to data races and the corruption the mutex was meant to prevent.
Depending on the implementation the extra unlock may also leave the mutex's
internal state inconsistent (e.g. a futex word or owner field driven below its
valid range), which can cause later lock operations to misbehave or crash.

# Vulnerability potential

The defect is mainly an availability and correctness hazard, with a secondary
memory-safety angle.

1. Releasing a mutex another thread thinks it owns collapses mutual exclusion,
   producing data races on the guarded structure — a classic precursor to
   use-after-free, double-free or torn writes that can become exploitable.
2. Corrupting the mutex's internal bookkeeping can wedge subsequent locking,
   hanging threads that wait on it and denying service.
3. The behavior is undefined, so on some implementations the second unlock simply
   crashes the process.

# Technical details

POSIX states that unlocking a mutex the calling thread does not own, or unlocking
an already-unlocked mutex, is undefined for a normal mutex. Implementations
differ in how loudly they fail:

## PTHREAD_MUTEX_NORMAL / default

No owner check. The second ``pthread_mutex_unlock`` may decrement or rewrite the
futex/owner state even though the mutex is free, leaving it corrupted; a
concurrently acquired lock can be spuriously released.

## PTHREAD_MUTEX_ERRORCHECK

Records the owner and returns ``EPERM`` when a non-owner or repeated unlock is
attempted, making the bug detectable instead of silent.

## PTHREAD_MUTEX_RECURSIVE

Maintains a count; one unlock too many drives the count negative or releases a
level that was never taken, again undefined.

The same hazard exists for C++ ``std::mutex`` (unlocking when not owned is UB —
RAII ``std::lock_guard``/``std::unique_lock`` exist precisely to avoid manual
double-unlock) and Windows ``ReleaseMutex`` (which returns failure for a
non-owner).

# Catching the issue

## Runtime

ThreadSanitizer flags ``unlock of an unlocked mutex`` and mismatched
lock/unlock. Helgrind/DRD report releasing a mutex that is not held by the
caller. Use ``PTHREAD_MUTEX_ERRORCHECK`` in test builds and assert that unlock
returns ``0``.

## Static analysis and design

Clang Thread Safety Analysis, Coverity and PVS-Studio track unbalanced
lock/unlock paths, which commonly arise from early ``return``/``goto`` in error
handling. Prefer RAII scope guards (C++) or ``pthread_cleanup_push`` so each
unlock is paired structurally with exactly one lock.

# How to reproduce

Build with ``-fsanitize=thread``; TSan reports the unlock of an already-unlocked
mutex.

```c
#include <pthread.h>
#include <stdio.h>

int main(void)
{
    pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;

    pthread_mutex_lock(&m);
    pthread_mutex_unlock(&m);
    printf("rc of second unlock: %d\n", pthread_mutex_unlock(&m)); /* UB */

    return 0;
}
```
