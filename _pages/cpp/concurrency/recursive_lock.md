---
title: "Recursive lock on non-recursive mutex"
author: Maxim Menshikov
layout: defect
permalink: /cpp/concurrency/recursive_lock
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: cpp.concurrency
group:
   - cpp
   - concurrency
---
The same mutex is locked twice in this function without an intervening unlock; with std::mutex (non-recursive) the second lock deadlocks

# Impact

`std::mutex` is non-recursive: a thread that already owns it and tries to lock
it again has undefined behavior, which in every mainstream implementation means
the thread blocks forever waiting for itself. Whatever data the mutex protects
is now permanently inaccessible to every other thread, and the offending thread
never returns. Most often the double-lock is not on two adjacent lines but
hidden: a locked public method calls another locked public method, or a
callback fired while the lock is held re-enters the same object. The program
hangs — sometimes a single worker, sometimes the whole service once all threads
pile up behind the stuck mutex.

# Vulnerability potential

The defect is an availability problem.

1. A reachable self-deadlock is a denial-of-service primitive: if an attacker
   can drive the program onto the re-entrant path (e.g. a request that makes a
   locked handler invoke another locked handler on the same object), one
   request can wedge a worker thread; enough of them exhaust the thread pool
   and take the service down.
2. It has essentially no memory-safety dimension on its own — nothing is
   corrupted, the thread simply stops — so the confidentiality/integrity weight
   is low.

# Technical details

## Why std::mutex deadlocks

`std::mutex::lock()` on a mutex the calling thread already holds is UB
(`[thread.mutex.requirements.mutex]`). Implementations back it with a futex /
`pthread_mutex_t` of the default (non-recursive) kind, so the second `lock()`
sees the mutex owned and the thread parks waiting for an unlock that, by
construction, only that same parked thread could issue.

## std::recursive_mutex is not a free fix

`std::recursive_mutex` permits the same thread to lock N times (and requires N
unlocks). It makes the re-entrant call *work*, but reaching for it is usually a
smell: it hides a tangled locking design where invariants may be observed
half-updated during the re-entrant call. Prefer restructuring: split each
public method into a thin locking wrapper and a private `_locked` core that
assumes the lock is held, and have internal callers use the core.

## RAII does not save you

`std::lock_guard`/`std::unique_lock` prevent *missing* unlocks, not double
locks: two guards on the same `std::mutex` in one call stack still deadlock on
construction of the second.

# Catching the issue

## ThreadSanitizer

TSan (`-fsanitize=thread`) reports a "double lock of a mutex" / deadlock when
the same non-recursive mutex is locked twice by one thread, with both stack
traces.

## Static analysis

Clang's thread-safety analysis (`-Wthread-safety` with `GUARDED_BY` /
`REQUIRES` annotations) flags a function that re-acquires a capability it
already holds. clang-tidy and Coverity have dedicated self-deadlock checks.

## Design / review

Adopt the "public locks, private assumes-locked" convention and forbid calling
a public (locking) method from inside a locked region. Code review should treat
any call made while a `lock_guard` is alive as suspect for re-entry.

# How to reproduce

Run it: `Account::transfer` locks the mutex and then calls `balance()`, which
locks the same `std::mutex` again — the program hangs on the second lock.

```cpp
#include <mutex>

struct Account {
    std::mutex m;
    long cents = 0;

    long balance() {
        std::lock_guard<std::mutex> g(m);    // second lock of the same mutex
        return cents;
    }

    void transfer(long amount) {
        std::lock_guard<std::mutex> g(m);    // first lock
        if (balance() >= amount)             // BUG: re-enters -> self-deadlock
            cents -= amount;
    }
};

int main() {
    Account a;
    a.transfer(100);                          // hangs
}
```
