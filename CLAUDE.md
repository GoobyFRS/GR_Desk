# Code Standards & Style Guide

## Language Preference
- **Primary language**: Python 3 (use when possible)
- **Compliance**: PEP8 compliant

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Variables | `snake_case` | `user_count`, `total_items` |
| Constants | `UPPERCASE` | `MAX_RETRIES`, `API_BASE_URL` |
| Functions | `snake_case` | `get_user_data()`, `calculate_total()` |
| Classes | `PascalCase` | `UsercodeManager`, `DataProcessor` |
| Private/Internal | `_leading_underscore` | `_internal_helper()`, `_cache` |
| Ignored variables | `_` prefix | `for _ in range(10)`, `x, _ = get_pair()` |
| Module constants | `SCREAMING_SNAKE_CASE` | `DEFAULT_TIMEOUT = 30` |

## Code Structure

### Nesting
- **Maximum nesting depth**: 4 levels
- Use early returns, guard clauses, and extraction to reduce nesting
- Prefer flat over nested

```python
# Bad - too nested
def process(data):
    if data:
        if data.is_valid:
            if data.has_items:
                for item in data.items:
                    if item.active:
                        # deeply nested logic

# Good - use early returns
def process(data):
    if not data or not data.is_valid:
        return None
    if not data.has_items:
        return []
    return [item for item in data.items if item.active]
```

### Single Responsibility Principle

Every function and class should do **one thing well**. If you can't describe what it does in a single sentence without using "and", split it.

**Functions:**

```python
# Bad - does multiple things
def process_user(user_data: dict) -> None:
    # Validates, transforms, saves, AND sends email
    if not user_data.get("email"):
        raise ValueError("Missing email")
    user = User(**user_data)
    db.save(user)
    send_welcome_email(user.email)

# Good - each function has one job
def validate_user_data(user_data: dict) -> None:
    if not user_data.get("email"):
        raise ValueError("Missing email")

def create_user(user_data: dict) -> User:
    return User(**user_data)

def register_user(user_data: dict) -> User:
    validate_user_data(user_data)
    user = create_user(user_data)
    db.save(user)
    send_welcome_email(user.email)
    return user
```

**Classes:**

```python
# Bad - class does too much (God object)
class UserManager:
    def validate_user(self): ...
    def save_to_database(self): ...
    def send_email(self): ...
    def generate_report(self): ...
    def export_to_csv(self): ...

# Good - separate concerns
class UserValidator:
    def validate(self, user_data: dict) -> ValidationResult: ...

class UserRepository:
    def save(self, user: User) -> None: ...
    def find_by_id(self, user_id: int) -> User | None: ...

class UserNotifier:
    def send_welcome_email(self, user: User) -> None: ...
```

**How to tell if you're violating SRP:**

- Function name contains "and" or "or"
- Function has multiple reasons to change
- Hard to write a concise docstring
- Unit tests require complex setup
- You're passing unused parameters to satisfy different code paths

### Function Guidelines

- Keep functions under ~50 lines when practical
- Use descriptive names that indicate purpose
- Prefer pure functions where possible

### Line Length

- Maximum **88 characters** (black formatter default)
- Break long lines at logical points

## Type Hints (Strict Mode)

Type hints are **mandatory**, not optional. All code must be fully typed and pass strict type checking.

### Why Strict Typing?

- **IDE intelligence**: Enables autocompletion, refactoring, and jump-to-definition
- **Catch bugs early**: Static analyzers find type mismatches before runtime
- **Living documentation**: Types describe expected inputs/outputs without prose
- **Safer refactoring**: Type checkers catch breakages across the codebase
- **Better code review**: Reviewers immediately see data flow and contracts

### Requirements

- **All function parameters** must have type annotations
- **All return types** must be declared (including `-> None`)
- **Class attributes** must be annotated
- **Module-level variables** must be annotated when not immediately obvious
- **No `Any` type** unless absolutely unavoidable (requires justification comment)

### Strict Typing Rules

```python
# Bad - missing types
def fetch_user(user_id, include_metadata=False):
    ...

# Bad - implicit None return
def process_item(item: Item):
    print(item.name)

# Bad - using Any without justification
def handle_data(data: Any) -> Any:
    ...

# Good - fully typed
def fetch_user(user_id: int, include_metadata: bool = False) -> User | None:
    """Fetch user by ID."""
    ...

# Good - explicit None return
def process_item(item: Item) -> None:
    print(item.name)

# Acceptable - Any with justification
def handle_external_api_response(
    data: Any  # External API returns untyped JSON; validated below
) -> ProcessedData:
    validated = DataSchema.model_validate(data)
    return ProcessedData.from_schema(validated)
```

### Collection Types

Always use specific collection types, never bare `list`, `dict`, or `set`:

```python
# Bad - untyped collections
def get_users() -> list:
    ...

def get_config() -> dict:
    ...

# Good - parameterized collections
def get_users() -> list[User]:
    ...

def get_config() -> dict[str, int | str | bool]:
    ...

# Better - use TypedDict for structured dicts
from typing import TypedDict

class ConfigDict(TypedDict):
    host: str
    port: int
    debug: bool

def get_config() -> ConfigDict:
    ...
```

### Type Aliases for Complex Types

Create type aliases when types become complex:

```python
from typing import TypeAlias

# Define aliases for readability
UserId: TypeAlias = int
JsonDict: TypeAlias = dict[str, "JsonValue"]
JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | JsonDict

Callback: TypeAlias = Callable[[int, str], bool]
ResultOrError: TypeAlias = tuple[Result, None] | tuple[None, Error]
```

### Protocols Over ABCs

Prefer `Protocol` for structural typing (duck typing with type safety):

```python
from typing import Protocol

# Good - structural typing
class Readable(Protocol):
    def read(self, n: int = -1) -> bytes: ...

def process_stream(source: Readable) -> bytes:
    return source.read()

# Works with any object that has read() method
process_stream(open("file.txt", "rb"))
process_stream(io.BytesIO(b"data"))
```

### Configuration

```toml
# pyproject.toml - enforce strict typing
[tool.mypy]
strict = true
disallow_any_explicit = true
disallow_any_generics = true
disallow_untyped_calls = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
warn_return_any = true
warn_unused_ignores = true
```

## Imports

Order imports in groups, separated by blank lines:

1. Standard library
2. Third-party packages
3. Local/project imports

```python
import os
import sys
from pathlib import Path

import requests
from pydantic import BaseModel

from myproject.utils import helpers
from myproject.models import User
```

- Prefer absolute imports over relative
- Avoid wildcard imports (`from module import *`)

## Documentation

### Docstrings

- Use **Google style** docstrings
- Required for public functions, classes, and modules
- Include: summary, args, returns, raises (when applicable)

```python
def calculate_discount(price: float, percentage: float) -> float:
    """Calculate discounted price.

    Args:
        price: Original price in dollars.
        percentage: Discount percentage (0-100).

    Returns:
        The discounted price.

    Raises:
        ValueError: If percentage is not between 0 and 100.
    """
    if not 0 <= percentage <= 100:
        raise ValueError("Percentage must be between 0 and 100")
    return price * (1 - percentage / 100)
```

### Comments

- Explain **why**, not **what**
- Don't add comments for self-explanatory code
- Use TODO format: `# TODO(username): description`

## Error Handling

- Use **specific exceptions** over bare `except:`
- Create custom exceptions for domain-specific errors
- Fail fast with clear error messages

```python
# Bad
try:
    result = risky_operation()
except:
    pass

# Good
try:
    result = risky_operation()
except ConnectionError as e:
    logger.error(f"Network failure: {e}")
    raise
except ValueError as e:
    return default_value
```

## Code Quality

### Avoid

- Global mutable state
- Magic numbers (use named constants)
- Deep inheritance hierarchies (prefer composition)
- Premature optimization
- Dead code (delete it, don't comment it out)

### Prefer

- List/dict/set comprehensions over manual loops (when readable)
- Context managers (`with`) for resource management
- `pathlib.Path` over `os.path`
- f-strings over `.format()` or `%` formatting
- Explicit over implicit

## Safety-Critical Code Principles (Power of 10 - Python Adaptation)

These principles are adapted from NASA/JPL's "Power of 10" rules for safety-critical C code. They ensure code is analyzable, predictable, and verifiable.

### 1. Simple Control Flow

- **No recursion** in production code (direct or indirect)
- Avoid complex control flow that's hard to trace
- Use iteration instead of recursion; if recursion is unavoidable, add explicit depth limits

```python
# Bad - unbounded recursion
def traverse(node):
    if node is None:
        return
    process(node)
    traverse(node.left)
    traverse(node.right)

# Good - iterative with explicit stack
def traverse(node):
    stack = [node]
    while stack:
        current = stack.pop()
        if current is None:
            continue
        process(current)
        stack.append(current.right)
        stack.append(current.left)

# Acceptable - recursion with depth limit for non-critical code
MAX_RECURSION_DEPTH = 100

def traverse(node, depth: int = 0):
    if depth > MAX_RECURSION_DEPTH:
        raise RecursionError("Maximum traversal depth exceeded")
    if node is None:
        return
    process(node)
    traverse(node.left, depth + 1)
    traverse(node.right, depth + 1)
```

### 2. Fixed Loop Bounds

- All loops must have a **deterministic, verifiable upper bound**
- Avoid `while True` without clear, guaranteed exit conditions
- Use `for` loops with explicit ranges when possible

```python
# Bad - unbounded loop
while True:
    data = fetch_next()
    if not data:
        break
    process(data)

# Good - explicit bounds
MAX_ITERATIONS = 10_000

for _ in range(MAX_ITERATIONS):
    data = fetch_next()
    if not data:
        break
    process(data)
else:
    raise RuntimeError("Loop did not terminate within expected iterations")
```

### 3. Bounded Data Structures

- **Pre-allocate** collections where size is known
- Set **explicit size limits** on dynamic collections
- Avoid unbounded growth in queues, caches, and buffers

```python
from collections import deque

# Bad - unbounded growth
cache = {}
def add_to_cache(key, value):
    cache[key] = value  # Can grow forever

# Good - bounded with maxlen
cache = deque(maxlen=1000)

# Good - explicit limit with LRU
from functools import lru_cache

@lru_cache(maxsize=1000)
def expensive_computation(x: int) -> int:
    return x ** 2
```

### 4. Short Functions

- **Maximum 60 lines** per function (fits on one screen/page)
- Single responsibility - if you can't describe it in one sentence, split it
- Extract helpers for complex logic

### 5. High Assertion Density

- Use **at least two assertions** per non-trivial function
- Assert preconditions at function entry
- Assert postconditions before return
- Assert invariants in loops

```python
def calculate_average(values: list[float]) -> float:
    """Calculate the arithmetic mean of a list of values."""
    # Precondition assertions
    assert values is not None, "values cannot be None"
    assert len(values) > 0, "values cannot be empty"
    assert all(isinstance(v, (int, float)) for v in values), "all values must be numeric"

    total = sum(values)
    count = len(values)
    result = total / count

    # Postcondition assertions
    assert isinstance(result, float), "result must be a float"
    assert min(values) <= result <= max(values), "average must be within value range"

    return result
```

### 6. Minimal Variable Scope

- Declare variables **as close to first use** as possible
- Avoid module-level mutable state
- Use local variables over instance variables when possible
- Delete references to large objects when no longer needed

```python
# Bad - variable declared far from use
def process_data(items):
    result = []  # Declared here...

    # ... 50 lines of other code ...

    for item in items:  # ... used here
        result.append(transform(item))
    return result

# Good - variable declared at point of use
def process_data(items):
    # ... other code ...

    result = [transform(item) for item in items]
    return result
```

### 7. Check All Return Values

- **Never ignore return values** from functions that can fail
- Handle `None` explicitly - don't let it propagate silently
- Use type hints to make return types explicit

```python
# Bad - ignoring potential None
def get_user_name(user_id: int) -> str:
    user = database.get_user(user_id)  # Could return None
    return user.name  # AttributeError if None

# Good - explicit handling
def get_user_name(user_id: int) -> str | None:
    user = database.get_user(user_id)
    if user is None:
        logger.warning(f"User not found: {user_id}")
        return None
    return user.name

# Better - fail fast with clear error
def get_user_name(user_id: int) -> str:
    user = database.get_user(user_id)
    if user is None:
        raise ValueError(f"User not found: {user_id}")
    return user.name
```

### 8. Limit Metaprogramming

- **No `exec()` or `eval()`** - ever
- Limit decorator nesting to **2 levels maximum**
- Avoid `__getattr__` magic unless absolutely necessary
- No dynamic class generation in production code

```python
# Bad - dynamic code execution
def run_user_code(code_string: str):
    exec(code_string)  # Security nightmare, unanalyzable

# Bad - excessive decorator stacking
@decorator_a
@decorator_b
@decorator_c
@decorator_d  # Too many layers
def my_function():
    pass

# Good - limited, clear decorators
@lru_cache(maxsize=100)
@log_execution_time
def my_function():
    pass
```

### 9. Limit Data Structure Nesting

- Maximum **3 levels** of nested data structures
- Avoid deeply nested dicts/lists - use dataclasses or named tuples
- If you need `data["a"]["b"]["c"]["d"]`, refactor

```python
# Bad - deeply nested
config = {
    "server": {
        "database": {
            "connection": {
                "pool": {
                    "size": 10  # data["server"]["database"]["connection"]["pool"]["size"]
                }
            }
        }
    }
}

# Good - flat with dataclasses
from dataclasses import dataclass

@dataclass
class PoolConfig:
    size: int = 10

@dataclass
class DatabaseConfig:
    pool: PoolConfig

@dataclass
class ServerConfig:
    database: DatabaseConfig

config = ServerConfig(database=DatabaseConfig(pool=PoolConfig(size=10)))
print(config.database.pool.size)  # Clear, type-checked access
```

### 10. Enable All Static Analysis

- Run **ruff** with all rules enabled (or explicit rule selection)
- Use **mypy** or **pyright** in **strict mode**
- Treat all warnings as errors in CI
- Configure pre-commit hooks for automatic checking

```toml
# pyproject.toml
[tool.mypy]
strict = true
warn_unreachable = true
warn_redundant_casts = true

[tool.ruff]
select = ["ALL"]  # Enable all rules, then exclude specific ones
ignore = ["D203", "D213"]  # Only ignore with justification

[tool.ruff.per-file-ignores]
"tests/*" = ["S101"]  # Allow assert in tests
```

### Quick Reference Table

| Rule | Python Guidance |
|------|-----------------|
| Simple control flow | No recursion; use iteration with explicit stacks |
| Fixed loop bounds | Always use `for` with range or set `MAX_ITERATIONS` |
| Bounded data | Pre-allocate; use `maxlen`, `maxsize` parameters |
| Short functions | ≤60 lines; single responsibility |
| High assertion density | ≥2 asserts per function; pre/post conditions |
| Minimal scope | Declare variables at point of use |
| Check returns | Handle `None` explicitly; fail fast |
| Limit metaprogramming | No `exec`/`eval`; ≤2 decorator levels |
| Limit nesting | ≤3 levels deep; use dataclasses |
| Static analysis | mypy strict mode; ruff with all warnings |

---

## Testing

- Test file naming: `test_<module_name>.py`
- Test function naming: `test_<function_name>_<scenario>`
- Use pytest as the test framework
- Aim for clear, focused tests (one assertion concept per test)

```python
def test_calculate_discount_with_valid_percentage():
    assert calculate_discount(100, 20) == 80.0

def test_calculate_discount_raises_on_invalid_percentage():
    with pytest.raises(ValueError):
        calculate_discount(100, 150)
```

## Logging

**Log format:** `TIMESTAMP - LEVEL - MODULE/FUNCTION - MESSAGE`

```python
import logging

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(module)s/%(funcName)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
)

logger = logging.getLogger(__name__)
```

**Output example:**
```
2024-03-15 14:32:07 - INFO - auth/validate_token - Token validated for user_id=123
2024-03-15 14:32:08 - WARNING - database/execute_query - Slow query detected (2.3s)
2024-03-15 14:32:09 - ERROR - api/fetch_user - Failed to fetch user: ConnectionTimeout
```

**Log levels:**

| Level | Use for |
|-------|---------|
| `DEBUG` | Detailed diagnostic info (disabled in production) |
| `INFO` | General operational events (startup, shutdown, key actions) |
| `WARNING` | Unexpected but handled situations |
| `ERROR` | Failures that need attention |
| `CRITICAL` | System-wide failures |

**Best practices:**

- Use f-strings or `%` formatting in log calls for lazy evaluation
- Include relevant context (IDs, counts, durations)
- Don't log sensitive data (passwords, tokens, PII)
- Use `logger.exception()` in except blocks to include traceback

```python
# Good - includes context
logger.info(f"Processing batch: items={len(items)}, batch_id={batch_id}")
logger.error(f"Payment failed: order_id={order_id}, reason={error.code}")

# In exception handlers - automatically includes traceback
try:
    process_order(order)
except PaymentError:
    logger.exception(f"Payment processing failed: order_id={order.id}")
    raise
```

## Secrets Management

- Store secrets in a single **`.env`** file in the project root
- **Never commit `.env` to version control** (add to `.gitignore`)
- Provide a `.env.example` with placeholder values for documentation
- Load secrets using `python-dotenv` or similar

```python
# .env
DATABASE_URL=postgresql://user:password@localhost/db
API_SECRET_KEY=your-secret-key-here
STRIPE_API_KEY=sk_live_xxxxx
```

```python
# Loading secrets
from dotenv import load_dotenv
import os

load_dotenv()  # Load from .env in project root

DATABASE_URL = os.getenv("DATABASE_URL")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
```

**Rules:**
- Secrets = credentials, API keys, passwords, tokens → `.env`
- Configuration = app settings, feature flags, thresholds → `configuration.yml`

## Configuration

- Use **PyYAML** for configuration files
- Configuration files should be named **`configuration.yml`**
- Prefer YAML over JSON or .env for non-secret configuration

```yaml
# configuration.yml
app:
  name: "My Application"
  debug: false
  log_level: "INFO"

server:
  host: "0.0.0.0"
  port: 8080
  workers: 4

features:
  enable_cache: true
  max_upload_size_mb: 10

database:
  pool_size: 5
  timeout_seconds: 30
```

```python
# Loading configuration
from pathlib import Path
import yaml

def load_config(path: Path = Path("configuration.yml")) -> dict:
    """Load YAML configuration file.

    Args:
        path: Path to configuration file.

    Returns:
        Configuration dictionary.

    Raises:
        FileNotFoundError: If configuration file doesn't exist.
    """
    with open(path) as f:
        return yaml.safe_load(f)

config = load_config()
port = config["server"]["port"]
```

**Always use `yaml.safe_load()`** - never `yaml.load()` without a Loader.

## Versioning

Follow **Semantic Versioning** (SemVer): `MAJOR.MINOR.PATCH`

| Increment | When |
|-----------|------|
| **MAJOR** | Breaking/incompatible API changes |
| **MINOR** | New functionality, backwards compatible |
| **PATCH** | Bug fixes, backwards compatible |

**Examples:**
- `1.0.0` → `2.0.0`: Removed a public function
- `1.0.0` → `1.1.0`: Added new optional parameter
- `1.0.0` → `1.0.1`: Fixed a bug

**Pre-release versions:**
- Alpha: `1.0.0-alpha.1`
- Beta: `1.0.0-beta.1`
- Release candidate: `1.0.0-rc.1`

Store version in `pyproject.toml` or `__version__` in package `__init__.py`:

```python
# src/package_name/__init__.py
__version__ = "1.2.3"
```

## Project Structure

```
project/
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── main.py
│       └── utils/
├── tests/
│   └── test_main.py
├── .env                 # Secrets (git-ignored)
├── .env.example         # Template for secrets
├── configuration.yml    # App configuration
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

## Tooling Preferences

- **Formatter**: black (or ruff format)
- **Linter**: ruff
- **Type checker**: mypy or pyright

# Golang Standards & Style Guide

## Philosophy

Go is opinionated by design. The toolchain enforces most formatting automatically — your job is to work *with* the language, not fight it. Where Python rewards flexibility, Go rewards clarity and explicitness. Adopt Go idioms rather than porting Python habits.

---

## Toolchain (Non-Negotiable)

These tools are mandatory, not optional. Run them before every commit.

| Tool | Purpose | Command |
|------|---------|---------|
| `gofmt` | Canonical formatting | `gofmt -w .` |
| `goimports` | Format + manage imports | `goimports -w .` |
| `go vet` | Catches common bugs | `go vet ./...` |
| `staticcheck` | Advanced static analysis | `staticcheck ./...` |
| `golangci-lint` | Aggregated linting | `golangci-lint run` |

Configure pre-commit hooks so formatting is never a manual step.

```toml
# .golangci.yml
linters:
  enable-all: true
  disable:
    - exhaustivestruct   # Too noisy for general use
    - gochecknoglobals   # Sometimes necessary

linters-settings:
  govet:
    enable-all: true
  cyclop:
    max-complexity: 10
```

---

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Variables | `camelCase` | `userCount`, `totalItems` |
| Constants | `camelCase` or `PascalCase` | `maxRetries`, `DefaultTimeout` |
| Functions / Methods | `camelCase` (unexported), `PascalCase` (exported) | `parseToken()`, `FetchUser()` |
| Types / Structs | `PascalCase` | `UserRepository`, `ParsedResult` |
| Interfaces | `PascalCase`, single-method = verb + `er` | `Reader`, `Stringer`, `UserFetcher` |
| Packages | lowercase, single word | `auth`, `httputil`, `store` |
| Error variables | `ErrXxx` for sentinel errors | `ErrNotFound`, `ErrTimeout` |
| Test files | `_test.go` suffix | `user_test.go` |

**Key difference from Python:** exported (public) identifiers start with a capital letter. Unexported identifiers start lowercase. This is enforced by the compiler, not convention.

```go
// Unexported — only accessible within the package
type userCache struct {
    entries map[string]User
}

func (c *userCache) get(id string) (User, bool) {
    u, ok := c.entries[id]
    return u, ok
}

// Exported — accessible from other packages
type UserRepository struct {
    cache *userCache
}

func (r *UserRepository) FindByID(id string) (User, error) {
    // ...
}
```

---

## Error Handling

Go has no exceptions. Errors are values returned explicitly. Treat them as first-class citizens.

### Core Rules

- **Always handle errors.** Never assign to `_` unless you have an explicit, commented reason.
- **Wrap errors with context** using `fmt.Errorf("operation failed: %w", err)`.
- **Sentinel errors** for known, checkable conditions; custom types for structured errors.
- Check errors immediately after the call — don't defer checking.

```go
// Bad — ignored error
file, _ := os.Open(path)

// Bad — error checked too late
result, err := doThing()
doOtherThing()  // runs even if doThing failed
if err != nil {
    return err
}

// Good — immediate check, wrapped context
result, err := fetchUser(ctx, id)
if err != nil {
    return fmt.Errorf("get user profile: %w", err)
}
```

### Custom Error Types

Use custom errors when callers need to inspect the error beyond its message.

```go
// Sentinel — for simple, known conditions
var (
    ErrNotFound   = errors.New("not found")
    ErrUnauthorized = errors.New("unauthorized")
)

// Structured — when callers need fields
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Message)
}

// Checking error types
if errors.Is(err, ErrNotFound) {
    // handle not found
}

var valErr *ValidationError
if errors.As(err, &valErr) {
    log.Printf("bad field: %s", valErr.Field)
}
```

---

## Types & Interfaces

### Interfaces

Go interfaces are **implicit** — a type satisfies an interface simply by implementing its methods. This is structural typing without declaration.

```go
// Define small, focused interfaces
type Storer interface {
    Store(ctx context.Context, key string, value []byte) error
}

type Fetcher interface {
    Fetch(ctx context.Context, key string) ([]byte, error)
}

// Compose interfaces when needed
type StoreFetcher interface {
    Storer
    Fetcher
}

// Accept interfaces, return concrete types
// (the "accept interfaces, return structs" principle)
func NewProcessor(store Storer) *Processor {
    return &Processor{store: store}
}
```

### Structs

Use structs for structured data. Prefer explicit field names in literals.

```go
// Bad — positional, fragile
user := User{"alice", "alice@example.com", 30}

// Good — explicit fields
user := User{
    Name:  "alice",
    Email: "alice@example.com",
    Age:   30,
}
```

### Zero Values

Design structs so the zero value is useful or safe. Document when it isn't.

```go
// Good — zero value is a valid, empty buffer
type Buffer struct {
    data []byte
}

// Requires constructor — zero value not safe; document this
// NewRateLimiter must be used; zero value of RateLimiter is not valid.
type RateLimiter struct {
    limit  int
    ticker *time.Ticker
}

func NewRateLimiter(limit int) *RateLimiter {
    return &RateLimiter{
        limit:  limit,
        ticker: time.NewTicker(time.Second),
    }
}
```

---

## Control Flow

### Early Returns & Guard Clauses

Mirror the Python principle: fail fast, keep the happy path unindented.

```go
// Bad — deeply nested
func processOrder(order *Order) error {
    if order != nil {
        if order.IsValid() {
            if order.HasItems() {
                // actual logic buried here
            }
        }
    }
    return nil
}

// Good — guard clauses
func processOrder(order *Order) error {
    if order == nil {
        return fmt.Errorf("processOrder: order is nil")
    }
    if !order.IsValid() {
        return fmt.Errorf("processOrder: invalid order %s", order.ID)
    }
    if !order.HasItems() {
        return fmt.Errorf("processOrder: order %s has no items", order.ID)
    }
    // happy path at top level
    return fulfil(order)
}
```

### Switch Over If-Else Chains

```go
// Bad
if status == "active" {
    handleActive()
} else if status == "pending" {
    handlePending()
} else if status == "cancelled" {
    handleCancelled()
}

// Good
switch status {
case "active":
    handleActive()
case "pending":
    handlePending()
case "cancelled":
    handleCancelled()
default:
    return fmt.Errorf("unknown status: %s", status)
}
```

---

## Concurrency

Go's concurrency primitives are powerful and easy to misuse. Follow these rules strictly.

### Core Rules

- **Document goroutine ownership.** Who starts it? Who stops it? What's its lifetime?
- **Always provide a cancellation path.** Pass `context.Context` as the first argument to any function that may block.
- **Never start a goroutine without knowing how it ends.**
- **Prefer channels for communication; mutexes for state protection.** Don't mix them without care.

```go
// Bad — goroutine with no cancellation, no lifecycle
go func() {
    for {
        process(fetchNext())
    }
}()

// Good — goroutine with context and clean shutdown
func startWorker(ctx context.Context, jobs <-chan Job) {
    go func() {
        for {
            select {
            case <-ctx.Done():
                return // clean exit
            case job, ok := <-jobs:
                if !ok {
                    return // channel closed
                }
                process(job)
            }
        }
    }()
}
```

### Context

```go
// Context is always the first parameter
func FetchUser(ctx context.Context, id string) (User, error) { ... }

// Respect cancellation
func longOperation(ctx context.Context) error {
    for i := 0; i < MAX_ITERATIONS; i++ {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }
        // do work
    }
    return nil
}
```

### Race Conditions

Run tests with the race detector. Always.

```bash
go test -race ./...
```

---

## Power of 10 — Go Adaptation

### 1. Simple Control Flow

No `goto`. Avoid deeply nested goroutine fan-outs. Use iterative patterns; if recursion is needed, add an explicit depth guard.

```go
const maxDepth = 100

func traverse(node *Node, depth int) error {
    if depth > maxDepth {
        return fmt.Errorf("traverse: exceeded max depth %d", maxDepth)
    }
    if node == nil {
        return nil
    }
    if err := process(node); err != nil {
        return fmt.Errorf("traverse: node %s: %w", node.ID, err)
    }
    return traverse(node.Next, depth+1)
}
```

### 2. Fixed Loop Bounds

```go
const maxRetries = 10

for attempt := range maxRetries {
    err := doOperation()
    if err == nil {
        break
    }
    if attempt == maxRetries-1 {
        return fmt.Errorf("operation failed after %d attempts: %w", maxRetries, err)
    }
}
```

### 3. Bounded Data Structures

```go
// Bad — unbounded channel
jobs := make(chan Job)

// Good — buffered with explicit capacity
const maxQueueDepth = 500
jobs := make(chan Job, maxQueueDepth)

// Bounded cache with explicit eviction
import "github.com/hashicorp/golang-lru/v2"

cache, err := lru.New[string, User](1000)
if err != nil {
    return fmt.Errorf("init cache: %w", err)
}
```

### 4. Short Functions

Maximum ~50 lines. If a function needs more, extract helpers. A function that
handles both the happy path and three error cases is probably two functions.

### 5. High Assertion Density

Go doesn't have `assert` in production code, but the principle maps directly to **early validation and invariant checks**.

```go
func calculateAverage(values []float64) (float64, error) {
    // Preconditions
    if values == nil {
        return 0, fmt.Errorf("calculateAverage: values is nil")
    }
    if len(values) == 0 {
        return 0, fmt.Errorf("calculateAverage: values is empty")
    }

    total := 0.0
    for _, v := range values {
        total += v
    }
    result := total / float64(len(values))

    // Postcondition
    min, max := slices.Min(values), slices.Max(values)
    if result < min || result > max {
        return 0, fmt.Errorf("calculateAverage: result %f outside range [%f, %f]", result, min, max)
    }

    return result, nil
}
```

### 6. Minimal Variable Scope

Declare variables inside the block where they're needed. Use `:=` in the narrowest scope possible. Avoid package-level mutable state.

```go
// Bad — broad scope
var result string
if condition {
    result = "yes"
} else {
    result = "no"
}
use(result)

// Good — scoped to use site
result := "no"
if condition {
    result = "yes"
}
use(result)
```

### 7. Check All Return Values

The compiler enforces this for errors — don't subvert it.

```go
// Bad — discarding error
os.Remove(tmpFile)

// Good — handle or explicitly acknowledge
if err := os.Remove(tmpFile); err != nil {
    logger.Warn("failed to clean up temp file", "path", tmpFile, "err", err)
}
```

### 8. Limit Metaprogramming

Avoid `reflect` outside of framework-level code. Avoid `unsafe` entirely. If you find yourself reaching for `interface{}` / `any` pervasively, reconsider your design.

```go
// Bad — opaque, unanalyzable
func process(data interface{}) interface{} { ... }

// Good — concrete types or constrained generics
func process[T Processable](data T) (Result, error) { ... }
```

### 9. Limit Data Structure Nesting

Use structs with named fields instead of `map[string]map[string]interface{}`. Nested maps are a code smell.

```go
// Bad
config := map[string]map[string]interface{}{
    "database": {
        "host": "localhost",
        "port": 5432,
    },
}

// Good
type DatabaseConfig struct {
    Host string
    Port int
}

type Config struct {
    Database DatabaseConfig
}
```

### 10. Enable All Static Analysis

```yaml
# .golangci.yml
run:
  timeout: 5m

linters:
  enable:
    - govet
    - staticcheck
    - errcheck
    - gosimple
    - ineffassign
    - unused
    - gocyclo
    - misspell
    - godot
    - noctx
    - bodyclose
    - contextcheck
```

```bash
# In CI — fail on any lint warning
golangci-lint run --max-issues-per-linter=0 --max-same-issues=0
go test -race -coverprofile=coverage.out ./...
```

---

## Documentation

Go doc comments are parsed by `godoc` and `pkg.go.dev`. Format matters.

```go
// Package auth provides token-based authentication utilities.
// It supports JWT and opaque token formats and is safe for concurrent use.
package auth

// UserStore retrieves and persists user records.
// Implementations must be safe for concurrent use.
type UserStore interface {
    // FindByID returns the user with the given ID.
    // Returns ErrNotFound if no user exists with that ID.
    FindByID(ctx context.Context, id string) (User, error)
}

// ParseToken validates and decodes a JWT token string.
// It returns the claims contained in the token or an error
// if the token is expired, malformed, or has an invalid signature.
func ParseToken(tokenStr string, secret []byte) (*Claims, error) {
```

Rules:
- Comments on exported identifiers are **mandatory**.
- Start the comment with the name of the thing being documented.
- Full sentences ending with periods.
- Document concurrency safety on types that will be shared.

---

## Project Layout (General Purpose)

```
myproject/
├── cmd/
│   └── myapp/
│       └── main.go          # Entry point only — minimal logic here
├── internal/                # Private packages — not importable externally
│   ├── auth/
│   ├── store/
│   └── config/
├── pkg/                     # Public packages — safe for external import
│   └── httputil/
├── testdata/                # Test fixtures
├── go.mod
├── go.sum
├── .golangci.yml
└── Makefile
```

`main.go` should only wire dependencies and start the application. All logic lives in packages.

---

## Testing

```go
// test_<function>_<scenario> naming, same principle as Python
func TestFindByID_ReturnsUser(t *testing.T) { ... }
func TestFindByID_ReturnsErrNotFound(t *testing.T) { ... }
func TestFindByID_ReturnsErrorOnDBFailure(t *testing.T) { ... }

// Table-driven tests for multiple scenarios
func TestCalculateAverage(t *testing.T) {
    tests := []struct {
        name    string
        input   []float64
        want    float64
        wantErr bool
    }{
        {"single value", []float64{5}, 5.0, false},
        {"multiple values", []float64{1, 2, 3}, 2.0, false},
        {"empty slice", []float64{}, 0, true},
        {"nil slice", nil, 0, true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := calculateAverage(tt.input)
            if (err != nil) != tt.wantErr {
                t.Errorf("wantErr=%v, got err=%v", tt.wantErr, err)
            }
            if got != tt.want {
                t.Errorf("want %f, got %f", tt.want, got)
            }
        })
    }
}
```

Always run: `go test -race -count=1 ./...`

---
---

# JavaScript, HTML5 & CSS3 Standards & Style Guide

## Philosophy

Vanilla-first means the platform is your framework. Prefer what the browser gives you natively before reaching for abstractions. Every dependency is a liability — add them deliberately, not habitually. Progressive enhancement is the default posture: content and function first, presentation layered on top.

---

## HTML5

### Document Structure

Every page starts with this canonical shell. No exceptions.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Page description — 150–160 characters">
    <title>Page Title — Site Name</title>
    <link rel="stylesheet" href="css/main.css">
</head>
<body>
    <!-- content -->
    <script src="js/main.js" defer></script>
</body>
</html>
```

Key rules:
- `lang` attribute on `<html>` is **mandatory** — affects screen readers and search.
- `charset` and `viewport` come before anything else in `<head>`.
- Scripts use `defer` and go at the bottom of `<body>` — never in `<head>` without `defer` or `async`.
- `<title>` follows the `Page — Site` pattern for breadcrumb clarity in browser tabs.

### Semantic Markup

Use the element that describes the content, not the one that looks right by default.

```html
<!-- Bad — div soup -->
<div class="header">
  <div class="nav">
    <div class="nav-item"><a href="/">Home</a></div>
  </div>
</div>
<div class="main-content">
  <div class="article">
    <div class="article-title">How to Write HTML</div>
  </div>
</div>

<!-- Good — semantic structure -->
<header>
  <nav aria-label="Primary navigation">
    <ul>
      <li><a href="/">Home</a></li>
    </ul>
  </nav>
</header>
<main>
  <article>
    <h1>How to Write HTML</h1>
  </article>
</main>
```

Landmark elements and their purposes:

| Element | Use for |
|---------|---------|
| `<header>` | Site or section header |
| `<nav>` | Navigation blocks |
| `<main>` | Primary page content (one per page) |
| `<article>` | Self-contained, independently distributable content |
| `<section>` | Thematic grouping with a heading |
| `<aside>` | Tangentially related content (sidebars, callouts) |
| `<footer>` | Footer for page or section |
| `<figure>` + `<figcaption>` | Images, diagrams, code blocks with captions |

### Heading Hierarchy

- One `<h1>` per page — the primary topic.
- Never skip levels (`<h1>` → `<h3>` without `<h2>`).
- Headings communicate document structure, not visual size. Use CSS for size.

### Forms

```html
<!-- Always pair labels with inputs -->
<label for="email">Email address</label>
<input
    type="email"
    id="email"
    name="email"
    autocomplete="email"
    required
    aria-describedby="email-hint"
>
<p id="email-hint">We'll never share your email.</p>

<!-- Fieldsets for grouped inputs -->
<fieldset>
    <legend>Notification preferences</legend>
    <label><input type="checkbox" name="notify" value="email"> Email</label>
    <label><input type="checkbox" name="notify" value="sms"> SMS</label>
</fieldset>
```

- Every `<input>` has a `<label>` — never use `placeholder` as a substitute for a label.
- Use the most specific `type` attribute available: `email`, `tel`, `url`, `number`, `date`.
- `autocomplete` attributes improve UX and reduce friction.

### Accessibility (WCAG 2.1 AA)

These are non-negotiable for static pages:

```html
<!-- Images: meaningful vs decorative -->
<img src="chart.png" alt="Bar chart showing Q3 revenue up 12% YoY">
<img src="divider.svg" alt="" role="presentation"> <!-- decorative: empty alt -->

<!-- Interactive elements need accessible names -->
<button aria-label="Close dialog">×</button>
<a href="/report.pdf" aria-label="Download Q3 report (PDF, 2MB)">Download</a>

<!-- ARIA only when native semantics don't exist -->
<div role="status" aria-live="polite" id="form-status"></div>
```

Rules:
- All images have `alt`. Decorative images have `alt=""`.
- Interactive elements are keyboard navigable — never remove `outline` without providing a replacement focus style.
- Color alone never conveys meaning.
- Minimum contrast ratio: 4.5:1 for normal text, 3:1 for large text.

---

## CSS3

### File Organisation

```
css/
├── main.css          # @import entry point only
├── base/
│   ├── reset.css     # Normalize/reset
│   └── typography.css
├── layout/
│   ├── grid.css
│   └── page.css
├── components/
│   ├── buttons.css
│   ├── forms.css
│   └── cards.css
└── utilities/
    └── helpers.css
```

`main.css` imports only — no rules directly in it:

```css
@import 'base/reset.css';
@import 'base/typography.css';
@import 'layout/grid.css';
@import 'components/buttons.css';
```

### Custom Properties (CSS Variables)

Define your entire design system as custom properties. Never hardcode values.

```css
:root {
    /* Color palette */
    --color-brand-primary: #1a6eff;
    --color-brand-secondary: #0d4abf;
    --color-neutral-900: #0f0f0f;
    --color-neutral-600: #4a4a4a