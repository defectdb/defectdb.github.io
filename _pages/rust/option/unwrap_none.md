---
title: "Unwrap of None"
author: Maxim Menshikov
layout: defect
permalink: /rust/option/unwrap_none
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: rust.option
group:
   - rust
   - option
---
Calling .unwrap() on a None value causes a panic

# Impact

`Option::unwrap` (and `expect`) on a `None` panics with the message
`called \`Option::unwrap()\` on a \`None\` value`. By default the panic unwinds
the current thread; if it reaches the thread's entry point the thread dies. If
that thread is `main`, the process exits with code 101. Under
`panic = "abort"` (common in release/embedded builds) the entire process aborts
immediately with `SIGABRT`, taking down every other thread with it.

In a server this turns a single unexpected-but-recoverable condition (a missing
header, an absent map entry, an empty iterator) into a request failure or, with
abort, a full process crash. The defect is not the panic mechanism itself but
using `unwrap` where a `None` is actually reachable from input or environment.

# Vulnerability potential

1. **Denial of service.** If an attacker can steer a code path so that an
   `Option` is `None` — a lookup that misses, a parse that yields nothing, a
   header that is absent — they can force a panic. Under `panic = "abort"`, or
   when the panicking thread is essential, this crashes the service; repeated
   requests make it a reliable remote DoS.
2. **Availability of dependent state.** A panic mid-operation can leave shared
   state partially updated or locks held (see poisoned `Mutex`), degrading the
   service even for clients that did not trigger the fault.

It is not a memory-safety issue: the panic is well-defined and does not corrupt
memory, hence the low vulnerability rating. The realistic harm is availability.

# Technical details

`Option<T>::unwrap` is defined roughly as `match self { Some(v) => v, None =>
panic!(...) }`. The panic invokes the registered panic hook (printing the
message and, if `RUST_BACKTRACE` is set, a backtrace) and then unwinds, running
destructors frame by frame until caught by `catch_unwind` or the thread boundary.

## Panic strategy

With the default `panic = "unwind"`, only the panicking thread is torn down and
the unwind can be intercepted with `std::panic::catch_unwind`. With
`panic = "abort"` the runtime calls `abort()` immediately — no unwinding, no
recovery, the whole process dies. Library code therefore cannot assume callers
can catch its panics.

# Catching the issue

## Static analysis / lint

Enable `clippy::unwrap_used` and `clippy::expect_used` (restriction lints) to
flag every `unwrap`/`expect` in code that must not panic. Review rule: `unwrap`
is acceptable only when the `None` case is provably impossible, and even then
`expect("reason")` documents the invariant.

## Safer constructs

Replace `unwrap` with `match`, `if let`, `?` (propagate via `Option`/`Result`),
`unwrap_or`, `unwrap_or_else`, `unwrap_or_default`, or `ok_or(...)?` to convert
the absence into a handled value or a returned error instead of a crash.

## Runtime

`std::panic::catch_unwind` at task boundaries (e.g. per-request handlers in a
thread-per-request server) contains the blast radius, and a custom panic hook
can log occurrences for monitoring.

# How to reproduce

Run the following; observe the thread panic and exit code 101 (or `SIGABRT` with
`panic = "abort"`).

```rust
fn main() {
    let maybe: Option<i32> = None;
    let value = maybe.unwrap(); // panic: called `Option::unwrap()` on a `None` value
    println!("{value}");
}
```
