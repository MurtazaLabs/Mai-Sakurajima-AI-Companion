# Modes Reference: Debug / Refactor / Performance / Security

---

## DEBUG MODE {#debug}

**Core Rule**: Never guess. Reason from evidence only. Trace the actual execution path.

### Process (always run in order)

**Step 1 — Problem Analysis**
- What is the expected behavior?
- What is the actual behavior?
- At which exact point does it diverge?
- What is the full traceback or error message?

**Step 2 — Root Cause Analysis**
- Why does this issue occur?
- Which component or line is responsible?
- Which conditions trigger it (always, intermittently, under specific inputs)?
- Trace backwards from symptom → cause:
  - Type mismatches? None propagation? Off-by-one?
  - Async timing issue? Race condition?
  - State mutation from unexpected location?
  - Incorrect assumption about library behavior?

**Step 3 — Impact Assessment**
- Severity: Critical (data loss/crash) / High (wrong output) / Medium (edge case) / Low (cosmetic)
- Affected systems or other components?
- Silent failure or visible crash?

**Step 4 — Resolution**
- Provide the fix
- Explain specifically what changed and why it works
- Show improved version that handles edge cases more robustly
- Provide a prevention strategy (test that would have caught this, type hint, assertion)

### Common Bug Patterns — Check First

**Mutable Default Argument**
```python
# BUG
def add(item, lst=[]):
    lst.append(item)
    return lst

# FIX
def add(item, lst=None):
    if lst is None:
        lst = []
    lst.append(item)
    return lst
```

**None Not Checked Before Attribute Access**
```python
# BUG
result = get_user()
print(result.name)  # AttributeError if None

# FIX
result = get_user()
if result is None:
    raise ValueError("User not found")
print(result.name)
```

**Bare Except Swallowing Everything**
```python
# BUG — catches KeyboardInterrupt, SystemExit, hides all errors
try:
    op()
except:
    pass

# FIX
try:
    op()
except ValueError as e:
    logger.error(f"Validation error: {e}")
    raise
```

**Async/Await Mistakes**
```python
# BUG — returns coroutine object, not result
result = some_async_func()

# FIX
result = await some_async_func()

# BUG — blocks entire event loop
async def handler():
    time.sleep(5)

# FIX
async def handler():
    await asyncio.sleep(5)
```

**Late Binding in Closures**
```python
# BUG — all lambdas capture final value of i
funcs = [lambda: i for i in range(3)]

# FIX
funcs = [lambda i=i: i for i in range(3)]
```

**Return None on Some Paths**
```python
# BUG — returns None implicitly on negative x
def compute(x):
    if x > 0:
        return x * 2
    # forgot the else!

# FIX
def compute(x):
    if x <= 0:
        raise ValueError(f"x must be positive, got {x}")
    return x * 2
```

---

## REFACTORING MODE {#refactor}

**Core Rule**: Understand design intent before touching anything. Preserve what works.

### Analysis Checklist

Run through all dimensions before proposing changes:

**Readability**
- [ ] Are names self-documenting? (avoid `d`, `tmp`, `val`, `data` as variable names)
- [ ] Are functions named with verbs? (`get_user`, `process_order`, not `user_data`)
- [ ] Is deep nesting present? (>3 levels = refactor candidate)
- [ ] Are there magic numbers? (`if count > 50` → `if count > MAX_RETRY_COUNT`)
- [ ] Are docstrings present on public APIs?

**Maintainability**
- [ ] Single responsibility per function/class?
- [ ] Functions longer than 50 lines? (often means split opportunity)
- [ ] Classes longer than 200 lines? (often means split opportunity)
- [ ] Duplicate logic in 2+ places? (extract to shared function)
- [ ] Comments explaining "what" instead of "why"? (code should explain what; comments explain why)

**Complexity**
- [ ] Cyclomatic complexity high? (many if/elif/else branches in one function)
- [ ] Nested loops operating on the same data? (O(n²) smell)
- [ ] Long parameter lists (>4 params)? (use dataclass or TypedDict)
- [ ] Boolean trap? (`process(True, False, True)` → use keyword args or enum)

**Scalability**
- [ ] State stored in-process that should be external?
- [ ] Hardcoded limits or configs in logic?
- [ ] Not designed for concurrent access?

**Reusability**
- [ ] Framework-specific logic tangled with business logic?
- [ ] Hard-coded dependencies instead of injected ones?
- [ ] Utilities that could be extracted to shared module?

**Testability**
- [ ] Functions that do I/O AND business logic mixed together?
- [ ] Global state that tests would need to reset?
- [ ] No seams for mocking external dependencies?

### Refactoring Patterns

**Guard Clauses (eliminate deep nesting)**
```python
# BEFORE — pyramid of doom
def process(data):
    if data:
        if data.get("user"):
            if data["user"].get("active"):
                run(data)

# AFTER — guard clauses
def process(data):
    if not data:
        return
    if not data.get("user"):
        return
    if not data["user"].get("active"):
        return
    run(data)
```

**Extract Method (long functions)**
```python
# BEFORE — one giant function
def process_voice(audio):
    # 20 lines of cleaning
    # 15 lines of transcribing
    # 25 lines of intent extraction
    # 30 lines of response generation

# AFTER — orchestrator + focused helpers
def process_voice(audio):
    clean_audio = _clean_audio(audio)
    transcript = _transcribe(clean_audio)
    intent = _extract_intent(transcript)
    return _generate_response(intent)
```

**Replace Magic Numbers**
```python
# BEFORE
if len(history) > 50:
    history = history[-25:]

# AFTER
MAX_HISTORY_LENGTH = 50
HISTORY_TRIM_TO = 25

if len(history) > MAX_HISTORY_LENGTH:
    history = history[-HISTORY_TRIM_TO:]
```

**Replace Type Checks with Polymorphism**
```python
# BEFORE
def speak(animal):
    if isinstance(animal, Dog):
        animal.bark()
    elif isinstance(animal, Cat):
        animal.meow()

# AFTER
def speak(animal):
    animal.speak()  # each class implements speak()
```

**Dependency Injection (for testability)**
```python
# BEFORE — untestable
class Service:
    def __init__(self):
        self.db = PostgresDB(os.getenv("DB_URL"))

# AFTER — injectable, testable
class Service:
    def __init__(self, db: DatabaseInterface):
        self.db = db
```

---

## PERFORMANCE MODE {#performance}

**Core Rule**: Measure before optimizing. The slowest part is rarely the obvious one.

### Evaluation Dimensions

**Time Complexity**
- Identify Big-O of every hot path
- O(n²) nested loops on same data → restructure with dict/set
- Repeated linear scans → convert to set for O(1) lookup

**Space Complexity**
- Large data loaded fully into RAM when streaming would work
- Unnecessary copies of large objects
- Growing unbounded collections (lists that only append, never trim)

**Memory Usage**
```python
# Loads entire dataset into RAM
data = [process(x) for x in huge_file]

# Streams one item at a time — O(1) memory
def stream(file):
    for line in file:
        yield process(line)
```

**CPU Usage**
- Repeated expensive computations inside loops → cache the result
- `re.compile()` outside loop, not inside
- Sorting when a heap would do

**Database Efficiency**
```python
# N+1 — catastrophic at scale
for user in db.get_all_users():
    orders = db.get_orders(user.id)  # called N times

# Fix: JOIN or batch fetch
users_with_orders = db.get_users_with_orders()  # 1 query
```

**Network Efficiency**
```python
# Sequential — O(n) latency
for url in urls:
    result = requests.get(url)

# Concurrent — O(1) latency (relative to n)
async with aiohttp.ClientSession() as s:
    results = await asyncio.gather(*[fetch(s, url) for url in urls])
```

### Quick-Win Checklist
| Pattern | Slow | Fast |
|---------|------|------|
| Membership test | `item in list` O(n) | `item in set` O(1) |
| String building in loop | `s += piece` O(n²) | `''.join(parts)` O(n) |
| Counting | manual loop | `collections.Counter` |
| Grouping | manual dict | `collections.defaultdict` |
| Repeated regex | `re.match(pat, s)` each call | `pat = re.compile(...)` once |
| Repeated expensive calls | no cache | `@lru_cache` or `@cache` |
| DataFrame row-by-row | `df.iterrows()` | vectorized ops / `.apply()` |

### Caching
```python
from functools import lru_cache, cache

@lru_cache(maxsize=256)
def expensive(n: int) -> int: ...

# Python 3.9+ — unbounded, slightly faster
@cache
def also_expensive(key: str) -> str: ...

# Async (pip install async-lru)
from async_lru import alru_cache

@alru_cache(maxsize=128)
async def async_expensive(key: str) -> str: ...
```

### Blocking in Async (most common AI/voice app issue)
```python
# KILLS event loop — all other tasks freeze
async def handler():
    data = requests.get(url)      # sync HTTP
    time.sleep(2)                 # sync sleep
    content = open("f").read()    # can block

# CORRECT
async def handler():
    async with aiohttp.ClientSession() as s:
        data = await s.get(url)
    await asyncio.sleep(2)
    async with aiofiles.open("f") as f:
        content = await f.read()

# For unavoidably-sync code, offload to thread pool
result = await asyncio.to_thread(sync_blocking_fn, arg)
```

---

## SECURITY MODE {#security}

**Core Rule**: Flag immediately. Explain severity. Never defer security issues to "later".

### Injection Risks

**SQL Injection**
```python
# CRITICAL — never do this
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# CORRECT — parameterized
query = "SELECT * FROM users WHERE name = %s"
cursor.execute(query, (user_input,))

# SQLAlchemy ORM (safe by default)
db.query(User).filter(User.name == user_input).all()
```

**Command Injection**
```python
# CRITICAL
os.system(f"convert {user_input} output.png")
subprocess.run(f"ping {host}", shell=True)

# CORRECT — pass as list, no shell=True
subprocess.run(["convert", user_input, "output.png"], check=True)
subprocess.run(["ping", "-c", "1", host], check=True)
```

**Unsafe Execution**
```python
# CRITICAL — arbitrary code execution
eval(user_input)
exec(user_input)

# If dynamic evaluation is genuinely needed, use ast.literal_eval for data only
import ast
value = ast.literal_eval(user_input)  # only safe for literals (str, int, list, dict)
```

### Secret Exposure
```python
# CRITICAL — never in source code
API_KEY = "sk-abc123..."
DB_PASSWORD = "hunter2"

# CORRECT — environment variables
import os
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY environment variable not set")

# Better — pydantic-settings with validation
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    api_key: str
    db_password: str
```

### Input Validation
```python
# Always validate before use
from pydantic import BaseModel, validator

class UserRequest(BaseModel):
    name: str
    age: int
    email: str

    @validator("age")
    def age_must_be_valid(cls, v):
        if not 0 < v < 150:
            raise ValueError("Invalid age")
        return v
```

### Authentication / Authorization
- [ ] Passwords hashed with bcrypt/argon2, never stored plain or MD5/SHA1
- [ ] JWT tokens verified (signature + expiry), not just decoded
- [ ] Authorization checked per-resource, not just at login
- [ ] Sessions invalidated on logout
- [ ] Rate limiting on auth endpoints

### Unsafe Deserialization
```python
# CRITICAL — pickle executes arbitrary code
import pickle
data = pickle.loads(user_provided_bytes)

# CORRECT — use JSON for untrusted data
import json
data = json.loads(user_provided_string)
```

### File Operations
```python
# DANGEROUS — path traversal
path = f"/data/{user_input}"
open(path).read()

# CORRECT — validate and restrict
import pathlib
base = pathlib.Path("/data").resolve()
requested = (base / user_input).resolve()
if not str(requested).startswith(str(base)):
    raise PermissionError("Path traversal detected")
```

### Security Checklist
- [ ] No hardcoded secrets in code or config files committed to git
- [ ] All SQL uses parameterized queries
- [ ] No `eval()`/`exec()` on untrusted input
- [ ] No `shell=True` with user input in subprocess
- [ ] User input validated with type + range checks before use
- [ ] Sensitive data (tokens, passwords, PII) not written to logs
- [ ] File paths constructed from user input are validated against a base directory
- [ ] Pickle/marshal not used on untrusted data
- [ ] JWT tokens have expiry and signature is verified
- [ ] No `pickle.loads()` on externally-provided bytes