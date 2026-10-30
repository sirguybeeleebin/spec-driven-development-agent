# Spec Driven Development Agent

A deterministic agent system built on strictly structured specifications.

Every specification is a task graph rendered as a Mermaid diagram, and every node is a fixed-schema contract: a goal, a target path, a set of interface blocks — each carrying a signature with mandatory docstring sections — and executable scenarios. The graph is parsed and validated before any agent runs — a malformed task, an orphan node, or a cycle is rejected at the boundary, not inside a session.

The work is done by narrow-specialized agents. Each role is wired to exactly the components of the specification it needs, and carries exactly the tools and skills its responsibility requires: the researcher reads and surveys, the implementer writes the target file, the tester writes one test per scenario, the fixer repairs the failing side from the traceback and the two candidate files alone. No role sees more than its part of the specification, and no role can do another role's work.

Every structural detail — the exact task schema, the workflow format, the role prompts, the tool surface, the skill catalogue, the configuration format — lives in `docs/`.

| Document | Contents |
|---|---|
| [docs/quickstart.md](docs/quickstart.md) | Quick start guide |
| [docs/specification.md](docs/specification.md) | Task schema, interface contract, workflow graph, AGENT.md, AGENT.yaml |
| [docs/workflow.md](docs/workflow.md) | Top-level run, task cycle, fail cascade, agent loop |
| [docs/agents.md](docs/agents.md) | Researcher, Implementer, Tester, Fixer — context, tools, budgets |
| [docs/skills.md](docs/skills.md) | `python-developer` and the four domain skills, and how each is loaded |
| [docs/tools.md](docs/tools.md) | Six tools: read, append, patch, grep, bash, load_skill |
| [docs/repomap.md](docs/repomap.md) | `# Context map`: what it is, why it exists, tree-sitter parser interface |
| [docs/cli.md](docs/cli.md) | `main.py init`, `info`, `config`, `run`, exit codes, AGENT.yaml format |
| [docs/structure.md](docs/structure.md) | Repository layout |
| [docs/benchmarks.md](docs/benchmarks.md) | `benchmarks/` — reference specifications |
| [docs/benchmarks/shop.md](docs/benchmarks/shop.md) | The shop benchmark, five tasks |