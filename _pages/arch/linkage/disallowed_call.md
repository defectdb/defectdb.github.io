---
title: "Disallowed call"
author: Maxim Menshikov
layout: defect
permalink: /arch/linkage/disallowed_call
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
Call is explicitly not allowed by architectural rules

# Impact

A module reaches a target (function, class, symbol, package or module) that the
project's architecture contract has *explicitly forbidden* for that source — a
deny rule, not merely an absence of permission. Concretely this means a layering
or module-boundary policy (for example "the UI layer must not call the
persistence driver directly", "no module outside `crypto/` may call the raw
cipher primitives", "feature module A must not depend on feature module B")
is broken by a real call edge in the code or the linked binary.

The immediate consequences are architectural rather than a runtime crash:

- An intended boundary is bypassed. If the forbidden target was protected
  precisely because the in-between layer performs validation, authorization,
  auditing, rate limiting, sanitization or transaction management, that logic
  is now silently skipped on this path.
- Coupling that the architecture was designed to prevent is introduced.
  Layers that were meant to be replaceable or testable in isolation become
  entangled, which raises change cost and makes future refactoring risky.
- Build/link-level invariants (allowed link sets, exported-symbol contracts,
  plugin sandboxes) no longer hold, so reasoning about what can reach what
  becomes unreliable for the whole component.

# Vulnerability potential

By itself a disallowed call is a maintainability defect, but it has a genuine,
if indirect, security dimension whenever the forbidden edge bypasses a layer
that existed to enforce a security property.

1. **Bypassed validation / sanitization.** If the deny rule protected an
   input-validation or escaping layer (e.g. UI code is forbidden from calling
   the SQL/driver layer directly, forcing all access through a repository that
   parameterizes queries), the disallowed call can reintroduce injection,
   path-traversal or deserialization flaws that the architecture had designed
   out.
2. **Bypassed authorization / auditing.** When a service-boundary or facade is
   the mandated entry point because it performs access-control checks or writes
   audit records, calling past it can yield an authorization bypass or destroy
   the audit trail.
3. **Trust-boundary erosion.** Rules such as "untrusted/plugin code must not
   call the privileged core directly" are security partitions; a disallowed
   call across them widens the attack surface and can defeat sandboxing.

If the forbidden boundary carried no security responsibility (a purely stylistic
or dependency-hygiene rule), the security impact is negligible and this is best
treated as technical debt.

# Technical details

An architecture contract describes the allowed call/dependency graph between
named units — layers, modules, packages, components or symbol groups. Each rule
classifies an edge `caller -> callee` as allowed, denied, or unspecified. A
*disallowed call* is the case where an explicit **deny** rule matches the edge:
the policy says "this caller must never reach this callee", and the analyzed
program nevertheless contains that edge.

## Where the edge comes from

The offending edge can be discovered at different stages:

- **Source level** — a direct function/method invocation, a `#include` or
  `import` that pulls in the forbidden module, or instantiation of a forbidden
  type. Detected by parsing the call graph from source/AST.
- **Link level** — for compiled native code, the edge appears as an undefined
  symbol that the linker resolves against the forbidden translation unit or
  library. Even with clean-looking source, a transitive header or macro can
  emit the reference.
- **Runtime / dynamic** — calls made through function pointers, virtual
  dispatch, `dlsym`, reflection or dependency injection may not be visible to a
  purely syntactic check and require a points-to/heuristic analysis.

## Why deny rules exist

Deny rules encode invariants that "allow everything except" cannot express
cheaply: forbidding back-edges that would create dependency cycles, isolating a
deprecated or unsafe API, keeping a security-sensitive primitive reachable only
through a vetted wrapper, or enforcing the acyclic layering of a clean/hexagonal
architecture. The contract is typically expressed in a config (layer maps,
`depends_on`/`forbidden` lists, module allow/deny matrices) checked by tooling
against the actual graph.

# Catching the issue

The defect is best caught automatically and continuously, since it tends to
creep back in during routine edits.

## Architecture-fitness tooling

Encode the layering contract in a dedicated checker run in CI: ArchUnit /
ArchUnitNET, Konsist, Spotify's `forbidden-apis`, Deptrac, Structure101 /
Sonargraph / Lattix, or NetArchTest. These let you assert deny rules such as
`noClasses().that().resideInLayer("ui").should().callMethodWhere(...layer ==
"persistence")` and fail the build on violation.

## Native / link level

For C/C++, restrict the export surface with linker version scripts
(`--version-script`), mark internal symbols hidden
(`-fvisibility=hidden`), and verify the actual symbol references with `nm`,
`objdump -d`, `readelf --dyn-syms` or a Bazel `deps`/visibility rule
(`visibility = ["//allowed:__pkg__"]`). Bazel and Buck `visibility`
attributes turn a disallowed dependency edge into a build error.

## Static analysis & review

Module-boundary rules in ESLint (`no-restricted-imports`), `import-linter`
(Python), `go vet`/`depguard` (Go) and clang-tidy's restricted-include checks
catch the source-level cases. Make the contract part of code review: any change
that adds a dependency edge between two units should require an explicit,
reviewed update to the architecture map rather than being added ad hoc.

# How to reproduce

Suppose the contract states: *the presentation layer (`ui.c`) must talk only to
the service layer (`service.h`); it is explicitly forbidden from calling the
storage driver (`db.h`) directly, because the service layer is where access
control and input validation live.* The reproducer below contains exactly that
forbidden edge — observe that `ui.c` references `db_exec`, a symbol that the
deny rule says it must never reach.

```c
/* db.h  --- storage layer: forbidden target for the UI layer */
int db_exec(const char *raw_sql);   /* low-level, no validation */

/* service.h --- the ONLY layer the UI is allowed to call */
int svc_delete_user(int caller_id, int user_id); /* checks authz, escapes input */

/* ui.c  --- presentation layer */
#include "db.h"        /* VIOLATION: UI must not depend on the storage layer  */
#include "service.h"

void on_delete_clicked(int user_id) {
    /* Allowed edge: goes through the service layer's checks. */
    /* svc_delete_user(current_user, user_id); */

    /* DISALLOWED CALL: jumps straight to the driver, skipping authz and
       SQL escaping that svc_delete_user would have performed. An architecture
       checker matching the deny rule ui -> db flags this edge. */
    char q[64];
    snprintf(q, sizeof q, "DELETE FROM users WHERE id=%d", user_id);
    db_exec(q);
}
```

