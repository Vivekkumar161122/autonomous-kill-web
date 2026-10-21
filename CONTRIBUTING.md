# Contributing to Autonomous Kill-Web Architecture

Thank you for your interest in contributing to the **Automated Preemptive Suppression Architecture (Autonomous Kill-Web)** project! This document outlines our development guidelines, branching workflows, and pull request procedures.

---

## 1. Code of Conduct
By participating in this project, you agree to abide by the terms of our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 2. Development Setup

### Prerequisites
* Python 3.10+ (Python 3.12+ recommended)
* `pip` and `virtualenv`
* Git

### Local Setup
1. Fork and clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/automated_preemptive_suppression_architecture.git
   cd automated_preemptive_suppression_architecture
   ```
2. Set up the virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run the automated test suite:
   ```bash
   pytest tests/ -v
   ```
4. Start the local simulation console:
   ```bash
   ./run.sh
   ```

---

## 3. Branching Strategy
* `main`: Stable production branch. All commits must pass CI checks.
* `feature/<feature-name>`: New capabilities (e.g., `feature/genetic-optimizer`, `feature/acoustic-sensor`).
* `fix/<bug-name>`: Bug fixes and performance tuning.

---

## 4. Coding Standards
* **Python**: Follow PEP 8 guidelines. Type hints are mandatory on all public interfaces and Pydantic models.
* **Frontend**: Pure Vanilla HTML5/CSS3/JavaScript. Avoid heavy frontend frameworks to keep the simulation real-time, low-latency, and zero-dependency.
* **Tests**: All new features or algorithmic changes must be accompanied by corresponding unit tests under `tests/`.

---

## 5. Submitting a Pull Request
1. Ensure all tests pass: `pytest tests/`
2. Update documentation and inline docstrings where applicable.
3. Write clear, semantic commit messages (e.g., `feat(fusion): add Doppler noise filter`, `fix(optimizer): resolve boundary condition on range checks`).
4. Submit your PR using the repository's Pull Request template.
