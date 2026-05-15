from agent_slack.project_routing import (
    ProjectOption,
    build_project_tools,
    route_projects_for_candidates,
    score_project_aliases,
)


def test_project_alias_tool_ranks_registered_project() -> None:
    projects = [
        ProjectOption(
            project_key='project-alpha',
            name='Project Alpha',
            summary='Redis queue status and sync job reliability work',
        ),
        ProjectOption(
            project_key='project-kindergarten',
            name='유치원 등교',
            summary='개인 일정과 등교 안내',
        ),
    ]

    ranked = score_project_aliases(
        text='Redis queue 상태와 sync job 실패 복구 흐름을 논의했습니다.',
        projects=projects,
    )

    assert ranked[0]['project_key'] == 'project-alpha'
    assert ranked[0]['score'] > ranked[1]['score']


def test_project_tools_expose_registered_projects_as_json() -> None:
    projects = [
        ProjectOption(
            project_key='project-alpha',
            name='Project Alpha',
            summary='Redis queue status and sync job reliability work',
        )
    ]

    tools = build_project_tools(projects)
    tool_by_name = {tool.name: tool for tool in tools}

    assert 'list_registered_projects' in tool_by_name
    assert 'score_project_candidates' in tool_by_name
    assert 'project-alpha' in tool_by_name['list_registered_projects'].invoke({})


class FakeProjectRouterModel:
    model_name = 'fake-project-router'

    def invoke(self, payload):
        return {
            'decisions': [
                {
                    'source_id': 'C123:1777600800.000100',
                    'item_index': 0,
                    'project_key': 'project-alpha',
                    'project_name': 'Project Alpha',
                    'confidence_score': 0.86,
                    'assignment_summary': 'Redis 큐 상태와 동기화 안정성 개선 논의입니다.',
                    'assignment_reason': 'Redis, queue, sync job이 프로젝트 설명과 직접 일치합니다.',
                    'alternatives': [],
                    'needs_user_selection': False,
                }
            ],
            'input_tokens': 100,
            'output_tokens': 40,
            'model_name': 'fake-project-router',
        }


def test_route_projects_for_candidates_returns_llm_tool_decision() -> None:
    result = route_projects_for_candidates(
        model=FakeProjectRouterModel(),
        projects=[
            ProjectOption(
                project_key='project-alpha',
                name='Project Alpha',
                summary='Redis queue status and sync job reliability work',
            )
        ],
        candidates=[
            {
                'item_index': 0,
                'source_id': 'C123:1777600800.000100',
                'title': 'Redis 큐 상태 확인',
                'summary': 'Redis 큐와 동기화 작업 상태를 확인했습니다.',
                'source_snippets': ['Redis queue 상태를 확인하고 sync job을 복구합니다.'],
            }
        ],
    )

    assert result.decisions[0].project_key == 'project-alpha'
    assert result.decisions[0].assignment_summary
    assert result.input_tokens == 100
