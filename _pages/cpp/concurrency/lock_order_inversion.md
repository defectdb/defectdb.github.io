---
title: "Mutexes acquired in inconsistent order"
author: Maxim Menshikov
layout: defect
permalink: /cpp/concurrency/lock_order_inversion
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
Another function in this translation unit acquires the same pair of mutexes in the opposite order; concurrent execution of the two paths can deadlock

# Impact

Two code paths lock the same pair of mutexes in opposite orders: one takes A
then B, the other takes B then A. If thread 1 holds A and is waiting for B at
the same moment thread 2 holds B and is waiting for A, neither can proceed —
a classic AB-BA deadlock. Both threads (and anything that later needs either
mutex) hang forever. The bug is timing-dependent, so it usually passes testing
and strikes intermittently in production under load, which makes it expensive
to diagnose. The protected resources become permanently unavailable and, in a
server, the stuck threads accumulate until throughput collapses.

# Vulnerability potential

An availability defect with no direct memory-safety impact.

1. When the two orderings are reachable from external input (e.g. a
   "transfer(a, b)" handler locks accounts in argument order, so concurrent
   `transfer(x, y)` and `transfer(y, x)` requests invert the order), an
   attacker can deliberately issue the crossing pair to provoke the deadlock on
   demand — a targeted denial of service.
2. Nothing is read or written out of bounds; confidentiality and integrity are
   not affected by the deadlock itself, so the security weight is low while the
   DoS weight is real.

# Technical details

## The ordering invariant

Deadlock-free locking requires a single global order: every thread that holds
more than one lock at a time must acquire them in the same sequence. An
inversion violates that invariant for one specific pair, which is all the
Coffman conditions need (mutual exclusion, hold-and-wait, no preemption,
circular wait) to permit a cycle.

## Fixes

- **Acquire both atomically.** `std::scoped_lock lk(m1, m2);` (or
  `std::lock(m1, m2)`) uses a deadlock-avoidance algorithm and locks the whole
  set without committing to an order — the idiomatic C++17 solution.
- **Impose a fixed order.** Lock by a stable key such as the mutex's address
  (`if (&a < &b) lock a,b else lock b,a`) so symmetric operations like
  `transfer(a,b)` and `transfer(b,a)` agree.
- **Reduce lock scope** so only one lock is ever held at a time, eliminating the
  hold-and-wait condition.

## Hidden inversions

The opposing order is often not visible locally: method A holds its lock and
calls into another object that locks its own mutex, while a callback runs the
reverse. Lock-order bugs therefore span call graphs, not just single functions.

# Catching the issue

## ThreadSanitizer

TSan tracks lock-acquisition order across the run and reports a
"lock-order-inversion (potential deadlock)" with both orderings' stacks even
when the deadlock did not actually occur in that execution — the best detector
for this class.

## Static analysis / annotations

Clang thread-safety analysis with `ACQUIRED_BEFORE`/`ACQUIRED_AFTER`
annotations enforces a declared lock order at compile time. Coverity and
PVS-Studio have lock-order checkers. Helgrind/DRD (Valgrind) detect it
dynamically as well.

## Design

Prefer `std::scoped_lock` for any site that needs two or more mutexes, and
document a global lock hierarchy that review enforces.

# How to reproduce

Run with two threads; `t1` locks a→b while `t2` locks b→a. Under
`-fsanitize=thread` it reports a lock-order inversion, and in practice the
threads can hang.

```cpp
#include <mutex>
#include <thread>

std::mutex a, b;

void path1() {                       // a then b
    std::lock_guard<std::mutex> la(a);
    std::lock_guard<std::mutex> lb(b);
}

void path2() {                       // BUG: b then a -> AB-BA inversion
    std::lock_guard<std::mutex> lb(b);
    std::lock_guard<std::mutex> la(a);
}

int main() {
    std::thread t1(path1), t2(path2);
    t1.join();
    t2.join();
    // Fix: use std::scoped_lock lk(a, b); in both paths.
}
```
