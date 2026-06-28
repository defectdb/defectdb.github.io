---
title: "mem::transmute called"
author: Maxim Menshikov
layout: defect
permalink: /rust/mem/transmute
arch:
   - native
vulnerability:
   - High
ddos:
   - Low
group_full: rust.mem
group:
   - rust
   - mem
---
std::mem::transmute is one of the most unsafe operations in Rust

# Impact

`std::mem::transmute::<Src, Dst>(x)` reinterprets the bytes of `x` as a value of
type `Dst` with no checks beyond `size_of::<Src>() == size_of::<Dst>()`. It
bypasses every type-system guarantee at once. If the source bit pattern is not a
valid `Dst`, the result is immediate undefined behavior: a transmuted `bool`,
`char`, enum, or reference holding an out-of-range or null/dangling value lets
the optimizer assume impossible things and miscompile surrounding code.

Concrete consequences include creating references to deallocated or arbitrary
memory (use-after-free, wild pointers), forging a `&mut` alias to data that is
also reachable as `&` (breaking the aliasing model and enabling data races),
fabricating invalid enum discriminants, and changing lifetimes to "extend"
borrows past the data they point to. Any of these can corrupt memory and crash
or be steered by an attacker.

# Vulnerability potential

1. **Memory corruption / RCE.** Transmuting integers to pointers/references, or
   one struct layout to an incompatible one, produces reads and writes through
   wild pointers. An attacker who influences the transmuted bytes can gain
   controlled out-of-bounds access, the foundation of arbitrary code execution.
2. **Lifetime laundering → use-after-free.** Transmuting `&'a T` to `&'static T`
   (or otherwise lengthening a lifetime) defeats the borrow checker; the
   reference outlives its referent and is later read/written as dangling memory.
3. **Aliasing violation → data races / torn state.** Transmuting `&T` to `&mut
   T` creates an exclusive reference that aliases shared ones, violating "XOR
   mutability" and enabling unsynchronized concurrent mutation.
4. **Invalid-value UB → info leak / corruption.** Transmuting bytes into types
   with validity invariants (`bool`, `char`, references, `NonNull`, niche-using
   enums) yields values the compiler treats as impossible, producing
   unpredictable behavior that can leak or overwrite adjacent data.

Because it can directly produce memory corruption controllable by inputs, the
vulnerability potential is High; it can also simply crash (Low DoS), but the
defining risk is unsoundness.

# Technical details

`transmute` is a compiler intrinsic: it copies the bytes of the argument and
hands them back typed as `Dst`. The *only* statically enforced rule is equal
size (checked at compile time; differently sized transmutes are a hard error).
Everything else — that the bytes form a valid `Dst`, that layout matches, that
lifetimes and aliasing are respected — is the programmer's unchecked obligation.

## Layout is not guaranteed

Rust's default `repr(Rust)` layout is unspecified and may differ between types,
between compiler versions, and even between generic instantiations. Transmuting
between two `struct`s that "look the same" is therefore unsound unless both are
`repr(C)` (or `repr(transparent)`) with identical, explicitly defined layouts.

## Almost always avoidable

The standard library documents safe replacements for nearly every real use:
`x as U` for numeric casts, `f32::to_bits`/`from_bits` for float↔int,
`ptr.cast()` and `as` for pointer retyping, `slice::from_raw_parts` for building
slices, `char::from_u32`, and `pointer::cast`/`NonNull` helpers. Transmute should
be a last resort, confined to a tiny audited `unsafe` block with a safety
comment proving validity, layout, and lifetimes.

# Catching the issue

## Compiler and lint

`rustc` enforces the size-equality rule and emits the `invalid_value` lint for
some obviously-wrong transmutes (e.g. producing an uninhabited type). Clippy adds
a family of targeted lints: `clippy::transmute_ptr_to_ref`,
`transmute_int_to_char`, `transmute_int_to_bool`, `transmute_ptr_to_ptr`,
`useless_transmute`, `transmute_undefined_repr`, and
`wrong_transmute` — most suggesting the safe alternative.

## Dynamic UB detection

Run the code under **Miri** (`cargo +nightly miri test`), which interprets the
program against Rust's operational semantics and reports invalid values,
out-of-bounds, use-after-free, and aliasing (Stacked/Tree Borrows) violations
that a transmute introduces. Compile with `-Z sanitizer=address`/`undefined`
(ASan/UBSan) for native detection of the resulting bad accesses.

## Review

Treat every `transmute` as a soundness review item: require an explicit
`# Safety` comment justifying size, validity, `repr`, and lifetimes, and prefer
`#![deny(clippy::transmute_ptr_to_ref)]` and friends in the project lint config.

# How to reproduce

Run the following under Miri (`cargo +nightly miri run`) to see the undefined
behavior reported; transmuting an integer into a reference fabricates a wild
pointer that is then dereferenced.

```rust
fn main() {
    unsafe {
        // Reinterpret a small integer as a reference, then read through it.
        let bogus: &i32 = std::mem::transmute(1usize); // invalid: not a valid &i32
        println!("{}", *bogus);                        // UB: dereference of a wild pointer
    }
}
```
