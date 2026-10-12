<div align="center">

<img src="../assets/automender-mark.svg" alt="AutoMender logo" width="76" />

# Security Incident Contracts

### Dataset 3 · Historical On-chain Vulnerability Cases

[![Contracts](https://img.shields.io/badge/Incident%20Contracts-29-B22222)](Dataset3/)
[![Metadata](https://img.shields.io/badge/Compiler%20Metadata-CSV-3776AB)](dataset3_solc_versions.csv)
[![Purpose](https://img.shields.io/badge/Purpose-Evaluation-2ea44f)](#dataset-scope)

</div>

Dataset 3 contains 29 Solidity contracts associated with publicly documented security incidents. It is used to evaluate whether AutoMender can reason about historically consequential defects under realistic contract structure and compiler constraints.

## 🧭 Quick Links

[📦 Contracts](Dataset3/) · [🔍 Training Separation](#training-corpus-separation) · [📊 Example Metadata](dataset3_examples.xlsx) · [⚙️ Compiler Versions](dataset3_solc_versions.csv) · [🧩 Bug Taxonomy](../Bug_examples/README.md) · [🏠 Project Home](../README.md)

## 📦 Dataset Scope

| Resource | Description |
|---|---|
| [`Dataset3/`](Dataset3/) | 29 incident-contract source files |
| [`dataset3_examples.xlsx`](dataset3_examples.xlsx) | Curated example metadata |
| [`dataset3_solc_versions.csv`](dataset3_solc_versions.csv) | Solidity compiler-version mapping |

Dataset 3 is evaluation-only and must remain outside all training and retrieval-index inputs. The contamination audit treats any whole-contract match against the semantic corpus or paired repair data as a hard failure.

## 🔍 Training-Corpus Separation

The data-separation audit compares all 29 Dataset3 contracts with the cleaned semantic corpus and all 8,930 sides of the 4,465 labeled defective-fixed pairs.

| Training source | Comparison | Observed overlap |
|---|---|---:|
| Cleaned semantic corpus (73,391 contracts) | Byte-exact whole contract | 0/29 |
| Cleaned semantic corpus (73,391 contracts) | Normalized-text whole contract | 0/29 |
| Cleaned semantic corpus (73,391 contracts) | Normalized-token whole contract | 0/29 |
| Defective-fixed corpus (4,465 pairs; 8,930 fragment sides) | Whole-fragment normalized text | 0/8,930 |
| Defective-fixed corpus (4,465 pairs; 8,930 fragment sides) | Whole-fragment normalized tokens | 0/8,930 |

The paired-data comparison tests complete fragment equality against complete Dataset3 contracts; it does not treat short shared Solidity idioms as duplicate samples.

## 🧪 Illustrative Repairs

The following compact diffs illustrate repairs discussed in the paper. They are explanatory excerpts rather than newly executed validation artifacts.

### 🕸️ SmartMesh (SMT)

The vulnerable addition can overflow and make the original balance check pass. The repair validates both the arithmetic result and the sender balance.

```diff
  mapping (address => uint256) balances;
  function transferProxy(uint256 _value, uint256 _feeSmt, ...) public ... {
-   if (balances[_from] < _feeSmt + _value) revert();
+   require(_feeSmt + _value >= _value && balances[_from] >= _feeSmt + _value);
    Transfer(_from, msg.sender, _feeSmt);
    ...
  }
```

### 💠 BeautyChain (BEC)

The vulnerable multiplication can overflow before the subsequent balance check. The repair uses the contract's existing SafeMath-style multiplication.

```diff
  mapping(address => uint256) balances;
  function batchTransfer(address[] _receivers, uint256 _value) ... {
-   uint256 amount = uint256(_receivers.length) * _value;
+   uint256 amount = uint256(_receivers.length).mul(_value);
    require(_value > 0 && balances[msg.sender] >= amount);
    balances[msg.sender] = balances[msg.sender].sub(amount);
    ...
  }
```

## 🔍 Interpretation

The SMT example combines an integer-overflow repair with replacement of a manual `revert` branch by a direct precondition. The BEC example shows why validating a value only after an unsafe multiplication is insufficient: the arithmetic operation itself must be protected. These examples motivate context-aware repair that accounts for nearby checks, available libraries, and minimal code change.

## ⚠️ Research and Safety Notice

- Files may contain intentionally vulnerable code and historical Solidity syntax.
- The source filename `not_supported` records a dataset/tooling constraint; it must not be interpreted as a clean-contract label.
- Reproduce results using the compiler version recorded in the CSV manifest and the full paper validation profile.
- Do not deploy these contracts or excerpts to a production network.

---

<div align="center">

[AutoMender Home](../README.md) · [Engineering Guide](../Code/README.md) · [Wild Instances](../Wild_instances/README.md)

</div>
