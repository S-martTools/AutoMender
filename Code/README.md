# Code — AutoMender Core

---

This folder hosts the **core pipeline** for AutoMender: RAG prompt building, CoT planning, RL (PPO skeleton) with a composite reward, multi-tool detection with weighted voting, and validation (compile/symbolic/gas/structure).  
The **MoE-LoRA** model plugs in via a single hook in `core/registry.py`.

---

## Folder Layout

.
├── README.md
├── requirements.txt
├── config/
│   └── default.yaml
├── core/
│   ├── registry.py            # MoE-LoRA  generate_patch
│   ├── rag.py                 # RAG  Prompt 
│   ├── cot.py                 # CoT
│   ├── reward.py              # Score Reward Ω
│   ├── rl/
│   │   └── ppo.py             # PPO RL
│   ├── detectors/
│   │   ├── base.py            # Ouput
│   │   ├── smartfast.py       # ST/AS
│   │   ├── vulhunter.py       # ML
│   │   ├── symx.py           # SymX
│   │   ├── slither.py         # Slither CLI
│   │   ├── securify.py        # Securify CLI
│   │   ├── ilf.py             # Fuzzer
│   │   └── aggregator.py      # Detection_weights
│   └── validate/
│       ├── compile_check.py   # solc
│       ├── symexec_check.py   # Symbolic Check
│       └── gas_similarity.py  # Similarity
├── preprocess.py              # Preprocess
├── repair.py                  # Main: Detection→RAG/CoT→MoE-LoRA→Validation
├── validate.py                # Validation
└── exp/
    └── run_ablation.py        # ablation

---

## ✨ What’s inside

- **RAG** (`core/rag.py`) — lightweight retrieval + prompt assembly
- **CoT** (`core/cot.py`) — plan + patch extraction via `// PATCH BEGIN/END`
- **Detectors** (`core/detectors/*`) — adapters for tools + **weighted voting** (`aggregator.py`)
- **Validation** (`core/validate/*`) — compile, symbolic sanity (stub), gas/structure similarity
- **Reward** (`core/reward.py`) — composite score Ω
- **RL (PPO)** (`core/rl/ppo.py`) — minimal skeleton wired to the reward
- **Entries** — `preprocess.py`, `repair.py`, `validate.py`

> Adapters degrade gracefully: if a tool is missing, outputs are neutral so the pipeline still runs.

---

## ⚙️ Environment Setup

### 0) Prerequisites
- **Python** ≥ 3.10
- (Optional) **CUDA GPU** for CMoE-LoRA acceleration
- (Optional) **Docker** if you wrap detectors as containers

### 1) Create and activate a virtual environment

**venv (recommended)**
```bash
### Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

### Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
````

**Conda (alternative)**

```bash
conda create -n automender python=3.10 -y
conda activate automender
```

### 2) Install Python dependencies

```bash
pip install --upgrade pip
pip install -r Code/requirements.txt
```

### 3) Install Solidity compiler (`solc`)

You need a native `solc` for accurate compilation checks (note: `solcjs` is **not** a drop-in replacement).

**Ubuntu (snap)**

```bash
sudo snap install solc --classic
```

**macOS (Homebrew)**

```bash
brew update && brew install solidity
```

**Alternative (Docker)**

```bash
docker run --rm -v "$PWD":/src ethereum/solc:stable --help
```

Verify:

```bash
solc --version
```

### 4) Install detector toolchain

You can integrate real tools later; the stubs already run. For higher fidelity:

**Slither**

```bash
pip install slither-analyzer
slither --version
```

**Securify 2.0 / RSymX / ILF / VulHunter**

* Adapters are provided as **stubs**. Wire your local CLI or service inside:

  * `core/detectors/securify.py`
  * `core/detectors/rsymx.py`
  * `core/detectors/ilf.py`
  * `core/detectors/vulhunter.py`
* If you use Dockerized tools, call them via `subprocess` in the adapters.

### 5) Configure paths and weights

Edit `Code/config/default.yaml`:

```yaml
solc_path: "solc"         # set to an absolute path if needed
detectors:
  slither_cmd: "slither"
  securify_cmd: "securify"
  ilf_cmd: "ilf"
  rsymx_cmd: "rsymx"
  smartfast_cmd: "smartfast"
  vulhunter_cmd: "vulhunter"
weights_path: "../Detection_weights/default.yaml"

reward:
  w_bug_removed: 0.5
  w_no_new_bugs: 0.2
  w_compile_ok: 0.1
  w_symexec_ok: 0.1
  w_gas_struct: 0.1

gas_similarity:
  leven_threshold: 0.4
  max_gas_penalty: 0.1
```

Place your voting weights in `Detection_weights/default.yaml` (reported / not\_reported per bug type per tool).

Edit `Code/config/moe_lora.yaml`:

```yaml
model_name: "/path/to/base/model"   # HF id or local folder
device: "cuda"                      # or "cpu"
dtype: "bfloat16"                   # float32 | float16 | bfloat16

rank: 8
alpha: 32.0
dropout: 0.1
num_experts: 3
top_k: 1
target_modules: ["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]

weights_path: "/path/to/moelora_weights.pth"  # state-dict for injected layers (optional)

max_new_tokens: 2048
repetition_penalty: 1.2
zh: false
```

> The pipeline imports `generate_patch` from `moe_lora/cmoe_lora.py` via `core/registry.py`.
> In `repair.py` we call:
>
> ```python
> gen = get_patch_generator()
> raw_out = gen(prompt, experts=experts, config_path="Code/config/moe_lora.yaml")
> ```

---

## 🚀 Quickstart

1. **Preprocess**

```bash
python Code/preprocess.py \
  --src Wild_instances/demo.sol \
  --out /mnt/data/demo.json
```

2. **Repair** (runs detectors → RAG/CoT → CMoE-LoRA → write patch)

```bash
python Code/repair.py \
  --input /mnt/data/demo.json \
  --experts reentrancy,arith \
  --patched /mnt/data/demo_patched.sol \
  --weights Detection_weights/default.yaml \
  --config Code/config/default.yaml
```

3. **Validate** (pre vs post)

```bash
python Code/validate.py \
  --orig Wild_instances/demo.sol \
  --patched /mnt/data/demo_patched.sol \
  --weights Detection_weights/default.yaml \
  --report /mnt/data/report.json \
  --config Code/config/default.yaml
```

---

## How the pieces fit

* **Detectors** → each adapter returns `{tool, found: {BUGTYPE: 0/1}}`.
* **Weighted voting** (`aggregator.py`) → sums `reported / not_reported` weights from `Detection_weights/*.yaml`.
* **RAG/CoT** → `rag.build_prompt(...)` + `cot.plan(...)`, then generator receives the composed `prompt`.
* **Generator** → `moe_lora/cmoe_lora.py::generate_patch()` produces a patch **wrapped with**:

---

## 🧪 Detectors & Weighted Voting

* Adapters live in `core/detectors/`.
* `aggregator.py` reads YAML from `Detection_weights/` and sums **reported / not\_reported** weights per bug type.
* Start from your paper’s weights and calibrate to your environment.

---

## 🧮 Reward & RL

* `core/reward.py` computes Ω from:

  * bug status change (pre/post detection),
  * compile/symbolic sanity,
  * gas/structure similarity.
* `core/rl/ppo.py` demonstrates rollouts + reward; replace with your trainer when ready.

---

## ✅ Validation

* **Compile**: `compile_check.py` uses `solc` if available; permissive if missing.
* **Symbolic sanity**: `symexec_check.py` is a placeholder (returns 1.0) — swap in your checker.
* **Gas/structure**: `gas_similarity.py` uses normalized edit distance; tune thresholds in `config/default.yaml`.

---

## 🧰 Troubleshooting

* `slither not found`: install Slither or ensure it’s on `PATH`.
* `solc not found`: install as above or set `solc_path` to an absolute path.
* Patch not applied: the demo appends the patch for visibility; in production, apply structured diffs.
* Mixed Solidity versions: align `solc` version with the target contract(s).

---

## Running Ways

```bash
# Preprocess
python Code/preprocess.py --src Wild_instances/demo.sol --out /mnt/data/demo.json

# Repair
python Code/repair.py --input /mnt/data/demo.json \
  --experts reentrancy,arith \
  --patched /mnt/data/demo_patched.sol \
  --weights Detection_weights/default.yaml \
  --config Code/config/default.yaml

# Validate
python Code/validate.py --orig Wild_instances/demo.sol \
  --patched /mnt/data/demo_patched.sol \
  --weights Detection_weights/default.yaml \
  --report /mnt/data/report.json
```

---

## Tips & Troubleshooting

- **`solc not found`**: install Solidity or set an absolute `solc_path` in `config/default.yaml`.
- **CMoE-LoRA loads but outputs no markers**: the pipeline will auto-wrap a fallback patch, but please ensure your model returns the block between `// PATCH BEGIN` and `// PATCH END`.
- **Detector not installed**: adapters return neutral outputs; the pipeline still works.
- **CUDA OOM**: reduce `max_new_tokens`, switch `dtype` to `float16`, or use `device: cpu` for debugging.
- **Different LoRA key names**: if your `weights_path` uses custom keys, remap them before `load_state_dict(strict=False)`.