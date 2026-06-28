---
title: "Null pointer write"
author: Maxim Menshikov
layout: defect
permalink: /rust/ptr/null_write
arch:
   - native
vulnerability:
   - High
ddos:
   - Medium
group_full: rust.ptr
group:
   - rust
   - ptr
---
Writing to a null raw pointer is undefined behavior

# Impact

Writing through a null raw pointer — `*null_ptr = v`, `std::ptr::write(null, v)`,
`(*null_ptr).field = v`, or `write_volatile(null, v)` — is undefined behavior.
On a hosted OS with the zero page unmapped the store faults and the process dies
with `SIGSEGV`. But a null write is strictly more dangerous than a null read:
when the pointer is "null + field offset" or the surrounding zero region is not
fully unmapped, the write lands on *some* address and corrupts whatever lives
there. Because it is UB, the optimizer may also assume the pointer was non-null
and miscompile the surrounding code.

The headline outcome is therefore memory corruption (or a crash), with the
corrupted location determined by the offset and by what an attacker can
influence about the value and address.

# Vulnerability potential

1. **Memory corruption → RCE.** A controlled write to a near-null address can
   overwrite adjacent data structures, function pointers, or vtable entries. The
   "null pointer + attacker-controlled offset/value" pattern is a classic
   primitive for hijacking control flow and achieving arbitrary code execution.
2. **Denial of service.** The common case — writing to an unmapped zero page —
   reliably crashes the process; if the path is attacker-reachable it is a
   dependable crash DoS, and a kernel panic in `no_std`/kernel code.
3. **Optimizer-assisted exploitation.** The compiler's non-null assumption can
   strip checks around the write, widening the set of reachable corrupting
   states.

A write that corrupts memory under partial attacker control is the most
exploitable of the null-pointer defects, hence the High vulnerability rating.

# Technical details

Raw-pointer stores in `unsafe` code carry the same contract as reads: the
pointer must be non-null, aligned, and pointing to a valid, writable place of the
right type. A null target breaks the contract, so the store is UB no matter what
the hardware does.

## Why offsets make it worse

`(*(0 as *mut Struct)).field` computes `0 + offset_of!(field)` as the store
address. If that address happens to be mapped (large structs, bare-metal targets
where low memory is RAM/registers, MCUs with memory-mapped peripherals at low
addresses), the write silently mutates real state instead of faulting —
overwriting peripheral registers or live data. The same source UB thus ranges
from "instant crash" to "silent, targeted corruption."

# Catching the issue

## Dynamic detection

**Miri** flags writes through null/dangling/misaligned pointers exactly. Native
builds with **AddressSanitizer** (`-Z sanitizer=address`) catch the faulting or
out-of-bounds store, and a `SIGSEGV`/core dump under a debugger localizes the
crash on Linux/macOS.

## Static and review

Prefer `NonNull<T>` to make non-nullness a type invariant, and obtain writable
references via `ptr.as_mut()` (returns `Option<&mut T>`, forcing a null check) or
`addr_of_mut!`-based construction from valid places. Keep `unsafe` blocks small
and require a `# Safety` comment establishing the pointer's validity before any
store; `clippy` lints flag dereferences of literal null pointers.

# How to reproduce

Run the following; observe a segmentation fault (or detection under Miri). The
store targets address zero.

```rust
fn main() {
    let p: *mut i32 = std::ptr::null_mut();
    unsafe { *p = 42; } // UB: write through null pointer -> SIGSEGV / memory corruption
    println!("done");
}
```
