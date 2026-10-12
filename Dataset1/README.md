<div align="center">

<img src="../assets/automender-mark.svg" alt="AutoMender logo" width="76" />

# Dataset 1

### Curated Solidity Contracts for Controlled Repair Evaluation

[![Contracts](https://img.shields.io/badge/Solidity%20Files-156-363636?logo=solidity)](Dataset1_Test/)
[![Bug Families](https://img.shields.io/badge/Bug%20Families-24-8A2BE2)](../Bug_examples/README.md)
[![Purpose](https://img.shields.io/badge/Purpose-Evaluation-2ea44f)](#dataset-scope)

</div>

Dataset 1 is AutoMender's curated evaluation collection. The checked-in snapshot contains 156 Solidity files organized by vulnerability family, together with a `complex_contracts` group for multi-bug repair cases.

## 🧭 Quick Links

[📦 Contracts](Dataset1_Test/) · [🔍 Training Separation](#training-corpus-separation) · [🧩 Bug Taxonomy](../Bug_examples/README.md) · [⚖️ Detection Weights](../Detection_weights/README.md) · [🏠 Project Home](../README.md)

## 📦 Dataset Scope

The contracts are stored under [`Dataset1_Test/`](Dataset1_Test/). Its directories cover security defects and optimization issues such as reentrancy, arithmetic errors, unchecked calls, access control, transaction/block dependence, and gas-related code improvements.

```text
Dataset1/
├── Dataset1_Test/
│   ├── complex_contracts/             # Multi-bug contract cases
│   ├── integer-overflow/              # Arithmetic defects
│   ├── reentrancy/                    # Reentrancy variants
│   ├── unchecked_low_level_calls_and_send/
│   └── ...                            # Remaining supported bug families
└── README.md
```

## 🔍 Training-Corpus Separation

The data-separation audit compares all 156 Dataset1 contracts with both training sources. The statistics below refer to the cleaned semantic corpus used for training.

| Training source | Comparison | Observed overlap |
|---|---|---:|
| Cleaned semantic corpus (73,391 contracts) | Byte-exact whole contract | 0/156 |
| Cleaned semantic corpus (73,391 contracts) | Normalized-text whole contract | 0/156 |
| Cleaned semantic corpus (73,391 contracts) | Normalized-token whole contract | 0/156 |
| Defective-fixed corpus (4,465 pairs; 8,930 fragment sides) | Whole-fragment normalized text | 0/8,930 |
| Defective-fixed corpus (4,465 pairs; 8,930 fragment sides) | Whole-fragment normalized tokens | 0/8,930 |
| Defective-fixed corpus | Local normalized-token containment, ≥50 tokens | 0 fragments; 0/156 contracts |
| Defective-fixed corpus | Local normalized-token containment, ≥20 tokens | 1/8,930 fragments (0.011%); 1/156 contracts (0.64%) |
| Defective-fixed corpus | Local normalized-token containment, ≥10 tokens | 2/8,930 fragments (0.022%); 2/156 contracts (1.28%) |

The two short local matches are a 32-token `_memcpy` idiom and a 12-token common event declaration. They are partial reusable code patterns, not identical contracts or complete repair samples. No complete Dataset1 contract overlaps with either the cleaned semantic corpus or a labeled vulnerable/fixed fragment.

## 🛡️ Evaluation Integrity

Dataset 1 is evaluation-only. It must not be included in domain-adaptation, supervised fine-tuning, retrieval-index construction, or PPO training inputs. Before training, run the repository's contamination audit against all three evaluation datasets:

```bash
automender audit-data --output runs/data_audit.json
```

The paper profile requires zero byte-, normalized-text-, and normalized-token whole-contract overlap with the cleaned semantic corpus. Complete paired-training samples that match a complete test contract also cause a hard failure.

## ⚠️ Usage Notes

- Several contracts intentionally contain exploitable code and historical Solidity syntax.
- Compile each file with the version declared by its pragma or experiment manifest.
- A directory name is an evaluation grouping, not a guarantee that every detector will support every contained pattern.
- Do not deploy these contracts to a production network.

## 🔎 Recount the Snapshot

To verify the number of Solidity files in the current checkout:

```bash
find Dataset1/Dataset1_Test -type f -name '*.sol' | wc -l
```

---

<div align="center">

[AutoMender Home](../README.md) · [Engineering Guide](../Code/README.md)

</div>
