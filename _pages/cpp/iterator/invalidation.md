---
title: "Iterator used after container mutation"
author: Maxim Menshikov
layout: defect
permalink: /cpp/iterator/invalidation
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: cpp.iterator
group:
   - cpp
   - iterator
---
An iterator captured from a container was used after a call that may invalidate it (e.g. push_back, insert, erase, clear, resize); dereferencing or incrementing is undefined behavior

# Impact

Iterators, pointers, and references into a standard container are only valid as
long as the container's internal storage does not move or shrink underneath
them. A mutating operation — `push_back` that reallocates a `vector`, `erase`
on the element being iterated, `insert`/`rehash` on an unordered container,
`clear`, `resize` — can invalidate them. Using an invalidated iterator
(dereferencing, incrementing, comparing) is undefined behavior. With a `vector`
the storage is typically freed and reallocated, so a stale iterator is a
dangling pointer into freed memory: the classic outcome is a use-after-free
read or write that returns wrong data, corrupts the heap, or crashes.

# Vulnerability potential

This is a genuine memory-safety defect.

1. After a reallocating `push_back`/`insert`, a retained iterator points into
   the freed old buffer. Continued reads through it leak whatever now occupies
   that memory; writes through it corrupt the heap — both classic
   use-after-free conditions that can be escalated to controlled corruption.
2. The erase-while-iterating mistake (`erase(it)` then `++it`) advances a
   dangling iterator and walks off the structure, producing out-of-bounds
   access whose reach depends on attacker-influenced element counts.
3. The wrong results from a silently invalidated iterator can also drive logic
   onto unintended paths. A crash on the corrupted access is an availability
   issue, but the memory-safety angle dominates, so the security weight is the
   higher concern.

# Technical details

## Per-container rules

`std::vector`: any insertion may reallocate and invalidate **all** iterators
and references when size exceeds capacity; `erase` invalidates everything from
the erase point onward. `std::deque`: insert/erase in the middle invalidates
all iterators. `std::unordered_map/set`: insertion invalidates iterators when a
rehash occurs (references stay valid); `erase` invalidates only the erased
element. `std::map/set` (node-based): insert never invalidates; `erase`
invalidates only the erased node. Knowing which operation invalidates what is
the whole game.

## Erase–remove and the modify-while-iterate loop

The single most common form is mutating a container inside a range-based or
iterator `for` loop over it. The correct idioms are the return value of
`erase` (`it = c.erase(it);`) for node and vector containers, and
`std::erase`/`std::erase_if` (C++20) or the erase–remove idiom for bulk
removal — none of which leave a stale iterator live.

## Reference and pointer invalidation

The same rules apply to raw pointers and references obtained from elements
(e.g. `T& r = v[0]; v.push_back(...); use(r);`), not only to iterator objects.

# Catching the issue

## Sanitizers

AddressSanitizer catches the use-after-free / heap-buffer-overflow when a
`vector`'s buffer is reallocated and a stale iterator is dereferenced. It is
the most reliable runtime detector.

## Hardened standard library

libstdc++ with `-D_GLIBCXX_DEBUG` and libc++ with `-D_LIBCPP_HARDENING_MODE=
_LIBCPP_HARDENING_MODE_DEBUG` add iterator-validity checks that abort with a
diagnostic precisely at the invalid use. MSVC's `_ITERATOR_DEBUG_LEVEL=2` does
the same.

## Static analysis

clang-tidy `bugprone-inaccurate-erase` and the
`clang-analyzer-cplusplus.InnerPointer` / iterator-invalidation checks, plus
Coverity and PVS-Studio (V789), flag retaining an iterator across a mutation.

# How to reproduce

Build with `-fsanitize=address` (or `-D_GLIBCXX_DEBUG`); the dereference after
`push_back` reallocates the buffer and ASan reports heap-use-after-free.

```cpp
#include <vector>
#include <iostream>

int main() {
    std::vector<int> v{1, 2, 3};
    auto it = v.begin();          // iterator into current buffer
    for (int i = 0; i < 1000; ++i)
        v.push_back(i);           // eventually reallocates -> it dangles
    std::cout << *it << '\n';     // use-after-free read
}
```
