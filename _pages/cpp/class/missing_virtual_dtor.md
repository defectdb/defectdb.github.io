---
title: "Missing virtual destructor"
author: Maxim Menshikov
layout: defect
permalink: /cpp/class/missing_virtual_dtor
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: cpp.class
group:
   - cpp
   - class
---
Class with a virtual method has a non-virtual destructor; deleting through a base pointer slices Derived destructors and leaks resources

# Impact

When an object of a derived type is destroyed through a pointer to a base class
whose destructor is **not** virtual, the behavior is undefined (`[expr.delete]`).
In practice the compiler emits a static call to the base destructor only: the
derived destructor never runs, derived members are never destroyed, and any
resources they own (heap buffers, file handles, sockets, locks) are leaked.
On most ABIs `delete` also passes the wrong size to the deallocation function
because the static type is smaller than the actual object, which can corrupt
the allocator's size class metadata. The symptoms range from a slow memory
leak to heap corruption and crashes.

# Vulnerability potential

This is undefined behavior, so its security weight is real but usually modest.

1. The leaked resources accumulate. A request path that creates and deletes
   such objects per operation gives an attacker a way to exhaust memory, file
   descriptors, or other handles, i.e. a denial-of-service primitive.
2. When `operator delete` is handed a size that does not match the real
   allocation (sized-deallocation, jemalloc/tcmalloc size classes), allocator
   metadata can be corrupted, which in rare cases is exploitable for memory
   corruption.

# Technical details

A destructor invoked through `delete base_ptr` uses virtual dispatch **only**
if the destructor is declared `virtual`. Without it, the call is resolved
statically to `Base::~Base`, the most-derived destructor and all intermediate
destructors are skipped, and no derived member destructors are run.

## Sized deallocation

Since C++14 the compiler may call the sized form `operator delete(void*,
std::size_t)`. The size is computed from the **static** type at the delete
site. For a derived object this size is wrong, which is exactly the kind of
mismatch that hardened allocators detect or that corrupts free-list metadata.

## When it is harmless

If objects are always deleted through a pointer of their own most-derived
type, or are never deleted polymorphically (e.g. held by value, or owned by a
`shared_ptr` created from the derived type — `shared_ptr` stores a type-erased
deleter), the bug does not trigger. The danger is specifically `delete` (or a
`unique_ptr<Base>`) acting on a base pointer.

# Catching the issue

## Compiler

GCC and Clang warn with `-Wnon-virtual-dtor` (part of `-Wall -Wextra` on
Clang via `-Weffc++`); `-Wdelete-non-virtual-dtor` fires directly at the
`delete` site. Treat both as errors with `-Werror`.

## Static analysis

clang-tidy `cppcoreguidelines-virtual-class-destructor` and the Core
Guidelines rule C.35 flag polymorphic base classes lacking a virtual or
protected destructor.

## Runtime

AddressSanitizer with `new-delete-type-mismatch` checking and LeakSanitizer
report both the size mismatch and the leaked derived members at run time.

# How to reproduce

Build with `-fsanitize=address`; ASan reports `new-delete-type-mismatch` and
the leaked `std::string` buffer.

```cpp
#include <memory>
#include <string>

struct Base {
    virtual void poll() {}
    ~Base() {}                       // BUG: not virtual
};

struct Derived : Base {
    std::string big = std::string(1 << 20, 'x');   // 1 MiB, leaked
    void poll() override {}
};

int main() {
    Base* p = new Derived();
    p->poll();
    delete p;                        // runs ~Base only; ~Derived skipped
}
```
