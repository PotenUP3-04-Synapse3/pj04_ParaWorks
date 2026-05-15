from backend.app.agent_runtime.project_routing import (
    ProjectOption,
    ProjectRoutingCandidate,
    ProjectRoutingDecision,
    ProjectRoutingResult,
    apply_project_routing_to_payload,
    route_projects_for_candidates,
    score_project_aliases,
)


class FakeProjectRouter:
    def __init__(self) -> None:
        self.payload: dict | None = None

    def invoke(self, payload: dict) -> dict:
        self.payload = payload
        return {
            'model_name': 'fake-project-router',
            'input_tokens': 17,
            'output_tokens': 9,
            'decisions': [
                {
                    'source_id': 'gmail:message-1|gmail_attachment:message-1:att-1',
                    'item_index': 0,
                    'project_key': 'project-alpha',
                    'project_name': 'Project Alpha',
                    'confidence_score': 0.88,
                    'assignment_summary': 'The email thread and attachment match Project Alpha.',
                    'assignment_reason': 'The evidence mentions the Project Alpha rollout and attached plan.',
                    'alternatives': ['project-beta'],
                    'needs_user_selection': False,
                },
                {
                    'source_id': 'drive:file-unknown',
                    'item_index': 1,
                    'project_key': None,
                    'project_name': None,
                    'confidence_score': 0.39,
                    'assignment_summary': 'No registered project can be selected confidently.',
                    'assignment_reason': 'The Drive file does not match registered project names or summaries.',
                    'alternatives': ['project-alpha'],
                    'needs_user_selection': True,
                },
            ],
        }


def test_shared_project_router_routes_each_candidate_and_keeps_unmatched_empty() -> None:
    router = FakeProjectRouter()
    projects = [
        ProjectOption(project_key='project-alpha', name='Project Alpha', summary='Rollout plan'),
        ProjectOption(project_key='project-beta', name='Project Beta', summary='Billing migration'),
    ]
    candidates = [
        ProjectRoutingCandidate(
            item_index=0,
            source_id='gmail:message-1|gmail_attachment:message-1:att-1',
            title='Project Alpha rollout follow-up',
            summary='The customer asked for the rollout plan.',
            item_type='todo',
            source_type='mail_document',
            source_links=['https://mail.google.com/mail/u/0/#inbox/message-1'],
            source_snippets=['Project Alpha rollout plan is attached.'],
            evidence_text='Project Alpha rollout plan is attached.',
            confidence_score=0.84,
        ),
        ProjectRoutingCandidate(
            item_index=1,
            source_id='drive:file-unknown',
            title='General office policy',
            summary='The file does not name a registered project.',
            item_type='history_event',
            source_type='mail_document',
            source_links=['https://drive.google.com/file/d/file-unknown/view'],
            source_snippets=['General policy update.'],
            evidence_text='General policy update.',
            confidence_score=0.72,
        ),
    ]

    result = route_projects_for_candidates(model=router, projects=projects, candidates=candidates)

    assert isinstance(result, ProjectRoutingResult)
    assert result.model_name == 'fake-project-router'
    assert result.input_tokens == 17
    assert result.output_tokens == 9
    assert router.payload is not None
    assert router.payload['projects_count'] == 2
    assert router.payload['candidate_items'][0]['source_type'] == 'mail_document'
    assert [decision.item_index for decision in result.decisions] == [0, 1]
    assert result.decisions[0].project_key == 'project-alpha'
    assert result.decisions[1].project_key is None
    assert result.decisions[1].needs_user_selection is True


def test_project_routing_payload_helper_clears_project_when_user_selection_needed() -> None:
    payload = {
        'agent_name': 'mail_document_agent',
        'project_key': 'legacy-project',
        'project_name': 'Legacy Project',
    }
    decision = ProjectRoutingDecision(
        source_id='drive:file-unknown',
        item_index=0,
        project_key=None,
        project_name=None,
        confidence_score=0.41,
        assignment_summary='A reviewer must select the project.',
        assignment_reason='Registered project evidence is insufficient.',
        alternatives=['project-alpha'],
        needs_user_selection=True,
    )

    updated = apply_project_routing_to_payload(payload, decision)

    assert updated['agent_name'] == 'mail_document_agent'
    assert updated['project_assignment_method'] == 'llm_tool'
    assert updated['project_assignment_confidence'] == 0.41
    assert updated['project_alternatives'] == ['project-alpha']
    assert updated['project_needs_user_selection'] is True
    assert 'project_key' not in updated
    assert 'project_name' not in updated


def test_project_alias_scoring_respects_word_boundaries() -> None:
    projects = [
        ProjectOption(
            project_key='seed-ir',
            name='Seed IR',
            summary='Investor meeting and fundraising deck',
        )
    ]

    unrelated = score_project_aliases('The office has a bird feeder issue.', projects)
    related = score_project_aliases('Seed IR investor meeting deck review is due.', projects)

    assert unrelated[0]['score'] == 0.0
    assert related[0]['score'] > unrelated[0]['score']
