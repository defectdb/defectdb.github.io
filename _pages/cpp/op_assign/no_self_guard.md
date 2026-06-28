---
title: "Self-assignment guard missing"
author: Maxim Menshikov
layout: defect
permalink: /cpp/op_assign/no_self_guard
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: cpp.op_assign
group:
   - cpp
   - op_assign
---
operator= body does not check for self-assignment (`if (this == &rhs)`); destructive operations on members before re-copy can corrupt state when called with the same object

# Impact

A hand-written copy-assignment operator that frees or overwrites its own
resources before copying from the right-hand side breaks when the right-hand
side **is** `*this`. The typical sequence is: `delete[] data; data = new T[rhs.size];
copy from rhs.data;`. On self-assignment the `delete[]` has already freed
`rhs.data`, so the subsequent read copies from freed memory — a use-after-free —
and the object is left pointing at a buffer it then re-copies from itself. The
object ends up corrupted or holding a dangling pointer, and the original data
is lost.

# Vulnerability potential

Real but conditional on reaching self-assignment with attacker influence.

1. The destructive path is a use-after-free read of the just-freed buffer.
   If the freed block is reallocated between the `delete[]` and the copy, the
   operator copies unrelated heap contents into the object, which can leak data
   or seed later corruption.
2. Self-assignment is rarely written literally (`a = a`); it usually arrives
   through aliasing — `v[i] = v[j]` with `i == j`, a `swap` built on
   assignment, or two references/smart pointers to the same object. That makes
   it data-dependent and only sometimes attacker-reachable, so the practical
   severity is low.

# Technical details

## The destructive-then-copy anti-pattern

The bug is specific to operators that release state *before* acquiring the new
state. If the order is reversed (allocate first, copy, then free the old
buffer) the operator is naturally self-assignment safe, because nothing of
`*this` is destroyed until the copy has succeeded.

## copy-and-swap

The idiomatic fix is the copy-and-swap idiom: take the parameter **by value**
(invoking the copy constructor), then `swap` member-wise with `*this` and let
the temporary's destructor clean up the old state. Self-assignment becomes a
harmless copy-then-swap, and the operator is also strongly exception-safe — if
the copy throws, `*this` is untouched. An explicit `if (this == &rhs) return
*this;` guard also works but only addresses the alias case, not exception
safety.

## Move assignment

The same trap exists for move assignment: a moved-from `*this` that aliases
`rhs` can be left empty. Move operators need an equivalent self-move guard or a
swap-based implementation.

# Catching the issue

## Static analysis

clang-tidy `cert-oop54-cpp` (CERT OOP54-CPP, "gracefully handle
self-copy-assignment") flags user-defined `operator=` that lacks a
self-assignment check and does not use copy-and-swap. `bugprone-unhandled-self-assignment`
is the same check.

## Sanitizers / tests

A unit test that does `x = x` (and the aliased forms `v[i] = v[i]`) under
AddressSanitizer immediately reports the use-after-free. Make such a test part
of every resource-owning type's suite.

## Design rule

Prefer the rule of zero — let members (`std::vector`, `std::string`,
`unique_ptr`) provide assignment — so no hand-written `operator=` exists to get
wrong. When you must write one, use copy-and-swap.

# How to reproduce

Run under AddressSanitizer (`-fsanitize=address`); the `b = b` line reports a
heap-use-after-free in the copy loop.

```cpp
#include <cstddef>
#include <cstring>

struct Buffer {
    std::size_t n;
    char* data;

    Buffer(std::size_t n) : n(n), data(new char[n]{}) {}
    ~Buffer() { delete[] data; }

    Buffer& operator=(const Buffer& rhs) {
        delete[] data;                       // BUG: frees rhs.data on self-assign
        n = rhs.n;
        data = new char[n];
        std::memcpy(data, rhs.data, n);      // reads freed memory
        return *this;
    }
};

int main() {
    Buffer b(64);
    b = b;                                   // self-assignment -> UAF
}
```
