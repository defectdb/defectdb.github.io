---
title: "Process.Start with string argument"
author: Maxim Menshikov
layout: defect
permalink: /csharp/process/start
arch:
   - native
vulnerability:
   - High
ddos:
   - Low
group_full: csharp.process
group:
   - csharp
   - process
---
Passing user-controlled text to Process.Start is a command-injection vector. Validate the file name or use the ProcessStartInfo overload with UseShellExecute=false

# Impact

`Process.Start` launches an external program. When the file name or arguments are built from user-controlled text, the call becomes a **command-injection** sink. Exactly what an attacker can do depends on the overload:

- `Process.Start(string fileName)` and the `ProcessStartInfo.FileName` with `UseShellExecute = true` route the string through the OS shell/`ShellExecute`. The shell interprets metacharacters, environment variables, and (on Windows) lets a bare document name launch its registered handler. Tainted input here can run arbitrary commands.
- Even with `UseShellExecute = false`, a single `Arguments` string is parsed by the target program (and on Windows split with `CommandLineToArgvW` rules), so unescaped quotes/spaces let an attacker smuggle extra arguments and change the program's behaviour.

The consequence ranges from running an unintended program, to argument injection that flips a flag (e.g. turning a read into a write), to full remote code execution.

# Vulnerability potential

This is a primary security defect (CWE-78 OS Command Injection, CWE-88 Argument Injection).

1. **Shell metacharacter injection.** With `UseShellExecute = true`, input like `file.txt & calc.exe` or `$(rm -rf ~)` is interpreted by the shell, running attacker-chosen commands with the privileges of the host process.
2. **Argument injection.** Even without a shell, concatenating user input into the `Arguments` string lets an attacker inject extra flags. A classic example is passing a value beginning with `-` to a tool, turning `app file` into `app --dangerous-option file`.
3. **PATH / search-order hijacking.** Starting a program by bare name (`"git"`) resolves through `PATH` and, on Windows, the current directory; an attacker who can drop a binary in a searched directory gets it executed.
4. **Privilege escalation.** If the host runs elevated (service, scheduled task), injected commands inherit that privilege.

To remediate: never pass untrusted text as a command line. Use `UseShellExecute = false`, set `FileName` to a fixed, validated absolute path, and supply each argument separately via `ProcessStartInfo.ArgumentList` (which escapes per-argument) instead of building one `Arguments` string.

# Technical details

## UseShellExecute
With `UseShellExecute = true` (the default for the simple `Process.Start(string)` overload on .NET Framework), the runtime calls the platform shell-execute API. The string is subject to shell parsing, file-association lookup, and verb handling — a much larger attack surface than a direct `CreateProcess`. On .NET Core/5+ the default is `false`, but code that explicitly enables it reopens the hole.

## Argument string vs ArgumentList
A Windows process receives one raw command line; the runtime builds it from `ProcessStartInfo.Arguments` verbatim, so the caller is responsible for quoting. `ArgumentList` (added in .NET Core 2.1+) takes a list and applies the correct Windows escaping rules per element, eliminating manual quoting bugs. On Unix, arguments are passed as a real `argv` array, so there is no shell involved at all when `UseShellExecute = false`.

## Resolution order
A non-rooted `FileName` is resolved against `PATH` (and the working directory on Windows). Always use an absolute, validated path to avoid binary-planting attacks.

# Catching the issue

## Static analysis
Security-focused analyzers flag tainted data flowing into `Process.Start`: the .NET `SecurityCodeScan` rules, SonarQube S4036 (PATH search) / command-injection rules, and CodeQL's `cs/command-line-injection` query all detect this. Roslyn's `CA3006` (process command injection) is part of the FxCop/security ruleset.

## Banned API
For libraries that should never spawn shells, add `System.Diagnostics.Process.Start` overloads taking a single string to a `BannedSymbols.txt` (BannedApiAnalyzers) and force callers onto a vetted wrapper.

## Code review
Require that every `Process.Start` uses `UseShellExecute = false`, a constant/whitelisted `FileName`, and `ArgumentList` for any dynamic values. Reject any string concatenation or interpolation that reaches `FileName` or `Arguments`.

# How to reproduce

Run with input `x & calc` (Windows) and observe that a second program launches. The safe version treats the whole value as one argument.

```csharp
using System.Diagnostics;

class Program
{
    // VULNERABLE: user text reaches the shell
    static void Unsafe(string userInput)
    {
        Process.Start(new ProcessStartInfo
        {
            FileName = "cmd.exe",
            Arguments = "/c type " + userInput, // "x & calc" injects a command
            UseShellExecute = true
        });
    }

    // SAFE: fixed program, per-argument escaping, no shell
    static void Safe(string userInput)
    {
        var psi = new ProcessStartInfo
        {
            FileName = @"C:\Windows\System32\find.exe",
            UseShellExecute = false
        };
        psi.ArgumentList.Add("/c");
        psi.ArgumentList.Add(userInput); // passed as a single opaque argument
        Process.Start(psi);
    }

    static void Main() => Unsafe("x & calc");
}
```

