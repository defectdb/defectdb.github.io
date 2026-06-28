---
title: "Too many threads or light-weight processes"
author: Maxim Menshikov
layout: defect
permalink: /threading/thread/too_many
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: threading.thread
group:
   - threading
   - thread
---
There might too many threads

# Impact

The program creates far more threads (or light-weight processes) than the
machine can usefully run. Each thread reserves a stack (commonly 1-8 MiB of
virtual address space by default) plus kernel bookkeeping, so thousands of
threads consume large amounts of memory and kernel resources. Once the count
exceeds the number of CPUs by a wide margin, performance degrades rather than
improves: the scheduler spends its time context-switching, caches thrash, and
lock contention rises. In the worst case `pthread_create` fails with `EAGAIN`,
`std::thread` throws, the process hits `RLIMIT_NPROC`/`threads-max`, or the
machine starts swapping and becomes unresponsive, taking down unrelated services
on the same host.

# Vulnerability potential

This issue is primarily a denial-of-service concern.

1. If the number of threads is driven by external input (one thread per
   connection, per request, or per file), an attacker can force unbounded thread
   creation and exhaust memory, PIDs, or the system-wide thread limit, denying
   service to the whole machine.
2. Thread-creation failures are often unchecked; the resulting null/invalid
   thread handle or ignored error can push the program down an untested error
   path. The direct memory-safety risk is otherwise low.

# Technical details

A thread is not free. On Linux a thread is a task sharing the address space; it
needs a stack, a kernel `task_struct`, and a slot subject to `RLIMIT_NPROC`,
`RLIMIT_STACK`, and `/proc/sys/kernel/threads-max`. Useful parallelism is bounded
by the number of hardware execution contexts; beyond that, additional threads
add overhead without adding throughput.

## Oversubscription

Running many more runnable threads than CPUs ("oversubscription") increases
context-switch and cache-miss costs. CPU-bound work scales best near one thread
per core; blocking/IO-bound work tolerates more, but should still be bounded by
a pool, not created ad hoc.

## Thread-per-task antipattern

Spawning a fresh thread for every unit of work (request, connection, item)
couples resource usage to workload size with no ceiling. The standard fix is a
fixed-size thread pool or a work-queue with a bounded number of workers, or an
async/event-driven model. Go's goroutines are far cheaper than OS threads, but
even there an unbounded number of goroutines exhausts memory and scheduler time,
so the same bounding discipline applies.

# Catching the issue

## Runtime limits and observability

Set `RLIMIT_NPROC` and a sane `RLIMIT_STACK` so runaway creation fails fast and
visibly. Monitor thread count (`/proc/<pid>/status` `Threads:`, `ps -L`,
`top -H`). Always check the return value of `pthread_create`/`std::thread`
construction.

## Static analysis and review

Flag thread creation inside loops whose bound is input-derived. Code review rule:
threads come from a bounded pool, not from per-item spawning. Tools such as
Coverity and PVS-Studio flag unbounded resource acquisition patterns.

## Load testing

Stress the service with many concurrent connections/requests and watch the
thread count and memory; a linear, unbounded climb confirms the defect.

# How to reproduce

Observe memory growth and eventual `pthread_create` failure (EAGAIN) as the loop
creates threads without bound and never joins them.

```c
#include <pthread.h>
#include <stdio.h>
#include <string.h>

static void *idle(void *arg) {
    (void)arg;
    pause();           /* never returns: each thread lives forever */
    return NULL;
}

int main(void) {
    for (long i = 0; ; i++) {
        pthread_t t;
        int rc = pthread_create(&t, NULL, idle, NULL);
        if (rc != 0) {
            printf("pthread_create failed after %ld threads: %s\n",
                   i, strerror(rc));
            break;
        }
        pthread_detach(t);
    }
    return 0;
}
```
