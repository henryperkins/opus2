/* eslint-env browser */
/* eslint-disable no-alert */
import { useRef, useEffect, useState, useCallback } from 'react';
import * as d3 from 'd3';
import PropTypes from 'prop-types';

import { codeAPI } from '../../api/code';
import { toast } from '../common/Toast';
import { useProjectTimeline } from '../../hooks/useProjects';

/**
 * Interactive SVG canvas with free-hand drawing, shape + text tools, zoom / pan,
 * and knowledge-base persistence.
 */
const InteractiveCanvas = ({ projectId, width = 800, height = 600 }) => {
  const svgRef = useRef(null);
  const { addEvent } = useProjectTimeline(projectId);

  /* ──────────────────────────── State ──────────────────────────── */
  const [tool, setTool] = useState('select');             // 'select' | 'draw'
  const [shapes, setShapes] = useState([]);               // drawn paths / rects
  const [annotations, setAnnotations] = useState([]);     // text labels
  const [isDrawing, setIsDrawing] = useState(false);
  const [selectedElement, setSelectedElement] = useState(null);
  const [showGrid, setShowGrid] = useState(true);
  const [savedArtifacts, setSavedArtifacts] = useState([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  /* ─────────────────────── Load saved artifacts ────────────────── */
  useEffect(() => {
    if (!projectId) return;
    (async () => {
      try {
        const { artifacts = [] } = await codeAPI.getCanvasArtifacts(projectId);
        setSavedArtifacts(artifacts);
        toast.success(`Loaded ${artifacts.length} saved artifacts`);
      } catch (err) {
        console.error(err);
        toast.error('Failed to load saved artifacts');
      }
    })();
  }, [projectId]);

  /* ──────────────────────────── Renderer ────────────────────────── */
  const renderShapes = useCallback(
    (group) => {
      group.selectAll('.shape').remove();

      shapes.forEach((shape) => {
        if (shape.type === 'path') {
          group
            .append('path')
            .attr('class', 'shape')
            .attr('d', shape.d)
            .attr('stroke', shape.stroke)
            .attr('stroke-width', shape.strokeWidth)
            .attr('fill', shape.fill)
            .style('cursor', 'pointer')
            .on('click', () => setSelectedElement(shape));
        } else if (shape.type === 'rect') {
          group
            .append('rect')
            .attr('class', 'shape')
            .attr('x', shape.x)
            .attr('y', shape.y)
            .attr('width', shape.width)
            .attr('height', shape.height)
            .attr('stroke', shape.stroke)
            .attr('stroke-width', shape.strokeWidth)
            .attr('fill', shape.fill)
            .style('cursor', 'pointer')
            .on('click', () => setSelectedElement(shape));
        }
      });

      group.selectAll('.annotation').remove();
      annotations.forEach((a) =>
        group
          .append('text')
          .attr('class', 'annotation')
          .attr('x', a.x)
          .attr('y', a.y)
          .attr('font-size', a.fontSize)
          .attr('fill', a.color)
          .text(a.text)
          .style('cursor', 'pointer')
          .on('click', () => setSelectedElement(a)),
      );
    },
    [shapes, annotations],
  );

  /* ──────────────────────────── Init / Grid / Zoom ──────────────── */
  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const gridSize = 20;

    /* Reset */
    svg.selectAll('*').remove();
    svg.on('.zoom', null).on('mousedown.draw mousemove.draw mouseup.draw', null);

    svg
      .attr('width', width)
      .attr('height', height)
      .style('border', '1px solid #e2e8f0')
      .style('background', '#ffffff');

    /* Grid */
    if (showGrid) {
      const defs = svg.append('defs');
      defs
        .append('pattern')
        .attr('id', 'grid')
        .attr('width', gridSize)
        .attr('height', gridSize)
        .attr('patternUnits', 'userSpaceOnUse')
        .append('path')
        .attr('d', `M ${gridSize} 0 L 0 0 0 ${gridSize}`)
        .attr('fill', 'none')
        .attr('stroke', '#f1f5f9')
        .attr('stroke-width', 1);

      svg.append('rect').attr('width', '100%').attr('height', '100%').attr('fill', 'url(#grid)');
    }

    /* Drawing layer */
    const drawingGroup = svg.append('g').attr('class', 'drawing-group');

    /* Zoom / pan */
    svg.call(
      d3
        .zoom()
        .scaleExtent([0.1, 5])
        .on('zoom', (event) => drawingGroup.attr('transform', event.transform)),
    );

    /* Draw-tool handlers */
    let pathStr = '';
    svg
      .on('mousedown.draw', (event) => {
        if (tool !== 'draw') return;
        const [x, y] = d3.pointer(event);
        pathStr = `M${x},${y}`;
        setIsDrawing(true);
      })
      .on('mousemove.draw', (event) => {
        if (!isDrawing || tool !== 'draw') return;
        const [x, y] = d3.pointer(event);
        pathStr += ` L${x},${y}`;

        drawingGroup.selectAll('.current-path').remove();
        drawingGroup
          .append('path')
          .attr('class', 'current-path')
          .attr('d', pathStr)
          .attr('stroke', '#3b82f6')
          .attr('stroke-width', 2)
          .attr('fill', 'none');
      })
      .on('mouseup.draw', () => {
        if (!isDrawing || tool !== 'draw') return;
        setIsDrawing(false);

        setShapes((s) => [
          ...s,
          {
            id: Date.now(),
            type: 'path',
            d: pathStr,
            stroke: '#3b82f6',
            strokeWidth: 2,
            fill: 'none',
          },
        ]);
        setHasUnsavedChanges(true);
        toast.success('Drawing saved to canvas');
      });

    /* Initial render */
    renderShapes(drawingGroup);
  }, [width, height, showGrid, tool, renderShapes]);

  /* ──────────────────────────── Helpers ─────────────────────────── */
  const addShape = (shapeType) => {
    setShapes((prev) => [
      ...prev,
      {
        id: Date.now(),
        type: shapeType,
        x: 100,
        y: 100,
        width: 100,
        height: 80,
        stroke: '#3b82f6',
        strokeWidth: 2,
        fill: 'rgba(59,130,246,0.1)',
      },
    ]);
    setHasUnsavedChanges(true);
    toast.success(`${shapeType} added to canvas`);
  };

  const addTextAnnotation = () => {
    const text = window.prompt('Enter text annotation:');
    if (!text) return;
    setAnnotations((prev) => [
      ...prev,
      {
        id: Date.now(),
        text,
        x: 200,
        y: 200,
        fontSize: 14,
        color: '#1f2937',
      },
    ]);
    setHasUnsavedChanges(true);
    toast.success('Text annotation added');
  };

  const clearCanvas = () => {
    if (hasUnsavedChanges && !window.confirm('Unsaved changes will be lost. Continue?')) return;
    setShapes([]);
    setAnnotations([]);
    setSelectedElement(null);
    setHasUnsavedChanges(false);
  };

  const saveToKnowledgeBase = async (name, description) => {
    setSaving(true);
    try {
      const serializer = new window.XMLSerializer();
      const svgContent = serializer.serializeToString(svgRef.current);

      const payload = {
        name,
        description,
        svgContent,
        shapes,
        annotations,
        metadata: {
          width,
          height,
          tool,
          showGrid,
          createdAt: new Date().toISOString(),
        },
      };

      const savedArtifact = await codeAPI.saveCanvasArtifact(projectId, payload);
      setSavedArtifacts((a) => [...a, savedArtifact]);
      setShowSaveDialog(false);
      setHasUnsavedChanges(false);

      await addEvent({
        event_type: 'canvas_created',
        title: `Canvas "${name}" created`,
        description,
        metadata: {
          canvas_name: name,
          shapes_count: shapes.length,
          annotations_count: annotations.length,
          artifact_id: savedArtifact?.id,
        },
      });

      toast.success(`Canvas "${name}" saved to knowledge base`);
    } catch (err) {
      console.error(err);
      toast.error(err?.response?.data?.detail ?? 'Failed to save canvas');
    } finally {
      setSaving(false);
    }
  };

  const loadArtifact = (artifact) => {
    setShapes(artifact.shapes || []);
    setAnnotations(artifact.annotations || []);
    setHasUnsavedChanges(false);
    toast.success(`Loaded "${artifact.name}"`);
  };

  const exportCanvas = () => {
    const serializer = new window.XMLSerializer();
    const source = serializer.serializeToString(svgRef.current);
    const blob = new window.Blob([source], { type: 'image/svg+xml' });
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'canvas-export.svg';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  /* ──────────────────────────── UI ─────────────────────────────── */
  return (
    <div className="interactive-canvas">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-4 bg-gray-50 border-b">
        <div className="flex items-center space-x-2">
          {hasUnsavedChanges && (
            <span className="flex items-center text-orange-600 text-xs mr-4">
              <span className="w-2 h-2 bg-orange-500 rounded-full mr-1" /> Unsaved changes
            </span>
          )}
          <button
            onClick={() => setTool('select')}
            className={`px-3 py-1 text-sm rounded ${
              tool === 'select' ? 'bg-blue-500 text-white' : 'bg-white border hover:bg-gray-50'
            }`}
          >
            Select
          </button>
          <button
            onClick={() => setTool('draw')}
            className={`px-3 py-1 text-sm rounded ${
              tool === 'draw' ? 'bg-blue-500 text-white' : 'bg-white border hover:bg-gray-50'
            }`}
          >
            Draw
          </button>
          <button
            onClick={() => addShape('rect')}
            className="px-3 py-1 text-sm bg-white border rounded hover:bg-gray-50"
          >
            Rectangle
          </button>
          <button
            onClick={addTextAnnotation}
            className="px-3 py-1 text-sm bg-white border rounded hover:bg-gray-50"
          >
            Text
          </button>
        </div>

        <div className="flex items-center space-x-2">
          {/* Artifact selector */}
          {savedArtifacts.length > 0 && (
            <select
              defaultValue=""
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
              onChange={(e) => {
                const art = savedArtifacts.find((a) => String(a.id) === e.target.value);
                if (art) loadArtifact(art);
              }}
            >
              <option value="">Load Artifact…</option>
              {savedArtifacts.map(({ id, name }) => (
                <option key={id} value={String(id)}>
                  {name}
                </option>
              ))}
            </select>
          )}

          <button
            onClick={() => setShowGrid((g) => !g)}
            className={`px-3 py-1 text-sm rounded ${
              showGrid ? 'bg-gray-200 text-gray-800' : 'bg-white border hover:bg-gray-50'
            }`}
          >
            Grid
          </button>
          <button
            disabled={saving}
            onClick={() => setShowSaveDialog(true)}
            className={`px-3 py-1 text-sm rounded flex items-center ${
              hasUnsavedChanges
                ? 'bg-orange-600 text-white hover:bg-orange-700'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            } disabled:opacity-50`}
          >
            {saving && (
              <svg
                className="animate-spin -ml-1 mr-1 h-3 w-3 text-white"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            )}
            {saving ? 'Saving…' : 'Save to KB'}
          </button>
          <button
            onClick={clearCanvas}
            className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
          >
            Clear
          </button>
          <button
            onClick={exportCanvas}
            className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
          >
            Export SVG
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="relative overflow-hidden">
        <svg
          ref={svgRef}
          className="w-full h-full cursor-crosshair"
          style={{ minHeight: '400px' }}
        />
        {isDrawing && (
          <span className="absolute top-2 left-2 px-2 py-1 bg-blue-500 text-white text-xs rounded">
            Drawing…
          </span>
        )}
      </div>

      {/* Properties panel */}
      {selectedElement && (
        <div className="p-4 bg-gray-50 border-t">
          <h4 className="font-medium text-gray-900 mb-2">Properties</h4>
          <div className="space-y-2 text-sm">
            <div>Type: {selectedElement.type}</div>
            {selectedElement.text && <div>Text: {selectedElement.text}</div>}
            <button
              onClick={() => {
                if (selectedElement.type === 'rect' || selectedElement.type === 'path') {
                  setShapes((s) => s.filter((sh) => sh.id !== selectedElement.id));
                } else {
                  setAnnotations((a) => a.filter((an) => an.id !== selectedElement.id));
                }
                setSelectedElement(null);
              }}
              className="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        </div>
      )}

      {/* Save dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 w-96 max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Save Canvas to Knowledge Base
            </h3>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                const data = new window.FormData(e.target);
                const name = data.get('name');
                const description = data.get('description');
                if (name) saveToKnowledgeBase(name, description);
              }}
            >
              <div className="space-y-4">
                <label className="block text-sm font-medium text-gray-700">
                  Name *
                  <input
                    name="name"
                    required
                    type="text"
                    placeholder="e.g., Architecture Diagram"
                    className="mt-1 w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
                  />
                </label>

                <label className="block text-sm font-medium text-gray-700">
                  Description
                  <textarea
                    name="description"
                    rows={3}
                    placeholder="Describe what this canvas represents…"
                    className="mt-1 w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
                  />
                </label>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowSaveDialog(false)}
                  className="px-4 py-2 text-sm border rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Saving…' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

/* ──────────────────────── PropTypes ──────────────────────────── */
InteractiveCanvas.propTypes = {
  projectId: PropTypes.string.isRequired,
  width: PropTypes.number,
  height: PropTypes.number,
};

InteractiveCanvas.defaultProps = {
  width: 800,
  height: 600,
};

export default InteractiveCanvas;
