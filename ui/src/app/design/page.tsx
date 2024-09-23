'use client';

import React from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap
} from 'reactflow';
import 'reactflow/dist/style.css';

const ArchitectureDiagram: React.FC = () => {
  const nodes: Node[] = [
    {
      id: 'frontend',
      data: { label: 'Frontend (Next.js)' },
      position: { x: 250, y: 0 },
      type: 'input',
    },
    {
      id: 'backend',
      data: { label: 'Backend (FastAPI)' },
      position: { x: 250, y: 100 },
    },
    {
      id: 'clinical-ner',
      data: { label: 'Clinical NER Service' },
      position: { x: 0, y: 200 },
    },
    {
      id: 'embedding',
      data: { label: 'Embedding Service' },
      position: { x: 250, y: 200 },
    },
    {
      id: 'mongodb',
      data: { label: 'MongoDB' },
      position: { x: 500, y: 200 },
    },
    {
      id: 'milvus',
      data: { label: 'Milvus' },
      position: { x: 250, y: 300 },
    },
    {
      id: 'etcd',
      data: { label: 'etcd' },
      position: { x: 100, y: 400 },
    },
    {
      id: 'minio',
      data: { label: 'MinIO' },
      position: { x: 400, y: 400 },
    },
  ];

  const edges: Edge[] = [
    { id: 'f-b', source: 'frontend', target: 'backend' },
    { id: 'b-c', source: 'backend', target: 'clinical-ner' },
    { id: 'b-e', source: 'backend', target: 'embedding' },
    { id: 'b-m', source: 'backend', target: 'mongodb' },
    { id: 'b-mv', source: 'backend', target: 'milvus' },
    { id: 'mv-e', source: 'milvus', target: 'etcd' },
    { id: 'mv-mi', source: 'milvus', target: 'minio' },
  ];

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
};

export default ArchitectureDiagram;
