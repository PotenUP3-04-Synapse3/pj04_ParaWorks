'use client'

import { useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useEffect } from 'react'

interface GraphNode {
  id: string
  label: string
  node_type: string
  data: Record<string, unknown>
}

interface GraphEdge {
  id: string
  source: string
  target: string
  edge_type: string
  label?: string
}

interface KnowledgeMapResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  total_nodes: number
  total_edges: number
}

const NODE_COLORS: Record<string, string> = {
  project: '#3b82f6',
  decision: '#8b5cf6',
  history: '#10b981',
}

function buildFlowNodes(nodes: GraphNode[]): Node[] {
  return nodes.map((n, i) => ({
    id: n.id,
    type: 'default',
    position: {
      x: 200 + (i % 4) * 240,
      y: Math.floor(i / 4) * 160 + 60,
    },
    data: { label: n.label },
    style: {
      background: NODE_COLORS[n.node_type] ?? '#6b7280',
      color: '#fff',
      border: 'none',
      borderRadius: '10px',
      padding: '8px 14px',
      fontSize: '12px',
      maxWidth: '180px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
    },
  }))
}

function buildFlowEdges(edges: GraphEdge[]): Edge[] {
  return edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: e.edge_type === 'similar_to',
    style: {
      stroke: e.edge_type === 'similar_to' ? '#f59e0b' : '#94a3b8',
      strokeWidth: 1.5,
    },
    labelStyle: { fontSize: 10, fill: '#64748b' },
  }))
}

export default function KnowledgeMapPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  const { data, isLoading } = useQuery<KnowledgeMapResponse>({
    queryKey: ['knowledge-map'],
    queryFn: () => api.get<KnowledgeMapResponse>('/knowledge-map'),
  })

  useEffect(() => {
    if (!data) return
    setNodes(buildFlowNodes(data.nodes))
    setEdges(buildFlowEdges(data.edges))
  }, [data, setNodes, setEdges])

  return (
    <div className="flex flex-col h-screen">
      <div className="flex items-center justify-between px-6 py-4 bg-white border-b">
        <div>
          <h1 className="text-xl font-bold text-gray-900">지식 맵</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            프로젝트 · 의사결정 · 히스토리 연결 관계
          </p>
        </div>
        {data && (
          <div className="flex gap-4 text-sm text-gray-500">
            <div className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-full bg-blue-500" />노드 {data.total_nodes}
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-full bg-gray-400" />연결 {data.total_edges}
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex gap-4 px-6 py-2 bg-white border-b text-xs text-gray-500">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
            {type === 'project' ? '프로젝트' : type === 'decision' ? '의사결정' : '히스토리'}
          </div>
        ))}
        <div className="flex items-center gap-1.5">
          <span className="h-px w-5 bg-yellow-500" />유사 사례
        </div>
      </div>

      {isLoading && (
        <div className="flex-1 flex items-center justify-center text-gray-400">
          지식 맵 로딩 중...
        </div>
      )}

      {!isLoading && data?.total_nodes === 0 && (
        <div className="flex-1 flex items-center justify-center text-gray-400">
          <div className="text-center">
            <p className="text-lg mb-1">표시할 데이터가 없습니다</p>
            <p className="text-sm">프로젝트와 의사결정이 추가되면 여기에 표시됩니다</p>
          </div>
        </div>
      )}

      {!isLoading && data && data.total_nodes > 0 && (
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            nodesDraggable
            nodesConnectable={false}
          >
            <Background gap={20} size={1} />
            <Controls />
            <MiniMap nodeColor={(n) => (n.style?.background as string) ?? '#94a3b8'} />
          </ReactFlow>
        </div>
      )}
    </div>
  )
}
