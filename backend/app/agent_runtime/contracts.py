from dataclasses import dataclass, field

_PERMISSION_RANK = {
    'public': 0,
    'internal': 1,
    'restricted': 2,
}


@dataclass(frozen=True)
class PermissionContext:
    user_id: str
    role: str
    allowed_permission_levels: tuple[str, ...] = ('public', 'internal')


@dataclass(frozen=True)
class EvidenceMessage:
    source_id: str
    source_url: str
    text: str
    author: str | None
    timestamp: str
    permission_level: str
    metadata: dict = field(default_factory=dict)
    source_snippet_override: str | None = None

    @property
    def source_snippet(self) -> str:
        if self.source_snippet_override:
            return self.source_snippet_override
        return self.text[:240]


@dataclass(frozen=True)
class EvidencePacket:
    source_type: str
    source_window: str
    messages: list[EvidenceMessage]
    permission_context: PermissionContext

    @property
    def strictest_permission(self) -> str:
        levels = [message.permission_level for message in self.messages]
        if not levels:
            return 'internal'
        return max(levels, key=lambda level: _PERMISSION_RANK.get(level, 1))

    @property
    def source_links(self) -> list[str]:
        return [message.source_url for message in self.messages]

    @property
    def source_ids(self) -> list[str]:
        return [message.source_id for message in self.messages]

    @property
    def source_snippets(self) -> list[str]:
        return [message.source_snippet for message in self.messages]


@dataclass(frozen=True)
class ReviewCandidate:
    item_type: str
    title: str
    summary: str
    source_links: list[str]
    source_snippets: list[str]
    confidence_score: float
    permission_level: str
    uncertainty_reason: str | None = None

    def validate_evidence(self) -> None:
        if not self.source_links or not self.source_snippets:
            raise ValueError('review candidate requires source evidence')


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class AgentRunCost:
    model_name: str
    token_usage: TokenUsage
    estimated_cost_usd: float
    cache_hit: bool


@dataclass(frozen=True)
class AgentRunResult:
    agent_name: str
    prompt_version: str
    candidates: list[ReviewCandidate]
    cost: AgentRunCost
    cache_key: str


@dataclass(frozen=True)
class AgentManifest:
    name: str
    owner: str
    input_contract: str
    output_contract: str
    prompt_versions: tuple[str, ...]
    supported_permissions: tuple[str, ...]
    capabilities: tuple[str, ...]
