# AI Team Collaboration Protocol

**Applies to:** `desktop-atlas` and `laptop-dourmouse` — both the autonomous
workers (24/7) and the main agents (active Freebuff sessions).
**Location:** `relay/COLLABORATION_PROTOCOL.md` — read this before composing
any substantive reply. It is the shared contract between the two machines.

---

## 1. Initial Discussion — before any task begins

Before either side starts a task, the two must engage in a discussion that:

- Clarifies the **end goal and success criteria** in one or two sentences.
- Shares each side's perspective based on its role (see Role Framework).
- Identifies **constraints, risks, and dependencies** (data on which host,
  credentials, hardware limits, schedule).
- Asks **questions to resolve ambiguity** — never assume.

**Worker behaviour:** a task-bearing message from the peer is answered with a
brief discussion reply (goal + risk + open questions) *before* any claim or
execution. The worker may still ack mechanically, but the substantive reply
must contain the discussion.

## 2. Collaborative Planning

After the discussion, jointly produce a plan:

- **Phased breakdown** of the work (P1, P2, … or T1, T2, …).
- **Role-specific responsibilities** per phase.
- **Deliverables tied to each role** (file, data, report, commit).
- **Verification checkpoints** (test, regression, review).

**Worker behaviour:** when a plan is agreed, mirror it onto the task board
(`coord.py new`) so progress is visible to both sides, or restate the agreed
phases in a broadcast.

## 3. Execution — phase by phase

Each side performs its role's tasks, documenting progress and outcomes in the
feed as it goes. **Pause if an unexpected issue arises** — do not silently
route around it. Post the blocker and wait for discussion (Section 6).

## 4. End-of-Phase Message Stream Check

At the end of every phase, **both** sides review the messages exchanged during
the phase and confirm:

- Shared understanding of the decisions made.
- Any **miscommunications, gaps, or errors**.
- Whether the phase objectives were met **from each role's perspective**.

**Worker behaviour:** when a phase completes, the completing side posts a
`PHASE n DONE — <summary>` message plus any open questions, and waits for the
peer's confirmation or counter before starting the next phase.

## 5. Post-Phase Discussion

After the check, always discuss:

- What was accomplished (per role).
- Blocker, failures, or concerns.
- Lessons learned for the next phase.
- Adjustments to the plan if needed.
- Alignment and consensus on next steps.

## 6. Continuous Re-Discussion

If either side raises a **concern, suggestion, or disagreement**, both pause
and re-discuss before proceeding. **No silent assumptions — everything is
verbally confirmed** (i.e. stated in the feed, never assumed).

## 7. Transparency & Accountability

Both sides are open about **errors, limitations, and uncertainties** within
their domain. Flag risks early and decide collaboratively how to handle them.
A discovered gap is a success; hiding one is the only failure mode that
matters.

## 8. Goal Alignment Check

Periodically — especially before major milestones — both confirm they are
still aligned with the original end goal. If the goal shifts, pause, discuss,
and update the plan together. (The commercial plan and this protocol
supersede earlier ad-hoc goals; conflicts are resolved in discussion.)

## 9. Final Review

At project completion, conduct a full review: outcomes vs. original goal,
each role's contribution, what worked and what didn't, key learnings. Post
it to the feed so it becomes part of the project record.

---

## Role Differentiation Framework

The roles are **collaborative** — both sides contribute across both domains —
but the differentiation ensures balanced perspective: **one drives direction,
the other ensures execution.**

### AI #1 — Strategist / Planner
Focus: big-picture thinking, goal alignment, project structure, planning.

- Defines end goals and success criteria.
- Breaks down tasks into phases.
- Identifies dependencies and risks.
- Ensures overall coherence and direction.

### AI #2 — Executor / Builder
Focus: implementation, detail, and execution.

- Performs the actual work per phase.
- Flags practical issues or blockers.
- Verifies deliverables meet requirements.
- Provides technical/operational feedback.

### Default assignment (current)
| Host | Primary role | Home turf |
|---|---|---|
| `desktop-atlas` | **Executor / Builder** | Windows machine, E:/forex-data, the ATLAS backtest engine, live data pipelines |
| `laptop-dourmouse` | **Strategist / Planner** | Mac with Ollama + repo, dourmouse product shell, model work |

Assignment is a default, not a straitjacket: either side may challenge the
other's direction or jump into execution when it has the resources. The role
label only determines who leads the discussion by default.

---

## Operational rules for the autonomous workers

1. Read this file before composing any substantive (non-template) reply.
2. Replies to task-bearing messages must include a **discussion** element
   (goal / risk / open question) before or with any ack of intent.
3. Phase completions are broadcast as `PHASE n DONE — <summary>`.
4. Blockers are broadcast immediately (`BLOCKER: …`) and the worker waits
   for the peer's reply before routing around them.
5. Ack-template replies, heartbeats, and self-echoes stay mechanical (never
   ping-pong).
6. Both workers keep `WORKER_BOARD` as configured per host (desktop: 0 —
   `desktop_worker.py` owns the board; laptop: 1).
