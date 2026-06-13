# Neuro-Symbolic Compliance

Neuro-Symbolic Compliance is an LLM-assisted legal reasoning pipeline that converts legal case narratives and statute text into structured compliance artifacts.

## How to Cite

If you use this project in research or a publication, please cite:

```bibtex
@inproceedings{hsia2025neuro,
  title={Neuro-Symbolic Compliance: Integrating LLMS and SMT Solvers for Automated Financial Legal Analysis},
  author={Hsia, Yung-Shen and Yu, Fang and Jiang, Jie-Hong Roland},
  booktitle={2025 2nd IEEE/ACM International Conference on AI-powered Software (AIware)},
  pages={01--10},
  year={2025},
  organization={IEEE}
}
```

The system combines:

- large language models for statute parsing, completion, and case mapping
- rule repair logic for malformed or inconsistent constraints
- Z3 for formal validation, satisfiability checking, and optimization
- structured outputs for inspection and downstream analysis

The goal is to move from unstructured legal text to machine-checkable constraints and facts that can be analyzed consistently.

## What This Project Does

The main entry point is [`main.py`](./main.py). It runs a multi-stage pipeline over rows in [`dataset/updated_processed_cases.csv`](./dataset/updated_processed_cases.csv).

For each case, the pipeline:

1. Extracts candidate legal constraints from the statute text.
2. Completes missing rule structure.
3. Validates and cleans the generated JSON.
4. Extracts variable specifications from the constraints.
5. Converts constraints into Z3 expressions and repairs syntax issues if needed.
6. Checks for logical consistency and repairs contradictions when possible.
7. Maps the case narrative into structured facts.
8. Validates the facts against Z3.
9. Checks whether the case produces a violation signal.
10. Optimizes the final model and exports an SMT2 version when possible.

The pipeline saves JSON, logs, a model dump, an SMT2 file, and an Excel summary under [`outputs/`](./outputs/).

## Repository Layout

- [`main.py`](./main.py) - pipeline orchestration and result export
- [`config.py`](./config.py) - environment-driven LLM configuration
- [`agents/`](./agents) - AutoGen agent definitions for parsing, mapping, repair, and related tasks
- [`core/`](./core) - repair pipeline logic and helper utilities
- [`find_optimize_result/`](./find_optimize_result) - JSON-to-Z3 conversion helpers
- [`dataset/`](./dataset) - input case data
- [`outputs/`](./outputs) - generated artifacts from pipeline runs

## Architecture

The project is organized as a staged agentic workflow:

- **Statute Parser** - extracts legal rules from statute text
- **Completion step** - expands and normalizes the extracted constraints
- **VarSpec Agent** - derives variable types and metadata from the constraints
- **Constraint Repair Agent** - fixes syntax or structure problems in constraints
- **Case Mapper** - converts case text into structured facts
- **Penalty / Repair logic** - assists with constraint repair and satisfiability correction
- **Z3 layer** - validates expressions, checks satisfiability, and produces a model

The orchestration layer in [`agents/orchestrator.py`](./agents/orchestrator.py) wires these agents together.

## Input Data

The pipeline expects a CSV file with at least two semantic fields:

- case text
- statute text

These columns can be named in either Chinese or English. Supported aliases include:

- case text: `法律案例`, `case`, `case_text`, `case_narrative`, `legal_case`, `legal_case_text`, `facts`
- statute text: `相關法條`, `statute`, `statute_text`, `relevant_statute`, `law_text`, `legal_provision`

The default dataset path is searched in this order:

- `dataset/updated_processed_cases.csv`
- `../updated_processed_cases.csv`
- `../data_preprocess/updated_processed_cases.csv`

If none of these files exist, the program raises an error at startup.

## Requirements

- Python 3.13
- [`uv`](https://docs.astral.sh/uv/)
- An OpenAI API key

Runtime dependencies include:

- `autogen`
- `openai`
- `pandas`
- `openpyxl`
- `z3-solver`
- `python-dotenv`

## Setup

Install dependencies:

```bash
uv sync
```

Create or update your `.env` file:

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Notes:

- `OPENAI_API_KEY` is required.
- `OPENAI_MODEL` is optional. If omitted, the project defaults to `gpt-4.1-mini`.
- Do not commit `.env` to version control.

## Run

Run the pipeline with:

```bash
uv run python main.py
```

### Current default behavior

At the bottom of [`main.py`](./main.py), the script currently contains:

```python
fail_list_path = [0]
main(failed_indices=fail_list_path)
```

That means the script processes only `case_0` by default.

To process the full dataset, either:

- change the list to the desired indices, or
- call `main()` without a filter

## Pipeline Stages

### 1. Statute parsing

The statute parser extracts candidate constraints from the statute text and returns a structured representation.

### 2. Completion

The parser is prompted again to fill in missing legal structure and improve coverage.

### 3. JSON validation

The output is cleaned and parsed into valid JSON. If this fails, the pipeline raises an error.

### 4. VarSpec extraction

The VarSpec agent identifies the variables referenced by the constraints and assigns types and metadata.

### 5. Constraint parseability

The constraints are converted into Z3 expressions. If parsing fails, the repair loop tries to fix the broken constraints.

### 6. Consistency check

The pipeline checks whether the constraints are logically consistent. If not, it attempts repair and may regenerate VarSpecs afterward.

### 7. Case mapping

The Case Mapper converts the case narrative into facts that can be evaluated by Z3.

### 8. Case-law hard check

The pipeline checks whether the case and constraints together indicate a violation. If the result is unexpected, the system attempts repair strategies to reach an UNSAT outcome.

### 9. Optimization

The final constraint set and facts are passed to the optimizer to generate a model.

### 10. SMT2 export

The project can export the final case to SMT-LIB format for inspection with external Z3 tooling.

## Outputs

Each case may generate the following files in [`outputs/`](./outputs/):

- `<case_id>.constraint_spec.json`
- `<case_id>.varspecs.json`
- `<case_id>.facts.json`
- `<case_id>.stats.json`
- `<case_id>.log`
- `<case_id>.smt2`
- `<case_id>.model.txt`

The full run also writes:

- `pipeline_statisticsv2.xlsx`

## Example Result Artifacts

If the pipeline completes successfully for a case, you will typically see:

- a cleaned constraint specification
- a variable specification file
- a facts file derived from the case narrative
- a text dump of the Z3 model
- an SMT2 file that can be replayed in Z3
- a statistics workbook containing summary metrics and checkpoint status

## Troubleshooting

### `openai` module is missing

Install dependencies again:

```bash
uv sync
```

### `openpyxl` module is missing

This project uses `pandas.ExcelWriter(..., engine="openpyxl")`, so the package must be installed through `uv sync`.

### `OPENAI_API_KEY` is not set

The app reads environment variables from `.env` via `python-dotenv`. If the key is missing, startup fails in [`config.py`](./config.py).

### No dataset found

Make sure the CSV file exists in one of the supported locations listed above and that the required columns are present.

### Unexpected SAT result

The pipeline is designed around violation-oriented cases. If the facts do not force a violation, the system may try repair logic or fail the case deliberately and still save partial outputs.

## Development Notes

- The codebase is currently optimized around a single dataset-driven batch workflow.
- `main.py` mixes orchestration, logging, repair, and export logic in one file. It works, but it is a good candidate for future refactoring.
- Several modules contain domain-specific prompts and repair heuristics, so behavior depends heavily on the quality of the LLM output.

## Reproducing a Clean Run

1. Install dependencies with `uv sync`.
2. Set `OPENAI_API_KEY` in `.env`.
3. Confirm the dataset exists at `dataset/updated_processed_cases.csv`.
4. Run `uv run python main.py`.
5. Inspect the generated files in `outputs/`.

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE).
# Neuro-Symbolic-Compliance
