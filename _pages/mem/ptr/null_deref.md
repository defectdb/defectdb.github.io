---
title: "Access to null pointer is possible"
author: Maxim Menshikov
layout: defect
permalink: /mem/ptr/null_deref
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
The operation may access null pointer

# Impact

Dereferencing a null pointer reads or writes through an address (`0`, possibly
plus a small struct-member or array offset) that the program almost never owns.

On a hosted operating system with virtual memory, the zero page is left
unmapped on purpose, so the access raises a hardware fault (`SIGSEGV` on
POSIX, an access-violation exception on Windows) and the process is terminated
unless it has installed a handler. The user loses unsaved work, in-flight
transactions are abandoned, and any resources the process held (locks, sockets,
temp files) are released abruptly.

In kernel or firmware context the consequence is worse: the fault occurs in a
mode that cannot simply unwind, so it escalates to a kernel panic / bugcheck
(BSOD) and takes the whole machine down. On microcontrollers and some embedded
targets address `0` is real, writable memory (often the start of RAM or the
interrupt vector table), so the dereference silently corrupts state instead of
faulting, producing arbitrary downstream misbehaviour that is far harder to
diagnose.

# Vulnerability potential

This issue has a real potential to become a vulnerability.

1. Because the default behaviour is to terminate the process or panic the
   kernel, a reliably reachable null dereference is a ready-made
   Denial-of-Service primitive: an attacker who can steer execution to the
   faulting path crashes the service on demand.
2. An offset null dereference (`p->field` or `p[i]` where `p` is null) accesses
   `0 + offset`, not `0`. If the attacker can influence that offset, or if the
   low pages of the address space can be mapped (historically possible via
   `mmap(NULL, ...)` / page-zero mappings, especially in older kernels and in
   setuid programs), the "null" access lands on attacker-controlled memory and
   turns into an arbitrary read/write — i.e. a path to privilege escalation or
   code execution. CVE-2009-2692 (Linux `sock_sendpage`) is the canonical
   example.
3. Crashing a process at the wrong moment can leave the system in a degraded
   state — half-written files, released locks, a restarted daemon with reset
   rate limits — that enables follow-on attacks.
4. If an attacker controls a signal handler or the unwinding/recovery code that
   runs after the fault, the crash itself becomes a foothold for further
   exploitation.

# Technical details

The behaviour stems from how the memory management unit (MMU) and the OS lay out
the virtual address space. By convention the page containing address `0` is left
unmapped, so any load or store to it triggers a page fault with no valid
translation, which the kernel converts into a fatal signal/exception.

In C and C++ dereferencing a null pointer is *undefined behaviour*, not merely
"a crash". Modern optimizers exploit this: if the compiler can prove a pointer
is dereferenced, it may assume the pointer is non-null and delete later
`if (p == NULL)` checks as dead code, which can remove an intended guard and
broaden the impact (this exact pattern caused CVE-2009-1897 in the Linux
kernel). Never rely on "it will just segfault".

## Offset dereferences

`p->member` or `&arr[i]` when `p`/`arr` is null computes `0 + offset`. With a
large enough struct or index the access can reach an *already mapped* page, so
instead of faulting it reads or writes valid memory — silent corruption rather
than a clean crash.

## Microcontrollers and freestanding targets

Most microcontrollers have no MMU and map real memory (RAM, or the reset/
interrupt vectors) at address `0`. A null dereference there does not fault; it
quietly corrupts critical data, and the symptom appears much later and far from
the cause.

## Kernel mode

In kernel context there is no process to kill, so a null dereference becomes a
panic / bugcheck that halts the system, and — as noted above — can be
weaponised when low memory is mappable from user space.

# Catching the issue

## Compilers / static analysis

Build with `-Wnull-dereference` (GCC/Clang) and run Clang Static Analyzer or
`clang-tidy` (`clang-analyzer-core.NullDereference`), Cppcheck, Coverity, or
PVS-Studio — all flag many null dereferences at analysis time. Treat
nullability annotations (`_Nonnull`/`_Nullable`, `[[gsl::nonnull]]`) as part of
the contract and let the compiler check them.

## Runtime sanitizers

`-fsanitize=null` (part of UBSan) instruments dereferences and prints a
diagnostic with file and line. AddressSanitizer also reports the faulting access
with a symbolized stack and an "address points to the zero page" hint. Run the
test suite under these in CI.

## Linux

Install a `SIGSEGV` handler with `sigaction` (using `SA_SIGINFO` to inspect
`si_addr`) to log and triage the fault. Harden the system by keeping
`mmap_min_addr` non-zero so the low pages cannot be mapped, which neutralises
offset-null exploitation.

## Windows

Wrap suspect code in a `__try`/`__except` structured-exception block, or install
a vectored exception handler, to intercept `EXCEPTION_ACCESS_VIOLATION` and
record the faulting address before failing safe.

## Prevention

Check the result of every allocation and lookup that can return null, prefer
references or non-nullable smart pointers in C++, and keep null checks even when
"the pointer can't be null here" — the compiler may otherwise optimise the check
away.

# How to reproduce

Compile and run; observe the program terminate with `SIGSEGV` (segmentation
fault). Building with `-fsanitize=null,address` prints the exact line.

```c
#include <stdio.h>

int main(void)
{
    int *p = NULL;

    /* Reading through the null pointer faults: there is no page at address 0. */
    printf("%d\n", *p);
    return 0;
}
```

