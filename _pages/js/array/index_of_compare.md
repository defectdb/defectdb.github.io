---
title: "indexOf compared to -1"
author: Maxim Menshikov
layout: defect
permalink: /js/array/index_of_compare
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: js.array
group:
   - js
   - array
---
arr.indexOf(x) >= 0 / !== -1 reads as a presence check; arr.includes(x) is shorter and clearer

# Impact

`arr.indexOf(x) !== -1` (or `>= 0`, or `> -1`) is the old idiom for "does the
array contain `x`?". It works, but it states the intent indirectly and invites
two concrete mistakes. The first is an off-by-one boundary error: writing
`indexOf(x) > 0` instead of `>= 0` silently treats an element found at index `0`
as absent — a real correctness bug that passes most tests because the searched
item is rarely first. The second is `indexOf`'s comparison semantics: it uses
strict equality and therefore can never find `NaN` (`[NaN].indexOf(NaN)` is
`-1`), so a presence check for `NaN` always reports "missing". Both issues, plus
the general readability cost, are why `arr.includes(x)` — which says exactly
"contains" and handles `NaN` — is preferred.

# Vulnerability potential

This is primarily a readability and correctness concern with little security
weight. The only realistic security angle is indirect: if the presence check
guards an allow/deny decision and the comparison boundary is wrong (`> 0`
missing index `0`, or the `NaN` blind spot), the membership test can return the
wrong answer and let a value slip past a filter it should have matched. That is a
logic bug that could weaken a check, not a vulnerability inherent to `indexOf`,
so the rating stays Low and a denial-of-service path is not credible.

# Technical details

`Array.prototype.indexOf` returns the index of the first match or `-1` when there
is none, comparing with the SameValueZero-minus-zero rule of *strict equality*
(`===`). `Array.prototype.includes`, added in ES2016, returns a boolean and
compares with *SameValueZero*, which differs from `===` in exactly one way: it
treats `NaN` as equal to `NaN`.

## The NaN difference

`[NaN].indexOf(NaN) === -1` (not found), but `[NaN].includes(NaN) === true`. Any
presence check that must account for `NaN` is wrong with `indexOf`.

## Boundary mistakes

The correct rewrites of `includes` are `indexOf(x) !== -1` and `indexOf(x) >= 0`.
The buggy variants `indexOf(x) > 0` and `indexOf(x) > -1`-vs-`>= -1` confusions
are easy to write and drop or admit the index-`0` element. `includes` removes the
comparison entirely, so the boundary cannot be wrong.

## Strings and TypedArrays

`String.prototype.includes` and `TypedArray.prototype.includes` exist too, with
the same advantage. Note `includes` is not available on plain objects or
`arguments`; use `Array.from`/spread first, or `Array.prototype.includes.call`.

# Catching the issue

## Linters

ESLint's `unicorn/prefer-includes` (from `eslint-plugin-unicorn`) flags
`indexOf(...) !== -1` / `>= 0` presence checks and autofixes them to `includes`.
Biome offers `useArrayLiterals`-adjacent style lints, and many shared configs
include the unicorn rule.

## Review

When a comparison against `-1` is doing a yes/no membership test, prefer
`includes`. Keep `indexOf` only when the *position* is actually needed (e.g. to
splice at that index). Watch specifically for `> 0` and for searches that could
encounter `NaN`, which are the two cases where the `indexOf` form is not merely
verbose but wrong.

# How to reproduce

Observe the off-by-one (`> 0` misses index 0) and the `NaN` blind spot, both
fixed by `includes`.

```js
const arr = ["a", "b", "c"];

console.log(arr.indexOf("a") > 0);    // false  -> BUG: "a" is at index 0
console.log(arr.indexOf("a") >= 0);   // true   (correct indexOf form)
console.log(arr.includes("a"));       // true   (clear and correct)

const nums = [1, NaN, 3];
console.log(nums.indexOf(NaN) !== -1); // false -> indexOf can't find NaN
console.log(nums.includes(NaN));       // true  -> includes can
```

