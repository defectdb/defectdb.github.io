---
title: "Blocks"
author: Maxim Menshikov
layout: defect
permalink: /mem/block
group:
   - mem
---

Defects in the life cycle of an allocated memory block — the span between obtaining storage and returning it. The failures cluster at the two ends of that span: never releasing a block whose last reference has been lost, which leaks memory, and releasing one through the deallocation paths in ways that go wrong. Both come from ownership that is unclear about who frees what, and when.
