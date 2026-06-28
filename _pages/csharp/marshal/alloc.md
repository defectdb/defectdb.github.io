---
title: "Marshal allocation"
author: Maxim Menshikov
layout: defect
permalink: /csharp/marshal/alloc
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Medium
group_full: csharp.marshal
group:
   - csharp
   - marshal
---
Marshal.AllocHGlobal/AllocCoTaskMem returns raw IntPtr that the runtime does not track; every allocation needs a matching Free call

# Impact

`Marshal.AllocHGlobal` and `Marshal.AllocCoTaskMem` allocate a block on an *unmanaged* heap and return a bare `IntPtr`. The garbage collector knows nothing about this memory: it is never moved, never traced, and never reclaimed automatically. Correctness depends entirely on the programmer pairing every allocation with exactly one matching free — `FreeHGlobal` for `AllocHGlobal`, `FreeCoTaskMem` for `AllocCoTaskMem` — on every path, including exceptions.

The failure modes are the classic unmanaged-memory bugs:

- **Leak.** Forgetting to free, or losing the pointer (overwriting the `IntPtr`, an early `return`, or an exception between alloc and free), leaks the block. Because the GC will never collect it, the leak is permanent and grows without bound for the life of the process.
- **Double free.** Calling a free routine twice on the same pointer corrupts the unmanaged heap's bookkeeping.
- **Wrong-allocator free.** Freeing an `AllocHGlobal` pointer with `FreeCoTaskMem` (or vice versa) mismatches the allocator. On Windows these route to different heaps (`LocalAlloc`/`HeapAlloc` vs `CoTaskMemAlloc`); the mismatch is heap corruption or undefined behavior.
- **Use-after-free.** Reading or writing through the pointer after it has been freed accesses memory that may have been recycled, yielding corruption or disclosure of unrelated data.
- **Uninitialized contents.** `AllocHGlobal` does **not** zero the block. The returned memory contains whatever was previously in that heap slot. Code that copies the block out, or marshals it back to managed code, before fully initializing it can leak stale process data.

# Vulnerability potential

This is genuinely security-relevant unsafe interop. Concrete attack scenarios:

1. **Information disclosure via uninitialized memory.** Because `AllocHGlobal` returns non-zeroed memory, a buffer that is allocated, partially filled, then handed to native code or copied back to the caller can expose bytes left over from prior allocations — potentially keys, tokens, or other secrets that previously occupied that heap slot.
2. **Heap corruption via double-free / wrong allocator.** An attacker who can drive a code path into freeing the same block twice, or freeing with the mismatched allocator, corrupts unmanaged heap metadata. Depending on the heap implementation, controlled corruption of allocator bookkeeping is a stepping stone to write-what-where primitives and, ultimately, code execution.
3. **Use-after-free.** If a freed pointer is retained and later written through, and an attacker can influence what gets reallocated into that slot, the stale write can corrupt live native state.
4. **Resource exhaustion (DoS).** An unbounded native leak driven by attacker-controlled request volume eventually exhausts address space / commit, crashing the process or starving it of memory. This is the basis for the `Medium` `ddos` rating.

The vulnerability rating is `Medium`: the bugs require a coding mistake to be present, but when present they sit directly on the memory-corruption / info-leak path.

# Technical details

## Allocators and their matching frees

| Allocate | Free | Underlying (Windows) |
| --- | --- | --- |
| `Marshal.AllocHGlobal` | `Marshal.FreeHGlobal` | `LocalAlloc` / process heap |
| `Marshal.AllocCoTaskMem` | `Marshal.FreeCoTaskMem` | `CoTaskMemAlloc` (the COM task allocator) |

The two heaps are independent. A pointer obtained from one must be returned to the same one. `Marshal.ReAllocHGlobal` / `ReAllocCoTaskMem` must likewise stay within their own allocator family. Mixing them is undefined behavior, not merely a leak.

## The GC does not see it

The returned `IntPtr` is just an integer to the runtime. There is no finalizer, no `IDisposable`, and no tracking. The memory is outside the managed heap, so it does not count against GC pressure and will never trigger or be reclaimed by a collection. This is exactly why a lost pointer leaks permanently.

## Memory is not zeroed

`AllocHGlobal` maps to a raw heap allocation, which returns memory in whatever state the heap left it. Do not assume zero-initialization. If zeroed memory is required, clear it explicitly (e.g. `new Span<byte>((void*)ptr, size).Clear()`), or allocate with an API that zeroes.

## Deterministic release: try/finally and SafeHandle

The minimum bar is `try { ... } finally { Marshal.FreeHGlobal(ptr); }`, so the free runs even when an exception unwinds between allocation and use.

The robust solution is a `SafeHandle`. Subclass `SafeHandleZeroOrMinusOneIsInvalid` (or use the framework's `SafeBuffer`-derived types) and free the block in `ReleaseHandle`. This ties the lifetime to a finalizable, GC-tracked wrapper, gives `Dispose` semantics, and closes the exception-safety and double-free gaps in one place. `NativeMemory.Alloc` / `NativeMemory.Free` (on modern .NET) are the lower-ceremony alternative, but still require manual pairing.

# Catching the issue

## Static analysis

Roslyn analyzer `CA2000` ("Dispose objects before losing scope") and the related disposed-resource rules can flag allocations that escape without a matching free along some path, especially when wrapped in a `SafeHandle`/`IDisposable`. SonarQube and similar tools have rules for unmanaged-resource lifetimes. CodeQL can be given a query that pairs `AllocHGlobal`/`AllocCoTaskMem` call sites against reachable `FreeHGlobal`/`FreeCoTaskMem` to surface unbalanced or mismatched frees.

## Banned / restricted APIs

Use `Microsoft.CodeAnalysis.BannedApiAnalyzers` to discourage raw `AllocHGlobal`/`FreeHGlobal` in application code and steer callers to a vetted `SafeHandle` wrapper. This makes every direct use a deliberate, reviewed exception.

## AddressSanitizer

Building and running the native side (or the whole process on a sanitizer-enabled runtime) under **AddressSanitizer** catches double-free, use-after-free, and out-of-bounds access on these unmanaged blocks at runtime — exactly the bugs static analysis cannot prove absent. Pair with leak detection (LeakSanitizer) to find blocks never freed.

## Code review

Treat every `AllocHGlobal`/`AllocCoTaskMem` as requiring: a `try/finally` or `SafeHandle`; a free with the *matching* allocator; explicit zeroing if the buffer is read before being fully written; and no retained copy of the pointer after free. Allocations near `await`/early returns deserve extra scrutiny.

# How to reproduce

Observe that the early exception path leaks the block (the free never runs) and that the freshly allocated bytes are not zero.

```csharp
using System;
using System.Runtime.InteropServices;

class Program
{
    static unsafe void Main()
    {
        // Uninitialized: AllocHGlobal does NOT zero. Prints leftover heap bytes.
        IntPtr p = Marshal.AllocHGlobal(16);
        Console.Write("uninitialized: ");
        for (int i = 0; i < 16; i++) Console.Write($"{((byte*)p)[i]:X2} ");
        Console.WriteLine();
        Marshal.FreeHGlobal(p);

        // Leak: no try/finally, exception between alloc and free loses the pointer.
        for (int i = 0; i < 1_000_000; i++)
        {
            IntPtr buf = Marshal.AllocHGlobal(4096);
            if (ThrowsSometimes(i))          // exception -> FreeHGlobal below is skipped
                throw new InvalidOperationException();
            Marshal.FreeHGlobal(buf);        // unreachable on the throwing iteration
        }
    }

    static bool ThrowsSometimes(int i) => i == 3;   // leaks the 4th block; in a loop, leaks unboundedly
}
```

