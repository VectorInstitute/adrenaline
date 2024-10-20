'use client'

import React, { useCallback } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

const initialNodes: Node[] = [
  {
    id: 'user-query',
    type: 'input',
    data: { label: 'User Query' },
    position: { x: 400, y: 0 },
    style: { backgroundColor: '#f0f0f0', width: 180, borderRadius: '12px', padding: '15px', fontWeight: 'bold', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
  {
    id: 'rag-system',
    type: 'default',
    data: { label: 'RAG System' },
    position: { x: 400, y: 120 },
    style: { backgroundColor: '#e6f3ff', width: 180, height: 80, borderRadius: '12px', padding: '15px', fontWeight: 'bold', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
  {
    id: 'retrieval',
    type: 'default',
    data: { label: 'Context Retrieval' },
    position: { x: 400, y: 240 },
    style: { backgroundColor: '#d1e7ff', width: 180, height: 80, borderRadius: '12px', padding: '15px', fontWeight: 'bold', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
  {
    id: 'general-sources',
    type: 'default',
    data: { label: 'General Medical Sources' },
    position: { x: 100, y: 360 },
    style: { backgroundColor: '#c2e0ff', width: 200, height: 90, borderRadius: '12px', padding: '15px', fontWeight: 'bold', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
  {
    id: 'umls',
    type: 'default',
    data: { label: 'UMLS Metathesaurus' },
    position: { x: 0, y: 500 },
    style: { backgroundColor: '#99ccff', width: 180, borderRadius: '12px', padding: '15px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
  {
    id: 'pubmed',
    type: 'default',
    data: { label: 'PubMed Central' },
    position: { x: 220, y: 500 },
    style: { backgroundColor: '#80b3ff', width: 180, borderRadius: '12px', padding: '15px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
  {
    id: 'patient-sources',
    type: 'default',
    data: { label: 'Patient-Specific Sources' },
    position: { x: 700, y: 360 },
    style: { backgroundColor: '#c2e0ff', width: 200, height: 90, borderRadius: '12px', padding: '15px', fontWeight: 'bold', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
  {
    id: 'ehr',
    type: 'default',
    data: { label: 'EHR Data' },
    position: { x: 600, y: 500 },
    style: { backgroundColor: '#b3ffcc', width: 140, borderRadius: '12px', padding: '15px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
  {
    id: 'radiology',
    type: 'default',
    data: { label: 'Radiology Images' },
    position: { x: 780, y: 500 },
    style: { backgroundColor: '#b3e6ff', width: 140, borderRadius: '12px', padding: '15px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
  {
    id: 'notes',
    type: 'default',
    data: { label: 'Patient Notes' },
    position: { x: 690, y: 600 },
    style: { backgroundColor: '#ccffcc', width: 140, borderRadius: '12px', padding: '15px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
  {
    id: 'llm',
    type: 'default',
    data: { label: 'Multi-Modal LLM' },
    position: { x: 400, y: 680 },
    style: { backgroundColor: '#a3c2c2', width: 220, height: 90, borderRadius: '12px', padding: '15px', fontWeight: 'bold', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
  {
    id: 'answer',
    type: 'output',
    data: { label: 'Generated Answer' },
    position: { x: 400, y: 820 },
    style: { backgroundColor: '#99ffcc', width: 180, borderRadius: '12px', padding: '15px', fontWeight: 'bold', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' },
  },
];

const initialEdges: Edge[] = [
  { id: 'e1', source: 'user-query', target: 'rag-system', animated: true, style: { stroke: '#888' }, type: 'smoothstep' },
  { id: 'e2', source: 'rag-system', target: 'retrieval', animated: true, style: { stroke: '#888' }, type: 'smoothstep' },
  { id: 'e3', source: 'retrieval', target: 'general-sources', style: { stroke: '#888' }, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed }, markerStart: { type: MarkerType.ArrowClosed } },
  { id: 'e4', source: 'retrieval', target: 'patient-sources', style: { stroke: '#888' }, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed }, markerStart: { type: MarkerType.ArrowClosed } },
  { id: 'e5', source: 'general-sources', target: 'umls', style: { stroke: '#99ccff' }, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed }, markerStart: { type: MarkerType.ArrowClosed } },
  { id: 'e6', source: 'general-sources', target: 'pubmed', style: { stroke: '#80b3ff' }, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed }, markerStart: { type: MarkerType.ArrowClosed } },
  { id: 'e7', source: 'patient-sources', target: 'ehr', style: { stroke: '#b3ffcc' }, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed }, markerStart: { type: MarkerType.ArrowClosed } },
  { id: 'e8', source: 'patient-sources', target: 'radiology', style: { stroke: '#b3e6ff' }, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed }, markerStart: { type: MarkerType.ArrowClosed } },
  { id: 'e9', source: 'patient-sources', target: 'notes', style: { stroke: '#ccffcc' }, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed }, markerStart: { type: MarkerType.ArrowClosed } },
  { id: 'e11', source: 'umls', target: 'llm', style: { stroke: '#99ccff' }, type: 'smoothstep' },
  { id: 'e12', source: 'pubmed', target: 'llm', style: { stroke: '#80b3ff' }, type: 'smoothstep' },
  { id: 'e13', source: 'ehr', target: 'llm', style: { stroke: '#b3ffcc' }, type: 'smoothstep' },
  { id: 'e14', source: 'radiology', target: 'llm', style: { stroke: '#b3e6ff' }, type: 'smoothstep' },
  { id: 'e15', source: 'notes', target: 'llm', style: { stroke: '#ccffcc' }, type: 'smoothstep' },
  { id: 'e17', source: 'llm', target: 'answer', animated: true, style: { stroke: '#888' }, type: 'smoothstep' },
];

const AdrenalineAIArchitecture: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  return (
    <div style={{ width: '100%', height: '920px', border: '1px solid #ddd', borderRadius: '12px', overflow: 'hidden' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
        minZoom={0.5}
        maxZoom={1.5}
      >
        <Controls />
        <Background color="#f8f8f8" gap={16} />
      </ReactFlow>
    </div>
  );
};

export default AdrenalineAIArchitecture;
