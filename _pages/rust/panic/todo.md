---
title: "todo! called"
author: Maxim Menshikov
layout: defect
permalink: /rust/panic/todo
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
todo! marks unfinished code and aborts at runtime

# Impact

`todo!()` is a placeholder macro that expands to a `panic!` with the message
`not yet implemented`. It is meant to satisfy the type checker for code paths the
author has not written yet, so the crate compiles while the body is still a stub.
The danger is that it compiles cleanly and gives no warning: if a `todo!` ships,
the first time execution reaches it the thread panics — unwinding to thread death
or, under `panic = "abort"`, aborting the whole process with `SIGABRT`. Main-
thread panics exit with code 101.

Because `todo!` returns the never type `!`, it type-checks in any position, so an
unfinished branch can hide behind a rarely taken code path and survive into
production undetected until a user happens to trigger it.

# Vulnerability potential

1. **Denial of service.** A `todo!` left on a reachable path is a guaranteed
   crash when reached. If an attacker (or simply an unusual but valid input) can
   steer execution into the unimplemented branch, they crash the request or, with
   `panic = "abort"` / on a critical thread, the process. Repeatable triggering
   is a DoS.

There is no memory-safety dimension — the panic is well-defined — so the
vulnerability rating is Low; the risk is availability and shipping obviously
unfinished code.

# Technical details

`todo!` and `unimplemented!` are near-identical: both expand to a panic and both
evaluate to `!`, fitting any expected type. The only difference is intent and
message: `todo!` says "I *will* implement this" (message `not yet implemented`),
while `unimplemented!` says "this is intentionally not provided". Functionally
they crash the same way through the standard panic machinery (hook, then unwind
or abort per the `panic` strategy).

## Why the compiler stays silent

A `todo!` body is valid code, so `rustc` emits no error or warning by default —
unlike a genuinely missing implementation, which would fail to compile. This is
exactly what makes a forgotten `todo!` easy to ship.

# Catching the issue

## Lint

Enable `clippy::todo` (a restriction lint) to flag every `todo!` so none survives
into a release; CI can `#![deny(clippy::todo)]` for release builds while allowing
it during development. A `grep`/CI check for `todo!` before tagging a release is a
cheap backstop.

## Process

Treat `todo!` as a build-blocker for production: pair it with a tracking issue,
and ensure tests exercise the code paths that contain stubs so a reachable
`todo!` fails loudly in CI rather than for a user. Replace it with a real
implementation or a returned `Result` error before release.

# How to reproduce

Run the following; observe the `not yet implemented` panic when the stubbed
branch is reached.

```rust
fn handle(command: &str) -> i32 {
    match command {
        "add" => 1,
        "remove" => todo!(), // unfinished: panics if a "remove" command arrives
        _ => 0,
    }
}

fn main() {
    println!("{}", handle("remove"));
}
```
