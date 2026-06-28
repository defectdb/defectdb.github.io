---
title: "Null pointer copy"
author: Maxim Menshikov
layout: defect
permalink: /rust/ptr/null_copy
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
Copying with a null source or destination is undefined behavior

# Impact

`std::ptr::copy`, `copy_nonoverlapping`, `swap`, and `replace` with a null source
or destination are undefined behavior. These are Rust's `memmove`/`memcpy`
equivalents: `copy_nonoverlapping(src, dst, count)` moves `count * size_of::<T>()`
bytes between the two pointers. If either is null — or null plus a count that
makes the access span into mapped memory — the operation reads from and/or writes
to invalid addresses.

The effect depends on which side is null and on `count`. A null *destination*
write corrupts or crashes much like a bulk null write; a null *source* read can
copy garbage or out-of-bounds bytes into a valid buffer (an info leak) or crash.
Because the count is multiplied by the element size, a single bad call can touch
a large, attacker-influenced span of memory, making this typically more
damaging than a single-element null read or write.

# Vulnerability potential

1. **Bulk memory corruption → RCE.** A null (or near-null) destination with a
   non-trivial `count` overwrites a contiguous range of memory; if the
   destination offset and length are influenced by input this is a powerful
   write primitive for overwriting control data and achieving code execution.
2. **Information disclosure.** A null/invalid *source* copied into a buffer that
   is later returned, logged, or sent to a client leaks whatever bytes were read
   from the bad region — an over-read in the spirit of Heartbleed.
3. **Denial of service.** The straightforward outcome — copying to/from an
   unmapped zero page — faults and crashes the process (kernel panic in
   `no_std`), giving a reliable crash DoS when reachable.
4. **Count/length confusion.** Mixing element count with byte count, or pairing
   a valid pointer with a length derived from elsewhere, amplifies any of the
   above into a large over-read or over-write.

A bulk copy through a null/invalid pointer under partial attacker control is
highly exploitable, hence the High vulnerability rating.

# Technical details

The `ptr::copy*` family requires that both `src` and `dst` be non-null, properly
aligned, and valid for reads/writes of `count` elements respectively (and
`copy_nonoverlapping` additionally forbids overlapping regions; using it on
overlapping ranges is itself UB). A null endpoint, an oversized `count`, or
misalignment each independently makes the call UB.

## copy vs. copy_nonoverlapping

`copy` permits overlapping regions (like `memmove`); `copy_nonoverlapping` (like
`memcpy`) does not and is UB if they overlap. Both still demand non-null, valid,
in-bounds endpoints. `swap`/`replace` are built on the same machinery and inherit
the same requirements. None of them perform any null or bounds check at runtime.

# Catching the issue

## Dynamic detection

**Miri** detects null/dangling/misaligned/out-of-bounds endpoints and overlap
violations in `copy*`. **AddressSanitizer** (`-Z sanitizer=address`) catches the
faulting or out-of-bounds bulk access in native runs; a crash produces a
`SIGSEGV`/core dump for debugger triage.

## Static and review

Validate or construct lengths and pointers from a single source of truth; prefer
safe slice operations (`slice::copy_from_slice`, `clone_from_slice`,
`<[T]>::copy_within`) which carry their own bounds, and `NonNull<T>` to encode
non-nullness. Confine `copy*` to small `unsafe` blocks with a `# Safety` comment
proving both endpoints' validity and the element/byte count. Clippy flags some
obviously-invalid pointer uses.

# How to reproduce

Run the following; observe a segmentation fault (or precise detection under
Miri). The copy writes through a null destination.

```rust
fn main() {
    let src = [1u8, 2, 3, 4];
    let dst: *mut u8 = std::ptr::null_mut();
    unsafe {
        // bulk write to a null destination -> SIGSEGV / corruption
        std::ptr::copy_nonoverlapping(src.as_ptr(), dst, src.len());
    }
    println!("done");
}
```
