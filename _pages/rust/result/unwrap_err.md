---
title: "Unwrap of Err"
author: Maxim Menshikov
layout: defect
permalink: /rust/result/unwrap_err
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: rust.result
group:
   - rust
   - result
---
Calling .unwrap() on an Err value causes a panic

# Impact

`Result::unwrap` (and `expect`) on an `Err` panics with the message
`called \`Result::unwrap()\` on an \`Err\` value: <debug of the error>`. The
current thread unwinds; if it is `main` the process exits with code 101, and
under `panic = "abort"` the whole process aborts with `SIGABRT`.

This pattern discards a perfectly good, already-typed error value and converts a
recoverable failure into a crash. It is especially dangerous on fallible I/O,
parsing, and network operations whose `Err` arm is routinely reachable in
production: a transient disk error, a malformed packet, or a closed socket then
becomes a process-level fault instead of a handled condition.

# Vulnerability potential

1. **Denial of service.** Any `Result`-returning operation whose error path an
   attacker can trigger — send malformed input that fails to parse, exhaust a
   resource so an allocation/`open` fails, drop a connection mid-request —
   becomes a crash vector when its result is `unwrap`ped. With `panic = "abort"`
   or on a critical thread this is a reliable remote DoS.
2. **Information exposure (minor).** The default panic message prints the
   `Debug` representation of the error, which may include file paths, internal
   addresses, query fragments, or other details. If panic output is surfaced to
   clients or shared logs it can leak implementation details.

No memory unsafety is involved, so the vulnerability rating is Low; the dominant
risk is loss of availability.

# Technical details

`Result<T, E>::unwrap` is `match self { Ok(v) => v, Err(e) => panic!("... {e:?}")
}` and requires `E: Debug` precisely so it can format the error into the panic
message. The panic runs the panic hook and then unwinds (default) or aborts,
depending on the `panic` profile setting.

## Why it is tempting and why it is wrong

`unwrap` is convenient in prototypes and tests because it avoids writing the
error arm. In library and service code it is an unhandled-error bug: the type
system already proved the call can fail (that is why it returns `Result`), and
`unwrap` deliberately throws that proof away.

# Catching the issue

## Lint

`clippy::unwrap_used` and `clippy::expect_used` flag the calls; many teams
`#![deny]` them outside tests. `clippy::unwrap_in_result` warns when a function
that itself returns `Result` uses `unwrap` internally instead of `?`.

## Refactor to propagation/handling

Prefer the `?` operator to bubble the error to a caller that can decide, or
handle it explicitly with `match`/`if let`, `unwrap_or`, `unwrap_or_else`,
`map_err` plus `?`, or `.ok()`/`.unwrap_or_default()`. Crates like `anyhow` and
`thiserror` make propagation ergonomic so `unwrap` is rarely needed.

## Runtime containment

Wrap task/request boundaries in `std::panic::catch_unwind` and install a panic
hook for telemetry so an `unwrap`-on-`Err` is logged rather than silently
killing a worker.

# How to reproduce

Run the following; observe the panic carrying the underlying `Err` value and
exit code 101.

```rust
fn main() {
    let r: Result<i32, String> = Err("boom".to_string());
    let value = r.unwrap(); // panic: called `Result::unwrap()` on an `Err` value: "boom"
    println!("{value}");
}
```
