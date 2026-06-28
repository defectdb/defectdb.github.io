---
title: "Empty catch block"
author: Maxim Menshikov
layout: defect
permalink: /js/error/empty_catch
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: js.error
group:
   - js
   - error
---
The catch block has no body and no rethrow — the error is silently swallowed

# Impact

An empty `catch` block catches an exception and then does nothing — no logging,
no recovery, no rethrow — so the error is silently swallowed. The program
continues past the failed operation as though it had succeeded, which is almost
never what the surrounding logic assumes. State that the `try` block was meant to
establish is missing: a parse that failed leaves a variable undefined, a write
that threw never happened, a validation that errored is treated as passed. The
result is corrupted or partial state whose symptom appears far away from the
swallowed error, with no log entry to trace it back. Empty `catch` is one of the
hardest defects to debug precisely because it destroys the evidence.

# Vulnerability potential

The defect does not introduce injection or memory unsafety, but suppressing
errors has a genuine, if low, security dimension.

1. **Masked security failures.** If the swallowed exception was a failed
   signature check, decryption, authorization, or input validation, the program
   proceeds as if the check passed. An empty `catch` around a verification call
   can silently turn "verification failed" into "continue normally", weakening a
   control.
2. **Lost audit trail.** Security monitoring relies on errors being logged.
   Swallowing them removes the signal an intrusion-detection or alerting system
   would have used, helping an attack go unnoticed.

These are correctness-driven weaknesses rather than a directly exploitable hole,
so the rating is Low — but an empty `catch` around any security-relevant
operation deserves closer scrutiny.

# Technical details

In JavaScript a `try`/`catch` intercepts any thrown value within the `try` block;
an empty handler simply discards the bound error and lets control fall through to
the code after the statement. Since ES2019 the binding can be omitted entirely
(`try { ... } catch { }`), which makes a truly empty handler even terser and
easier to leave in by accident.

## When ignoring is legitimate

There are a few cases where the *operation* may fail harmlessly — a best-effort
`localStorage.setItem`, an optional cleanup, a feature-detection probe. Even
then the right pattern is an explicit, commented no-op (`catch { /* storage
unavailable; non-fatal */ }`) so a reader knows it is deliberate, not a
forgotten `TODO`. A bare empty block carries no such signal.

## Swallowing changes control flow

Catching also stops the exception from propagating, so callers that would have
handled or logged it never see it. If the only goal was to add context, prefer
`catch (e) { throw new Error("...", { cause: e }); }`, which preserves the
original via the error `cause` chain.

# Catching the issue

## Linters

ESLint's `no-empty` rule with `{ "allowEmptyCatch": false }` (the default) flags
empty `catch` blocks; it permits a block containing only a comment, which is the
sanctioned way to mark an intentional ignore. Biome's `noEmptyBlockStatements`
is the equivalent. Some teams add `@typescript-eslint`-style rules requiring a
caught error to be used or rethrown.

## Review rule

Require every `catch` to do one of: handle and recover, log/report, or rethrow
(optionally wrapped with `cause`). A handler that intentionally ignores the
error must contain a comment explaining why — an empty block with no comment is
treated as a defect. Wiring a logger or error-reporting SDK into catch sites
makes the "do nothing" path stand out in review.

# How to reproduce

Observe that the failure is invisible: `parse` returns `undefined` for bad input
with no error anywhere, so the caller silently mis-behaves.

```js
function parse(json) {
  let result;
  try {
    result = JSON.parse(json);
  } catch {
    // swallowed: no log, no rethrow
  }
  return result; // undefined on failure, indistinguishable from valid `undefined`
}

console.log(parse('{"ok":true}')); // { ok: true }
console.log(parse("not json"));    // undefined — error lost

// better: handle or rethrow
function parseStrict(json) {
  try {
    return JSON.parse(json);
  } catch (err) {
    console.error("invalid JSON:", err.message);
    throw err;
  }
}
```

