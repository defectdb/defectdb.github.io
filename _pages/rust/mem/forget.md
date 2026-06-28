---
title: "mem::forget called"
author: Maxim Menshikov
layout: defect
permalink: /rust/mem/forget
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Medium
group_full: rust.mem
group:
   - rust
   - mem
---
std::mem::forget leaks the value's destructor

# Impact

`std::mem::forget(x)` takes ownership of `x` and returns without running its
destructor. Whatever cleanup `Drop` would have performed simply never happens:
heap allocations behind a `Box`/`Vec`/`String` are leaked, files and sockets
stay open, `MutexGuard`s never release their lock, reference counts in
`Rc`/`Arc` are never decremented, and buffers holding secrets are never zeroed.

Leaking is *memory-safe* — it does not, by itself, cause undefined behavior, and
that is why `forget` is a safe function. The damage is resource exhaustion and
broken invariants: a forgotten `MutexGuard` poisons access to its data forever
(a deadlock for every later locker), a forgotten transmit/cleanup leads to
monotonically growing memory and FD usage, and a forgotten guard that was
supposed to restore state leaves the program in an inconsistent condition.

# Vulnerability potential

1. **Resource-exhaustion DoS.** If a code path that an attacker can drive
   repeatedly forgets owned resources (memory, file descriptors, connections),
   usage grows without bound until the process is OOM-killed or hits the FD
   limit and can no longer accept work.
2. **Deadlock DoS.** Forgetting a lock guard (`MutexGuard`, `RwLockWriteGuard`)
   means the lock is never released; every subsequent attempt to acquire it
   blocks forever, hanging the affected subsystem.
3. **Secret retention / info leak.** Types that zero sensitive material in their
   destructor (keys, passwords, `Zeroizing<_>` buffers) leave that material in
   memory if forgotten, lengthening the window for it to be read via a memory
   disclosure or to appear in a core dump.
4. **Breaking unsafe invariants.** Several `unsafe` patterns rely on a
   destructor running exactly once. `forget`ting a value mid-way (e.g. a guard
   that owns raw resources, or a half-initialized value during a `ptr::write`
   dance) can leave another owner believing it must also free the same
   resource — a setup for a later double-free if combined with `unsafe` code.

These are availability and information risks rather than direct memory
corruption, hence Medium rather than High.

# Technical details

`forget` is implemented as `ManuallyDrop::new(t);` — it moves the value into a
wrapper that suppresses `Drop` and then lets that wrapper go out of scope without
dropping the inner value. No bytes are freed and no `Drop::drop` runs.

## Leaking is safe, not unsound

Rust deliberately does *not* guarantee that destructors run (the "leak is safe"
or "leakpocalypse" decision). APIs must therefore remain memory-safe even if a
value is leaked; this is why `thread::scope`/scoped threads were redesigned and
why `Vec::drain`/`mem::forget` interactions were hardened. The hazard here is
semantic (resources/locks/secrets), not a soundness hole in `forget` itself.

## Legitimate uses

`forget` is correct when ownership has already been transferred elsewhere — e.g.
after handing a raw pointer to FFI that will free it, or after `ptr::read`ing a
value out of a place you must not let drop. In those cases prefer
`ManuallyDrop`, which makes the intent explicit and local.

# Catching the issue

## Lint

`clippy::mem_forget` flags calls to `std::mem::forget` so each can be reviewed
for justification. Code-review rule: every `forget` needs a comment explaining
who runs the cleanup instead.

## Leak detection

Run under a leak detector — Valgrind/Memcheck, or build with
`-Z sanitizer=leak` (LeakSanitizer, nightly) / link against LSan — to see the
leaked allocations. Miri also reports leaks at the end of execution unless
`-Zmiri-ignore-leaks` is set, making it useful in tests.

## Safer alternatives

Use `ManuallyDrop<T>` for deliberate, scoped suppression; use `drop(x)` (or just
let the value fall out of scope) when you *do* want cleanup; and for FFI
hand-off prefer explicit `into_raw`/`from_raw` pairs so ownership transfer is
auditable.

# How to reproduce

Run the following under a leak checker; observe that the `String`'s heap buffer
is never freed because its destructor is skipped.

```rust
fn main() {
    let secret = String::from("super secret that should be cleaned up");
    std::mem::forget(secret); // destructor never runs: heap buffer leaked
    // `secret` is gone from scope but its allocation is never freed.
}
```
