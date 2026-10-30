# Stack

1. Python 3.12+
2. SQLite
3. FastAPI
4. Pydantic v2

# Database

The database schema is defined by the SQL migration files under
`migrations/`. The `migrations/` directory is the single source of
truth for table names, column names, column types, primary keys,
foreign keys, `NOT NULL` constraints, and default values.

Every `*.sql` file under `migrations/` is a migration. The schema
is the cumulative result of applying them in filename order.

Read the migration files before writing code or tests. Read them
again before every `INSERT`, `SELECT`, `UPDATE`, or `DELETE`, and
before every raw setup `INSERT` in a test.

To change the schema, add a new file — `migrations/002_<name>.sql`,
`migrations/003_<name>.sql`, and so on. Never edit an existing
migration; the applied history is the source of truth. `init`
discovers new files automatically; no code change is needed.

# Implementing

1. A target component that receives collaborators through its
   constructor declares a `typing.Protocol` for each collaborator,
   in the same module as the implementation.
2. The protocol lives in the target file, above the class that
   uses it. It names only the methods the target actually calls —
   no more.
3. The target file imports no concrete repository, service, or
   client class. Dependencies are typed against the local
   protocols and satisfied at composition time by the caller.
4. The protocol's method signatures match the operations the
   target invokes: same parameter names, same argument order,
   same return shape, same exception class the contract names.
5. A protocol carries a docstring describing what the
   collaborator does, step by step, and every method it declares
   carries its own docstring with `Description`, `Steps`, `Returns`,
   and `Raises` — same shape as the target's own methods.
6. If the task does not describe a collaborator's contract, stop
   and return `GAP: protocol for <collaborator> is not specified`.
   Do not invent methods the target does not call, and do not
   import a concrete class to fill the gap.

# Comments

1. Every logical block is preceded by a comment.
2. The comment answers **why** the block exists, not **what** it
   does; a comment that restates the code is a defect.
3. No commented-out code.

# Tracing

Tracing is not optional. A function without a start trace is a
defect. A SQL statement without a trace before it is a defect.
The absence of a trace in a function body that is not empty is a
defect.

1. **Every** function or method whose body is not empty starts
   with a trace line.
2. **Every** SQL statement and **every** state transition
   (commit, rollback, connection open/close) has its own trace
   line immediately before it executes.
3. Format: `[<module>] <symbol> <detail>`, where `<symbol>` is
   the literal function or method name.
4. `<detail>` is a space-separated list of `name=value` tokens,
   one per meaningful argument or outcome. A trace with no
   `name=value` token is a defect.
5. For collections use their length; for presence use `"ok"` or
   `"missing"`; for flags use the boolean. Never embed a full
   object.
6. A trace line fits in 120 columns, one physical line, no
   wrapping.
7. Trace output is the **only** allowed debugging output. Other
   debugging output is forbidden. The absence of trace output is
   a defect.
8. Traces are emitted with `print(..., flush=True)`. Always one
   f-string, always one physical line, always `flush=True`. No
   `logging`, no `warnings`, no `sys.stderr.write`.