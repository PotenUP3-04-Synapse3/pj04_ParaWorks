"""GitHub connector — webhook event handling and API calls."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from github import Github, GithubException

logger = logging.getLogger(__name__)


def get_client(token: str) -> Github:
    return Github(token)


def get_pull_request(token: str, repo_full_name: str, pr_number: int) -> Dict:
    g = get_client(token)
    try:
        repo = g.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        return {
            'id': pr.id,
            'number': pr.number,
            'title': pr.title,
            'body': pr.body or '',
            'state': pr.state,
            'user': {'login': pr.user.login},
            'html_url': pr.html_url,
            'created_at': pr.created_at.isoformat(),
            'requested_reviewers': [{'login': r.login} for r in pr.requested_reviewers],
            'type': 'pull_request',
            'comments': [
                {'body': c.body, 'user': c.user.login}
                for c in pr.get_review_comments()
            ],
        }
    except GithubException as e:
        logger.error('Failed to fetch PR %s#%d: %s', repo_full_name, pr_number, e)
        return {}


def get_issue(token: str, repo_full_name: str, issue_number: int) -> Dict:
    g = get_client(token)
    try:
        repo = g.get_repo(repo_full_name)
        issue = repo.get_issue(issue_number)
        return {
            'id': issue.id,
            'number': issue.number,
            'title': issue.title,
            'body': issue.body or '',
            'state': issue.state,
            'user': {'login': issue.user.login},
            'html_url': issue.html_url,
            'created_at': issue.created_at.isoformat(),
            'type': 'issue',
        }
    except GithubException as e:
        logger.error('Failed to fetch issue %s#%d: %s', repo_full_name, issue_number, e)
        return {}
