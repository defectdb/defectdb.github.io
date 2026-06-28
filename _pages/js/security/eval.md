---
title: "eval() called"
author: Maxim Menshikov
layout: defect
permalink: /js/security/eval
arch:
   - native
vulnerability:
   - High
ddos:
   - Low
group_full: js.security
group:
   - js
   - security
---
eval executes arbitrary code from a string and disables many engine optimisations

# Impact

`eval(s)` parses and executes the string `s` as JavaScript in the current scope,
with the current privileges. If any part of `s` derives from input the program
does not fully control — a request parameter, a config value, a field from a
database, a postMessage payload — the program is executing attacker-authored
code. The consequences are the full power of the host: in a browser it can read
the DOM, cookies and `localStorage`, exfiltrate data and perform actions as the
user; in Node.js it can reach `require`, `process`, the filesystem and the
network, i.e. full server compromise.

Beyond the security hole, `eval` deoptimises the surrounding code. Because the
engine cannot know what names the evaluated string will reference or create, it
must disable scope-based optimisations for the calling function, so nearby code
runs slower and uses more memory. `eval` also defeats minifier name-mangling and
dead-code elimination.

# Vulnerability potential

`eval` on attacker-influenced input is a textbook code-injection vulnerability
(CWE-95, "eval injection").

1. **Remote code execution.** Any string that reaches `eval` and contains
   attacker data lets the attacker run arbitrary JavaScript. In Node this means
   `require("child_process").execSync(...)` and full host takeover; in the
   browser it means script execution in the page's origin (effectively stored or
   reflected XSS that bypasses naive output encoding).
2. **Data theft and session hijacking.** Injected browser code reads
   `document.cookie`, tokens in `localStorage`, CSRF tokens and form data, and
   POSTs them to an attacker server, all within the same-origin trust boundary.
3. **Privilege and sandbox escape.** Code runs with the privileges of the
   calling context, so `eval` inside a privileged extension, service worker or
   server process inherits that authority.
4. **Denial of service.** Even without full RCE, an attacker who controls the
   string can supply `while(true){}` or an allocation bomb to hang or exhaust
   the single-threaded event loop — hence the Low DDoS rating.

Filtering or escaping the input is not a reliable defence: JavaScript has too
many ways to express the same operation. The only robust fix is to not use
`eval` on dynamic data at all.

# Technical details

`eval` is a function-valued property of the global object. Called *directly*
(`eval(s)`) it runs the code in the caller's lexical scope, so it can read and
write the caller's locals. Called *indirectly* (e.g. `(0, eval)(s)`,
`window.eval(s)`, or aliased) it runs in global scope instead — a distinction
the spec calls direct vs indirect eval. Either way the code executes with the
realm's full capabilities.

## Relatives that are also eval

`new Function("...")`, and a string passed to `setTimeout`/`setInterval`, compile
and run a string the same way (`new Function` only in global scope). They carry
the same injection risk and should be treated identically.

## Strict mode and CSP

Inside a `"use strict"` eval, variables and functions declared in the string do
not leak into the caller's scope, which limits some abuse but does not stop code
execution. In the browser a Content-Security-Policy without `'unsafe-eval'`
makes `eval` and `new Function` throw, which is the strongest mechanical
mitigation.

## Legitimate alternatives

To parse data use `JSON.parse`. To read a property by computed name use bracket
access `obj[name]`. To dispatch on a value use a lookup table/`Map` of
functions. None of these execute arbitrary code.

# Catching the issue

## Linters and static analysis

ESLint's `no-eval` and `no-implied-eval` (the latter covers `new Function` and
string `setTimeout`) flag these constructs. Security-focused scanners
(`eslint-plugin-security`'s `detect-eval-with-expression`, Semgrep, CodeQL's
`js/code-injection`, SonarQube) report eval-injection sinks and can trace
tainted input into them.

## Runtime / deployment

In the browser, ship a Content-Security-Policy that omits `'unsafe-eval'` so any
remaining `eval`/`new Function` throws at runtime. In Node, the
`--disallow-code-generation-from-strings` flag (or the `vm` option of the same
name) makes `eval`/`new Function` throw process-wide.

## Review rule

Any `eval` whose argument is not a string literal the developer fully controls is
a defect. Even literal `eval` is worth replacing with `JSON.parse`, a lookup
table, or bracket property access.

# How to reproduce

Observe that data flowing into `eval` is executed: the "calculator" input below
runs an arbitrary side effect instead of doing arithmetic.

```js
// pretend `expr` came from a URL parameter or request body
function calculate(expr) {
  return eval(expr); // code-injection sink
}

calculate("1 + 2");                       // 3 (intended)
calculate("globalThis.pwned = true; 0");  // executes attacker code
console.log(globalThis.pwned);            // true

// safe replacement for the intended use case:
const safe = (a, b) => a + b;             // or JSON.parse for data
```

