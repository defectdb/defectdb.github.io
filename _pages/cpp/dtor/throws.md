---
title: "Throw reachable in destructor"
author: Maxim Menshikov
layout: defect
permalink: /cpp/dtor/throws
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: cpp.dtor
group:
   - cpp
   - dtor
---
Throwing from a destructor that runs during stack unwinding calls std::terminate; wrap risky calls in try/catch or mark the dtor noexcept(true)

# Impact

Since C++11 a destructor is implicitly `noexcept`. If an exception escapes it,
`std::terminate` is called and the process aborts immediately — no further
unwinding, no other destructors, no flushing. The most dangerous case is a
destructor that throws **while the stack is already being unwound** by another
in-flight exception: two exceptions are then active simultaneously, which the
language resolves by calling `std::terminate` unconditionally. The result is an
abrupt crash, often with half-released resources and no chance for an orderly
shutdown.

# Vulnerability potential

The defect is primarily an availability problem.

1. The guaranteed `std::terminate` on a double exception is a reliable crash
   primitive. If an attacker can drive the program onto an error path during
   unwinding (e.g. a write that fails on a full or closed socket inside a
   buffered writer's destructor), they can force the process down, which is a
   denial of service.
2. Because the abort skips the rest of cleanup, any invariant that other
   destructors were supposed to restore (release a lock, roll back a file,
   zero a secret) is left in whatever intermediate state existed at the throw —
   occasionally a route to information disclosure or a corrupt persisted file.

# Technical details

## noexcept default

`[except.spec]` gives destructors an implicit `noexcept(true)` exception
specification unless a base or member destructor is `noexcept(false)`. Throwing
out of a `noexcept` function calls `std::terminate` directly via
`__cxa_throw` → `std::terminate`.

## Double exception during unwinding

When an exception propagates, every automatic object whose scope is exited is
destroyed. If one of those destructors throws, there are now two active
exceptions; `[except.throw]` requires `std::terminate`. `std::uncaught_exceptions()`
returning non-zero is the signal that a destructor is running mid-unwind, and
is the correct way to detect "am I being called because of an exception".

## RAII writers are the classic trap

Buffered streams, transactional handles, and loggers commonly do real work
(flush, commit, fsync) in their destructor. Those operations can genuinely
fail, which is exactly where an exception wants to be raised but must not be.

# Catching the issue

## Compiler / static analysis

clang-tidy `bugprone-exception-escape` flags functions declared (or implicitly)
`noexcept` from which an exception can escape, destructors included. The C++
Core Guidelines rule C.36/C.37 ("a destructor must not fail / make it
noexcept") is enforced by `cppcoreguidelines-*` checks.

## Design

Make the destructor explicitly `noexcept` and handle failures internally:
catch and log, or expose a separate `close()`/`commit()` that the caller
invokes (and that *may* throw) before destruction. Provide a "still dirty"
fallback in the destructor that swallows the error.

# How to reproduce

Run it: the second exception during unwinding triggers `std::terminate` and
the process aborts (`terminate called ...`).

```cpp
#include <iostream>

struct Flusher {
    bool fail;
    ~Flusher() noexcept(false) {           // opts out of the noexcept default
        if (fail) throw std::runtime_error("flush failed");
    }
};

void work() {
    Flusher f{true};                        // its dtor will throw...
    throw std::logic_error("primary");      // ...while THIS exception unwinds
}

int main() {
    try { work(); }
    catch (const std::exception& e) { std::cerr << e.what() << '\n'; }
}
```
