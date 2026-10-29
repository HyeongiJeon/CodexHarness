# Codex harness research

Verified on **2026-10-30** against official OpenAI documentation, the installed **`codex-cli 0.163.0`**, and public `openai/codex` source. This is an implementation reference for the repository harness, not a claim that every documented model is enabled for this account.

## Evidence and version boundaries

The documentation search and actual page fetches preceded source inspection. The former `developers.openai.com/codex/…` URLs currently redirect to `learn.chatgpt.com`. Both are official OpenAI documentation. The public source was cloned into temporary directories; the installed CLI and user configuration were not edited.

| Evidence | Pinned version | Date |
| --- | --- | --- |
| Installed CLI, observed with `codex --version` | `codex-cli 0.163.0` | Observed 2026-10-30 |
| Public release tag corresponding to that version | [`rust-v0.163.0`, commit `83086188ae0614bd882818ff1aa23f3194962012`](https://github.com/openai/codex/tree/83086188ae0614bd882818ff1aa23f3194962012) | Commit timestamp `2026-10-15T18:57:07Z` |
| Latest public default branch observed during research | [`2681f8cba2831ef72bca2c0672b2e49d5f690745`](https://github.com/openai/codex/tree/2681f8cba2831ef72bca2c0672b2e49d5f690745) | Commit timestamp `2026-10-29T14:30:02Z` |

The binary version and matching public release tag establish a useful baseline, but do not prove that this environment's binary is a byte-for-byte build of that tag. Source findings below use the release commit unless explicitly labeled latest. No compiled source changes were applied. Temporary research checkouts were `/tmp/codex-official-research` and `/tmp/codex-0163-research`.

## Agent role configuration

The installed release accepts both explicit role registration in `config.toml` and standalone role discovery. The latest documentation's standalone-file format is **already implemented in 0.163.0**; it is not necessary to upgrade for that format. Explicit registration remains documented in the [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) and implemented by [`AgentsToml` / `AgentRoleToml`](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/config/src/config_toml.rs#L758).

```toml
# .codex/config.toml
[agents]
enabled = true
max_concurrent_threads_per_session = 3
max_depth = 2

[agents.reviewer]
description = "Review a bounded change and report actionable defects."
config_file = "agents/reviewer.toml"
```

```toml
# .codex/agents/reviewer.toml
name = "reviewer"
description = "Review a bounded change and report actionable defects."
model = "gpt-6.1-terra"
model_reasoning_effort = "high"
developer_instructions = "Review only the assigned scope. Report evidence and verification gaps."
```

This is a schema example, not the final role assignment. `config_file` paths resolve relative to the declaring config file. For explicit CLI registration use absolute paths to avoid depending on a config file's base directory. Role names must not collide with reserved scalar keys under `[agents]`.

| Setting | Installed 0.163.0 behavior |
| --- | --- |
| `agents.enabled` | Enables multi-agent tools; default true. An enabled V2 feature takes precedence. |
| `agents.max_concurrent_threads_per_session` | Positive integer concurrency setting; `agents.max_threads` is a legacy alias. See backend distinction below. |
| `agents.max_depth` | V1 nesting depth; default 1, so children cannot delegate further without a larger limit. V2 ignores this setting. |
| `agents.default_subagent_model` | Default when the spawn does not specify a model. |
| `agents.default_subagent_reasoning_effort` | Default when the spawn does not specify effort. |
| `agents.interrupt_message` | Records a model-visible interruption message; default true. |
| `agents.<role>.description` | Role selection guidance; required after file/layer metadata resolution. |
| `agents.<role>.config_file` | Optional TOML role file, which must exist if referenced. |
| `agents.<role>.nickname_candidates` | Optional nonempty list of distinct, nonblank ASCII names; unrelated to model selection. |

Standalone files are scanned recursively beneath a config layer's `agents` directory, including project `.codex/agents/`. They require a nonblank `name`, `description`, and `developer_instructions`. An explicitly registered file can use its registration name as a hint and can omit `developer_instructions`; supplying all three keeps the same file usable independently. A file's `name` is authoritative, including when explicitly registered. Declared file paths are skipped during discovery to prevent duplicate registration. Invalid definitions can be ignored with startup warnings; TOML parsing alone is not proof that a role loaded. See the release [role parser](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/agent-roles/src/agent_role_config.rs) and [role loader](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/agent-roles/src/loader.rs).

## Model and reasoning inheritance

The effective child configuration begins with the parent's live model, effort, provider, instructions, current directory, and permission state. The sequence in the installed release is:

1. Resolve explicit spawn model/effort, falling back independently to the corresponding `[agents]` defaults.
2. If a model is selected at this step but no effort is selected, use that model's default effort.
3. Apply the configured role. A role's `model` and `model_reasoning_effort` override the values resolved above.
4. Restore the live parent permission state and root service-tier preference.

A role that sets only `model` preserves the effort already resolved before role application; it does not automatically obtain the new model's default. **Set both model and effort in a role** when predictability matters. Explicit spawn selection must match an available model, and unsupported efforts are rejected when authoritative model metadata is available. Fallback model metadata is a validation limitation, not evidence of access. Sources: release [`child_config.rs`](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/agent/child_config.rs#L53), [`role.rs`](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/agent/role.rs#L63).

Role files can change instructions and supported model settings and disable supported capabilities. They cannot replace the parent's sandbox, approval policy, provider, or MCP server definitions. Supported reductions include disabling shell tools, apps, plugins, memories, permission requests, and individual skills. A reviewer instruction saying “do not edit” is behavioral guidance; it does not create a separate read-only sandbox. The [official subagents page](https://learn.chatgpt.com/docs/agent-configuration/subagents) and the release role projection code agree on these limits.

### Exact model names and access

The user's requested **GPT-5.6 Terra** is documented with the exact ID **`gpt-5.6-terra`**. It supports `none`, `low`, `medium`, `high`, `xhigh`, and `max` reasoning efforts according to the fetched [official model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra). It is a different model from `gpt-6.1-terra`; the latter must never be presented as a spelling or alias of the former.

This active session's exposed delegation tool lists `gpt-6.1-sol`, `gpt-6.1-terra`, `gpt-6-luna`, and `gpt-6-sol` among permitted choices. It does **not** expose `gpt-5.6-terra` as a callable override. That is evidence about this session, not a complete catalog for the installed CLI or the user's account. An actual CLI request or its model catalog must establish access before claiming GPT-5.6 Terra works. Preserve the requested ID in a preference or optional configuration; use a clearly named, explicit fallback when unavailable, and record the model actually used. The excluded model family must not be selected. No inference from a public model page alone establishes account access.

The CLI's [`ReasoningEffort` enum](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/protocol/src/openai_models.rs#L62) can parse additional effort names, including `ultra`. Parsing is not proof that every model supports those names. In particular, the GPT-5.6 Terra page does not list `ultra`.

## Separate context, forks, and shared files

Each child is a separate agent thread with its own conversation and result. A fresh specialist should receive an explicit bounded task, relevant paths, constraints, expected evidence, and an output contract. Separate conversation context does **not** imply separate storage: the installed spawn code passes the parent's environment selection and working directory into children. Files changed by one child are visible to the other agents in that environment; a child spawn does not automatically create a Git worktree. Assign file ownership, coordinate overlapping writes, and reserve integration changes for one owner. Sources: release [spawn implementation](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/tools/handlers/multi_agents/spawn.rs#L106), [child runtime configuration](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/agent/child_config.rs#L174).

The active hosted collaboration tool and the installed CLI's default backend expose different schemas. Do not paste the current session's tool arguments into CLI instructions as if they were universal.

| Surface/backend | Context selection | Coordination |
| --- | --- | --- |
| Installed V1, default feature path | `fork_context` boolean, default false. True forks full history and rejects `agent_type` overrides. Fresh false allows role selection. | `spawn_agent`, `send_input`, `resume_agent`, `wait`, `close_agent` tools exposed by its backend. |
| Installed V2, feature available but locally observed disabled | `fork_turns`, default `all`; `none` starts fresh. Legacy `fork_context` is explicitly rejected. | Named tasks and collaboration tools, including follow-up, messaging, listing, interruption, waiting. |
| Current hosted tool in this task | `fork_turns: "none"` for independent context; full history inherits parent settings and rejects model/effort overrides under its tool contract. | Use the exact tool schemas supplied in the session. |

V1 implementation: [spawn arguments](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/tools/handlers/multi_agents/spawn.rs#L220). V2 implementation: [spawn arguments and fork resolution](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs#L200). V1 tool registration is in [`multi_agents.rs`](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/tools/handlers/multi_agents.rs).

## Concurrency and nested delegation

The release defaults are 6 for V1 and 4 for V2, but their counting differs. V1's registry cap counts spawned threads and excludes the root. In the release V2 path, `effective_agent_max_threads` subtracts one from `max_concurrent_threads_per_session`, so the configured V2 value includes the root. The current public documentation describes the setting as excluding the primary thread. **This is a documented/source discrepancy: keep the harness on its verified backend and measure actual behavior before switching.** Sources: release [constants](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/config/mod.rs#L255), [effective cap](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/config/mod.rs#L1666), [registry](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/agent/registry.rs#L20), and [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

V1's default depth 1 permits root-to-child delegation only; setting `max_depth = 2` permits one further level. The registry is shared across the session tree, so descendants do not receive independent copies of the concurrency allowance. Closing completed V1 threads releases slots. The active hosted run has its own supplied limit of four total slots, including the root; repository TOML does not enlarge that limit. Prefer a small number of independent tasks with clear owners, and let the coordinator combine evidence.

## Project config loading and trust

Ordinary configuration precedence is CLI flags/`-c`, trusted project `.codex/config.toml` layers from root toward CWD, selected user profile, base user config, cloud-managed defaults, system config, then defaults. Enforced requirements can constrain all these settings. Project config cannot bootstrap its own trust merely by declaring itself trusted. Untrusted `.codex` layers are skipped; this also affects project role discovery. The fetched [config basics](https://learn.chatgpt.com/docs/config-file/config-basic) explains trust and ordering.

The installed main loader merges CLI overrides before computing project trust. A one-run `projects.<absolute path>.trust_level` override can therefore influence that main loading path without editing the home config. There is a separate executor-local loader that discovers trust from system/base-user/legacy-managed inputs and does not include session flags or selected profiles. Avoid assuming every executor-local discovery path follows the main loader; verify the effective result. Sources: release [main loader](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/config/src/loader/mod.rs#L339), [local loader](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/config/src/loader/local.rs#L105), [loader architecture](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/config/src/loader/README.md).

Use repo-local checked-in settings and a launcher with explicit one-run arguments where necessary. Do not edit `~/.codex/config.toml`, copy authentication files, or change `CODEX_HOME` just to make the harness load. This research did none of those. In installed 0.163.0, `-p NAME` selects `$CODEX_HOME/NAME.config.toml`; do not assume older `[profiles.NAME]` examples describe this version.

## Skills and AGENTS.md

For repository skills, use **`.agents/skills/<skill-name>/SKILL.md`**. Codex discovers these along the CWD-to-repository-root path. Additional sources include `$HOME/.agents/skills`, `/etc/codex/skills`, and bundled system skills; system skills are materialized under `$CODEX_HOME/skills/.system`. A skill needs YAML `name` and `description`, followed by instructions. Metadata is advertised for selection; the full instructions are read when invoked. Skill files are reusable procedures, not separate agents. Source: [official skill discovery and format](https://learn.chatgpt.com/docs/build-skills), release [system-skill installer](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/skills/src/lib.rs#L60).

Use root `AGENTS.md` for shared repository agreements and deeper files only for narrower scope. Global Codex-home instructions load first. At each directory, discovery prefers `AGENTS.override.md`, then `AGENTS.md`, then configured fallback filenames; at most one nonempty file per directory is used. Project instructions are combined root to CWD, with later, more specific guidance taking precedence. The default combined byte cap is 32 KiB. This is an instruction chain, not a mechanism to override higher-priority session instructions. Source: [official AGENTS.md precedence](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

## CLI controls, MCP, and plugins

The installed `--help` commands were checked directly. These are user-facing CLI commands; agent orchestration tools remain model tools, not `codex spawn` shell subcommands.

| Command/control | Purpose |
| --- | --- |
| `codex --version`; `codex --help` | Establish the installed version and supported options. |
| `codex features list` | Inspect feature defaults, including `multi_agent`, `multi_agent_v2`, and plugins. |
| `codex --strict-config …` | Reject unknown config fields; does not prove role discovery or account model access. |
| `codex exec --json …` | Noninteractive run with JSONL events. Supports `--ephemeral`, `--ignore-user-config`, `--output-schema`, and `-o`. |
| `/subagents` | Inspect/switch threads in the current session. |
| `/agents`; `codex agents` | Open the shared-server agent command center; not a role configuration listing. |
| `codex resume`; `codex fork` | Continue or fork a saved interactive session. |
| `codex mcp list/get` | Inspect configured MCP servers without installing one. |
| `codex plugin list`; `/plugins` | Inspect or browse plugin availability. Installation is separate work. |

See [official CLI commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli) and release [`slash_command.rs`](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/tui/src/slash_command.rs#L81).

MCP supplies tools; skills supply instructions. Configure MCP servers in the parent session using `[mcp_servers.<name>]`; STDIO servers use `command`/`args`, while HTTP servers use `url` and can require authentication. Children inherit the parent's MCP configuration. Defining a dependency in skill metadata does not grant access or install its server. Prefer optional integrations and report missing tools explicitly. Source: [official MCP guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

Plugins package reusable skills and optionally MCP connections, hooks, and other capabilities. In the CLI, `/plugins` opens the browser, and newly installed bundled capabilities require a new session. User/service authentication and tool-specific permissions remain separate from a role file. This harness does not need a plugin installation simply to define roles or repository skills. Source: [official plugins guide](https://learn.chatgpt.com/docs/plugins).

## Verification limits and maintenance

The latest source retains the relevant registration schema, role parser, inheritance logic, and V1/V2 distinction. A focused diff found the child-config and role-discovery files unchanged between the pinned release and latest snapshot. Nearby changes include carrying additional config metadata through role projection and using an inherited environment selection in V1 spawn. This supports using the release as the implementation baseline; it is not an assertion that the entire latest release is compatible.

Static checks can establish TOML validity, file existence, role schemas, source correspondence, and local CLI option support. They cannot establish an account's model access, actual delegation, MCP authentication, total token cost, or successful parallel execution. A live smoke test should record the effective parent/child models and efforts, prove a bounded child task returns, and inspect run artifacts. If no such authenticated run occurred, describe the harness as configured and statically checked, with runtime verification outstanding.

Recheck these official pages and the installed version when upgrading. In particular, re-evaluate concurrency counting, role inheritance, trust loading, and the live model catalog before changing backends or model assignments.
