---
title: "Mismatched allocator and deallocator"
author: Maxim Menshikov
layout: defect
permalink: /cpp/mem/mismatched_allocator
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: cpp.mem
group:
   - cpp
   - mem
---
Memory allocated with one allocator (new / new[] / malloc) is being freed with an incompatible deallocator (delete / delete[] / free); undefined behavior

# Impact

Each allocation routine must be paired with its matching deallocation routine:
`new` ↔ `delete`, `new[]` ↔ `delete[]`, `malloc`/`calloc`/`realloc` ↔ `free`,
and any custom `operator new`/`Allocator::allocate` with its own counterpart.
Crossing them is undefined behavior. `free`ing a `new`-ed pointer (or vice
versa) hands the block to an allocator that knows nothing about it; `delete`
(scalar) on a `new[]` array misses the array cookie that records the element
count, so destructors are skipped and the wrong base pointer or size is
returned to the allocator. The practical results are heap corruption, skipped
destructors with leaked sub-resources, double-free-like state, and crashes.

# Vulnerability potential

A real memory-safety defect (CWE-762 mismatched memory routines).

1. **Heap corruption → exploitation.** Returning a block to the wrong allocator
   (or with the wrong base/size because of a missed array cookie) corrupts
   free-list or size-class metadata. Heap-metadata corruption is a
   well-established primitive for controlled writes and, with attacker-shaped
   allocations, code execution.
2. **Skipped destructors → resource/leak issues.** `delete` instead of
   `delete[]` runs only the first element's destructor (or none), leaking the
   resources the rest owned, which over time degrades availability.
3. **Crash.** Hardened allocators detect the mismatch and abort; otherwise the
   process faults — an availability impact (the secondary DoS weight). The
   corruption-to-exploit path is the dominant concern, hence the medium rating.

# Technical details

## Why new[]/delete differ

Array `new[]` may over-allocate to store an element count ("array cookie")
ahead of the returned pointer so `delete[]` can run the right number of
destructors and free the true base. Scalar `delete` neither reads that cookie
nor runs N destructors, so `delete` on a `new[]` pointer frees the wrong
address and corrupts the heap. The reverse (`delete[]` on `new`) misreads
arbitrary bytes as a count.

## new/malloc are separate heaps in principle

`operator new` is *allowed* to be implemented on top of `malloc`, but is not
required to be, and may be replaced globally or per-class. Code must therefore
never assume `free(new int)` works, even where it happens to today.

## Modern C++ avoids the choice

Use owning types that pair allocation and deallocation automatically:
`std::make_unique<T>()` / `std::make_unique<T[]>(n)`, `std::vector`,
`std::string`. With these the programmer never writes a raw `delete`, so the
pairing cannot be wrong. For C interop, wrap `malloc`'d resources in a
`unique_ptr` with a custom `free` deleter.

# Catching the issue

## Sanitizers

AddressSanitizer reports `alloc-dealloc-mismatch` (e.g. "operator new []" vs
"operator delete") and `new-delete-type-mismatch`, naming both the allocation
and the deallocation call sites. This is the most direct detector.

## Compiler

GCC/Clang `-Wmismatched-new-delete` warns when `new` and a mismatched `delete`
form can be paired at compile time; `-Wfree-nonheap-object` catches some
`free` misuse.

## Static analysis

clang-tidy `clang-analyzer-cplusplus.NewDelete` /
`clang-analyzer-unix.MismatchedDeallocator`, CERT `MEM51-CPP`, Coverity, and
PVS-Studio (V611) all flag mismatched allocation/deallocation pairs.

# How to reproduce

Build with `-fsanitize=address`; freeing a `new[]` array with scalar `delete`
makes ASan report `alloc-dealloc-mismatch`.

```cpp
#include <cstdlib>

int main() {
    int* a = new int[10];
    delete a;            // BUG: should be delete[] a;

    int* b = new int(5);
    free(b);             // BUG: new -> must use delete, not free

    int* c = (int*)malloc(sizeof(int));
    delete c;            // BUG: malloc -> must use free, not delete
}
```
