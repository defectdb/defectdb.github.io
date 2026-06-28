---
title: "Virtual call from constructor or destructor"
author: Maxim Menshikov
layout: defect
permalink: /cpp/ctor_dtor/virtual_call
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: cpp.ctor_dtor
group:
   - cpp
   - ctor_dtor
---
During construction / destruction the dynamic type is the base; the virtual dispatch resolves to the base override, not the derived one

# Impact

While a base subobject's constructor (or destructor) runs, the object's dynamic
type **is** the base, not the eventual most-derived type. A virtual call made
from the base constructor therefore dispatches to the base's override, never
the derived one — even though the programmer almost always intended the derived
behavior. The derived part of the object does not exist yet (its members are
uninitialized, its constructor has not run), so calling its override would read
garbage; the language prevents that by adjusting the vtable per construction
stage. The visible effect is that an "initialization hook" silently runs the
wrong (base) version, leaving the object configured as if the derived
customization never happened.

# Vulnerability potential

Usually a logic defect, with one sharp edge.

1. If the virtual function is **pure** and has no definition, the call from the
   constructor/destructor invokes `__cxa_pure_virtual`, which calls
   `std::terminate` and aborts. A path that constructs such an object on demand
   then gives a reliable crash, i.e. a denial-of-service trigger.
2. When the base override and the intended derived override differ in a
   security-relevant way (a no-op base validator vs. a real derived one), the
   object can finish construction in a weaker-than-intended state. This is
   secondary and design-specific.

Without a pure-virtual or security-relevant override, it is a plain correctness
bug.

# Technical details

## vtable staging

The implementation sets the object's vtable pointer to the base class vtable
when the base constructor begins, then updates it to the derived vtable once
the derived constructor body starts (and reverses the sequence during
destruction). So inside `Base::Base`, `this`'s vptr names `Base`, and any
virtual dispatch resolves statically to `Base`'s entry. `dynamic_cast` and
`typeid` likewise report the base type during this window.

## Pure virtual from a constructor

If the resolved entry is a pure virtual function with no body, calling it is
undefined and the standard libraries route it to `std::terminate` via
`__cxa_pure_virtual`. Even a *non*-virtual member called from the constructor
that itself makes a virtual call hits the same staging rule.

## Why it surprises people

In languages like Java/C# the most-derived override runs from the base
constructor (which has its own hazard: it sees uninitialized derived fields).
C++ deliberately chose the opposite to keep calls type-safe, so developers
coming from those languages expect the derived call and do not get it.

# Catching the issue

## Compiler

GCC/Clang warn with `-Wclass-memaccess`-adjacent diagnostics, but the direct
one is clang-tidy. Calling a pure virtual is caught at run time by the
`__cxa_pure_virtual` abort.

## Static analysis

clang-tidy `clang-analyzer-optin.cplusplus.VirtualCall` (and the standalone
`bugprone-virtual-near-miss`) flag virtual calls made from constructors and
destructors. The Core Guidelines rule C.82 ("don't call virtual functions in
constructors and destructors") is the canonical reference.

## Design

Move post-construction customization out of the constructor: use a two-phase
`init()` called after the object is fully built, or a factory function that
constructs and then invokes the virtual step.

# How to reproduce

Run it: even though a `Derived` is created, the constructor prints the **base**
configuration because the virtual call dispatches to `Base::configure`.

```cpp
#include <iostream>

struct Base {
    Base() { configure(); }                       // virtual call during base ctor
    virtual void configure() { std::cout << "base config\n"; }
    virtual ~Base() = default;
};

struct Derived : Base {
    void configure() override { std::cout << "derived config\n"; }
};

int main() {
    Derived d;        // prints "base config", not "derived config"
}
```
