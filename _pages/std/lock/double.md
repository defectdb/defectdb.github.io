---
title: "Double lock"
author: Maxim Menshikov
layout: defect
permalink: /std/lock/double
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: std.lock
group:
   - std
   - lock
---
The mutex is locked twice or more times successfully

# Impact

A thread locks the same mutex a second time without releasing it first. For a
default (non-recursive) ``pthread_mutex_t`` the standard makes the second lock
attempt by the owning thread undefined behavior; with the ``PTHREAD_MUTEX_NORMAL``
type the canonical result is **self-deadlock** — the thread blocks forever
waiting for a lock it already holds, and any other thread that later needs the
mutex blocks behind it. A subsystem, or the whole process, hangs. If the mutex is
explicitly recursive (``PTHREAD_MUTEX_RECURSIVE``) the second lock succeeds and
bumps an owner count, which avoids the deadlock but usually hides a logic error:
the code's invariants probably assumed the critical section was entered once, and
the recursion count must be matched by an equal number of unlocks or the mutex is
never released.

# Vulnerability potential

The defect is primarily an availability problem rather than a memory-safety one.

1. A self-deadlock freezes the thread and cascades to every thread contending for
   the mutex, a denial-of-service condition an attacker can trigger by steering
   execution down the re-locking path.
2. With error-checking mutexes the second lock returns ``EDEADLK``; if that
   return value is ignored, the code proceeds believing it holds the lock when
   the lock state is inconsistent, which can corrupt the data the mutex was
   meant to protect — an indirect, low-likelihood security risk.

# Technical details

A POSIX mutex has a type attribute that decides the re-lock behavior:

## PTHREAD_MUTEX_NORMAL / default

No owner or recursion tracking. Re-locking deadlocks (or is plainly undefined).
This is the default for ``PTHREAD_MUTEX_INITIALIZER`` on Linux/glibc.

## PTHREAD_MUTEX_ERRORCHECK

The implementation records the owner and returns ``EDEADLK`` instead of
deadlocking, making the bug observable at the cost of a check on every lock.

## PTHREAD_MUTEX_RECURSIVE

Keeps an ownership count; nested locks succeed and must be balanced by the same
number of ``pthread_mutex_unlock`` calls. Convenient but easy to leave
unbalanced.

Equivalent rules apply to C11 ``mtx_t`` (``mtx_plain`` vs ``mtx_recursive``),
Windows ``CRITICAL_SECTION`` (recursive by design) and C++ ``std::mutex``
(non-recursive — re-locking is UB) versus ``std::recursive_mutex``.

# Catching the issue

## Runtime

ThreadSanitizer (``-fsanitize=thread``) detects double-lock/lock-order problems.
Helgrind and DRD (Valgrind tools) report a thread relocking a mutex it already
holds. Using ``PTHREAD_MUTEX_ERRORCHECK`` during testing turns the latent
deadlock into a returned ``EDEADLK`` you can assert on.

## Static analysis

Clang Thread Safety Analysis (``-Wthread-safety`` with capability annotations),
Coverity and PVS-Studio track lock/unlock pairing and flag a lock held across a
second acquisition. Always check the return value of locking calls.

# How to reproduce

Run under a single thread; the program prints the first message and then hangs
on the second lock.

```c
#include <pthread.h>
#include <stdio.h>

int main(void)
{
    pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER; /* non-recursive */

    pthread_mutex_lock(&m);
    printf("locked once\n");
    fflush(stdout);

    pthread_mutex_lock(&m); /* self-deadlock: blocks forever */
    printf("locked twice (never reached)\n");

    pthread_mutex_unlock(&m);
    pthread_mutex_unlock(&m);
    return 0;
}
```
