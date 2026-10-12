<div align="center">

<img src="../assets/automender-mark.svg" alt="AutoMender logo" width="76" />

# Detection Weights

### Signed Evidence for the Six-Detector Ensemble

[![Bug Types](https://img.shields.io/badge/Bug%20Types-24-8A2BE2)](../Bug_examples/README.md)
[![Detectors](https://img.shields.io/badge/Detectors-6-3776AB)](#weight-matrix)
[![Voting](https://img.shields.io/badge/Voting-Signed-2ea44f)](#runtime-semantics)

</div>

AutoMender combines SmartFast, VulHunter, RSymX, Slither, Securify 2.0, and ILF using bug-specific evidence weights. A reported finding contributes positive evidence; a successful, supported, but unreported check contributes negative evidence. A tool that is unsupported, unavailable, timed out, or failed contributes no vote.

## 🧭 Quick Links

[⚖️ Weight Matrix](#weight-matrix) · [🧮 Runtime Semantics](#runtime-semantics) · [🧠 Assignment Rationale](#weight-assignment-rationale) · [⚙️ Executable Defaults](default.yaml) · [🏠 Project Home](../README.md)

## ⚖️ Weight Matrix

|   ID | Bug  | SmartFast N | SmartFast P | VulHunter N | VulHunter P | SymX N | SymX P | Slither N | Slither P | Securify2.0 N | Securify2.0 P | ILF N | ILF P |
| ---: | :--: | ----------: | ----------: | ----------: | ----------: | ------: | ------: | --------: | --------: | ------------: | ------------: | ----: | ----: |
|    1 |  RE  |           2 |           2 |           2 |           2 |       1 |       3 |         1 |         1 |             1 |             1 |     - |     - |
|    2 |  SU  |           3 |           2 |           2 |           2 |       1 |       3 |         2 |         1 |             1 |             1 |     1 |     3 |
|    3 |  AS  |           3 |           2 |           2 |           2 |       1 |       3 |         2 |         1 |             - |             - |     1 |     3 |
|    4 | TOD  |           - |           - |           2 |           2 |       1 |       3 |         - |         - |             1 |             1 |     - |     - |
|    5 | REN  |           2 |           2 |           - |           - |       - |       - |         1 |         1 |             1 |             1 |     - |     - |
|    6 |  IO  |           2 |           2 |           2 |           2 |       1 |       3 |         - |         - |             - |             - |     - |     - |
|    7 | UCL  |           2 |           2 |           2 |           2 |       1 |       3 |         2 |         1 |             1 |             1 |     1 |     3 |
|    8 | UCS  |           2 |           2 |           2 |           2 |       1 |       3 |         2 |         1 |             1 |             1 |     - |     - |
|   9 |  TO  |           3 |           2 |           2 |           2 |       1 |       3 |         2 |         2 |             1 |             1 |     - |     - |
|   10 | REE  |           2 |           2 |           - |           - |       - |       - |         1 |         1 |             - |             - |     - |     - |
|   11 |  TS  |           3 |           2 |           2 |           2 |       1 |       3 |         2 |         1 |             2 |             1 |     1 |     2 |
|   12 |  BP  |           3 |           2 |           2 |           2 |       1 |       3 |         - |         - |             - |             - |     1 |     2 |
|   13 |  ST  |           3 |           3 |           2 |           2 |       1 |       2 |         - |         - |             - |             - |     - |     - |
|   14 | CNE  |           2 |           2 |           - |           - |       - |       - |         - |         - |             - |             - |     - |     - |
|   15 |  RR  |           3 |           3 |           - |           - |       - |       - |         - |         - |             - |             - |     - |     - |
|   16 | UUS  |           3 |           3 |           2 |           2 |       - |       - |         2 |         2 |             1 |             1 |     - |     - |
|   17 | EGL  |           3 |           3 |           - |           - |       - |       - |         - |         - |             - |             - |     - |     - |
|   18 | COL  |           3 |           3 |           2 |           2 |       - |       - |         2 |         2 |             - |             - |     - |     - |
|   19 | RDS  |           3 |           3 |           - |           - |       - |       - |         2 |         2 |             - |             - |     - |     - |
|   20 |  BE  |           2 |           3 |           2 |           2 |       1 |       2 |         2 |         2 |             - |             - |     - |     - |
|   21 | AIB  |           3 |           3 |           2 |           2 |       - |       - |         - |         - |             - |             - |     - |     - |
|   22 |  CS  |           3 |           3 |           - |           - |       - |       - |         2 |         2 |             1 |             1 |     - |     - |
|   23 | RTS  |           3 |           3 |           - |           - |       - |       - |         2 |         2 |             - |             - |     - |     - |
|   24 |  EF  |           3 |           3 |           2 |           2 |       - |       - |         2 |         2 |             1 |             1 |     - |     - |

`P` is the positive confidence magnitude when a detector reports the bug. `N` is the negative confidence magnitude when that detector successfully runs, supports the bug type, and does not report it. A dash means the detector is not part of the voting set for that bug type.

## 🧮 Runtime Semantics

For bug type `b`, the aggregate detector score is:

```text
score(b) = Σ reported_weight(tool, b) - Σ not_reported_weight(tool, b)
```

The second sum includes only tools whose run status is `success` and whose adapter explicitly declares support for `b`.

| Detector outcome | Vote |
|---|---:|
| Supported and reported | `+P` |
| Supported, successful, and not reported | `-N` |
| Unsupported bug type | `0` |
| Unavailable executable/model | `0` |
| Timeout or execution error | `0` |
| Missing or malformed output | `0` |

This distinction prevents an absent or failed tool from being interpreted as evidence that a vulnerability is not present.

## 🧠 Weight Assignment Rationale

1. **Source and pattern analyzers — SmartFast, Slither, and Securify 2.0.** SmartFast operates over source-level semantics and is therefore assigned stronger confidence for several optimization findings. Some patterns, such as code with no effects (CNE), may disappear during compilation, which motivates combining source and bytecode analysis. For suicidal (SU) and arbitrary-send (AS) findings, a successful whole-source analysis also provides comparatively strong negative evidence.

2. **Symbolic execution and fuzzing — RSymX and ILF.** Runtime-state exploration and concrete triggering inputs can provide strong positive evidence. Their path coverage is incomplete, however, so a missed report is intentionally weak negative evidence. ILF is further downweighted for timestamp (TS) and block-parameter (BP) findings.

3. **Learning-based analysis — VulHunter.** VulHunter analyzes execution-path representations. The matrix uses balanced confidence magnitudes while retaining conservative treatment of possible model bias.

## ⚙️ Executable Configuration

[`default.yaml`](default.yaml) defines the detector/bug support matrix consumed by the implementation. Its current `reported: 1.0` and `not_reported: -1.0` values are explicitly documented as **equal-magnitude implementation defaults**; the detailed table above records the manuscript's confidence design. Experimental reports must record the exact YAML fingerprint in the run manifest so the two settings cannot be conflated.

## 🔗 Bug Identifiers

The 24 IDs and their seven expert categories are defined in the [bug knowledge base](../Bug_examples/README.md). Adapter-specific detector names are normalized to these IDs before voting.

---

<div align="center">

[AutoMender Home](../README.md) · [Engineering Guide](../Code/README.md) · [Bug Knowledge Base](../Bug_examples/README.md)

</div>
