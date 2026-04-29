HISTORY_EXTRACTION_PROMPT = """
You are an expert at analyzing workplace communications and extracting decision-making history.

Given the following conversation excerpts, extract all significant decision-making events.
Focus on **WHY a decision was made**, not just what was decided.

For each decision:
- title: concise one-line summary of the decision
- situation: what context/problem triggered this decision
- reason: why this particular decision was made (not another option)
- process: how the decision was reached (who discussed, what was considered)
- constraints: any limitations, deadlines, or blockers that influenced the decision
- decision: the actual decision/outcome
- decision_maker: who made the final call (email or name)
- participants: list of all people involved
- event_time: when this decision occurred (ISO8601 if known, else null)

CRITICAL RULES:
1. Every history event MUST have at least one source_link.
2. If you cannot identify a clear source, set needs_human_review=true and add to missing_evidence.
3. Do NOT fabricate participants or decision_makers not present in the source.
4. confidence_score should reflect how complete the evidence is (0.0-1.0).
5. If confidence_score < 0.7, set needs_human_review=true.

Source documents:
{documents}

Respond ONLY with valid JSON matching the HistoryExtractionResult schema.
"""

TIMELINE_EXTRACTION_PROMPT = """
You are an expert at extracting project timeline events from workplace communications.

Given the following documents, extract result-oriented timeline events.
Focus on OUTCOMES and COMPLETIONS, not discussions.

Examples of timeline events:
- Feature X confirmed/completed
- Deployment to production
- QA passed
- Client request accepted
- Deadline changed
- Major decision finalized

For each event:
- title: what happened (result-focused)
- result_summary: one sentence describing the outcome
- event_time: when it happened (ISO8601 if known)

CRITICAL RULES:
1. Every event MUST have at least one source_link.
2. Only include events that actually happened (not planned).
3. If confidence_score < 0.7, set needs_human_review=true.

Source documents:
{documents}

Respond ONLY with valid JSON matching the TimelineExtractionResult schema.
"""

TODO_EXTRACTION_PROMPT = """
You are an expert at extracting actionable tasks from workplace communications.

Given the following documents, extract all action items / todos.

For each todo:
- title: clear, actionable task description
- assignee: who is responsible (email if mentioned)
- due_date: deadline in ISO8601 format if mentioned
- priority: critical/high/medium/low based on context
- priority_reason: brief explanation of why this priority level
- blocker: true if this is blocking other work
- needs_approval: true if this needs a decision-maker to sign off

CRITICAL RULES:
1. Every todo MUST have at least one source_link proving it was actually requested.
2. Do NOT create todos that are not explicitly mentioned in the sources.
3. If confidence_score < 0.7, set needs_human_review=true.

Source documents:
{documents}

Respond ONLY with valid JSON matching the TodoExtractionResult schema.
"""

PROJECT_MAPPING_PROMPT = """
You are an expert at identifying which project a set of communications belongs to.

Given:
1. A new batch of documents/messages
2. A list of existing projects with their names, keywords, participants, and descriptions

Determine:
- Does this content belong to an existing project? (matched_project_id)
- If not, suggest a new project candidate

Consider:
- Project name mentions
- Participant overlap
- Keyword similarity
- Timeline overlap
- Shared documents

CRITICAL RULES:
1. Only match if match_confidence >= 0.75. Below that, create a new project candidate.
2. New project candidate always needs human review.

Existing projects:
{existing_projects}

New documents:
{documents}

Respond ONLY with valid JSON matching the ProjectMappingResult schema.
"""

PRIORITY_DECISION_PROMPT = """
You are an expert at prioritizing work items based on business context.

Given the following todo item and its context, assign a priority score and level.

Score each factor (0-10):
- deadline_urgency: how soon is this due?
- customer_impact: does this affect paying customers or external stakeholders?
- project_risk: does this affect project success?

Boolean factors:
- decision_maker_needed: does this require C-level or manager approval?
- is_blocker: is this blocking other work?
- needs_consensus: does this need team agreement?
- external_collaboration: does this involve external parties?
- c_level_report: does this need to be reported to senior leadership?

Final priority_score = weighted sum (0-100).
priority: critical (80+), high (60-79), medium (40-59), low (<40).

Todo: {todo}
Project context: {project_context}

Respond ONLY with valid JSON matching the PriorityDecisionResult schema.
"""

VALIDATION_PROMPT = """
You are a quality assurance agent for AI-generated workplace summaries.

Check the following AI-generated content for:
1. Faithfulness: Does every claim trace back to the provided sources?
2. Hallucination: Are there any claims NOT supported by sources?
3. Source validation: Does every item have a valid source_link?
4. Completeness: Is important context missing?

faithfulness_score: 0.0-1.0 (1.0 = fully supported by sources)
hallucination_detected: true if ANY claim is not in the sources
source_validation_passed: true if ALL items have at least one source_link
recommendation: "approve" if valid, "reject" if hallucination detected, "needs_review" otherwise

Content to validate:
{content}

Source documents:
{sources}

Respond ONLY with valid JSON matching the ValidationResult schema.
"""
