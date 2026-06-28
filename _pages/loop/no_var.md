---
title: "Missing loop variable"
author: Maxim Menshikov
layout: defect
permalink: /loop/no_var
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: loop
group:
   - loop
---
No influental variable is changed in this loop.

# Impact

The loop's continuation condition depends on state that the loop body never
changes. Nothing the loop does can ever make the condition false, so once entered
the loop runs forever (or until an external event, signal, or watchdog
intervenes). The thread that hit the loop stops making progress, CPU spins at
100%, and any resources it holds — locks, file handles, memory it keeps
allocating — are never released.

In a server this freezes a request handler or worker; in embedded or kernel code
it can wedge the whole device. Even when the loop is not strictly infinite, "no
influential variable changes" usually means the intended exit logic was lost in a
refactor and the code does not behave as written.

# Vulnerability potential

The dominant risk is denial of service.

1. If the loop is reachable with attacker-influenced input that selects the buggy
   path, a single request can pin a worker thread indefinitely. Repeating it
   exhausts the thread/connection pool and takes the service offline.
2. A spin loop holding a mutex or other shared resource can deadlock unrelated
   threads that wait on it, amplifying a local hang into a system-wide stall.

It is not itself a memory-safety or code-execution issue, so the security rating
is `Low`; the hang/resource-exhaustion behaviour drives the `Medium` DoS rating.

# Technical details

A terminating loop must, on every path through its body, move some state that the
condition reads toward the exit value. This defect is flagged when the analyzer
sees that none of the variables (or observable state) the condition reads are
modified inside the body.

## Common causes
- The increment/decrement was written on the wrong variable, or shadowed by a
  loop-local copy, so the counter the condition tests never advances.
- The update is present but unreachable — guarded by a branch that is never taken,
  or placed after a `continue`/`break` that always fires first.
- The condition reads a cached or by-value snapshot while the body updates a
  different object.
- A `while (running)` style flag is meant to be cleared by another thread, but the
  variable is not `volatile`/atomic and the compiler hoists the read, so the
  update is never observed.

## Undefined behaviour
In C and C++, a side-effect-free loop with a constant-true condition is special:
the standard permits the compiler to assume forward progress, so an optimizer may
remove or miscompile such a loop, producing surprising behaviour rather than a
clean hang.

# Catching the issue

## Compiler warnings
Modern GCC and Clang warn on some non-progressing loops; build with `-Wall
-Wextra` and review any "loop has no effect" / "variable not modified" notes.

## Static analysis
Tools such as clang-tidy, Cppcheck, Coverity and the analyzer that emits this
diagnostic perform data-flow on the condition variables and report when none are
written in the body. This is the most reliable detection.

## Runtime guards
Add a watchdog or iteration cap to loops bounded by external state, and assert
forward progress. For flags shared between threads, use `std::atomic` /
`volatile` plus proper synchronization so updates are observed.

## Review rule
Whenever a loop condition is non-constant, confirm by eye that the body has a path
that moves the tested state toward termination.

# How to reproduce

Run the program: it prints nothing further and spins forever because `i` (the
variable the condition reads) is never incremented.

```c
#include <stdio.h>

int main(void)
{
    int i = 0;
    int j = 0;

    /* The condition tests i, but the body only touches j: no influential
       variable changes, so the loop never terminates. */
    while (i < 10) {
        j = j + 1;
    }

    printf("done: %d\n", j);
    return 0;
}
```
