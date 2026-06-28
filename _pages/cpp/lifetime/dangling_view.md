---
title: "string_view / span bound to a temporary"
author: Maxim Menshikov
layout: defect
permalink: /cpp/lifetime/dangling_view
arch:
   - native
vulnerability:
   - High
ddos:
   - Low
group_full: cpp.lifetime
group:
   - cpp
   - lifetime
---
The non-owning view's source object is a temporary (or a function return by value); after the full-expression ends the view dangles

# Impact

`std::string_view`, `std::span`, and similar non-owning views store a pointer
(and length) into memory they do not own. When the source is a temporary — a
function returning `std::string` by value, an implicit `std::string` built from
a `const char*`, a temporary `std::vector` — that temporary is destroyed at the
end of the full-expression, and the view is left pointing at freed memory. Every
later read through the view is a use-after-free: it may return the original
bytes (if the storage has not been reused yet), return whatever now occupies
that memory, or crash. Because the view often *seems* to work in debug builds,
the dangling is easy to ship and surfaces as intermittent garbage or corruption.

# Vulnerability potential

This is a genuine memory-safety defect (CWE-416 use-after-free / CWE-825).

1. **Information disclosure.** Reading a dangling `string_view` returns the
   contents of memory that has since been reallocated to unrelated data —
   another request's buffer, a freed object holding secrets — which can be
   echoed back to a user or written to a log, leaking data across trust
   boundaries.
2. **Corruption / exploitation.** A `std::span` to a freed buffer that is then
   *written* through is a use-after-free write into reclaimed heap, a primitive
   that can be escalated to controlled memory corruption.
3. **Crash.** When the freed page is unmapped or the bytes are nonsensical, the
   access faults — an availability issue, hence the secondary DoS weight; the
   confidentiality/integrity impact dominates, so the rating is high.

# Technical details

## Temporary lifetime and the binding rule

A temporary lives until the end of the full-expression that created it
(`[class.temporary]`). Lifetime *extension* only happens when a temporary binds
directly to a `const` (or `&&`) reference — and a view is **not** a reference,
it is an object that merely copies a pointer, so no extension applies. Thus

```cpp
std::string_view sv = get_name();        // get_name() returns std::string
```

constructs `sv` from a temporary `std::string`, the temporary is destroyed at
the semicolon, and `sv` dangles immediately.

## The implicit-string trap

`std::string_view sv = some_function_taking_string_view("literal" + suffix);`
and storing a view returned from a function that took an `std::string` by value
are the same bug in different clothes. A particularly sharp one is a member
`string_view` initialized from a constructor parameter passed by value.

## Why P2foo / lifetimebound exists

The committee added `[[clang::lifetimebound]]` annotations and assignment
deletions (e.g. `std::string_view`'s deleted assignment from `std::string&&` in
some proposals) precisely because this pattern is so easy to write.

# Catching the issue

## Sanitizers

AddressSanitizer reports the heap/stack-use-after-free when the dangling view
is read, with the allocation and free stacks — the most reliable detector.

## Compiler warnings

Clang `-Wdangling`, `-Wdangling-gsl`, and `-Wreturn-stack-address` diagnose
many cases at compile time, including a view initialized from a temporary
(the GSL-style lifetime warnings). GCC has `-Wdangling-pointer`. Functions can
be annotated with `[[clang::lifetimebound]]` to extend the diagnosis to APIs.

## Static analysis

clang-tidy `bugprone-dangling-handle` is the dedicated check for views/handles
bound to temporaries; the Clang Static Analyzer lifetime checker and CodeQL
also flag it.

# How to reproduce

Build with `-fsanitize=address`; reading `sv` reports heap-use-after-free
because the `std::string` returned by `make_name()` is gone by then.

```cpp
#include <string>
#include <string_view>
#include <iostream>

std::string make_name() { return std::string("alice-") + std::to_string(42); }

int main() {
    std::string_view sv = make_name();   // BUG: temporary string dies here
    std::cout << sv << '\n';             // use-after-free read
    // Fix: std::string name = make_name(); std::string_view sv = name;
}
```
