# RestAlchemy Agent Guide

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```text
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## Project Overview

RESTAlchemy is a Python toolkit for building HTTP REST APIs on top of a flexible data model and storage abstraction.

## Architecture

### Directory Structure

```text
restalchemy/
├── api/           # API controllers and endpoints
├── dm/            # Data models (domain models)
├── openapi/       # OpenAPI specification utilities
└── storage/       # Storage implementations (SQL-based)
```

### Key Components

- **API Layer** (`restalchemy/api/`): Handles HTTP requests and responses
- **Data Models** (`restalchemy/dm/`): Domain models and business logic
- **OpenAPI** (`restalchemy/openapi/`): API documentation and specification
- **Storage** (`restalchemy/storage/`): Database persistence layer using SQLAlchemy

## Build & Dependencies

- **Build System**: `pyproject.toml` (PEP 517/518 compliant)
- **Python Version**: Configured in `pyproject.toml`
- **Dependencies**: Listed in `pyproject.toml` under `[project.dependencies]`

## Testing

- **Test Framework**: pytest (configured in `pyproject.toml`)
- **Test Location**: `tests/` directory
- **Configuration**: `tox.ini` for test environment management

## Development Setup

1. Install dependencies: `pip install -e .`
2. Run tests: `pytest` or `tox`
3. Start services: `docker-compose up`

## Code Style and Naming Conventions

### Style Guidelines

- **Indentation**: 4 spaces (Python standard)
- **Line length**: 88 characters (Ruff default)
- **Imports**: Grouped and sorted via Ruff (I rule)
- **Type hints**: Required for all function signatures

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `BaseResourceController`)
- **Functions/variables**: `snake_case` (e.g., `build_filter`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `PACKAGE_NAME`)
- **Private members**: Leading underscore (e.g., `_internal_method`)
- **Comments for code**: write in English

### Testing Requirements

- **Unit tests**: Located in `restalchemy/tests/unit/`
- **Functional tests**: Located in `restalchemy/tests/functional/`
- **Test naming**: `test_<method_name>_<scenario>`
- **Coverage**: Measured via `coverage.py`, HTML report in `cover/`

## VCS Recommendations

### Commit Message Format

```text
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`  
**Scopes**: `cli`, `builder`, `repo`, `packer`, `tests`

**Example:**

```text
feat(repo): add HTTP server proxy driver

- Implement SimplePythonRepoDriver for file serving
- Add port configuration and error handling
- Include unit tests for driver lifecycle

Closes #123
```

### Pull Request Requirements

- **Title**: Use imperative, present tense: "Add feature", not "Added feature"
- **Description**: Clear summary of changes

## Important Files

- `pyproject.toml` - Project configuration and dependencies
- `README.rst` - Project documentation
- `docker-compose.yml` - Container orchestration
- `tox.ini` - Test environment configuration
