---
title: "unimplemented! called"
author: Maxim Menshikov
layout: defect
permalink: /rust/panic/unimplemented
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
unimplemented! marks unfinished code and aborts at runtime

# Impact

`unimplemented!()` expands to a `panic!` with the message `not implemented`. It
is used to fill in trait methods or match arms that a type deliberately does not
support, so the code compiles. Like `todo!`, it produces no compiler warning, so
if execution ever reaches it the thread panics: it unwinds to thread death, or
under `panic = "abort"` aborts the whole process with `SIGABRT`; a main-thread
panic exits with code 101.

A frequent source is implementing a large trait and stubbing the methods a given
type "shouldn't" need with `unimplemented!()`. If a caller — or a generic code
path — invokes one of those methods, the program crashes instead of returning a
meaningful error.

# Vulnerability potential

1. **Denial of service.** An `unimplemented!` on a reachable path is a guaranteed
   crash when hit. If an attacker or an unusual valid input can drive execution
   to the unsupported method/branch, they crash the request or, under
   `panic = "abort"` / on a critical thread, the process — a repeatable DoS.

No memory unsafety is involved (the panic is well-defined), so the vulnerability
rating is Low; the real exposure is availability and unsupported-but-reachable
code paths.

# Technical details

`unimplemented!` and `todo!` are functionally the same: both expand to a panic
and both evaluate to the never type `!`, so they type-check in any position. The
distinction is intent and message — `unimplemented!` (`not implemented`) signals
"intentionally not provided", whereas `todo!` (`not yet implemented`) signals
"to be done". Both crash through the standard panic machinery and obey the
crate's `panic = "unwind"`/`"abort"` strategy.

## Trait stubs are the classic case

Because `unimplemented!()` satisfies any return type, it is commonly used to stub
trait-method bodies. The compiler cannot tell that such a method is reachable, so
it issues no warning; correctness depends entirely on the assumption that the
method is never actually called — an assumption that breaks when the type is used
through a generic bound or a trait object.

# Catching the issue

## Lint

`clippy::unimplemented` (restriction lint) flags every `unimplemented!`. For
release builds, `#![deny(clippy::unimplemented)]` (and `clippy::todo`) prevents
shipping such stubs; a CI grep is a simple additional gate.

## Design alternatives

If a method genuinely cannot be supported, prefer a typed error: return
`Result<_, E>` with a "not supported" variant, or redesign the trait so
unsupported operations are not expressible (split traits, narrower bounds) rather
than panicking at runtime. Ensure tests cover the paths that reach stubs so a
reachable `unimplemented!` fails in CI.

# How to reproduce

Run the following; observe the `not implemented` panic when the stubbed trait
method is called.

```rust
trait Storage {
    fn read(&self) -> i32;
    fn write(&self, value: i32);
}

struct ReadOnly;

impl Storage for ReadOnly {
    fn read(&self) -> i32 { 7 }
    fn write(&self, _value: i32) {
        unimplemented!() // panics if anyone calls write on a read-only store
    }
}

fn main() {
    let s = ReadOnly;
    s.write(1); // panic: not implemented
}
```
