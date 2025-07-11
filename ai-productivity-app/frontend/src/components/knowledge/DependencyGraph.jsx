// Interactive dependency graph visualization using D3.js
import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { searchAPI } from "../../api/search";
import LoadingSpinner from "../common/LoadingSpinner";

export default function DependencyGraph({
  projectId,
  width = 800,
  height = 600,
}) {
  const svgRef = useRef(null);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    fetchGraphData();
  }, [projectId]);

  useEffect(() => {
    if (graphData && !loading) {
      renderGraph();
    }
  }, [graphData, loading]);

  const fetchGraphData = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await searchAPI.getDependencyGraph(projectId);
      setGraphData(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load dependency graph");
    } finally {
      setLoading(false);
    }
  };

  const renderGraph = () => {
    if (!graphData || !svgRef.current) return;

    const container = svgRef.current.parentElement;
    const w = container?.clientWidth || width;
    const h = container?.clientHeight || height;
    const nodeRadius = 8;

    // Clear previous graph
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3
      .select(svgRef.current)
      .attr("width", w)
      .attr("height", h)
      .attr("viewBox", [0, 0, w, h]);

    // Add zoom behavior
    const g = svg.append("g");

    svg.call(
      d3
        .zoom()
        .extent([
          [0, 0],
          [w, h],
        ])
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
        }),
    );

    // Create force simulation
    const simulation = d3
      .forceSimulation(graphData.nodes)
      .force(
        "link",
        d3
          .forceLink(graphData.edges)
          .id((d) => d.id)
          .distance(100),
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(w / 2, h / 2))
      .force("collision", d3.forceCollide().radius(nodeRadius + 2));

    // Create arrow marker for directed edges
    svg
      .append("defs")
      .selectAll("marker")
      .data(["arrow"])
      .join("marker")
      .attr("id", (d) => d)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("markerWidth", 8)
      .attr("markerHeight", 8)
      .attr("orient", "auto")
      .append("path")
      .attr("fill", "#999")
      .attr("d", "M0,-5L10,0L0,5");

    // Add links
    const link = g
      .append("g")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(graphData.edges)
      .join("line")
      .attr("stroke-width", 1)
      .attr("marker-end", "url(#arrow)");

    // Add nodes
    const node = g
      .append("g")
      .selectAll("circle")
      .data(graphData.nodes)
      .join("circle")
      .attr("r", nodeRadius)
      .attr("fill", (d) => getNodeColor(d.language))
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .style("cursor", "pointer")
      .call(drag(simulation));

    // Add labels
    const label = g
      .append("g")
      .selectAll("text")
      .data(graphData.nodes)
      .join("text")
      .text((d) => d.label)
      .attr("font-size", 12)
      .attr("dx", 15)
      .attr("dy", 4)
      .style("pointer-events", "none");

    // Add tooltips
    const tooltip = d3
      .select("body")
      .append("div")
      .attr("class", "dependency-graph-tooltip")
      .style("opacity", 0)
      .style("position", "absolute")
      .style("background", "rgba(0, 0, 0, 0.8)")
      .style("color", "white")
      .style("padding", "8px")
      .style("border-radius", "4px")
      .style("font-size", "12px");

    node
      .on("mouseover", (event, d) => {
        tooltip.transition().duration(200).style("opacity", 0.9);
        tooltip
          .html(
            `
        <strong>${d.file_path}</strong><br/>
        Type: ${d.type}<br/>
        Language: ${d.language}
      `,
          )
          .style("left", event.pageX + 10 + "px")
          .style("top", event.pageY - 28 + "px");
      })
      .on("mouseout", () => {
        tooltip.transition().duration(500).style("opacity", 0);
      })
      .on("click", (event, d) => {
        setSelectedNode(d);
      });

    // Update positions on tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);

      label.attr("x", (d) => d.x).attr("y", (d) => d.y);
    });

    // Cleanup tooltip on unmount
    return () => {
      d3.select("body").selectAll(".dependency-graph-tooltip").remove();
    };
  };

  const drag = (simulation) => {
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    return d3
      .drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended);
  };

  const getNodeColor = (language) => {
    const colors = {
      python: "#3776ab",
      javascript: "#f7df1e",
      typescript: "#3178c6",
      default: "#718096",
    };
    return colors[language] || colors.default;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <LoadingSpinner label="Loading dependency graph..." showLabel={true} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-12 w-12 text-red-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">
          Error loading graph
        </h3>
        <p className="mt-1 text-sm text-gray-500">{error}</p>
        <button
          onClick={fetchGraphData}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="dependency-graph">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Dependency Graph</h3>
        <div className="flex items-center space-x-4 text-sm">
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-blue-500 mr-2"></div>
            <span>Python</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-yellow-400 mr-2"></div>
            <span>JavaScript</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-blue-600 mr-2"></div>
            <span>TypeScript</span>
          </div>
        </div>
      </div>

      <div className="border border-gray-200 rounded-lg overflow-hidden w-full h-full">
        <svg ref={svgRef} className="w-full h-full"></svg>
      </div>

      {selectedNode && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <h4 className="font-medium text-gray-900">
            {selectedNode.file_path}
          </h4>
          <p className="text-sm text-gray-600 mt-1">
            Type: {selectedNode.type} | Language: {selectedNode.language}
          </p>
          {graphData.stats && (
            <p className="text-sm text-gray-500 mt-2">
              Dependencies:{" "}
              {
                graphData.edges.filter((e) => e.source === selectedNode.id)
                  .length
              }{" "}
              | Dependents:{" "}
              {
                graphData.edges.filter((e) => e.target === selectedNode.id)
                  .length
              }
            </p>
          )}
        </div>
      )}

      {graphData && (
        <div className="mt-4 text-sm text-gray-600">
          Total files: {graphData.stats.total_files} | Total dependencies:{" "}
          {graphData.stats.total_dependencies}
        </div>
      )}
    </div>
  );
}
