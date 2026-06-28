---
title: "Unwrap of Ok"
author: Maxim Menshikov
layout: defect
permalink: /rust/result/unwrap_ok
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
Calling .unwrap_err() on an Ok value causes a panic

# Impact

`Result::unwrap_err` (and `expect_err`) returns the `Err` value, but panics when
the result is `Ok`, with the message
`called \`Result::unwrap_err()\` on an \`Ok\` value: <debug of the Ok value>`.
The current thread unwinds and, if it is `main`, the process exits with code 101;
under `panic = "abort"` the whole process aborts with `SIGABRT`.

This is the mirror image of `unwrap`: the code asserts "this must have failed"
and panics when the operation unexpectedly succeeded. It shows up in tests and
in code that expects a specific failure (e.g. validation that *should* reject
input) and then mishandles the success branch, turning an unexpected `Ok` into a
crash.

# Vulnerability potential

1. **Denial of service.** If an attacker can make an operation succeed where the
   code assumed it would fail — supply input that unexpectedly validates, or
   satisfy a precondition the developer believed unreachable — they trigger the
   panic. On a critical thread or under `panic = "abort"` this crashes the
   service.
2. **Information exposure (minor).** The panic prints the `Debug` form of the
   `Ok` payload, which may contain sensitive data; if panic output reaches logs
   or clients it can leak that value.

It does not corrupt memory, so vulnerability is Low; the real exposure is
availability, and it tends to be rarer than `unwrap`-on-`Err` because the "this
always fails" assumption is itself unusual.

# Technical details

`Result<T, E>::unwrap_err` is `match self { Ok(t) => panic!("... {t:?}"), Err(e)
=> e }` and requires `T: Debug` so it can format the unexpected success value.
The panic follows the standard hook-then-unwind (or abort) path governed by the
crate's `panic` strategy.

## Typical origin

It is most often a logic error: a test written as
`do_thing(bad_input).unwrap_err()` that breaks when a code change makes
`do_thing` accept the input, or production code that treats a fallible call as
"can only fail here" and uses `unwrap_err` to extract the error without handling
the success case.

# Catching the issue

## Lint and review

`clippy::unwrap_used`/`clippy::expect_used` cover `unwrap_err`/`expect_err` as
well. Review rule: never assert a specific outcome of a fallible call with
`unwrap_err`; handle both arms. In tests prefer `assert!(matches!(r, Err(_)))`
or `assert_eq!` on the mapped error so a surprising `Ok` produces a readable
assertion failure rather than a raw panic.

## Safer constructs

Use `match`/`if let Err(e)`, `.err()` (which yields `Option<E>` without
panicking), or `.is_err()` checks to handle both the success and failure paths
explicitly.

# How to reproduce

Run the following; observe the panic reporting the unexpected `Ok` value.

```rust
fn main() {
    let r: Result<i32, String> = Ok(42);
    let err = r.unwrap_err(); // panic: called `Result::unwrap_err()` on an `Ok` value: 42
    println!("{err}");
}
```
