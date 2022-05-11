---
title: Inconsistent locking
author: Maxim Menshikov
layout: defect
permalink: /threading/locking/inco
arch:
   - native
vulnerability:
   - High
ddos:
   - High
group_full: threading.locking
group:
   - threading
   - locking
---

The interthread locking is used inconsistently. For example, the same variable is used both in locked and unlocked contexts.

# Impact
The issue might lead to data corruption and coherence errors.

# Vulnerability potential

High potential.

# Technical details

Locking context might differ. But, realistically, if a field or a variable is used in locked context, it means that it might be used across threads, so atomic reads and assignments are important.
