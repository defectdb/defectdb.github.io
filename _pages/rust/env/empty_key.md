---
title: "Empty environment variable key"
author: Maxim Menshikov
layout: defect
permalink: /rust/env/empty_key
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: rust.env
group:
   - rust
   - env
---
Environment variable operations require a non-empty key

# Impact

`std::env::set_var` and `std::env::remove_var` panic if the key is empty,
contains an ASCII `=` (`0x3D`), or contains a NUL byte (`0x00`); on most
platforms the key must also be valid Unicode. An empty key is the most common
trigger and produces a panic such as
`environment variable name cannot be empty`. The current thread unwinds, and if
it is `main` the process exits with code 101 (or aborts under
`panic = "abort"`).

The defect is usually a logic or input-validation slip: a key string is built
from configuration or user input and turns out to be empty (or to contain `=`),
so a call meant to set an environment variable instead crashes the program. The
blast radius is whatever depended on that thread.

# Vulnerability potential

1. **Denial of service.** If the key passed to `set_var`/`remove_var` is derived
   from untrusted input and an attacker can make it empty or insert `=`/NUL, they
   force a panic; on a critical thread or under `panic = "abort"` this crashes
   the process.

It is otherwise low-impact: the panic is well-defined, memory-safe, and the
input that reaches an environment-mutation call is rarely attacker-controlled in
practice. Note also that `set_var`/`remove_var` were made `unsafe` in Rust 2024
because mutating the process environment is not thread-safe, which is a separate
and arguably larger concern than the empty-key panic.

# Technical details

The key validation lives in the platform `set_var`/`remove_var` implementations.
Empty keys, keys containing `=`, and keys containing interior NUL are rejected
because the underlying OS environment representation (`NAME=VALUE` C strings)
cannot encode them unambiguously: `=` is the name/value separator and NUL
terminates the C string. The functions therefore `panic!` rather than silently
corrupt the environment block.

## Reads do not panic

`std::env::var(key)` and `var_os(key)` do *not* panic on an empty or odd key —
they simply return `Err(VarError::NotPresent)` / `None`. Only the *mutating*
calls validate and panic, so the defect is specific to `set_var`/`remove_var`.

# Catching the issue

## Validation

Validate keys before mutating the environment: reject empty strings and any key
containing `=` or NUL, ideally constraining keys to a known charset
(`[A-Za-z_][A-Za-z0-9_]*`). Treat environment names derived from external input
as untrusted.

## Lint and review

Code review should flag `set_var`/`remove_var` calls with dynamically built keys
and ensure a non-empty, well-formed key is guaranteed. Under Rust 2024 these
calls are `unsafe`, so each already requires a `# Safety` justification that can
also cover key validity. Tests that exercise the empty-key path will surface the
panic immediately.

# How to reproduce

Run the following; observe the panic on the empty key.

```rust
fn main() {
    let key = ""; // built from config/input; turns out empty
    std::env::set_var(key, "value"); // panic: environment variable name cannot be empty
    println!("set");
}
```
