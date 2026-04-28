'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/authStore';
import { knowledgeMapApi } from '@/lib/api/knowledgeMap';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type NodeTypes,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { KnowledgeMapNode } from '@/lib/types/api';
import { useMemo, useCallback } from 'react';

// 노드 타입별 색상
const nodeColor: Record<string, string> = {
  decision: '#3b82f6',
  knowledge_asset: '#22c55e',
  document: '#94a3b8',
};

function DecisionNode({ data }: { data: KnowledgeMapNode['data'] }) {
  return (
    <div className="px-3 py-2 rounded-lg border-2 border-blue-400 bg-blue-50 text-xs font-medium text-blue-800 max-w-[140px] text-center">
      {data.label}
    </div>
  );
}

function KnowledgeAssetNode({ data }: { data: KnowledgeMapNode['data'] }) {
  return (
    <div className="px-3 py-2 rounded-lg border-2 border-green-400 bg-green-50 text-xs font-medium text-green-800 max-w-[140px] text-center">
      {data.label}
    </div>
  );
}

function DocumentNode({ data }: { data: KnowledgeMapNode['data'] }) {
  return (
    <div className="px-3 py-2 rounded-lg border-2 border-gray-300 bg-gray-50 text-xs font-medium text-gray-600 max-w-[140px] text-center">
      {data.label}
    </div>
  );
}

const nodeTypes: NodeTypes = {
  decision: DecisionNode as NodeTypes[string],
  knowledge_asset: KnowledgeAssetNode as NodeTypes[string],
  document: DocumentNode as NodeTypes[string],
};

// 간단한 그리드 레이아웃 (서버에서 x=0,y=0 반환하므로 클라이언트 배치)
function applyLayout(nodes: Node[]): Node[] {
  const grouped: Record<string, Node[]> = {};
  nodes.forEach((n) => {
    const t = n.type ?? 'document';
    if (!grouped[t]) grouped[t] = [];
    grouped[t].push(n);
  });

  const colOrder = ['decision', 'knowledge_asset', 'document'];
  const result: Node[] = [];
  colOrder.forEach((type, colIdx) => {
    (grouped[type] ?? []).forEach((node, rowIdx) => {
      result.push({
        ...node,
        position: { x: colIdx * 220, y: rowIdx * 90 },
      });
    });
  });
  return result;
}

export default function KnowledgeMapPage() {
  const user = useAuthStore((s) => s.user);
  const orgId = user?.organization_id ?? '';

  const { data, isLoading } = useQuery({
    queryKey: ['knowledge-map', orgId],
    queryFn: () => knowledgeMapApi.get(orgId),
    enabled: !!orgId,
  });

  const nodes: Node[] = useMemo(
    () => applyLayout((data?.nodes ?? []) as Node[]),
    [data],
  );
  const edges: Edge[] = useMemo(() => (data?.edges ?? []) as Edge[], [data]);

  const nodeColor2 = useCallback((node: Node) => {
    return nodeColor[node.type ?? 'document'] ?? '#94a3b8';
  }, []);

  if (isLoading) {
    return <p className="text-sm text-gray-500">지식 맵을 불러오는 중...</p>;
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">지식 맵</h1>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-blue-400 inline-block" /> 의사결정
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-green-400 inline-block" /> 지식자산
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-gray-300 inline-block" /> 문서
          </span>
        </div>
      </div>

      <div className="flex-1 rounded-xl border border-gray-200 overflow-hidden bg-white">
        {nodes.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-400 text-sm">
            연결된 지식 데이터가 없습니다.
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            className="bg-gray-50"
          >
            <Background />
            <Controls />
            <MiniMap nodeColor={nodeColor2} className="!bg-white" />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
