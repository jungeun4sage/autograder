# 🧠 AutoGrader — Automated Jupyter Notebook Grading Framework

AutoGrader is a modular pipeline for **automatic grading of Jupyter notebooks**, designed for educational and research purposes.  
It performs:

- Label-based grading (required / optional cells)
- Execution and output comparison
- Optional code similarity analysis
- Structured report and log generation

---

## 📁 Project Structure

```
autograder/
├─ README.md
├─ pyproject.toml
└─ src/
   ├─ AutoGrader_Module.ipynb
   └─ autograder/
      ├─ policy.py
      ├─ io_utils.py
      ├─ nb_utils.py
      ├─ label_tagging.py
      ├─ report.py
      ├─ similarity.py
      ├─ logging.py
      └─ configs/
         ├─ base.toml
         ├─ sessions.toml
         └─ logging.toml
```

---

## 🚀 Quick Start

### A) Google Colab (Development)
1. Open `src/AutoGrader_Module.ipynb`
2. Run **Step 0** – Google Drive mount and dependency install
3. Execute Steps **1–8** in order
4. Outputs are saved in:
   - `/outputs/`
   - `/executed/<RUN_TS>/`

### B) Local Environment (VS Code or CLI)
```bash
python -m venv .venv
source .venv/Scripts/activate    # (Windows)
pip install -e .
code src/AutoGrader_Module.ipynb
```

---

## ⚙️ Configuration

Session configuration is in:
```
src/autograder/configs/sessions.toml
```

Example:
```python
session = load_config("autograder/configs/sessions.toml", 9, "DEV")
# session = load_config("autograder/configs/sessions.toml", 9, "PROD")
```

Important paths:
| Variable | Description |
|-----------|-------------|
| TEMPLATE_PATH | Instructor template notebook |
| ANSWER_PATH | Correct answer notebook |
| SUBMIT_DIR | Student submission directory |
| OUT_DIR | Root output directory |
| EXEC_DIR | Executed result folder (timestamped) |

---

## 🧩 Grading Steps Overview

| Step | Description |
|------|--------------|
| 0 | (Optional) Colab setup |
| 1 | Import libraries & initialize |
| 2 | Tag template (required/optional) |
| 3 | Read tagged template |
| 4 | Load previous results & set thresholds |
| 5 | Grade submissions |
| 6 | Compute code similarity (optional) |
| 7 | Save CSV outputs |
| 8 | Log and print summary |

---

## 🔍 Similarity Check (Optional)

Toggle in notebook:
```python
ENABLE_SIMILARITY_CHECK = True  # or False
```

Function:
```python
from autograder.similarity import compute_similarity_pairs
pairs, df_sim = compute_similarity_pairs(fps, sid2file, sid2path, sid2name, sim_func=_sim, threshold=0.99)
```

⚠️ **Note:** Step 6 is O(n²) and may take time for large classes.

---

## 📊 Output Files

| File | Description |
|------|--------------|
| summary_static_with_name_<RUN_TS>.csv | Main grading summary |
| similar_pairs_<RUN_TS>.csv | Similarity report (optional) |
| new_today_<RUN_TS>.csv | Today’s submissions |
| *_latest.csv | Latest snapshots |
| autograde_run.log | Execution log summary |

---

## 🧱 Developer Notes

- Use `pathlib.Path` for all file operations.
- All timestamps use **KST (UTC+9)**.
- Configurable penalties (in `policy.py`):
  ```python
  BASE_SCORE = 100
  PENALTY_REQUIRED_MISS = 1.0
  PENALTY_REQUIRED_MISMATCH = 0.5
  PENALTY_OPTIONAL_MISS = 0.2
  ```

---

## 🧹 .gitignore Template

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/

# Notebooks
.ipynb_checkpoints/

# System
.DS_Store
Thumbs.db

# Outputs
outputs/**
executed/**
autograde_run.log
*.csv

# Virtual env
.venv/
.env
```

---

## 🤝 Credits

Developed by **Jungeun 4 Sage**  
Designed for reproducible, transparent, and efficient notebook grading.

---

## 🧩 License

MIT License © 2025 Jungeun 4 Sage
