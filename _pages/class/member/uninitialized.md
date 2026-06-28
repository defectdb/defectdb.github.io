---
title: "Uninitialized class member"
author: Maxim Menshikov
layout: defect
permalink: /class/member/uninitialized
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: class.member
group:
   - class
   - member
---
One or more class members might be uninitialized

# Impact

A constructor that does not initialize every data member leaves those members
holding indeterminate values for objects with automatic or dynamic storage.
Methods that later read such a member operate on garbage: a flag is randomly
true or false, a count is enormous, a pointer member points nowhere in
particular. Because the object otherwise looks fully constructed, the bug
surfaces only when that member is used, often far from the constructor, and may
behave differently between debug and release builds or between consecutive
allocations.

# Vulnerability potential

This issue has a meaningful potential to be a vulnerability.

1. An uninitialized pointer or handle member that is later dereferenced or freed
   leads to wild reads/writes, use-after-free-like corruption, or double frees —
   classic paths to memory corruption and code execution.
2. An uninitialized size or length member used to bound a copy or loop can drive
   a buffer overflow or massive over-read.
3. If the object (or a sub-object) is serialized, copied into an output buffer,
   or sent across a trust boundary, the indeterminate member leaks whatever heap
   or stack residue occupied that memory, disclosing pointers or secrets.

# Technical details

In C++ a member of class type is default-constructed if not mentioned in the
initializer list, but members of *built-in* type (`int`, `bool`, raw pointers,
`enum`) and arrays of them are left uninitialized unless the constructor lists
them, a default member initializer is provided, or the object is value-/aggregate-
initialized with `{}`. Reading such a member before assignment is undefined
behavior.

## Initializer list vs assignment in body
Initialize members in the constructor's member initializer list, not by
assignment in the body; members are initialized in declaration order regardless
of list order, and a body assignment runs after default initialization. A
`-Wreorder` warning hints when the list order diverges from declaration order.

## Easy ways to get it wrong
Adding a new member but forgetting to update every constructor; multiple
constructors where only some initialize a member; and `= default` constructors
for classes with built-in members (which do *not* zero them for non-aggregate
automatic objects).

## Prefer default member initializers
Since C++11, `int count_ = 0;` / `T *p_ = nullptr;` at the point of declaration
guarantees a sane value in every constructor and is the most robust fix.

# Catching the issue

## Compiler warnings
GCC/Clang: `-Wuninitialized`, `-Wmaybe-uninitialized`, and (Clang)
`-Wuninitialized-const-reference`; also `-Weffc++` flags members missing from the
initializer list. MSVC `/W4` and `/sdl` report uninitialized members. Build with
`-Werror`.

## Sanitizers and analysis
MemorySanitizer (`-fsanitize=memory`) and Valgrind Memcheck catch the read of an
uninitialized member at runtime. clang-tidy
(`cppcoreguidelines-pro-type-member-init`) flags constructors that fail to
initialize all members; Coverity and PVS-Studio (V730) do the same statically.
As a rule, give every member a default member initializer.

# How to reproduce

Run under `clang -fsanitize=memory`; reading `ready_` reports a use of
uninitialized value, and the printed result is unpredictable.

```cpp
#include <iostream>

struct Widget {
    int  id_;
    bool ready_;          // never initialized
    Widget() : id_(1) {}  // forgot ready_
    bool usable() const { return ready_ && id_ > 0; }
};

int main() {
    Widget w;
    std::cout << w.usable() << "\n";  // depends on garbage in ready_
}
```
