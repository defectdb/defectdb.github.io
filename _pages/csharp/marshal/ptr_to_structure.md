---
title: "Marshal.PtrToStructure"
author: Maxim Menshikov
layout: defect
permalink: /csharp/marshal/ptr_to_structure
arch:
   - native
vulnerability:
   - High
ddos:
   - Medium
group_full: csharp.marshal
group:
   - csharp
   - marshal
---
Reading a managed structure out of a raw pointer is unsafe — the runtime does not validate layout, alignment, or that the pointer is actually owned

# Impact

`Marshal.PtrToStructure<T>(IntPtr)` (and its non-generic and `Span`-free overloads) reads a managed value of type `T` out of raw unmanaged memory. It computes `Marshal.SizeOf<T>()` and copies that many bytes from the pointer into a new `T`, performing field-by-field marshaling for non-blittable members. Crucially, the runtime performs **no validation**:

- It does not check that the pointer is non-null, valid, or owned by you.
- It does not check that at least `SizeOf<T>()` readable bytes exist at that address.
- It does not check that the source bytes actually represent a well-formed `T` — alignment, layout, and the meaning of embedded pointer/handle fields are all assumed, never verified.

It blindly copies `sizeof(T)` bytes. The consequences when any assumption is wrong:

- **Out-of-bounds read / information disclosure.** If `T` is larger than the real buffer (or the pointer is offset near the end of a region), `PtrToStructure` reads past the buffer into adjacent process memory and surfaces those bytes as field values.
- **Access violation / crash.** A wild, freed, or unmapped pointer causes a read fault. Unlike managed null-deref, this is an `AccessViolationException` (or hard crash) originating in native code, generally non-recoverable.
- **Type confusion.** If the source bytes do not match `T`'s layout — particularly when `T` contains `IntPtr`, handles, function pointers, or reference-like fields — the marshaler interprets arbitrary attacker-influenced bytes as those typed members. A 64-bit field controlled by the attacker becomes a pointer the program later dereferences or a handle it later operates on.

# Vulnerability potential

This is high-impact unsafe interop because it converts untrusted bytes directly into typed managed state with no bounds or sanity checking. Attack scenarios:

1. **Memory disclosure via oversized read.** An attacker who controls (or can shorten) the source buffer — a network packet, a memory-mapped file, a shared-memory segment, an IPC message — while the code reads a fixed, larger `T`, causes `PtrToStructure` to read adjacent heap/stack memory. Returned field values then leak whatever happened to be there (pointers defeating ASLR, secrets, other sessions' data).
2. **Type confusion into a pointer/handle.** If `T` contains an `IntPtr`, function pointer, or OS handle and the attacker controls those bytes, the program subsequently dereferences or invokes an attacker-chosen address/handle. This is a direct route from "parse untrusted data" to controlled memory access and potentially code execution.
3. **Crash / DoS.** A malformed length or pointer that points just before unmapped memory (or to freed memory) triggers an `AccessViolationException`. An attacker who can supply the pointer offset or buffer length can crash the process at will — the basis for the `Medium` `ddos` rating.

Because reading unvalidated native data straight into a typed struct is squarely on the OOB-read / type-confusion path, the vulnerability potential is **High**.

# Technical details

## What the marshaler actually does

`PtrToStructure<T>` reads `Marshal.SizeOf<T>()` bytes starting at the pointer. `SizeOf<T>` reflects the **marshaled** size as governed by `[StructLayout]` and per-field `[MarshalAs]`, which is not necessarily the same as the managed `sizeof(T)`. The copy honors the declared layout: `LayoutKind.Sequential` with the type's `Pack`, or explicit `[FieldOffset]` under `LayoutKind.Explicit`. If the native producer used a different packing/alignment, fields are read from the wrong offsets even when the total size matches.

## Blittable vs non-blittable

- **Blittable** types (only integers, floats, pointers, and structs/arrays thereof) have identical managed and unmanaged representations. For these, marshaling is effectively a `memcpy`, and `MemoryMarshal`/`Unsafe.ReadUnaligned` give the same result far more cheaply.
- **Non-blittable** types (containing `bool`, `char`, `string`, arrays marshaled `ByValArray`, nested non-blittable structs, etc.) require real conversion. `PtrToStructure` will *allocate and convert* — e.g. follow an embedded string pointer — which means a bad embedded pointer is dereferenced *during* marshaling, not later. This widens the attack surface considerably.

## The missing bounds check

The core defect: the API takes a pointer and a type, never a length. There is no way for it to know how many bytes are valid. Safe code must establish the available length out-of-band and refuse to read when `availableBytes < Marshal.SizeOf<T>()`.

## Safer alternatives

When `T` is blittable, prefer working over a length-bounded `Span<byte>`/`ReadOnlySpan<byte>` and `MemoryMarshal.Read<T>(span)` / `MemoryMarshal.AsRef<T>(span)`. These throw `ArgumentOutOfRangeException` when the span is shorter than `sizeof(T)`, turning a silent OOB read into a checked failure. Validate the length explicitly before the read, and validate field invariants (lengths, tags, ranges) *after* it, before trusting any embedded pointer or handle.

# Catching the issue

## Static analysis

CodeQL ships taint-tracking queries that follow untrusted data into unsafe interop; a query can flag `PtrToStructure` reads whose pointer or backing length derives from network/file/IPC input without an intervening length check. SonarQube and Roslyn security analyzers flag unsafe pointer usage and interop boundaries. There is no single built-in "PtrToStructure is unsafe" rule, so a custom analyzer/CodeQL query keyed on the call together with the absence of a size guard is the most reliable detector.

## AddressSanitizer

Run the native interop (or the whole process on an ASan-enabled build) under **AddressSanitizer**. An oversized `PtrToStructure` read off the end of a native allocation is a textbook heap-buffer-overflow read that ASan reports with the faulting offset — catching exactly the out-of-bounds reads that produce silent disclosure rather than a crash.

## Banned APIs and review

Add `Marshal.PtrToStructure` to a `BannedApiAnalyzers` list for code that parses untrusted input, steering callers to length-checked `MemoryMarshal` reads. In review, require for every call: a proven available length `>= Marshal.SizeOf<T>()`; a `[StructLayout]` that matches the native producer's packing/alignment; and post-read validation of every field that is used as a length, index, pointer, or handle before it is trusted. Be especially suspicious of non-blittable `T` (embedded strings/pointers) read from untrusted memory.

# How to reproduce

Observe that reading a 16-byte struct from a 4-byte buffer succeeds and prints adjacent heap bytes as `B`/`C` — an out-of-bounds read with no error.

```csharp
using System;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential)]
struct Header
{
    public int A;     // the only field the buffer actually holds
    public int B;     // read out of bounds
    public long C;    // read out of bounds; could be a pointer/handle => type confusion
}

class Program
{
    static void Main()
    {
        // Source buffer is only 4 bytes, but we read a 16-byte struct out of it.
        IntPtr buf = Marshal.AllocHGlobal(4);
        Marshal.WriteInt32(buf, 0, 0x41414141);

        // No length is passed; PtrToStructure copies SizeOf<Header>() == 16 bytes.
        Header h = Marshal.PtrToStructure<Header>(buf);
        Console.WriteLine($"A=0x{h.A:X8} B=0x{h.B:X8} C=0x{h.C:X16}");  // B, C are leaked adjacent memory

        Marshal.FreeHGlobal(buf);

        // Safe alternative: a bounded span throws instead of reading OOB.
        Span<byte> small = stackalloc byte[4];
        // MemoryMarshal.Read<Header>(small);  // throws ArgumentOutOfRangeException: too short
    }
}
```

