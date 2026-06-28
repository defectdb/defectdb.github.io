---
title: "panic! called"
author: Maxim Menshikov
layout: defect
permalink: /rust/panic/panic
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: rust.panic
group:
   - rust
   - panic
---
panic! aborts the thread; consider returning Result instead

# Impact

`panic!` triggers an unrecoverable error: it runs the panic hook (printing the
message and optionally a backtrace) and then unwinds the current thread, running
destructors as it goes. If the unwind reaches the thread's boundary the thread
dies; if that thread is `main`, the process exits with code 101. Under
`panic = "abort"` the runtime calls `abort()` immediately and the whole process
dies with `SIGABRT`, no unwinding.

Using `panic!` for conditions that are actually recoverable — bad input, a
missing file, a failed network call — converts ordinary error handling into a
crash. In a server each such panic kills at least the handling task and, with
abort or on a critical thread, the entire process.

# Vulnerability potential

1. **Denial of service.** If an attacker can reach a `panic!` — by supplying
   input that hits a `panic!`-guarded branch or violates an asserted
   precondition — they can crash the request, the worker, or (under
   `panic = "abort"`) the whole service. Repeated triggering is a reliable
   remote DoS.
2. **State and lock damage.** A panic mid-operation can leave shared data
   partially updated and poisons any `Mutex`/`RwLock` held across it, so even
   non-malicious clients see degraded or failing behavior afterward.
3. **Information exposure (minor).** Panic messages may include internal details
   (paths, values, addresses); if surfaced to clients or shared logs they leak
   implementation information.

It is not memory-unsafe, so vulnerability is Low; the dominant risk is
availability, hence the Medium DoS rating.

# Technical details

`panic!` expands to a call into the standard panic machinery
(`core::panicking::panic` / `panic_fmt`), which invokes the current panic hook
and then either unwinds or aborts depending on the crate's `panic` strategy. The
unwind can be intercepted at a boundary with `std::panic::catch_unwind`, but only
under `panic = "unwind"`; library code cannot rely on callers catching it.

## Panic vs. Result

Rust separates *recoverable* errors (`Result<T, E>`, propagated with `?`) from
*unrecoverable* ones (`panic!`). `panic!` is appropriate only for bugs and
violated invariants that indicate the program is in an unexpected state, not for
conditions that arise from valid-but-unfortunate inputs or environment. Reaching
for `panic!` where a `Result` belongs is the defect.

# Catching the issue

## Lint and review

`clippy::panic` (a restriction lint) flags explicit `panic!` calls so they can be
justified or replaced; teams often `#![deny(clippy::panic)]` in library crates,
allowing it only in tests. Review rule: `panic!` is for "this should be
impossible" invariants, not for handling expected failures.

## Refactor and contain

Return `Result`/`Option` and propagate with `?`; use `thiserror`/`anyhow` for
ergonomic error types. Where panics must be tolerated, wrap task/request
boundaries in `std::panic::catch_unwind` and install a panic hook to log
occurrences for monitoring. Building with `panic = "abort"` removes the safety
net entirely, so audit panics accordingly.

# How to reproduce

Run the following; observe the panic message and exit code 101.

```rust
fn divide(a: i32, b: i32) -> i32 {
    if b == 0 {
        panic!("division by zero"); // crashes instead of returning an error
    }
    a / b
}

fn main() {
    println!("{}", divide(10, 0));
}
```
