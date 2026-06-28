---
title: "Null pointer read"
author: Maxim Menshikov
layout: defect
permalink: /rust/ptr/null_read
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Medium
group_full: rust.ptr
group:
   - rust
   - ptr
---
Reading from a null raw pointer is undefined behavior

# Impact

Reading through a null raw pointer — `*null_ptr`, `std::ptr::read(null)`,
`(*null_ptr).field`, or `std::ptr::read_volatile(null)` — is undefined behavior
in Rust. In practice, on a hosted OS with the zero page unmapped, the access
faults and the process is killed with `SIGSEGV` (exit by signal 11). But because
it is UB rather than a defined trap, the compiler is also entitled to assume the
pointer is non-null and optimize accordingly, which can delete checks, reorder
code, or produce results that read adjacent or attacker-influenced memory.

The most common real-world effect is a hard crash. The more dangerous, less
visible effect is silent miscompilation around the dereference, since UB is not
required to fail at the point of the bad read.

# Vulnerability potential

1. **Denial of service.** A reliable null read crashes the process (or panics
   the kernel in `no_std`/kernel contexts). If an attacker can reach the code
   path — a missing FFI return value, an uninitialized pointer field — repeated
   triggering is a dependable crash-based DoS.
2. **Information disclosure.** When the pointer is "null + offset" (e.g.
   `(*(null as *const Struct)).far_field`), the effective address is not zero
   and may land on mapped memory, reading bytes the attacker should not see.
3. **Optimizer-induced bypass.** Because the compiler may assume the pointer is
   non-null, surrounding null/bounds checks can be eliminated, turning a
   would-be safe path into one that proceeds with garbage — potentially enabling
   further out-of-bounds access.

It does not, by reading alone, overwrite memory, so it sits below the write/copy
variants in severity; the realistic outcomes are crashes and limited info leaks.

# Technical details

Raw-pointer dereference is only allowed in `unsafe` code, and the language
contract requires the pointer to be non-null, properly aligned, and pointing to a
valid, live, initialized `T` for the access. A null pointer violates that
contract, so the operation is UB independent of what the hardware happens to do.

## Hardware vs. language semantics

On most platforms address 0 (and a surrounding guard region) is unmapped, so the
MMU raises a fault and the OS delivers `SIGSEGV`. On bare-metal targets or
microcontrollers where address 0 *is* mapped (vector tables, RAM), the read
silently returns whatever lives there with no fault — the same source-level UB,
a quieter and more dangerous outcome. Either way the compiler's null-non-null
assumption applies, so reasoning must be done at the language level, not from the
observed crash.

# Catching the issue

## Dynamic detection

Run under **Miri** (`cargo +nightly miri run/test`), which detects dereferences
of null/dangling/misaligned pointers precisely. Native builds with
`-Z sanitizer=address` (AddressSanitizer) catch the faulting access, and on Linux
a `SIGSEGV` handler or `coredumpctl` plus a debugger pinpoints it.

## Static and review

`clippy` and `rustc` flag some constructs (e.g. dereferencing a literal null),
and the broader discipline is to minimize `unsafe`, wrap raw pointers in
`NonNull<T>` (which encodes non-nullness in the type), and convert raw pointers
with `ptr.as_ref()`/`as_mut()` which return `Option<&T>` and force an explicit
null check instead of an unchecked dereference.

# How to reproduce

Run the following; observe a segmentation fault (or detection under Miri). The
read dereferences address zero.

```rust
fn main() {
    let p: *const i32 = std::ptr::null();
    let value = unsafe { *p }; // UB: read through null pointer -> SIGSEGV
    println!("{value}");
}
```
