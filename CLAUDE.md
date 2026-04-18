# Trend Bridge

Python monolith. Backend only (frontend may come later in `frontend/`).

## Structure

- `src/trend_bridge/` — application code
- `tests/` — pytest tests
- `.worktrees/` — git worktrees for isolated feature work

## Setup

```bash
./init.sh
```

## Conventions

- Imports: `from trend_bridge import ...` (editable install via `pip install -e .`)
- Deps: `requirements.txt`
- Tests: `pytest`
- Worktrees: use `.worktrees/` directory
