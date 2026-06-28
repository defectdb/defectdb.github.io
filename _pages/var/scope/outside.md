---
title: "Variable is accessible outside its scope"
author: Maxim Menshikov
layout: defect
permalink: /var/scope/outside
arch:
   - native
vulnerability:
   - High
ddos:
   - Low
group_full: var.scope
group:
   - var
   - scope
---
Reference to a variable or a pointer to it is invalid after leaving variable's scope

# Impact

A pointer or reference that outlives the storage it names becomes dangling the
moment the variable's scope ends. The memory is reclaimed for reuse — by the next
function call's stack frame or by a later allocation — so reads return stale or
unrelated data and writes silently corrupt whatever now occupies the slot.
Returning the address of a local, or stashing it in a longer-lived structure, is
the classic form. The symptoms appear far from the cause and often only under
optimization or specific call patterns, making this one of the most expensive
classes of bug to diagnose.

# Vulnerability potential

This issue has a strong potential to be a vulnerability; use-after-scope is a
form of use-after-free.

1. A write through a dangling pointer overwrites whatever the storage was reused
   for — a return address, a saved register, a function pointer, or heap
   metadata — giving an attacker a path to control-flow hijack and remote code
   execution.
2. A read through the dangling pointer leaks the contents of a later stack frame
   or allocation, exposing secrets, pointers, and canaries and helping defeat
   ASLR.
3. Because the reused storage often contains attacker-influenced data (the next
   function's arguments or a freshly read network buffer), the attacker can
   frequently choose what the stale pointer "sees" or what gets corrupted.

# Technical details

In C and C++ an object with automatic storage duration ceases to exist at the
end of its block; any pointer or reference to it becomes invalid and using it is
*undefined behavior*. The address itself does not change, which is why the bug is
sneaky: the pointer still "points somewhere", and the data may even look correct
until that stack space is overwritten by the next call.

## Returning addresses of locals
`return &local;` and returning a reference to a local are the textbook cases.
The frame is popped on return, so the caller holds a pointer into freed stack.

## Dangling references in C++
References do not extend the lifetime of the underlying object except in the
narrow lifetime-extension rules for temporaries bound to `const&`. A reference
member or a captured-by-reference lambda that outlives its referent has the same
defect. `std::string_view` and `std::span` into a temporary are modern variants.

## Loop and block scope
Taking the address of a variable declared inside a loop or `if` block and using
it after the block exits is the same problem at finer granularity.

# Catching the issue

## Compiler warnings
GCC and Clang emit `-Wreturn-local-addr` / `-Wreturn-stack-address` and
`-Wdangling-pointer` (GCC 12+) for the common return-of-local cases. Build with
`-Wall -Wextra -Werror`.

## Sanitizers
AddressSanitizer with `-fsanitize=address` plus `-fsanitize-address-use-after-scope`
(on by default in recent Clang) detects use-after-scope and use-after-return at
runtime with a precise stack trace. Set `ASAN_OPTIONS=detect_stack_use_after_return=1`.

## Static analysis
Clang static analyzer, clang-tidy, Coverity, and PVS-Studio track many escaping
pointers across function boundaries. In C++ the Lifetime profile / GSL and
`[[clang::lifetimebound]]` annotations let the compiler flag dangling
`string_view`/`span`. As a rule, never return or store the address of a local.

# How to reproduce

Compile with `clang -fsanitize=address` and run; ASan reports a
stack-use-after-return when the dangling pointer is read.

```c
#include <stdio.h>

int *leak_local(void) {
    int x = 42;
    return &x;          /* address of a local escapes the scope */
}

int main(void) {
    int *p = leak_local();
    /* The frame holding x is gone; *p is a dangling read. */
    printf("%d\n", *p);
    return 0;
}
```
