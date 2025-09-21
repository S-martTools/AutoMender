# Detection Weights

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

> N refers to the bug was not reported, and P indicates the tool detect the bug.

## Weight Assignment Guidelines

1. **Pattern-matching (SmartFast & Slither & Securify2.0).**
    SmartFast matches against **source-level semantics**, so it is accurate for many **optimization-severity** issues. For example, the **ST** bug can be directly identified by matching `send` operations in the source. Therefore, SmartFast receives **higher confidence (weights)** for **bugs #13–#24**.In addition, for **SU** and **AS**, because SmartFast scans the entire source code, *not detecting* SU/AS strongly suggests they are absent; we thus set the **“not reported” weight to 3** for these two.Note that some problems exist **only at the source level** (e.g., **CNE** is filtered out by the compiler at build time). Such issues can **only** be detected by SmartFast—this is why we combine **bytecode-level** detectors with **source-code** analyzers.
2. **Symbolic execution (SymX) & fuzzing (ILF).**
    SymX and ILF generally achieve **higher precision** (thus **higher weights**) because they observe **runtime states** and can produce **concrete inputs** that trigger vulnerabilities. However, ILF has **incomplete detection logic** for some issues, which leads to **false positives**, so we **downweight** ILF for **TS** and **BP**. The biggest challenge for both approaches is **code coverage**: a missed finding may simply mean the vulnerable path wasn’t explored. To prevent such misses from skewing results, **our system (AutoMender)** adopts a **conservative scheme** and sets the **“not reported” weight to 1** for these tools.
3. **Machine learning (VulHunter).**
    VulHunter extracts **execution paths** as instances, which generally makes it **more precise** than tools like **Slither** and **Securify 2.0**. That said, potential **model bias** during training remains, so we set **both “not reported” and “reported” weights to 2** for VulHunter.