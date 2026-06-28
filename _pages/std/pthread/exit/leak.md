---
title: "pthread_exit() might cause leaks"
author: Maxim Menshikov
layout: defect
permalink: /std/pthread/exit/leak
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Medium
group_full: std.pthread.exit
group:
   - std
   - pthread
   - exit
---
pthread_exit() might cause leaks

# Impact

``pthread_exit`` terminates the calling thread immediately, unwinding only what
the POSIX cleanup machinery knows about. Any resource the thread owns that is not
registered with a cleanup handler is simply abandoned: heap blocks it allocated,
file descriptors and sockets it opened, mutexes it still holds, and — crucially —
C++ automatic objects whose destructors would have run on a normal ``return``.
Because ``pthread_exit`` does a non-local exit, local variables go out of scope
without their destructors firing on many implementations, so RAII-managed memory,
locks and handles leak. A long-running process that spawns and exits many threads
this way accumulates leaks until it exhausts memory, descriptors or lock state.
A held mutex that is never unlocked is worse than a memory leak: it can deadlock
every other thread that needs it.

# Vulnerability potential

The defect contributes to denial of service and, through leaked locks, to
correctness/safety failures.

1. Steady resource leakage (memory, file descriptors, thread-stack space for
   detached threads) under attacker-driven request volume drives the process to
   exhaustion and crash — a denial-of-service vector.
2. A mutex abandoned while held deadlocks all contending threads, hanging the
   subsystem or process.
3. Leaked sensitive buffers that are never freed (and thus never scrubbed) linger
   in memory longer than intended, a minor information-exposure risk; abandoned
   file descriptors can also keep privileged resources open.

# Technical details

``pthread_exit`` runs the thread's cleanup-handler stack
(``pthread_cleanup_push``/``pop``) and thread-specific-data destructors, then
frees the thread's own stack only if the thread was *joined* or *detached*
correctly. What it does **not** do is run arbitrary unwinding for resources the
program forgot to register.

## C vs C++

In C, only resources tied to ``pthread_cleanup_push`` handlers and TSD
destructors are released; raw ``malloc`` blocks and open descriptors leak. In
C++, whether automatic-object destructors run during ``pthread_exit`` is
implementation-defined — glibc implements ``pthread_exit`` via forced unwinding
so destructors often *do* run, but this is not guaranteed by POSIX and does not
hold on every platform, so relying on it is non-portable. Mixing ``pthread_exit``
with C++ objects is therefore fragile.

## Detached vs joinable

A joinable thread that exits keeps its stack and exit status reserved until some
thread calls ``pthread_join``; if no one ever joins, that memory leaks for the
life of the process. Detached threads free their resources automatically but
leave any joiner with a dangling reference.

## main()

Calling ``pthread_exit`` from ``main`` keeps the process alive until all other
threads finish (instead of terminating them via the normal ``return``), which can
strand resources and is a frequent source of confusion.

# Catching the issue

## Runtime

Valgrind/Memcheck and LeakSanitizer (``-fsanitize=leak``, bundled with ASan)
report blocks still reachable/lost at thread or process exit. Run leak detection
in a loop that repeatedly spawns and ``pthread_exit``s threads to surface
per-thread growth.

## Static analysis and design

Coverity, Clang Static Analyzer and PVS-Studio flag resources that escape a
function via ``pthread_exit`` without release. Prefer returning normally from the
thread function so RAII and the natural control flow free everything; register
every unguarded resource with ``pthread_cleanup_push`` if an early
``pthread_exit`` is unavoidable, and always unlock mutexes before exiting.

# How to reproduce

Run under Valgrind (``valgrind --leak-check=full``); the block allocated before
``pthread_exit`` is reported as definitely lost.

```c
#include <pthread.h>
#include <stdlib.h>

static void *worker(void *arg)
{
    (void)arg;
    char *buf = malloc(1024); /* not registered with any cleanup handler */
    (void)buf;
    pthread_exit(NULL);       /* buf is leaked: never freed */
}

int main(void)
{
    pthread_t t;
    pthread_create(&t, NULL, worker, NULL);
    pthread_join(t, NULL);
    return 0;
}
```
