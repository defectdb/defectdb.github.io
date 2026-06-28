---
title: "Files"
author: Maxim Menshikov
layout: defect
permalink: /file
---

Defects in how programs handle files: the mismatches between what the code
assumes about a file's state and what the operating system actually permits at
the moment of the call. A file handle carries an implicit lifecycle — opened,
read, written, closed — and most failures here come from acting out of step
with it.

The entries group by the operation at fault. Reads and writes that move zero
bytes betray confused length or buffer logic and accomplish nothing while
masking the real intent; and state errors — using a handle that was never
opened, or closing one twice — corrupt the descriptor's lifecycle and lead to
failed I/O, undefined behaviour, or use of a stale or recycled descriptor.

