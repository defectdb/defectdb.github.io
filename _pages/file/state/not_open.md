---
title: "File is not open"
author: Maxim Menshikov
layout: defect
permalink: /file/state/not_open
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: file.state
group:
   - file
   - state
---
It is possible that the file is not open

# Impact

A file operation (`fread`, `fwrite`, `fprintf`, `fseek`, `fclose`) is performed on
a handle that may not be open. The usual cause is using the result of `fopen`
without checking it: when the open fails — missing file, wrong permissions, out of
descriptors — `fopen` returns `NULL`, and the subsequent call dereferences that
null `FILE*`, crashing the process. With raw descriptors the analogue is using an
`fd` of `-1` returned by a failed `open`, which makes every later `read`/`write`
fail with `EBADF`.

Either way the program proceeds on the false assumption that I/O succeeded:
expected data is never read or written, and in the null-`FILE*` case the program
terminates abruptly at the first use.

# Vulnerability potential

The exposure is limited.

1. **Denial of service.** Passing a `NULL` `FILE*` to `stdio` dereferences it and
   crashes the process. If an attacker can force the open to fail (deleting the
   file, exhausting descriptors, or pointing the path at something they control),
   they can turn that into a reliable crash.
2. **Silent data loss / wrong control flow.** Ignoring the failed-open state means
   "successful" writes that never land, or reads that leave a buffer
   uninitialized; downstream logic then acts on stale or garbage data, which can
   mildly weaken security decisions.

There is no memory corruption beyond the null dereference, so both ratings are
`Low`.

# Technical details

## `fopen` / `FILE*`
`fopen` returns `NULL` on failure and sets `errno`. The `FILE*` is opaque; passing
`NULL` to any `stdio` function is undefined behaviour and in practice
dereferences a null pointer inside libc, faulting immediately.

## POSIX descriptors
`open` returns `-1` on failure. Unlike a null `FILE*`, calling `read`/`write` on
`-1` does not crash — it returns `-1` with `errno == EBADF`. Code that ignores
those return values then loses the data silently, which is harder to notice than a
crash.

## Partially constructed state
The handle can also be "not open" because the open path was skipped by an earlier
`return`/`break`, or because a struct holding the handle was zero-initialized and
never populated. The analyzer flags I/O on any path where the handle's open state
is not established.

# Catching the issue

## Always check the open result
Test `fopen` against `NULL` and `open` against `-1` immediately, report `errno`
(`strerror`/`perror`), and do not proceed to I/O on failure. This single check
prevents the entire defect.

## Sanitizers and runtime
A null `FILE*` dereference is caught by a normal crash and by AddressSanitizer.
UBSan flags the null pointer use. Checking `ferror`/return values after I/O
surfaces the descriptor-based variant.

## Static analysis
Cppcheck, clang-tidy and the analyzer emitting this diagnostic perform null/value
tracking from `fopen`/`open` to the first use and report any I/O on a
possibly-unopened handle. Annotate APIs with nullability attributes to strengthen
this.

# How to reproduce

Run this so the open fails (the path is not writable). `fopen` returns `NULL` and
the unchecked `fputs` dereferences it, crashing the program.

```c
#include <stdio.h>

int main(void)
{
    /* Opening a file in a non-existent directory fails and returns NULL. */
    FILE *f = fopen("/no/such/dir/out.txt", "w");

    /* No check: f may be NULL, and fputs then dereferences a null FILE*. */
    fputs("data\n", f);

    fclose(f);
    return 0;
}
```
