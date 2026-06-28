---
title: "dbg! left in code"
author: Maxim Menshikov
layout: defect
permalink: /rust/debug/dbg
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: rust.debug
group:
   - rust
   - debug
---
dbg! macro should be removed before committing

# Impact

`dbg!(expr)` prints the file, line, the source text of `expr`, and its `Debug`
representation to **stderr**, then returns the value so it can be dropped into an
expression unchanged. It is a debugging aid that should never reach a release. A
forgotten `dbg!` is mostly a quality problem: it clutters stderr, adds I/O on hot
paths (the print happens on every evaluation, and stderr is typically
unbuffered/line-buffered, so it can noticeably slow tight loops), and — unlike
`println!` — is not silenced by log-level configuration.

The more serious edge is that `dbg!` prints whatever value flows through it. If
it wraps a token, password, key, PII, or other secret, that data is written to
stderr in plaintext and may land in logs, CI output, journald, or container
console history.

# Vulnerability potential

1. **Information disclosure.** A `dbg!` left around sensitive data writes that
   data to stderr, which is frequently captured into log aggregation, crash
   reporters, or CI artifacts. Anyone with access to those sinks then sees
   secrets or personal data that should never have been logged.

There is no memory-safety or availability impact beyond minor stderr I/O, so the
rating is Low for vulnerability and None for DoS. Most occurrences are pure code
smell; the rating reflects the realistic worst case of leaking a value into logs.

# Technical details

`dbg!` is a `std` macro that expands to code capturing `file!()`, `line!()`, the
stringified expression, and `format!("{:#?}", value)`, writing them to
`io::stderr()` and yielding the (moved-back) value. Because it returns the value,
it can be inserted mid-expression (`let x = dbg!(compute());`) without changing
program behavior — which is exactly why it is easy to leave behind: the code
still compiles and runs correctly.

## Not affected by release mode

Unlike `debug_assert!`, `dbg!` is **not** compiled out in release builds; `cargo
build --release` keeps the print. The bare `dbg!()` form (no argument) prints
only the file/line, and `dbg!` requires its argument to implement `Debug`.

# Catching the issue

## Lint

`clippy::dbg_macro` flags every `dbg!` invocation. Projects commonly set
`#![deny(clippy::dbg_macro)]` (or enforce it in CI) so a stray `dbg!` fails the
build rather than shipping. A pre-commit hook or CI grep for `dbg!(` is a simple
additional gate.

## Review and tooling

Code review should reject `dbg!` in committed code; prefer a real logging
facade (`log`/`tracing`) with appropriate levels and redaction for anything that
must be observable in production. `cargo fmt`/`clippy` in CI plus a deny-on-warn
policy keeps debug prints out of the main branch.

# How to reproduce

Run the following; observe the `[src/main.rs:N] ...` diagnostic written to stderr
that should not be in committed code.

```rust
fn main() {
    let token = "secret-api-token";
    let len = dbg!(token.len()); // prints to stderr; also a place secrets leak
    dbg!(token);                 // worse: writes the secret itself to stderr
    println!("length = {len}");
}
```
