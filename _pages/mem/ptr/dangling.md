---
title: "Dangling pointer"
author: Maxim Menshikov
layout: defect
permalink: /mem/ptr/dangling
arch:
   - native
vulnerability:
   - High
ddos:
   - Medium
group_full: mem.ptr
group:
   - mem
   - ptr
---
The memory by the pointer might be used after freeing

# Impact

A dangling pointer still holds the address of an object whose lifetime has
ended — memory that was `free`d/`delete`d, a stack frame that has returned, or a
container element that was reallocated. Dereferencing it is use-after-free
(CWE-416), which is undefined behaviour. In the best case the old contents are
still intact and the program seems to work; more often the allocator has reused
that memory for an unrelated object, so the read returns another object's data
and the write corrupts it. Because the freed region may hold allocator metadata
or a new object's vtable, the corruption frequently leads to a crash or to fully
controllable behaviour — and the failure is intermittent, depending entirely on
allocation timing.

# Vulnerability potential

Use-after-free is among the most weaponised memory-safety defects, routinely
exploited in browsers and kernels.

1. After the object is freed, an attacker who can trigger a same-sized
   allocation can place controlled data where the stale pointer points (heap
   "grooming"/feng-shui), so the subsequent use operates on attacker bytes.
2. If the freed object contained a function pointer or C++ vtable, replacing it
   yields control-flow hijack and remote code execution.
3. A use-after-free read discloses whatever now occupies the memory (info leak,
   useful for defeating ASLR).
4. Even without a controlled reuse, the resulting corruption commonly crashes
   the process, a Denial-of-Service vector.

# Technical details

`free`/`delete` returns the memory to the allocator but does *not* change any
pointer that referenced it. Every such pointer is now dangling. The window of
exploitability opens the moment the memory is reused — by the same thread or by
another allocation anywhere in the program.

## Sources of dangling pointers

Heap: using a pointer after `free`/`delete`, or keeping a second alias after
freeing through the first. Stack: returning the address of a local variable, or
keeping a pointer to a local after its scope ends. Containers: holding a pointer
or iterator into a `std::vector` after it reallocates on growth, or into a
container element after `erase`. C strings: keeping a pointer into a buffer that
was `realloc`'d to a new address.

## Double-free and friends

A dangling pointer passed back to `free` is a double-free, a closely related and
equally exploitable corruption of allocator state.

## Mitigation idioms

Set pointers to `NULL`/`nullptr` immediately after freeing (turns a UAF into a
detectable null deref), and prefer ownership models — RAII, `std::unique_ptr`,
`std::shared_ptr`/`weak_ptr` — that tie lifetime to scope.

# Catching the issue

## AddressSanitizer

`-fsanitize=address` quarantines freed memory and reports use-after-free and
use-after-return (`ASAN_OPTIONS=detect_stack_use_after_return=1`) with both the
allocation and the free stack traces. This is the single most effective tool.

## Other dynamic tools

Valgrind/Memcheck flags reads/writes to freed blocks. MemorySanitizer catches
some uses of uninitialised reused memory. GWP-ASan provides low-overhead
sampling detection in production.

## Static analysis

Clang Static Analyzer, Coverity, Cppcheck, and PVS-Studio detect many
use-after-free paths, including return-of-local-address (also a plain compiler
warning: `-Wreturn-local-addr`, `-Wdangling-pointer` in recent GCC).

## Design

Use smart pointers and clear ownership; avoid raw owning pointers; null out
freed pointers; never return addresses of locals; re-fetch pointers/iterators
after any container operation that can reallocate.

# How to reproduce

Compile with `-fsanitize=address` and run; ASan reports a heap-use-after-free,
showing where the block was freed and where it was used.

```c
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int *p = malloc(sizeof *p);
    *p = 42;
    free(p);            /* p is now dangling */

    /* use-after-free: reads/writes memory that no longer belongs to us */
    *p = 7;
    printf("%d\n", *p);
    return 0;
}
```

