import json
from decimal import Decimal
from hashlib import sha256

from backend.app.agent_runtime.contracts import (
    AgentCostBudgetDecision,
    AgentRunCost,
    EvidencePacket,
    TokenUsage,
)


def build_evidence_cache_key(packet: EvidencePacket, prompt_version: str) -> str:
    payload = {
        'prompt_version': prompt_version,
        'source_type': packet.source_type,
        'source_window': packet.source_window,
        'messages': [
            {
                'source_id': message.source_id,
                'source_url': message.source_url,
                'text': message.text,
                'timestamp': message.timestamp,
                'permission_level': message.permission_level,
            }
            for message in packet.messages
        ],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return sha256(serialized.encode('utf-8')).hexdigest()


def estimate_agent_run_cost(
    *,
    model_name: str,
    token_usage: TokenUsage,
    input_cost_per_1m: float,
    output_cost_per_1m: float,
    cache_hit: bool,
) -> AgentRunCost:
    input_cost = Decimal(token_usage.input_tokens) * Decimal(str(input_cost_per_1m))
    output_cost = Decimal(token_usage.output_tokens) * Decimal(str(output_cost_per_1m))
    estimated_cost = (input_cost + output_cost) / Decimal(1_000_000)

    return AgentRunCost(
        model_name=model_name,
        token_usage=token_usage,
        estimated_cost_usd=float(estimated_cost),
        cache_hit=cache_hit,
    )


def evaluate_agent_cost_budget(
    *,
    model_name: str,
    token_usage: TokenUsage,
    input_cost_per_1m: float,
    output_cost_per_1m: float,
    max_cost_usd: float | None,
    cache_hit: bool,
) -> AgentCostBudgetDecision:
    estimated_cost = estimate_agent_run_cost(
        model_name=model_name,
        token_usage=token_usage,
        input_cost_per_1m=input_cost_per_1m,
        output_cost_per_1m=output_cost_per_1m,
        cache_hit=cache_hit,
    )

    if cache_hit:
        return AgentCostBudgetDecision(
            action='use_cache',
            reason='cache_hit',
            budget_status='cached',
            model_name=model_name,
            token_usage=token_usage,
            estimated_cost_usd=estimated_cost.estimated_cost_usd,
            budget_limit_usd=max_cost_usd,
            cache_hit=True,
        )

    if max_cost_usd is not None and estimated_cost.estimated_cost_usd > max_cost_usd:
        return AgentCostBudgetDecision(
            action='skip',
            reason='budget_exceeded',
            budget_status='over_budget',
            model_name=model_name,
            token_usage=token_usage,
            estimated_cost_usd=estimated_cost.estimated_cost_usd,
            budget_limit_usd=max_cost_usd,
            cache_hit=False,
        )

    return AgentCostBudgetDecision(
        action='run',
        reason='within_budget',
        budget_status='within_budget',
        model_name=model_name,
        token_usage=token_usage,
        estimated_cost_usd=estimated_cost.estimated_cost_usd,
        budget_limit_usd=max_cost_usd,
        cache_hit=False,
    )
