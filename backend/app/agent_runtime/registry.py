from backend.app.agent_runtime.contracts import AgentManifest


class AgentRegistry:
    def __init__(self) -> None:
        self._manifests: dict[str, AgentManifest] = {}

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._manifests)

    def register(self, manifest: AgentManifest) -> None:
        if manifest.name in self._manifests:
            raise ValueError(f'agent already registered: {manifest.name}')
        self._manifests[manifest.name] = manifest

    def get(self, name: str) -> AgentManifest:
        return self._manifests[name]

    def find_by_capability(self, capability: str) -> list[AgentManifest]:
        return [
            manifest
            for manifest in self._manifests.values()
            if capability in manifest.capabilities
        ]
