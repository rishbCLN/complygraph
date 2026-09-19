"use client";

import { DataNode, type GraphNodeData } from "@/components/data-node";
import { ErrorState, Spinner } from "@/components/panel";
import { PageHeader } from "@/components/ui";
import { cn } from "@/lib/format";
import { useDataGraph } from "@/lib/queries";
import type { DataGraph, GraphEdge, GraphNode } from "@/lib/types";
import {
  Background,
  Controls,
  type Edge,
  type Node,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo, useState } from "react";

type Filters = {
  personalOnly: boolean;
  crossBorder: boolean;
  thirdParty: boolean;
  vendorsOnly: boolean;
};

const nodeTypes = { data: DataNode };

// Layered left-to-right layout: nodes with no inbound edge start at layer 0,
// each downstream node sits one layer to the right of its deepest source.
function layout(nodes: GraphNode[], edges: GraphEdge[]) {
  const incoming = new Map<string, string[]>();
  const nodeIds = new Set(nodes.map((n) => n.id));
  for (const e of edges) {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) continue;
    incoming.set(e.target, [...(incoming.get(e.target) || []), e.source]);
  }
  const layerOf = new Map<string, number>();
  function depth(id: string, seen: Set<string>): number {
    if (layerOf.has(id)) return layerOf.get(id)!;
    if (seen.has(id)) return 0; // break cycles
    const parents = incoming.get(id) || [];
    if (parents.length === 0) {
      layerOf.set(id, 0);
      return 0;
    }
    const next = new Set(seen);
    next.add(id);
    const d = Math.max(...parents.map((p) => depth(p, next))) + 1;
    layerOf.set(id, d);
    return d;
  }
  nodes.forEach((n) => depth(n.id, new Set()));

  const byLayer = new Map<number, GraphNode[]>();
  nodes.forEach((n) => {
    const l = layerOf.get(n.id) ?? 0;
    byLayer.set(l, [...(byLayer.get(l) || []), n]);
  });

  const positions = new Map<string, { x: number; y: number }>();
  const COL = 260;
  const ROW = 110;
  Array.from(byLayer.keys())
    .sort((a, b) => a - b)
    .forEach((l) => {
      const col = byLayer.get(l)!;
      col.forEach((n, i) => {
        positions.set(n.id, {
          x: l * COL,
          y: i * ROW - ((col.length - 1) * ROW) / 2,
        });
      });
    });
  return positions;
}

function GraphInner({ data }: { data: DataGraph }) {
  const [filters, setFilters] = useState<Filters>({
    personalOnly: false,
    crossBorder: false,
    thirdParty: false,
    vendorsOnly: false,
  });

  const { nodes, edges } = useMemo(() => {
    let edgeSet = data.edges;
    if (filters.personalOnly) edgeSet = edgeSet.filter((e) => e.personal_data);
    if (filters.crossBorder) edgeSet = edgeSet.filter((e) => e.cross_border);
    if (filters.thirdParty)
      edgeSet = edgeSet.filter(
        (e) => e.flow_type === "PROCESSOR" || e.flow_type === "THIRD_PARTY",
      );

    // Keep only nodes touched by the (filtered) edge set, unless no edge filter
    // is active — then show everything.
    const anyEdgeFilter =
      filters.personalOnly || filters.crossBorder || filters.thirdParty;
    const touched = new Set<string>();
    edgeSet.forEach((e) => {
      touched.add(e.source);
      touched.add(e.target);
    });
    let nodeSet = data.nodes.filter((n) => {
      if (filters.vendorsOnly && n.kind !== "VENDOR") return false;
      if (anyEdgeFilter && !touched.has(n.id)) return false;
      return true;
    });
    if (filters.personalOnly && !anyEdgeFilter) {
      nodeSet = nodeSet.filter((n) => n.personal_data);
    }

    const visibleIds = new Set(nodeSet.map((n) => n.id));
    edgeSet = edgeSet.filter(
      (e) => visibleIds.has(e.source) && visibleIds.has(e.target),
    );

    const positions = layout(nodeSet, edgeSet);
    const rfNodes: Node<GraphNodeData>[] = nodeSet.map((n) => ({
      id: n.id,
      type: "data",
      position: positions.get(n.id) || { x: 0, y: 0 },
      data: {
        label: n.label,
        kind: n.kind,
        personal_data: n.personal_data,
        sensitivity_level: n.sensitivity_level,
        system: n.system,
        country: n.country,
        risk_level: n.risk_level,
      },
    }));
    const rfEdges: Edge[] = edgeSet.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.cross_border ? "cross-border" : e.relation.toLowerCase(),
      animated: e.personal_data,
      style: {
        stroke: e.cross_border ? "#ef4444" : e.personal_data ? "#f97316" : "#3b82f6",
        strokeWidth: e.sensitive ? 2 : 1.2,
        strokeDasharray: e.discovered ? "4 3" : undefined,
      },
      labelStyle: { fill: "#8b95a7", fontSize: 9 },
      labelBgStyle: { fill: "#111826" },
    }));
    return { nodes: rfNodes, edges: rfEdges };
  }, [data, filters]);

  const toggles: { key: keyof Filters; label: string }[] = [
    { key: "personalOnly", label: "Personal data only" },
    { key: "crossBorder", label: "Cross-border" },
    { key: "thirdParty", label: "Third party" },
    { key: "vendorsOnly", label: "Vendors only" },
  ];

  return (
    <div className="flex h-[calc(100vh-9rem)] flex-col">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {toggles.map((t) => (
          <button
            key={t.key}
            onClick={() => setFilters((f) => ({ ...f, [t.key]: !f[t.key] }))}
            className={cn(
              "rounded border px-2.5 py-1 text-xs transition-colors",
              filters[t.key]
                ? "border-accent bg-accent-2/15 text-fg"
                : "border-border bg-panel-2 text-muted hover:text-fg",
            )}
          >
            {t.label}
          </button>
        ))}
        {data.stats && (
          <div className="ml-auto flex items-center gap-3 text-xs text-muted">
            <span>{data.stats.assets} assets</span>
            <span>{data.stats.vendors} vendors</span>
            <span>{data.stats.flows} flows</span>
            <span className="text-critical">
              {data.stats.cross_border_flows} cross-border
            </span>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-hidden rounded-lg border border-border bg-panel-2">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#1f2937" gap={20} />
          <Controls className="!border-border !bg-panel" />
        </ReactFlow>
      </div>
    </div>
  );
}

export default function DataMapPage() {
  const { data, isLoading, isError } = useDataGraph();
  return (
    <>
      <PageHeader
        title="Data Map"
        description="How personal data moves across systems, applications, and vendors."
      />
      {isLoading ? (
        <Spinner label="Building data map…" />
      ) : isError || !data ? (
        <ErrorState message="Could not load the data map." />
      ) : data.nodes.length === 0 ? (
        <div className="flex h-64 items-center justify-center text-sm text-muted">
          No data assets discovered yet. Run a scan to populate the map.
        </div>
      ) : (
        <ReactFlowProvider>
          <GraphInner data={data} />
        </ReactFlowProvider>
      )}
    </>
  );
}
