```text
spec-driven-development-agent/
│
├── agents/                                 # Four specialized agents — one class per role, no shared base
│   ├── __init__.py                         # Package marker, re-exports ResearcherAgent, ImplementerAgent, TesterAgent, FixerAgent
│   ├── fixer.py                            # FixerAgent — run(constitution, interfaces, target, target_test, test_output, goal, context_map)
│   ├── fixer_test.py                       # Tests: skill selection, patch flow, post-hook stop after target/test write
│   ├── implementer.py                      # ImplementerAgent — run(constitution, context_map, goal, target, interfaces, research_report)
│   ├── implementer_test.py                 # Tests: skill selection, append flow, post-hook stop after write
│   ├── researcher.py                       # ResearcherAgent — run(constitution, context_map, goal, target, interfaces); no skill selection
│   ├── researcher_test.py                  # Tests: tool execution, hint handling, max iterations, no skill registry
│   ├── tester.py                           # TesterAgent — run(constitution, goal, target, target_test, interfaces, scenario, context_map)
│   └── tester_test.py                      # Tests: skill selection, append flow, post-hook stop after test write
│
├── benchmarks/                             # Reference specifications that exercise the engine
│   └── shop/                               # Full end-to-end project: five tasks, five skills
│       ├── AGENT.md                        # Constitution: stack, migrations, comments, tracing
│       ├── AGENT.yaml                      # Engine config: four roles, providers, tools, skills, budgets
│       ├── migrations/
│       │   └── 001_init.sql                # Creates products, orders, order_lines
│       ├── skills/                         # Domain skills the shop project loads
│       │   ├── fastapi-implementing/
│       │   │   └── SKILL.md                # Router factories, Pydantic v2, status constants
│       │   ├── fastapi-testing/
│       │   │   └── SKILL.md                # TestClient, fresh app per test, status + json asserts
│       │   ├── python-developer/
│       │   │   └── SKILL.md                # Base layer: layout, imports, typing, docstrings, errors
│       │   ├── sqlite-implementing/
│       │   │   └── SKILL.md                # Connections, placeholders, transactions, DDL, PRAGMA
│       │   └── sqlite-testing/
│       │       └── SKILL.md                # Isolation, schema source, raw inserts, PRAGMA asserts
│       ├── tasks/                          # One markdown file per target source file
│       │   ├── 001_products_repository.md  # repositories/products.py — ProductRepository
│       │   ├── 002_orders_repository.md    # repositories/orders.py — OrderRepository
│       │   ├── 003_checkout_service.md     # services/checkout.py — CheckoutService
│       │   ├── 004_orders_router.md        # routers/orders.py — Order models + factory
│       │   └── 005_main.md                 # main.py — composition root, lifespan, app instance
│       └── workflows/
│           └── end_to_end.md               # Mermaid graph: five tasks, edges, layer order
│
├── benchmark.sh                            # Runs `init` then `run workflow` on the shop benchmark
│
├── commands/                               # CLI use cases — each one self-contained: root + full configuration inside
│   ├── __init__.py                         # Package marker, re-exports every command
│   ├── config.py                           # RunConfigSet/Get/Delete/ClearCommand — AGENT.yaml CRUD
│   ├── config_test.py                      # Tests: set/get/delete/clear, missing file, missing key
│   ├── info.py                             # RunInfoCommand — static command table
│   ├── info_test.py                        # Tests: row count, numbering, expected commands
│   ├── init.py                             # RunInitCommand — create skills/, tasks/, workflows/
│   ├── init_test.py                        # Tests: missing/existing files, directory creation
│   ├── task.py                             # RunTaskCommand — builds four specialized agents + hooks + TaskRunner
│   ├── task_test.py                        # Tests: happy path, missing task/skill, unknown tool, per-role hooks
│   ├── workflow.py                         # RunWorkflowCommand — builds agents, parses graph, loads every task, runs WorkflowRunner
│   └── workflow_test.py                    # Tests: happy path, missing workflow/task, per-role hooks, all_targets wiring
│
├── docs/                                   # Everything a reader needs to understand the engine
│   ├── agents.md                           # Four specialized classes; hooks; prompt-driven stopping; per-role diagrams
│   ├── benchmarks/
│   │   └── shop.md                         # Walkthrough of the shop specification
│   ├── benchmarks.md                       # What `benchmarks/` contains and how to add one
│   ├── cli.md                              # `init`, `info`, `config`, `run`, exit codes, AGENT.yaml format
│   ├── quickstart.md                       # Install, init, run the shop benchmark
│   ├── repomap.md                          # `# Context map`: what it is, why it exists
│   ├── skills.md                           # The five skills: python-developer + four domain skills
│   ├── specification.md                    # AGENT.md, AGENT.yaml, workflow, task — full reference
│   ├── structure.md                        # Repository layout, module responsibilities
│   ├── tools.md                            # read, append, patch, load_skill — interfaces and behavior
│   └── workflow.md                         # Run pipeline, task cycle, fail cascade, agent session, hooks
│
├── hooks/                                  # Tool-call hooks: pre (hint) and post (stop)
│   ├── __init__.py                         # Package marker, re-exports RepeatedReadHook, RepeatedWriteHook, PostWriteStopHook, StopError
│   ├── post_write_stop.py                  # PostWriteStopHook — raises StopError after successful append/patch to a watched path
│   ├── post_write_stop_test.py             # Tests: ignores non-write/error/wrong path; raises on append/patch to watched path
│   ├── repeated_read.py                    # RepeatedReadHook — returns hint if path already read or already failed
│   ├── repeated_read_test.py               # Tests: ignores non-read/missing path; hint on already read/failed; different path passes
│   ├── repeated_write.py                   # RepeatedWriteHook — returns hint if path already written
│   └── repeated_write_test.py              # Tests: ignores non-write/missing path; hint on repeat append/patch; failed prior does not block
│
├── llm/                                    # Thin wrapper over the OpenAI-compatible client
│   ├── __init__.py                         # Package marker, re-exports LLMClient
│   ├── client.py                           # LLMClient — streaming, prompt/response logging, tool calls, metrics
│   └── client_test.py                      # Tests: text reply, metrics, native tool call, tool message
│
├── main.py                                 # Typer CLI: info, init, config *, run task|workflow — imports only commands
│
├── Makefile                                # `make test`, `make format`, `make bench` convenience targets
│
├── models/                                 # Typed data shared across the whole engine
│   ├── __init__.py                         # Package marker, re-exports every model
│   ├── agent.py                            # AgentStatus, AgentResult (with ok + final_response)
│   ├── graph.py                            # Node, Edge, Graph — workflow graph
│   ├── llm.py                              # Role, Metric, MetricName, ToolCall, Message
│   ├── result.py                           # TaskResult, TestResult, WorkflowResult (with ok properties)
│   ├── skill.py                            # Skill — name, description, content
│   ├── task.py                             # TaskID, TaskStatus, Interface, Scenario, Task
│   └── tool.py                             # Tools — enum of tool names used in AGENT.yaml
│
├── parsers/                                # Markdown to typed model — pure functions, no state
│   ├── __init__.py                         # Package marker, re-exports parse_graph, parse_skill, parse_task
│   ├── graph.py                            # parse_graph — mermaid fence to Graph
│   ├── graph_test.py                       # Tests: chain, standalone, multiple edges, all directions
│   ├── skill.py                            # parse_skill — YAML frontmatter + body
│   ├── skill_test.py                       # Tests: valid frontmatter, missing name/description, empty fields
│   ├── task.py                             # parse_task — task markdown with interfaces and scenarios
│   └── task_test.py                        # Tests: header, interfaces, scenarios, step keywords
│
├── promptproviders/                        # Per-role system and user prompt construction
│   ├── __init__.py                         # Package marker, re-exports five providers
│   ├── fixer.py                            # FixerPromptProvider — format_user(constitution, interfaces, target, target_test, test_output, history)
│   ├── fixer_test.py                       # Tests: system sections, user fields, history rendering
│   ├── implementer.py                      # ImplementerPromptProvider — format_user(constitution, context_map, goal, target, interfaces, research_report, history)
│   ├── implementer_test.py                 # Tests: system sections, user fields, research report, history
│   ├── researcher.py                       # ResearcherPromptProvider — format_user(constitution, context_map, goal, target, interfaces, history)
│   ├── researcher_test.py                  # Tests: system sections, user fields, no legacy sections
│   ├── skillselector.py                    # SkillSelectorPromptProvider — format_user(*, goal, context_map); JSON array output
│   ├── skillselector_test.py               # Tests: system preview, empty registry, JSON array format, fallback context map
│   ├── tester.py                           # TesterPromptProvider — format_user(constitution, goal, target, target_test, interfaces, scenario, history)
│   └── tester_test.py                      # Tests: system sections, scenario rendering, derived test function name
│
├── pyproject.toml                          # Project metadata, dependencies, Python version pin
│
├── README.md                               # Engine overview: problems, solutions, quick start
│
├── registries/                             # In-memory registries over parsed models
│   ├── __init__.py                         # Package marker, re-exports SkillRegistry
│   ├── skill.py                            # SkillRegistry — skills list, preview(), load(name), __len__
│   └── skill_test.py                       # Tests: load by name, unknown raises, preview lines, empty, __len__
│
├── repomap/                                # Project catalog rendered as `# Context map`
│   ├── __init__.py                         # Package marker, re-exports RepoMap
│   ├── models.py                           # Tag — a definition or reference extracted from a file
│   ├── parsers/
│   │   ├── __init__.py                     # Package marker
│   │   ├── python.py                       # PythonParser — tree-sitter backed Parser implementation
│   │   └── python_test.py                  # Tests for tag extraction from Python source
│   ├── repomap.py                          # RepoMap — scan, graph, rank, render
│   └── repomap_test.py                     # Tests for focus, reachability, budget, rendering
│
├── runners/                                # Orchestrates agents into task and workflow pipelines
│   ├── __init__.py                         # Package marker, re-exports TaskRunner, WorkflowRunner
│   ├── task.py                             # TaskRunner — explicit kwargs per agent; no State; ok-gated stages; fix loop
│   ├── task_test.py                        # Tests: kwargs per role, research_report forwarding, fail cascade, fix loop, per-scenario
│   ├── workflow.py                         # WorkflowRunner — walk the graph, one task at a time
│   └── workflow_test.py                    # Tests: single/multi task, failure isolation, side effects
│
├── testrunners/                            # Runs the test file and returns a TestResult
│   ├── __init__.py                         # Package marker, re-exports PytestRunner
│   ├── pytest.py                           # PytestRunner — node id, subprocess, timeout
│   └── pytest_test.py                      # Tests for node id building, output capture, timeout
│
├── tools/                                  # The four tools a role can be given
│   ├── __init__.py                         # Package marker, re-exports every tool
│   ├── append.py                           # AppendTool — append content, create parents
│   ├── append_test.py                      # Tests: create, append, missing parent, UTF-8, schema
│   ├── load_skill.py                       # LoadSkillTool — delegates to SkillRegistry.load(name)
│   ├── load_skill_test.py                  # Tests: name lookup, unknown, schema shape, delegates to registry
│   ├── patch.py                            # PatchTool — replace exactly one occurrence
│   ├── patch_test.py                       # Tests: replace, ambiguous, missing file, missing search
│   ├── read.py                             # ReadTool — read one file, return its content
│   └── read_test.py                        # Tests: content, empty file, UTF-8, missing file
│
├── uv.lock                                 # Locked dependency graph for reproducible installs
│
├── validators/                             # Semantic checks after parsing, before any agent runs — pure functions
│   ├── __init__.py                         # Package marker, re-exports validate_graph, validate_skill, validate_task
│   ├── graph.py                            # validate_graph — node presence, edge endpoints
│   ├── graph_test.py                       # Tests: valid, no nodes, duplicate, orphan edge endpoints
│   ├── skill.py                            # validate_skill — non-empty name, description, content
│   ├── skill_test.py                       # Tests: valid, empty name/description/content
│   ├── task.py                             # validate_task — required fields, target paths, scenarios
│   └── task_test.py                        # Tests: every rejection rule
│
└── workflow/                               # Dependency graph over tasks
    ├── __init__.py                         # Package marker, re-exports Workflow
    ├── workflow.py                         # Workflow — tasks, edges, dependency helpers, public tasks/edges properties
    └── workflow_test.py                    # Tests: ready set, dependent blocking, diamond progression
```