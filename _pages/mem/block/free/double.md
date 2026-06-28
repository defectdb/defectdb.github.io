---
title: "Double free"
author: Maxim Menshikov
layout: defect
permalink: /mem/block/free/double
arch:
   - native
vulnerability:
   - High
ddos:
   - Medium
group_full: mem.block.free
group:
   - mem
   - block
   - free
---
The memory by the pointer might be freed twice or more times

# Impact

Freeing the same block twice (CWE-415) corrupts the allocator's internal
bookkeeping. Between the two frees the block may have been handed out again to
satisfy a different allocation; the second `free` then returns *that* live
block's memory to the free list, so two parts of the program now believe they
own the same region. The allocator's free-list links — often stored inside the
freed chunk — get tangled, which leads to crashes (`malloc`/`free` aborting with
"double free or corruption"), silent heap corruption, and, in the hands of an
attacker, controlled writes. Like other heap bugs it is timing-dependent and may
appear far from the offending call.

# Vulnerability potential

Double-free is a high-severity, actively exploited corruption primitive.

1. By controlling the allocations between the two frees, an attacker can make
   the free list point where they choose; a subsequent `malloc` then returns a
   pointer into attacker-influenced memory, yielding an arbitrary-write
   primitive (the classic "fastbin dup" and related glibc techniques).
2. That write is commonly leveraged to overwrite a function pointer, GOT entry,
   or vtable, achieving remote code execution.
3. Two live pointers to the same block (the aliasing the second free creates)
   is itself a use-after-free situation enabling type confusion and info leaks.
4. At minimum, the corruption aborts the process — a Denial-of-Service.

# Technical details

`free(p)` records `p`'s chunk as available, typically by writing free-list
pointers into the chunk body. Calling `free(p)` again on a pointer that is
already free (or has been re-allocated) writes those bookkeeping pointers a
second time over memory whose state no longer matches, breaking the invariants
`malloc` relies on.

## How it arises

Two code paths both freeing the same pointer; freeing in a loop or error handler
that also runs in the normal path; two aliases to one allocation each freed by
its owner; freeing a `realloc`'d pointer and the original; and exception/`goto`
cleanup that double-runs.

## Allocator hardening

Modern glibc detects some cases ("double free or corruption (fasttop)") and many
allocators (glibc tcache with `tcache_double_free` detection, hardened_malloc,
Windows LFH) add checks — but these are best-effort and bypassable, not a
substitute for correct code.

## The null trick

`free(NULL)` is defined as a no-op, so setting a pointer to `NULL` right after
freeing turns an accidental second free into a harmless no-op. Free exactly
once, and clear the pointer.

# Catching the issue

## AddressSanitizer

`-fsanitize=address` reports `attempting double-free` with the stack traces of
both frees and the original allocation — the fastest way to pinpoint it.

## Valgrind

Memcheck reports "Invalid free() / delete / delete[]" on the second free,
identifying both the bad free and the first one.

## Static analysis

Clang Static Analyzer (`unix.Malloc`), Coverity, Cppcheck, and PVS-Studio find
many double-free paths, especially around error handling.

## Design

Single ownership via `std::unique_ptr`; set pointers to `NULL`/`nullptr` after
freeing; never free through more than one alias; centralise cleanup with a
single-exit pattern; avoid mixing manual `free` with smart-pointer ownership of
the same block.

# How to reproduce

Compile with `-fsanitize=address` and run; ASan reports an attempting
double-free with both free stack traces.

```c
#include <stdlib.h>

int main(void)
{
    int *p = malloc(sizeof *p);
    *p = 1;

    free(p);   /* first free — fine */
    free(p);   /* second free of the same pointer — corruption */
    return 0;
}
```

