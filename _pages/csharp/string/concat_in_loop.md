---
title: "string concatenation in loop"
author: Maxim Menshikov
layout: defect
permalink: /csharp/string/concat_in_loop
arch:
   - native
vulnerability:
   - None
ddos:
   - Low
group_full: csharp.string
group:
   - csharp
   - string
---
Each += allocates a new string; use StringBuilder when concatenating in a loop

# Impact

Building a string by repeatedly doing `result += piece` inside a loop turns a linear job into a **quadratic** one. Because `string` is immutable, each `+=` allocates a brand-new string and copies every character accumulated so far. For `n` iterations producing a final length `L`, the loop performs on the order of `O(n^2)` character copies and allocates `O(n)` intermediate strings totalling `O(n^2)` bytes of short-lived garbage.

Concrete consequences:

- **CPU time** grows with the square of the input. A loop that is instant for 100 items can take seconds for 100,000 and effectively hang for a few million.
- **GC pressure.** Every iteration's intermediate string becomes garbage immediately, driving frequent Gen 0 collections and, for large accumulators, promotions to Gen 2 and Large Object Heap allocations (any string over ~85,000 bytes). This stalls the whole process, not just the offending thread.
- **Memory spikes** to roughly twice the final size at the moment of the last copy, plus collector overhead.

The fix is `System.Text.StringBuilder`, which appends in amortised `O(1)` into a resizable buffer, giving overall `O(L)` time and a single backing array. `string.Join`, `string.Concat(IEnumerable)`, and interpolation/`Span`-based formatting are also linear.

# Vulnerability potential

This is primarily a performance defect, not a security flaw, so the vulnerability rating is None. There is a measured **denial-of-service** angle (rated Low): if the iteration count or per-item size is driven by attacker-controlled input — number of rows in an uploaded CSV, items in a JSON array, repeated tokens in a request — the quadratic blowup lets a modestly sized request consume disproportionate CPU and memory, an algorithmic-complexity (resource-exhaustion) vector. In most code paths the counts are bounded or small, so the practical risk is minor; it becomes meaningful only on hot paths that concatenate untrusted, unbounded collections.

# Technical details

## Why immutability forces copies

A `string` is an immutable sequence of UTF-16 code units stored in a fixed-size object. There is no in-place append, so `a += b` compiles to `a = string.Concat(a, b)`, which allocates a new string of length `a.Length + b.Length` and copies both operands into it. Inside a loop the left operand keeps growing, so iteration `k` copies all `~k` characters accumulated so far. Summing `1 + 2 + ... + n` gives `n(n+1)/2`, i.e. `O(n^2)` copies and `O(n)` discarded strings.

## What StringBuilder does differently

`StringBuilder` holds a mutable `char[]` (in modern runtimes, a chunked linked structure). `Append` writes into free capacity and only reallocates when the buffer is full, doubling capacity each time. Amortised over all appends this is `O(1)` per character and `O(L)` total, with one (or a few) backing arrays instead of `n` throwaway strings. Pre-sizing with `new StringBuilder(expectedLength)` removes the intermediate growth reallocations entirely.

## GC interaction

The discarded intermediates are exactly the kind of short-lived allocation Gen 0 is designed for, but at `O(n^2)` total bytes the allocation rate alone forces many collections. Large accumulators cross the ~85 KB LOH threshold, and LOH allocations are expensive and not compacted by default, so a big quadratic concat can fragment the heap and trigger full blocking GCs.

# Catching the issue

## Roslyn / .NET analyzers

- **CA1834 (Use `StringBuilder.Append(char)` for single characters)** and the broader performance category nudge toward `StringBuilder`.
- Many teams add the dedicated **"string concatenation in a loop"** rule via analyzer packs; SonarQube ships it directly.

## SonarQube

Rule **S1643 — "Strings should not be concatenated using `+` in a loop"** flags `+=`/`+` on strings inside `for`/`foreach`/`while` bodies and recommends `StringBuilder`. This is the most reliable automated catch for this defect.

## Profiling and review

- A memory profiler (Visual Studio Diagnostic Tools, dotMemory, PerfView) shows a flood of short-lived `System.String` allocations and high Gen 0 collection counts that scale super-linearly with input — the signature of this bug.
- In review, treat any `+=` on a string inside a loop as a defect by default. Prefer `StringBuilder`, or `string.Join` / `string.Concat(collection)` when the pieces already exist as a sequence.

# How to reproduce

Observe that the `+=` version is dramatically slower and allocates far more than the `StringBuilder` version for the same output.

```csharp
using System;
using System.Diagnostics;
using System.Text;

class Program
{
    static void Main()
    {
        const int n = 100_000;

        long before = GC.GetTotalAllocatedBytes();
        var sw = Stopwatch.StartNew();
        string slow = "";
        for (int i = 0; i < n; i++)
            slow += "x";                       // O(n^2): reallocates and copies every time
        sw.Stop();
        Console.WriteLine($"+=          : {sw.ElapsedMilliseconds} ms, " +
                          $"{(GC.GetTotalAllocatedBytes() - before) / 1_000_000} MB allocated");

        before = GC.GetTotalAllocatedBytes();
        sw.Restart();
        var sb = new StringBuilder(n);         // pre-sized; O(n)
        for (int i = 0; i < n; i++)
            sb.Append('x');
        string fast = sb.ToString();
        sw.Stop();
        Console.WriteLine($"StringBuilder: {sw.ElapsedMilliseconds} ms, " +
                          $"{(GC.GetTotalAllocatedBytes() - before) / 1_000_000} MB allocated");
    }
}
```

