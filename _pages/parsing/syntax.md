---
title: "Parsing failed"
author: Maxim Menshikov
layout: defect
permalink: /parsing/syntax
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
Parsing failed

# Impact

This is an analyzer-internal diagnostic. Visao could not build a syntax tree for
the source because the token stream did not conform to the grammar it expects.
The diagnostic does not describe a runtime fault in the program; it reports that
the file could not be turned into an AST.

The direct consequence is that the affected file (or the region after the failure
point) is **not analyzed**. Subsequent passes — type checking, IR lowering,
defect detection — never run on it, so the file is effectively excluded from the
report. As with any coverage gap, real defects in that file are not surfaced.

# Vulnerability potential

The diagnostic itself carries little security weight: a parse failure is a
front-end limitation, not an exploitable condition in the analyzed program. The
only meaningful risk is indirect — a file that fails to parse is silently skipped,
so a genuine vulnerability inside it goes undetected. That coverage concern is why
the severity is `Low` rather than `None`. The message implies no memory-safety or
injection issue inside Visao.

# Technical details

The parser consumes tokens from the lexer and applies the language grammar. A
failure is emitted when it reaches a state with no valid production for the
current token.

## Genuine syntax errors
Unbalanced braces or parentheses, a missing semicolon, a stray token, or a
keyword used in an invalid position. Such code would also be rejected by a normal
compiler.

## Dialect and extension gaps
Code that is valid for a specific compiler but uses an extension Visao's parser
does not model: GCC statement expressions, MSVC `__declspec` forms, attribute
syntax, or a newer language standard (e.g. C++20/23 constructs) the parser
predates. The code compiles in the real build but trips the analyzer's grammar.

## Preprocessor-dependent text
When the file is parsed without the correct macro definitions, unexpanded or
wrongly expanded macros can leave the token stream syntactically invalid even
though the post-preprocessing form is fine.

## Recovery limits
Even with error recovery, a failure early in a declaration can cascade, causing
the parser to abandon the rest of the construct.

# Catching the issue

This is a tool diagnostic; resolution means making the source parseable rather
than changing program behaviour.

## Confirm with a compiler
Compile the same file with the project's real compiler and flags. If the compiler
also errors, fix the syntax. If it compiles cleanly, the gap is in the analyzer's
grammar or in the flags/macros handed to it.

## Match the language mode
Pass the correct `-std=` / dialect and the same predefined macros the real build
uses, so dialect-specific or version-specific constructs are recognised.

## Report grammar gaps
When valid, standard code fails to parse, capture the minimal snippet and report
it so the parser can be extended. Treat parse failures as hard errors in CI to
avoid silent coverage holes.

# How to reproduce

Feed the parser a construct that is outside the grammar it models. Observe that
the analyzer reports a parsing failure and emits no further diagnostics for the
file.

```c
int main(void)
{
    int x = 0;

    /* Unterminated statement and unbalanced brace: the parser reaches a
       state with no valid production and gives up on the function body. */
    if (x > 0
        x = 1;

    return x;
/* missing closing brace for main() */
```
