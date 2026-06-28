---
title: "Lock not locked"
author: Maxim Menshikov
layout: defect
permalink: /std/unlock/not_locked
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
The mutex is not locked when unlocking

# Impact

A thread calls unlock on a mutex that is not currently locked, or that is locked
by a *different* thread. POSIX makes both cases undefined for a default mutex.
The visible effect is a violation of the ownership discipline mutexes rely on:
unlocking a mutex held by another thread hands that thread's critical section to
everyone, so two or more threads execute protected code at once and race on the
data it guards. Unlocking a never-locked mutex tends to drive its internal
counter or futex word out of its valid range, leaving the mutex in a state where
later locks deadlock, return errors, or are granted incorrectly. The defect
usually originates in error-handling paths that unlock without a matching lock,
or in code that unlocks based on a flag that was set wrong.

# Vulnerability potential

Like the other mutex misuse defects, this is chiefly an availability and
correctness issue with a secondary memory-safety tail.

1. Releasing a lock the caller does not own destroys mutual exclusion, allowing
   concurrent access to the protected structure and the races (use-after-free,
   double-free, torn state) that can follow.
2. Corrupting the mutex's bookkeeping can wedge future lock attempts, hanging
   threads and denying service.
3. The operation is undefined, so on stricter implementations it aborts the
   process outright.

# Technical details

Mutual exclusion depends on the rule that a mutex is unlocked only by the thread
that locked it, and only while it is held. Whether a violation is caught depends
on the mutex type:

## PTHREAD_MUTEX_NORMAL / default

There is no ownership record, so the runtime cannot tell that the caller never
locked the mutex; it performs the release anyway, with undefined results on the
mutex state and on any other thread that holds it.

## PTHREAD_MUTEX_ERRORCHECK

The owner is tracked, so unlocking an unlocked mutex or one owned by another
thread returns ``EPERM`` rather than corrupting state — ideal for catching the
bug in testing.

The same ownership requirement holds for C++ ``std::mutex`` (unlocking a
non-owned mutex is UB), C11 ``mtx_unlock``, and Windows ``ReleaseMutex`` (which
fails with ``ERROR_NOT_OWNER`` for a non-owner). RAII guards exist specifically
so that an unlock cannot happen without a preceding lock on the same path.

# Catching the issue

## Runtime

ThreadSanitizer reports ``unlock of an unlocked mutex`` and unlocks by a
non-owning thread. Helgrind and DRD flag the same. Switching test builds to
``PTHREAD_MUTEX_ERRORCHECK`` converts the undefined behavior into an observable
``EPERM`` you can assert on.

## Static analysis and design

Clang Thread Safety Analysis (``-Wthread-safety``), Coverity and PVS-Studio
track lock/unlock balance per control-flow path and flag an unlock with no
dominating lock. Structurally pair locks and unlocks with scope guards
(``std::lock_guard``) or ``pthread_cleanup_push`` to make the defect impossible.

# How to reproduce

Build with ``-fsanitize=thread`` or use an error-checking mutex; the unlock of a
freshly initialized, never-locked mutex is reported (or returns ``EPERM``).

```c
#include <pthread.h>
#include <stdio.h>

int main(void)
{
    pthread_mutexattr_t a;
    pthread_mutex_t     m;

    pthread_mutexattr_init(&a);
    pthread_mutexattr_settype(&a, PTHREAD_MUTEX_ERRORCHECK);
    pthread_mutex_init(&m, &a);

    /* Unlock without ever locking. */
    printf("rc: %d (EPERM expected)\n", pthread_mutex_unlock(&m));

    return 0;
}
```
