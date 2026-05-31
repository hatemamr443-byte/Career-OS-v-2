# AEOS_ENTERPRISE_v5.0.md

# Autonomous Engineering Operating System (AEOS)

Version: 5.0 Enterprise Edition

## Mission

Transform the project into a continuously improving, verifiable, production-grade engineering system.

Core principle:

NO EVIDENCE = NO CLAIM

---

# GOVERNING PRINCIPLES

- Stability First
- Verification First
- Memory First
- Security First
- Maintainability First
- Improvement Second

Never sacrifice stability for novelty.

---

# SOURCE OF TRUTH HIERARCHY

1. Repository State
2. Git History
3. Runtime Logs
4. Test Results
5. CI/CD Results
6. Specifications
7. Graphify Memory
8. External Knowledge

---

# EXECUTION LIFECYCLE

SPEC
→ PLAN
→ TASKS
→ IMPLEMENT
→ VERIFY
→ COMMIT
→ DOCUMENT
→ MEMORY UPDATE

No phase may be skipped.

---

# TASK STATE MACHINE

PLANNED
IN_PROGRESS
APPLIED
VERIFIED
COMPLETED
BLOCKED
ROLLED_BACK

---

# ANTI-HALLUCINATION LAYER

Forbidden unless verified:

- fixed
- completed
- deployed
- production ready
- secure
- optimized

Required evidence:

- git diff
- logs
- tests
- runtime validation
- CI status

---

# CONTINUOUS DEBUG LOOP

Repeat until success or blocker:

1. Inspect
2. Reproduce
3. Gather logs
4. Root cause analysis
5. Apply fix
6. Verify
7. Compare
8. Continue

---

# ROOT CAUSE POLICY

Never patch symptoms when root causes can be identified.

---

# STABILITY POLICY

Priority:

1. Broken Production
2. Broken Workflow
3. Failing Tests
4. Security Issues
5. Performance Issues
6. Enhancements

---

# MEMORY ARCHITECTURE

## Graphify

Primary long-term memory.

Repository:
https://github.com/safishamsi/graphify

Store:

- architecture
- decisions
- bugs
- fixes
- workflows
- deployment notes
- lessons learned

Never store unverified information.

---

# MEMORY TAXONOMY

## Architecture Memory

System structure.

## Decision Memory

Why choices were made.

## Bug Memory

Failures and causes.

## Fix Memory

Verified solutions.

## Deployment Memory

Infrastructure knowledge.

## Technical Debt Memory

Known future work.

---

# SESSION PERSISTENCE

Required Files:

PROJECT_MEMORY_SESSION_SUMMARY.md

SESSION_HANDOFF.md

WORK_QUEUE.md

OPEN_BLOCKERS.md

---

# RESUME PROTOCOL

Trigger:

RESUME

Actions:

1. Load Graphify
2. Load session files
3. Restore state
4. Restore blockers
5. Restore queue
6. Continue execution

Never restart completed analysis.

---

# RATE LIMIT PROTOCOL

Before interruption:

Update:

- PROJECT_MEMORY_SESSION_SUMMARY.md
- SESSION_HANDOFF.md
- WORK_QUEUE.md

---

# TOOL FRAMEWORK

## Graphify
https://github.com/safishamsi/graphify

## GitReverse
https://github.com/filiksyos/gitreverse

Repository understanding.

## Spec Kit
https://github.com/github/spec-kit

Specification-driven workflow.

## Multica
https://github.com/multica-ai/multica

Agent orchestration.

## LangGraph
https://github.com/langchain-ai/langgraph

Workflow state management.

## AutoGen
https://github.com/microsoft/autogen

Multi-agent collaboration.

## OpenHands
https://github.com/All-Hands-AI/OpenHands

Code execution and implementation.

## OpenDevin
https://github.com/OpenDevin/OpenDevin

Planning and repository analysis.

## Vibecode Pro Max Kit
https://github.com/withkynam/vibecode-pro-max-kit

Engineering playbooks.

## Semgrep
https://github.com/semgrep/semgrep

Static analysis and security.

## Sweep
https://github.com/sweepai/sweep

GitHub automation.

---

# MULTI-AGENT ROLE MODEL

Architect
Backend Engineer
Frontend Engineer
QA Engineer
Security Engineer
DevOps Engineer
Reviewer

All recommendations must pass verification.

---

# SECURITY GATES

Before merge:

- dependency review
- secret scan
- static analysis
- permissions review

Security findings must be tracked.

---

# TESTING STRATEGY

Required layers:

- unit tests
- integration tests
- workflow tests
- regression tests

No critical change without validation.

---

# CI/CD POLICY

Pipeline:

Lint
→ Tests
→ Security
→ Build
→ Deploy

Deployment blocked on critical failures.

---

# GITHUB OPERATING MODEL

Issue
→ Plan
→ Branch
→ Implementation
→ Verification
→ Pull Request
→ Review
→ Merge

---

# CODE REVIEW STANDARD

Review:

- correctness
- security
- maintainability
- performance
- observability

---

# OBSERVABILITY POLICY

Every major workflow should expose:

- logs
- metrics
- failure signals

---

# PERFORMANCE POLICY

Measure before optimizing.

Do not perform speculative optimization.

---

# API DISCOVERY LAYER

Sources:

https://github.com/public-apis/public-apis

https://repodir.com/repo/cporter202-api-mega-list

Only integrate APIs after stability is verified.

---

# IMPROVEMENT ENGINE

When stable:

Look for:

- automation opportunities
- architecture improvements
- developer experience improvements
- performance gains
- security hardening

For every improvement:

1. Benefit
2. Risk
3. Cost
4. Compatibility
5. Verification

---

# ARCHITECTURE PROTECTION

Never:

- rewrite stable systems without evidence
- replace working components unnecessarily
- introduce complexity without value

---

# COMPLETION CRITERIA

A task is complete only if:

- implementation exists
- verification exists
- documentation updated
- memory updated
- blockers resolved

Otherwise:

STATUS = IN_PROGRESS

---

# EXECUTIVE COMMANDS

RESUME
Continue from last verified checkpoint.

VERIFY
Re-validate current state.

AUDIT
Perform architecture, security, and workflow review.

STABILIZE
Prioritize fixes over enhancements.

IMPROVE
Evaluate safe improvements after stability.

---

# FINAL LAW

No Evidence = No Claim

Fix First.
Verify Second.
Improve Third.
