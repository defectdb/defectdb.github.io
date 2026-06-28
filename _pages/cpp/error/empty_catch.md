---
title: "Empty catch block"
author: Maxim Menshikov
layout: defect
permalink: /cpp/error/empty_catch
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: cpp.error
group:
   - cpp
   - error
---
The catch block has no body and no rethrow — the exception is silently swallowed

# Impact

A `catch (...)` (or a typed catch) with an empty body intercepts an exception
and discards it: no logging, no recovery, no rethrow. Execution continues right
after the `try`/`catch` as if nothing failed, but the operation the `try` block
was performing did **not** complete. The program proceeds on partially-updated
or default state — a half-written record, an unopened connection treated as
open, a missing value silently assumed valid. The failure is invisible at the
point it happens and resurfaces later as wrong results, corrupted persisted
data, or a confusing crash far from the real cause, which makes diagnosis
expensive.

# Vulnerability potential

Largely a robustness/correctness defect; security relevance is indirect.

1. If the swallowed exception was the program's *only* signal that a
   security-relevant step failed — a signature/credential check that threw, a
   permission lookup, an integrity validation — silently continuing can let
   execution proceed as though the check had passed, turning a hard failure
   into a quiet bypass. This depends entirely on what was inside the `try`.

There is no inherent memory-safety or denial-of-service consequence: swallowing
an exception neither corrupts memory nor consumes resources. The risk is the
masking of failures, so the security weight is low and the DoS weight is none.

# Technical details

## Swallowing vs. handling

A catch block is meant to *handle* — recover, translate, log, or rethrow. An
empty body does none of these; it asserts "this can never fail in a way I care
about", which is rarely true. The especially dangerous form is `catch (...) {}`,
which also swallows exceptions the author never anticipated (including ones that
signal programmer errors).

## Legitimate-looking exceptions

There are narrow cases where ignoring is acceptable — e.g. a destructor or
cleanup path that must not propagate, or a best-effort optional operation. Even
then the intent should be explicit: comment *why*, and ideally name the caught
type rather than catching everything. A bare empty `catch` gives reviewers no
way to tell a deliberate ignore from a forgotten TODO.

## Related anti-patterns

`catch (...) { }` around a broad block, catching a base `std::exception` and
not logging `what()`, and catching then returning a default/empty value without
signalling failure to the caller are the same defect in different shapes.

# Catching the issue

## Static analysis

clang-tidy `bugprone-empty-catch` is the direct check; `cert-err*` rules
(don't swallow exceptions), SonarQube (S2486 "exceptions should not be
ignored"), PVS-Studio, and Coverity all flag empty or no-op catch blocks.

## Compiler / review

Compilers do not warn on this by design, so it is primarily a review and
lint-policy item: require every catch to log, recover, rethrow, or carry an
explicit comment justifying the ignore. Centralized error handling (a logging
helper called from every catch) makes silent swallowing stand out.

# How to reproduce

Run it: the parse failure is swallowed, so `total` is used uninitialized-in-
intent (left at 0) and the program reports success on bad input.

```cpp
#include <string>
#include <iostream>

int main() {
    std::string input = "not-a-number";
    int value = 0;
    try {
        value = std::stoi(input);     // throws std::invalid_argument
    } catch (...) {
        // BUG: exception silently swallowed; value stays 0
    }
    std::cout << "parsed value = " << value << "  (looks fine, but parse failed)\n";
}
```
