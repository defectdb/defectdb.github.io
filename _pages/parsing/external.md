---
title: "External tool error"
author: Maxim Menshikov
layout: defect
permalink: /parsing/external
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: parsing
group:
   - parsing
---
External tool error

# Impact

This is an analyzer-internal diagnostic, not a defect in the analyzed program
itself. Visao drives an external tool (a compiler front-end, a preprocessor, a
build wrapper, or a language-specific parser binary) to obtain the data it needs.
The diagnostic is raised when that external tool exits with a non-zero status,
crashes, times out, or writes output that cannot be consumed.

The practical consequence is that the affected translation unit is **not
analyzed**. Real defects that live in that file are silently skipped, so the run
produces a false sense of safety. In a CI gate this typically means the file is
reported as "clean" only because it was never examined.

# Vulnerability potential

This diagnostic has no direct security relevance to the analyzed code: it
describes a failure of the analysis pipeline, not an exploitable condition in the
target program. The only indirect concern is **coverage loss** — a genuine
vulnerability in the skipped file can slip through unnoticed — which is why the
severity is kept at `Low` rather than `None`. There is no memory corruption,
injection or privilege issue in Visao itself implied by the message.

# Technical details

The external tool is invoked as a child process. Visao captures its exit code,
`stdout`, and `stderr`, and reads any artifact files it was expected to emit. The
diagnostic fires when one of the following happens:

## Non-zero exit
The tool returned a failure status. The most common causes are a missing include
path, an undefined macro, an unsupported language standard flag, or a header that
only exists in the project's real build environment. The compile database
(`compile_commands.json`) passed to the tool may be stale or reference paths that
do not exist on the analysis host.

## Crash or signal
The tool terminated on a signal (segfault, abort). This usually points to a bug
in the external tool or to an input that triggers it, and is outside Visao's
control.

## Timeout
The tool exceeded the configured time budget. Pathological inputs (deeply nested
templates, generated code) or a hung subprocess produce this.

## Unconsumable output
The process succeeded but emitted output in an unexpected format or version,
which the parsing stage could not deserialize.

# Catching the issue

Because this is a tool diagnostic, "catching" it means restoring a working
analysis environment rather than editing program logic.

## Reproduce the invocation
Re-run the exact command line Visao used (it is printed with the diagnostic) by
hand. The external tool's own `stderr` almost always states the underlying cause
directly.

## Fix the build context
Ensure the compile database is regenerated against the same toolchain, that all
include directories and generated headers are present, and that the language
standard / target flags match the project. Pin the external tool version so the
output format matches what Visao expects.

## Guard rails
Treat these diagnostics as build errors in CI rather than warnings, so coverage
gaps are never silently accepted. Raise the per-tool timeout for legitimately
large units.

# How to reproduce

Point the analyzer at a unit that references a header absent from the analysis
host. The external compiler front-end exits non-zero and Visao surfaces the
external tool error instead of analyzing the file. Observe that no other
diagnostics are reported for this unit.

```c
/* The build host does not provide this vendor header, but the real
   firmware build does. The external front-end aborts on the missing
   include before any analysis can run. */
#include <vendor/secret_soc_regs.h>

int main(void)
{
    return SOC_BOOT_MAGIC; /* macro defined only inside the missing header */
}
```
