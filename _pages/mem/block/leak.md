---
title: "Memory leak is possible"
author: Maxim Menshikov
layout: defect
permalink: /mem/block/leak
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: mem.block
group:
   - mem
   - block
---
The memory by the pointer might be leaking

# Impact

A memory leak is allocated memory that is never released and is no longer
reachable, so it can never be freed. A single leaked block is harmless, but a
leak on a repeated path — a request handler, a loop, an event callback — makes
the process's resident set grow without bound. Over time this causes increased
paging and slowdowns, allocation failures, the OOM killer terminating the
process (or an unrelated process) on Linux, and eventually a crash or hang. The
defect is silent: there is no immediate error, only a slow degradation that
typically manifests in production after hours or days of uptime, which makes it
costly to diagnose.

# Vulnerability potential

A leak does not corrupt memory, so its direct security weight is low; the real
risk is availability.

1. If an attacker can repeatedly trigger the leaking path (e.g. a request that
   leaks a few KB each time), they drive the process to exhaust memory and
   crash — a classic resource-exhaustion Denial-of-Service (CWE-401).
2. On a shared host the OOM killer may terminate a *different*, innocent process
   when memory runs out, widening the blast radius.
3. Leaks of buffers that held secrets can prolong the time sensitive data stays
   in memory, marginally increasing exposure, but this is secondary.

There is no memory-corruption or code-execution path, so the vulnerability
severity is low while the DoS severity is meaningful.

# Technical details

Manual memory management requires every successful allocation to have exactly
one matching deallocation on every path. A leak occurs when that pairing is
broken.

## Common causes

Losing the only pointer to a block (overwriting it, or letting it go out of
scope) before freeing; early `return`/`break`/exception between `malloc` and
`free`; forgetting to free on an error path; `realloc` to a temporary that is
discarded on failure (`p = realloc(p, n)` leaks the original if `realloc`
returns null); and reference cycles with `std::shared_ptr` (two objects
referencing each other never reach refcount zero).

## Not just heap memory

The same pattern applies to file descriptors, sockets, mutexes, and OS handles;
these "handle leaks" exhaust their own limited tables and are often more damaging
than RAM leaks.

## Why GC does not fully solve it

Even garbage-collected runtimes leak logically: an object kept reachable by a
forgotten reference (a growing cache, an un-removed listener) is never
collected.

# Catching the issue

## LeakSanitizer / AddressSanitizer

`-fsanitize=address` (which bundles LeakSanitizer) reports still-reachable and
definitely-lost allocations with their allocation stack traces at program exit.
LSan can also run standalone (`-fsanitize=leak`).

## Valgrind

`valgrind --leak-check=full --show-leak-kinds=all` categorises leaks (definitely
/indirectly/possibly lost) and points to the allocation site.

## Static analysis

Clang Static Analyzer (`unix.Malloc`), Coverity, Cppcheck, and PVS-Studio find
many leaks on error paths without running the program.

## Monitoring and design

Watch RSS over time in long-running services; a steadily rising baseline signals
a leak. Prevent leaks structurally with RAII / `std::unique_ptr` /
`std::shared_ptr` in C++, `goto cleanup` single-exit patterns in C, and by
breaking `shared_ptr` cycles with `weak_ptr`.

# How to reproduce

Compile with `-fsanitize=address` and run; on exit LeakSanitizer reports the
blocks allocated in the loop and never freed.

```c
#include <stdlib.h>

int main(void)
{
    for (int i = 0; i < 1000; i++) {
        int *p = malloc(1024);  /* allocated each iteration */
        if (p) p[0] = i;
        /* p goes out of scope without free(): leaked */
    }
    return 0;   /* ~1 MB lost */
}
```

