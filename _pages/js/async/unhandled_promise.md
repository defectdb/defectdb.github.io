---
title: "Promise result is unhandled"
author: Maxim Menshikov
layout: defect
permalink: /js/async/unhandled_promise
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: js.async
group:
   - js
   - async
---
The Promise has no .then/.catch and is not awaited; rejections propagate as uncaught and the value is discarded

# Impact

A Promise that is neither `await`ed nor given a `.then`/`.catch` is a
fire-and-forget operation whose result and errors are discarded. Two distinct
problems follow. First, the resolved value is lost: if the call did real work
(a fetch, a DB write, a computation) the program continues without it, often
racing ahead of an operation that has not finished — a classic source of "it
works locally but the data is sometimes missing" bugs. Second, and more serious,
a rejection has nowhere to go and becomes an *unhandled rejection*. In Node.js
the default behaviour since v15 is to print the error and terminate the process
with a non-zero exit code, so a single unhandled rejection on a request path can
crash the server. In browsers it fires a global `unhandledrejection` event and
logs to the console, leaving the operation half-done and the failure invisible
to the user.

# Vulnerability potential

The security impact is mostly availability and error-masking rather than
injection or memory safety.

1. **Denial of service.** Under Node's default `--unhandled-rejections=throw`,
   any code path whose Promise can reject without a handler lets an attacker
   crash the process by steering input down that path (a malformed request, a
   failing downstream call). On an unsupervised process this is an outage; even
   with a supervisor it is a restart-amplified resource drain — hence the Low
   DDoS rating.
2. **Silenced security errors.** If the discarded rejection was a failed
   authorization, signature check or validation, the program proceeds as if it
   succeeded, so a security-relevant failure passes unnoticed.

The defect does not itself grant code execution or data access, so the
vulnerability rating stays Low; the realistic harm is crashes and masked
failures.

# Technical details

A Promise tracks whether it has a rejection handler. If it settles to *rejected*
and the microtask queue drains without any `.then(onRejected)`/`.catch`/`await`
having been attached, the host raises an "unhandled rejection". Attaching a
handler later (after the tick) clears a previously reported rejection via the
`rejectionhandled` event, which is why the warning is timing-sensitive.

## Node.js

Since Node 15 the default mode is `--unhandled-rejections=throw`: the rejection
is thrown from the top level and, if not caught by a `process.on
('unhandledRejection')` handler, terminates the process. Older modes (`warn`,
`none`) only logged. A leftover global handler that swallows rejections trades a
crash for silent data loss, so it is not a real fix.

## Browsers

The `window`/`globalThis` `unhandledrejection` event fires and the error is
logged to the console; the page keeps running but the operation is incomplete.

## await vs floating

Inside an `async` function, `await p` routes a rejection into the surrounding
`try`/`catch` (or rejects the function's own Promise). Calling `p` without
`await` or a `.catch` leaves it "floating". `void p` documents intent but does
*not* add a handler — it still rejects unhandled.

# Catching the issue

## Linters and types

ESLint's `no-floating-promises` (in `@typescript-eslint`, type-aware) flags any
Promise that is not awaited, returned, or given a `.catch`, and is the single
most effective control; pair it with `no-misused-promises` (Promises passed
where a void callback is expected) and `require-await`. TypeScript itself does
not catch floating Promises, but the type-aware lint rule needs its type info.

## Runtime nets

Register `process.on('unhandledRejection', ...)` in Node and a
`window.addEventListener('unhandledrejection', ...)` in the browser to *log and
report* (to Sentry etc.) — as observability, not as a substitute for handling
each Promise. Keep Node in the default `throw` mode so failures are loud.

## Review

Every async call should be awaited, returned, or explicitly handled with
`.catch`. A bare `doAsync();` on its own line is a defect.

# How to reproduce

Run under Node (`node file.js`) and observe the process exiting non-zero with
"Unhandled promise rejection"; the awaited version handles it cleanly.

```js
function risky() {
  return Promise.reject(new Error("boom"));
}

// floating: rejection is unhandled -> Node crashes the process
risky();

// fixed: await inside try/catch (or attach .catch)
async function main() {
  try {
    await risky();
  } catch (err) {
    console.error("handled:", err.message);
  }
}
main();
```

