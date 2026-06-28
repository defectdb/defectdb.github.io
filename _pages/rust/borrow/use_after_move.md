---
title: "Use of moved value"
author: Maxim Menshikov
layout: defect
permalink: /rust/borrow/use_after_move
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: rust.borrow
group:
   - rust
   - borrow
---
The value was moved (ownership transferred) and is no longer usable here

# Impact

This is a compile-time error (`E0382`): the program does not build, so there is
no runtime effect. The developer must clone, borrow, or restructure ownership
before the code compiles.

The check prevents the use-after-free / double-free family of bugs. After a
non-`Copy` value is moved, the source binding is logically empty; reading it
would alias memory now owned elsewhere, and dropping both the source and the
destination would free the same resource twice. Rust statically guarantees each
owned value is dropped exactly once by rejecting any use of a moved-from binding.

# Vulnerability potential

None in safe Rust. The ownership/move analysis runs entirely at compile time and
rejects the program, so no vulnerable binary is produced. Move semantics are a
core part of how Rust statically eliminates double-free and use-after-free; this
error is that guarantee firing as intended.

# Technical details

When a value of a non-`Copy` type is assigned, passed by value, or returned, its
ownership *moves*: the bytes are conceptually relocated to the new owner and the
original binding is marked uninitialized by the move checker. Any subsequent read
of the original is `error[E0382]: borrow of moved value` (or "use of moved
value"). Types implementing `Copy` (integers, `bool`, `char`, shared references,
small `Copy` structs) are duplicated bit-for-bit instead of moved, so they are
never affected.

## Closures and partial moves

The error also appears when a closure captures a value by move (`move ||`) and
the surrounding code later uses it, and when one field of a struct is moved out,
making the whole struct partially uninitialized and unusable as a whole.

# Catching the issue

`rustc`/`cargo check` reports `E0382` with notes showing where the move occurred
and suggesting fixes. Resolutions, in rough order of preference: borrow instead
of move (`&value`) when the callee does not need ownership; derive or implement
`Clone` and call `.clone()` when an independent copy is acceptable; make a small
value `Copy`; or redesign so ownership flows in one direction. `clippy` adds
lints such as `clippy::redundant_clone` to avoid over-correcting with needless
clones.

# How to reproduce

Compile the following; the move checker rejects the second use with `E0382`.

```rust
fn main() {
    let s = String::from("hello");
    let t = s;             // ownership of the heap buffer moves from `s` to `t`
    println!("{t}");
    println!("{s}");       // error[E0382]: borrow of moved value: `s`
}
```
