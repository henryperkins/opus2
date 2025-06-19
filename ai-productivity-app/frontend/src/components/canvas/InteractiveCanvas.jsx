import React, { useRef, useEffect, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { codeAPI } from '../../api/code';
import { toast } from '../common/Toast';
import { useProjectTimeline } from '../../hooks/useProjects';

const InteractiveCanvas = ({ projectId, width = 800, height = 600 }) => {
  const canvasRef = useRef(null);
  const svgRef = useRef(null);
  const { addEvent } = useProjectTimeline(projectId);
  const [tool, setTool] = useState('select'); // 'select', 'draw', 'text', 'shape'
  const [shapes, setShapes] = useState([]);
  const [annotations, setAnnotations] = useState([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentPath, setCurrentPath] = useState('');
  const [selectedElement, setSelectedElement] = useState(null);
  const [showGrid, setShowGrid] = useState(true);
  const [savedArtifacts, setSavedArtifacts] = useState([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  useEffect(() => {
    initializeCanvas();
    if (projectId) {
      loadSavedArtifacts();
    }
  }, [projectId]);

  const loadSavedArtifacts = async () => {
    setLoading(true);
    try {
      const artifacts = await codeAPI.getCanvasArtifacts(projectId);
      setSavedArtifacts(artifacts.artifacts || []);
      toast.success(`Loaded ${artifacts.artifacts?.length || 0} saved artifacts`);
    } catch (error) {
      console.error('Failed to load canvas artifacts:', error);
      toast.error('Failed to load saved artifacts');
    } finally {
      setLoading(false);
    }
  };

  const initializeCanvas = () => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Set up canvas
    svg
      .attr("width", width)
      .attr("height", height)
      .style("border", "1px solid #e2e8f0")
      .style("background", "#ffffff");

    // Add grid if enabled
    if (showGrid) {
      const gridSize = 20;
      const defs = svg.append("defs");
      
      const pattern = defs.append("pattern")
        .attr("id", "grid")
        .attr("width", gridSize)
        .attr("height", gridSize)
        .attr("patternUnits", "userSpaceOnUse");

      pattern.append("path")
        .attr("d", `M ${gridSize} 0 L 0 0 0 ${gridSize}`)
        .attr("fill", "none")
        .attr("stroke", "#f1f5f9")
        .attr("stroke-width", 1);

      svg.append("rect")
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("fill", "url(#grid)");
    }

    // Add main drawing group
    const drawingGroup = svg.append("g").attr("class", "drawing-group");

    // Set up zoom and pan
    const zoom = d3.zoom()
      .scaleExtent([0.1, 5])
      .on("zoom", (event) => {
        drawingGroup.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Set up drawing events
    setupDrawingEvents(svg, drawingGroup);
  };

  const setupDrawingEvents = (svg, group) => {
    let drawing = false;
    let path = "";

    svg.on("mousedown", (event) => {
      if (tool === 'draw') {
        drawing = true;
        const [x, y] = d3.pointer(event);
        path = `M${x},${y}`;
        setCurrentPath(path);
        setIsDrawing(true);
      }
    });

    svg.on("mousemove", (event) => {
      if (drawing && tool === 'draw') {
        const [x, y] = d3.pointer(event);
        path += ` L${x},${y}`;
        setCurrentPath(path);
        
        // Update current drawing path
        group.selectAll(".current-path").remove();
        group.append("path")
          .attr("class", "current-path")
          .attr("d", path)
          .attr("stroke", "#3b82f6")
          .attr("stroke-width", 2)
          .attr("fill", "none");
      }
    });

    svg.on("mouseup", () => {
      if (drawing && tool === 'draw') {
        drawing = false;
        setIsDrawing(false);
        
        // Save the drawn path
        const newShape = {
          id: Date.now(),
          type: 'path',
          d: path,
          stroke: "#3b82f6",
          strokeWidth: 2,
          fill: "none"
        };
        
        setShapes(prev => [...prev, newShape]);
        setCurrentPath('');
        setHasUnsavedChanges(true);
        
        // Remove current path and add permanent one
        group.selectAll(".current-path").remove();
        renderShapes(group);
        
        toast.success('Drawing saved to canvas');
      }
    });
  };

  const renderShapes = useCallback((group) => {
    // Clear existing shapes
    group.selectAll(".shape").remove();
    
    // Render all shapes
    shapes.forEach(shape => {
      if (shape.type === 'path') {
        group.append("path")
          .attr("class", "shape")
          .attr("d", shape.d)
          .attr("stroke", shape.stroke)
          .attr("stroke-width", shape.strokeWidth)
          .attr("fill", shape.fill)
          .style("cursor", "pointer")
          .on("click", () => setSelectedElement(shape));
      } else if (shape.type === 'rect') {
        group.append("rect")
          .attr("class", "shape")
          .attr("x", shape.x)
          .attr("y", shape.y)
          .attr("width", shape.width)
          .attr("height", shape.height)
          .attr("stroke", shape.stroke)
          .attr("stroke-width", shape.strokeWidth)
          .attr("fill", shape.fill)
          .style("cursor", "pointer")
          .on("click", () => setSelectedElement(shape));
      }
    });
  }, [shapes]);

  const addShape = (shapeType) => {
    const newShape = {
      id: Date.now(),
      type: shapeType,
      x: 100,
      y: 100,
      width: 100,
      height: 80,
      stroke: "#3b82f6",
      strokeWidth: 2,
      fill: "rgba(59, 130, 246, 0.1)"
    };
    
    setShapes(prev => [...prev, newShape]);
    setHasUnsavedChanges(true);
    toast.success(`${shapeType} added to canvas`);
  };

  const addTextAnnotation = () => {
    const text = prompt("Enter text annotation:");
    if (text) {
      const newAnnotation = {
        id: Date.now(),
        text,
        x: 200,
        y: 200,
        fontSize: 14,
        color: "#1f2937"
      };
      setAnnotations(prev => [...prev, newAnnotation]);
      setHasUnsavedChanges(true);
      toast.success('Text annotation added');
    }
  };

  const clearCanvas = () => {
    if (hasUnsavedChanges) {
      if (!window.confirm('You have unsaved changes. Are you sure you want to clear the canvas?')) {
        return;
      }
    }
    
    setShapes([]);
    setAnnotations([]);
    setSelectedElement(null);
    setHasUnsavedChanges(false);
    initializeCanvas();
    toast.info('Canvas cleared');
  };

  const saveToKnowledgeBase = async (name, description) => {
    setSaving(true);
    try {
      const svg = svgRef.current;
      const serializer = new XMLSerializer();
      const svgContent = serializer.serializeToString(svg);
      
      const canvasData = {
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
          createdAt: new Date().toISOString()
        }
      };

      const savedArtifact = await codeAPI.saveCanvasArtifact(projectId, canvasData);
      await loadSavedArtifacts();
      setShowSaveDialog(false);
      setHasUnsavedChanges(false);
      
      // Add timeline event
      await addEvent({
        event_type: 'canvas_created',
        title: `Canvas "${name}" created`,
        description,
        metadata: {
          canvas_name: name,
          shapes_count: shapes.length,
          annotations_count: annotations.length,
          artifact_id: savedArtifact?.id
        }
      });
      
      toast.success(`Canvas "${name}" saved to knowledge base`);
    } catch (error) {
      console.error('Failed to save canvas artifact:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to save canvas to knowledge base';
      toast.error(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const loadArtifact = async (artifact) => {
    try {
      setShapes(artifact.shapes || []);
      setAnnotations(artifact.annotations || []);
      setHasUnsavedChanges(false);
      // Reinitialize canvas with loaded data
      initializeCanvas();
      toast.success(`Loaded "${artifact.name}"`);
    } catch (error) {
      console.error('Failed to load artifact:', error);
      toast.error('Failed to load artifact');
    }
  };

  const exportCanvas = () => {
    const svg = svgRef.current;
    const serializer = new XMLSerializer();
    const source = serializer.serializeToString(svg);
    const blob = new Blob([source], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = 'canvas-export.svg';
    a.click();
    
    URL.revokeObjectURL(url);
  };

  // Re-render when shapes or annotations change
  useEffect(() => {
    if (svgRef.current) {
      const svg = d3.select(svgRef.current);
      const group = svg.select(".drawing-group");
      if (!group.empty()) {
        renderShapes(group);
        
        // Render annotations
        group.selectAll(".annotation").remove();
        annotations.forEach(annotation => {
          group.append("text")
            .attr("class", "annotation")
            .attr("x", annotation.x)
            .attr("y", annotation.y)
            .attr("font-size", annotation.fontSize)
            .attr("fill", annotation.color)
            .text(annotation.text)
            .style("cursor", "pointer")
            .on("click", () => setSelectedElement(annotation));
        });
      }
    }
  }, [shapes, annotations, renderShapes]);

  return (
    <div className="interactive-canvas">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-4 bg-gray-50 border-b">
        <div className="flex items-center space-x-2">
          {hasUnsavedChanges && (
            <div className="flex items-center text-orange-600 text-xs mr-4">
              <div className="w-2 h-2 bg-orange-500 rounded-full mr-1"></div>
              Unsaved changes
            </div>
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
          {/* Saved Artifacts Dropdown */}
          {savedArtifacts.length > 0 && (
            <select
              onChange={(e) => {
                if (e.target.value) {
                  const artifact = savedArtifacts.find(a => a.id === e.target.value);
                  if (artifact) loadArtifact(artifact);
                }
              }}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
              defaultValue=""
            >
              <option value="">Load Artifact...</option>
              {savedArtifacts.map(artifact => (
                <option key={artifact.id} value={artifact.id}>
                  {artifact.name}
                </option>
              ))}
            </select>
          )}
          
          <button
            onClick={() => setShowGrid(!showGrid)}
            className={`px-3 py-1 text-sm rounded ${
              showGrid ? 'bg-gray-200 text-gray-800' : 'bg-white border hover:bg-gray-50'
            }`}
          >
            Grid
          </button>
          <button
            onClick={() => setShowSaveDialog(true)}
            disabled={saving}
            className={`px-3 py-1 text-sm rounded flex items-center ${
              hasUnsavedChanges 
                ? 'bg-orange-600 text-white hover:bg-orange-700' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            } disabled:opacity-50`}
          >
            {saving && (
              <svg className="animate-spin -ml-1 mr-1 h-3 w-3 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            {saving ? 'Saving...' : 'Save to KB'}
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
        
        {/* Status indicator */}
        {isDrawing && (
          <div className="absolute top-2 left-2 px-2 py-1 bg-blue-500 text-white text-xs rounded">
            Drawing...
          </div>
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
                if (selectedElement.type === 'path') {
                  setShapes(prev => prev.filter(s => s.id !== selectedElement.id));
                } else {
                  setAnnotations(prev => prev.filter(a => a.id !== selectedElement.id));
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

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 w-96 max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Save Canvas to Knowledge Base</h3>
            
            <form onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.target);
              const name = formData.get('name');
              const description = formData.get('description');
              if (name) {
                saveToKnowledgeBase(name, description);
              }
            }}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Name *
                  </label>
                  <input
                    name="name"
                    type="text"
                    required
                    placeholder="e.g., Architecture Diagram"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    name="description"
                    rows={3}
                    placeholder="Describe what this canvas represents..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowSaveDialog(false)}
                  className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save to Knowledge Base'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default InteractiveCanvas;