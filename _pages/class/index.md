---
title: "Classes"
author: Maxim Menshikov
layout: defect
permalink: /class
---

Defects rooted in the definition and lifecycle of classes — the fields, members, and invariants that an object is supposed to uphold from construction to destruction. These are bugs in the contract a class makes with the rest of the program, where the type compiles cleanly yet an instance is left in a state its methods never anticipated.

The recurring theme is incomplete or inconsistent object setup: members that are read before they are assigned, invariants that hold for some constructors but not others, and state that drifts out of sync with the class's assumptions. Such faults are easy to miss because each method looks correct in isolation; the defect lives in the gap between them, surfacing only when an object reaches a member that was never properly established.

