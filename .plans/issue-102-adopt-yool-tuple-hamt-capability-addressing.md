# Issue #102: Adopt yool/tuple/HAMT capability addressing

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/102

## Original description (excerpt)

```
# Adopt yool / tuple / HAMT capability addressing

## Why

This repo has no canonical way to address agent capabilities. The `yool-tuple-hamt` spec (v0.2, https://github.com/wesleysimplicio/yool-tuple-hamt) gives every callable agent action a stable opcode (`yool`), a content-addressable receipt log, and a HAMT-backed catalog so multi-agent workflows can route, audit, and reproduce calls.

Reference implementations already shipped:
- **llm-project-mapper** (TS): vendored `docs/YOOL_TUPLE_HAMT.md` + `AGENTS.md` yool block + `.catalog/` bootstrap. See https://github.com/wesleysimplicio/llm-project-mapper/blob/main/docs/YOOL_TUPLE_HAMT.md and https://github.com/wesleysimplicio/llm-project-mapper/blob/main/AGENTS.md
- **SendSprint** (Python): `sendsprint/catalog.py` HAMT module + `sendsprint catalog build|list|find|show` CLI. See https://github.com/wesleysimplicio/SendSprint/blob/main/sendsprint/catalog.py

## Scope

1. **Vendor the spec** at `docs/YOOL_TUPLE_HAMT.md` (copy verbatim from yool-tuple-hamt repo `SPEC.md` v0.2). Add `!docs/YOOL_TUPLE_HAMT.md` exception to `.gitignore` if `docs/**` is ignored.
2. **Add yool block to `AGENTS.md`** (and mirror in `CLAUDE.md` / `.github/copilot-instructions.md`):

```markdown
## yool / tuple / HAMT (capability addressing)

Spec: `docs/YOOL_TUPLE_HAMT.md` (vendored from https://github.com/wesleysimplicio/yool-tuple-hamt, version v0.2).

Every agent registered in this repo MUST declare its capability with these fields:

### <Agent Name>
- yool_id: `agent.<authority>.<slug>` (e.g. `agent.dev.python`)
- authority: dev | ops | review | audit
- lane: fast | slow | background
- agent_terms:
    cpu_quota_pct: 60       # MANDATORY guardrail (spec §11.1)
    disk_quota_mb: 100      # MANDATORY guardrail (spec §11.2)
    timeout_s: 300

Guardrails are MANDATORY per Victor Genaro's review: *"precisa de guardrail pra não fritar o processador. Você precisa de garbage collector também pra não encher 100% do disco."* See spec §11.
```

3. **Bootstrap `.catalog/` skeleton** at repo root:
   - `.catalog/.gitkeep`
   - `.catalog/README.md` (one-liner: "HAMT catalog of yool capabilities. Built from AGENTS.md. Do not edit by hand.")
   - Add `.catalog/hamt.json` and `.catalog/receipts/` to `.gitignore` (they are build artifacts).

4. **Declare every existing agent** in `AGENTS.md` (or `.agents/*.agent.md`) with the yool block above. Default guardrails: `cpu_quota_pct=60`, `disk_quota_mb=100`, `timeout_s=300`.

5. **Implement catalog builder** (stack-appropriate):
   - **Python repos**: copy `sendsprint/catalog.py` pattern. HAMT constants: `BITS_PER_LEVEL=5`, `BRANCH=32`, `MAX_LEVELS=6`, `HASH_BITS=30`, hash = `blake2b` truncated to 30 bits. Output `.catalog/hamt.json`.
   - **TS/JS repos**: copy llm-project-mapper `bin/build-hamt-catalog` pattern.
   - **Other stacks**: port the algorithm; spec §6 has canonical pseudocode.

6. **CLI surface** (if the repo has a CLI): expose `<cli> catalog build|list|find|show`. See `sendsprint/cli.py` for the Typer sub-app pattern.

## Acceptance Criteria

- [ ] `docs/YOOL_TUPLE_HAMT.md` exists, matches spec v0.2 verbatim.
- [ ] `AGENTS.md` has the yool block with mandatory guardrails section.
- [ ] `.catalog/` skeleton exists with README and `.gitignore` excludes `hamt.json` + `receipts/`.
- [ ] Every existing agent in this repo declares `yool_id`, `authority`, `lane`, and `agent_terms` (cpu/disk/timeout).
- [ ] Catalog builder runs end-to-end on this repo's `AGENTS.md` and produces `.catalog/hamt.json` with HAMT branch factor 32 and 30-bit hashes.
- [ ] `lookup`, `list`, `find` operations work against the built catalog.
- [ ] Victor Genaro's guardrail quote referenced in `AGENTS.md` yool block.
- [ ] CHANGELOG entry under current version mentions yool/HAMT adoption.

## Out of scope (separate issues)

- Receipt log persistence layer (spec §7) — file-backed JSONL stub is fine here; full Merkle chain is a follow-up.
- Disk GC three-tier policy (spec §8) — stub 
```

## Implementation plan
- [ ] Read context (module / spec / ADR)
- [ ] Draft minimal change set
- [ ] Add tests (unit + e2e where applicable)
- [ ] Lint / typecheck / coverage >= 80% on diff
- [ ] Update CHANGELOG + docs
- [ ] Link ADR if architectural

## Definition of Done
Per AGENTS.md DoD: lint + unit + e2e green, evidence attached, AC checked, conventional commit.
