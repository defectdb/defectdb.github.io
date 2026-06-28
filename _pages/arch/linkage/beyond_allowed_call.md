---
title: "Call beyond allowed"
author: Maxim Menshikov
layout: defect
permalink: /arch/linkage/beyond_allowed_call
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: arch.linkage
group:
   - arch
   - linkage
---
Call is beyond allowed by architectural rules

# Impact

A module makes a call that falls *outside the set of targets it is permitted to
reach*. Unlike an explicit deny ("you must never call X"), this is an
allow-list violation: the architecture contract enumerates which targets a unit
may legitimately call, and the observed call edge is not on that list — it goes
"beyond" what was allowed. The call is not necessarily named as forbidden;
it simply has no grant.

The practical effect is that the module's dependency surface has grown past its
sanctioned scope:

- The unit now reaches code it was never specified to depend on, so its real
  contract (what it touches, what can break it, what must be present to build
  and run it) no longer matches its documented one.
- Because allow-list policies are how minimal-coupling, plugin-isolation and
  capability-confinement designs are expressed, a call beyond the allowed set
  quietly expands the module's effective capabilities and its blast radius when
  something goes wrong.
- Reviewers and tools that trust the allow-list to reason about reachability
  draw wrong conclusions: an edge exists that the model says cannot, so impact
  analysis, test scoping and security partitioning based on that model are
  invalidated for this component.

# Vulnerability potential

An allow-list is, in security terms, a least-privilege boundary, so exceeding it
has the same flavor of risk as a privilege or capability escalation — though
whether it matters depends entirely on what the unsanctioned target does.

1. **Capability creep / least-privilege break.** Allow-list contracts are the
   architectural form of "this module may only do these things". A call beyond
   the list grants the module an ability (file access, network egress, a
   privileged syscall wrapper, a crypto primitive) it was never meant to have,
   which is precisely the shape of a confused-deputy or sandbox-escape problem.
2. **Reaching code that bypasses a mandated gateway.** If the allowed target was
   a single vetted facade and the unit now calls a sibling that skips that
   facade, validation/authorization performed only in the facade is lost.
3. **Unreviewed external surface.** When the unallowed target is third-party or
   cross-component code, the module now trusts inputs/outputs that were never
   threat-modeled for this caller, expanding the attack surface.

When the call merely reaches a benign internal helper that happens not to be on
the list (an over-strict policy), the security relevance is minimal and the
finding is mostly about keeping the architecture model accurate.

# Technical details

The architecture contract for a unit can be expressed in two complementary
styles. A **deny-list** says "these specific edges are forbidden, everything
else is fine". An **allow-list** (whitelist) says "these are the only edges
permitted, everything else is forbidden by default". This defect is the
allow-list case: the contract grants a unit a finite set of legal callees, and
the analyzed program contains a call edge that is *not in that set*.

## Default-deny semantics

The key property is that the policy is default-deny: anything not explicitly
permitted is a violation. This is stricter and safer than a deny-list, because
a newly introduced dependency is flagged automatically without anyone having to
predict and enumerate it as "bad" in advance. The trade-off is that legitimate
new dependencies require an explicit, deliberate update to the allow-list —
which is the point: the update is a reviewable decision.

## How the out-of-scope edge appears

As with explicit-deny violations, the offending edge may be a direct source call,
an `import`/`#include`, a link-time symbol reference, or a dynamic call via
function pointer, virtual dispatch, `dlsym` or reflection. Allow-lists are
frequently scoped by capability or layer (a "ports and adapters" boundary, a
plugin's permitted host API, a module's declared `deps`), so the analyzer
compares each outgoing edge of the unit against the grant set and reports any
edge whose target is outside it.

## Distinction from "disallowed call"

A *disallowed call* matches an explicit deny rule; a *call beyond allowed*
matches no grant in an allow-list. The first is "you crossed a wall someone put
up"; the second is "you stepped outside the fenced area you were given". Both
break the contract, but the allow-list violation is detected by default-deny
rather than by enumerated prohibition.

# Catching the issue

Allow-list violations are caught by tools that support default-deny dependency
policies, and by build systems whose visibility model is allow-list by nature.

## Build-system visibility (native and beyond)

Bazel and Buck express allow-lists directly: a target's `visibility` and its
explicit `deps` form the permitted set, and any edge outside it is a build
error. For C/C++ this is the most robust enforcement because it also covers the
link graph. Pair it with hidden default symbol visibility
(`-fvisibility=hidden`) and a linker `--version-script` so that only the
sanctioned exports are reachable in the first place.

## Architecture-fitness frameworks

ArchUnit/ArchUnitNET, Deptrac (with `ruleset`/`layers` as an allow map),
Sonargraph/Structure101, import-linter's `layers`/`forbidden` contracts and
Konsist let you state "module M may depend only on {A, B}" and fail CI on any
extra edge. Configure them in *allow* mode (default-deny) rather than listing
prohibitions.

## Linters and review discipline

ESLint `no-restricted-imports` with an allow pattern, Go `depguard` in allow
mode, and clang-tidy include restrictions handle source-level edges. Crucially,
make adding a target to the allow-list a reviewed, intentional change: the
value of default-deny is lost if developers reflexively widen the list to make
the checker pass.

# How to reproduce

Suppose the contract grants the report module exactly one permitted dependency:
*`report.c` may call only the read-only query API (`store_read.h`); that is the
whole allow-list for this unit.* The mutation API `store_write.h` is not on the
list — it is not specifically banned, it is simply outside the granted set.
Observe that `report.c` below calls `store_delete_old`, an edge with no grant,
so a default-deny architecture check reports a call beyond the allowed set.

```c
/* store_read.h  --- the ONLY API report.c is allowed to use */
const char *store_query(const char *key);

/* store_write.h --- NOT in report.c's allow-list */
int store_delete_old(int days);   /* mutates the store */

/* report.c  --- allow-list = { store_read.h } */
#include "store_read.h"
#include "store_write.h"   /* edge is outside the granted set */

void build_monthly_report(void) {
    const char *v = store_query("revenue");   /* OK: target is on the allow-list */
    /* ... format the report ... */
    (void)v;

    /* BEYOND ALLOWED: report generation reaches into the write API, which the
       allow-list never granted to this module. The call is not explicitly
       denied, yet it exceeds report.c's permitted capability set, so a
       default-deny checker flags report -> store_write as out of scope. */
    store_delete_old(30);
}
```

