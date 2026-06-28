---
title: "Important function result is ignored"
author: Maxim Menshikov
layout: defect
permalink: /fn/result/ignored
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: fn.result
group:
   - fn
   - result
---
The function result must not be ignored

# Impact

A function whose return value carries essential information — an error/status
code, a count of bytes actually transferred, a reallocated pointer, or a
success/failure flag — is called and its result discarded. The program then
proceeds as if the operation succeeded and produced what was expected. When it did
not, every later step operates on wrong assumptions: uninitialized buffers treated
as valid, partial writes treated as complete, freed-and-moved memory accessed
through a stale pointer, or a security check that silently failed but is treated as
passed.

Ignored results are insidious because the code works in testing (where the call
usually succeeds) and fails only under the error conditions the return value was
meant to signal — exactly the conditions an attacker can provoke.

# Vulnerability potential

Dropping a meaningful return value is a well-known weakness (CWE-252) with
concrete security consequences.

1. **Ignored security-check results.** If the return of an access-control,
   signature-verification, or authentication call is discarded, the code continues
   on the success path regardless of the actual verdict — a fail-open auth or
   integrity bypass.
2. **Ignored `realloc`/allocation results.** Discarding the value of `realloc`
   (or not checking `malloc` for `NULL`) leads to use of a stale/freed pointer or
   a null dereference — use-after-free or crash.
3. **Ignored short reads/writes.** Treating an unchecked `read`/`write`/`recv`
   return as "all bytes done" yields truncated data, buffer over-reads of
   uninitialized memory, or protocol desync that can be steered by input.
4. **Denial of service.** Ignored error codes let the program march into an
   invalid state and crash later, away from the real cause.

The auth-bypass and use-after-free potential gives a `Medium` vulnerability
rating; the crash potential gives `Low` for DoS.

# Technical details

## Where it matters most
`read`/`write`/`recv`/`send` (return *actual* count, may be short),
`realloc`/`malloc` (may move or fail), `fork`/`exec`/`setuid`/`seteuid`
(privilege-drop failures are a classic ignored-return CVE source), `scanf`-family
(number of fields converted), `pthread_*`/locking calls, and any function
returning an error code instead of throwing.

## Why it slips through
C has no mechanism that forces a caller to consume a return value, so an ignored
result is perfectly legal and silent. Refactors that change a void function into
one returning a status often leave old call sites unchanged.

## Markers that turn it into a diagnostic
C++17 `[[nodiscard]]`, GCC/Clang `__attribute__((warn_unused_result))`, and the
POSIX-recommended annotations on `write`-like calls let the toolchain warn when
the value is dropped. The analyzer emitting this diagnostic flags discarded
results of functions deemed important even without annotations.

# Catching the issue

## Compiler / attributes
Annotate status-returning functions with `[[nodiscard]]` /
`warn_unused_result` and build with `-Wall -Wextra` (and treat
`-Wunused-result` as an error) so dropped values are compile-time failures.

## Static analysis
Cppcheck, clang-tidy (`bugprone-unused-return-value`,
`cert-err33-c`), Coverity and the analyzer here track discarded returns of
security- and resource-critical functions.

## Discipline
Always check I/O and allocation results; for privilege-dropping calls, verify the
new state rather than assuming success. If a result is genuinely irrelevant, make
the intent explicit (`(void)fn();`) so reviewers and tools know it was deliberate.

# How to reproduce

Compile with `-Wall -Werror`. The `[[nodiscard]]` status return is ignored, so the
build fails — and at runtime the code proceeds as if the operation succeeded.

```cpp
#include <iostream>

enum class Status { Ok, Denied };

[[nodiscard]] Status authorize(int user)
{
    return user == 0 ? Status::Ok : Status::Denied;
}

int main()
{
    authorize(1000);                 // result discarded: warning/error here
    std::cout << "proceeding as authorized\n";   // runs regardless of verdict
    return 0;
}
```
