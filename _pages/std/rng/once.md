---
title: "srand() should be called only once"
author: Maxim Menshikov
layout: defect
permalink: /std/rng/once
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: std.rng
group:
   - std
   - rng
---
srand() shouldn't be called more than once

# Impact

``srand`` sets the seed of the C library's pseudo-random generator. It is meant
to be called exactly once, at startup. Calling it repeatedly — especially inside
a loop or before every ``rand`` — resets the generator's state each time, so the
sequence restarts instead of advancing. A very common form is
``srand(time(NULL))`` called in a tight loop: ``time`` has one-second resolution,
so every iteration within the same second reseeds with the *identical* value and
``rand`` returns the *same* number over and over. The result is output that looks
random across runs but is highly repetitive within a run, with far less entropy
than intended. Code that depends on distinct values — shuffles, sampling, jitter,
unique-ish tokens, backoff timers — quietly misbehaves.

# Vulnerability potential

``rand``/``srand`` are not cryptographically secure regardless of seeding, so
this defect should never affect security-critical values; if it does, the real
bug is using ``rand`` for security at all. Within that limitation, the reseeding
makes the output even more predictable, which can matter where weak randomness is
already (wrongly) relied upon — for example reusing the same "random" token,
nonce or temporary filename because the same seed produced the same first value.
There is no memory-safety or availability impact, hence no DoS dimension.

# Technical details

The standard PRNG keeps internal state that ``rand`` advances on each call;
``srand(seed)`` overwrites that state with a deterministic function of ``seed``.
Reseeding therefore discards all the advancement done since the last seed.

## time(NULL) granularity

``time`` returns whole seconds. Reseeding from it more than once per second
yields identical seeds, so the first ``rand`` after each reseed is identical.
This is the classic "my random numbers are all the same" bug.

## Determinism is sometimes intended

Seeding once with a fixed value for reproducible tests is legitimate; the defect
is *re*-seeding during normal operation, which neither improves randomness nor
adds entropy — the entropy of the output is bounded by the entropy of the seed,
not by how often you apply it.

## Modern alternatives

C++ ``<random>`` (``std::mt19937`` seeded once from ``std::random_device``) and
POSIX ``random``/``srandom`` have the same once-only seeding rule. For security,
use a CSPRNG (``getrandom``, ``arc4random``, ``/dev/urandom``), not ``rand``.

# Catching the issue

## Static analysis

PVS-Studio (V1041-class checks), Clang-Tidy, Coverity and PC-lint flag ``srand``
called inside a loop or more than once. A simple code-review rule — "exactly one
``srand`` near program start" — catches most cases.

## Review and runtime

Search the codebase for multiple ``srand`` call sites; there should be one.
Observing repeated identical ``rand`` outputs within a single run is the runtime
symptom. Move the single ``srand`` to initialization and never call it again.

# How to reproduce

Run the program; every printed value is identical because the loop reseeds with
the same one-second timestamp each iteration.

```c
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int main(void)
{
    for (int i = 0; i < 5; i++) {
        srand(time(NULL));      /* WRONG: reseeds every iteration */
        printf("%d\n", rand()); /* prints the same number five times */
    }
    return 0;
}
```
