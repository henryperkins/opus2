/**
 * Citation transformation utilities
 * Converts backend citation format to frontend CitationRenderer format
 */

/**
 * Transform backend citation object to frontend format
 * Backend format: { id, title, source, lines, similarity, source_type }
 * Frontend format: { id, number, source: { title, path, author }, content, confidence, context }
 */
function transformCitation(backendCitation, citationNumber, content = "") {
  return {
    id: backendCitation.id,
    number: citationNumber,
    source: {
      title: backendCitation.title || "Unknown",
      path: backendCitation.source || "Unknown",
      author: backendCitation.author || null,
    },
    content: content || backendCitation.content || "",
    confidence: backendCitation.similarity || 0.0,
    source_type: backendCitation.source_type || "unknown",
    context: {
      before: null,
      after: null,
    },
  };
}

/**
 * Transform backend citations map to frontend citations array
 * Backend format: { "[1]": { id, title, source, lines, similarity, source_type }, "[2]": {...} }
 * Frontend format: [{ id, number, source, content, confidence, source_type }, ...]
 */
export function transformCitationsMap(backendCitationsMap) {
  if (!backendCitationsMap || typeof backendCitationsMap !== "object") {
    return [];
  }

  const citations = [];

  // Sort citation markers numerically for consistent ordering
  const sortedMarkers = Object.keys(backendCitationsMap).sort((a, b) => {
    const aNum = parseInt(a.replace(/[[\]]/g, ""));
    const bNum = parseInt(b.replace(/[[\]]/g, ""));
    return aNum - bNum;
  });

  sortedMarkers.forEach((marker) => {
    const backendCitation = backendCitationsMap[marker];
    const citationNumber = parseInt(marker.replace(/[[\]]/g, ""));

    const transformedCitation = transformCitation(
      backendCitation,
      citationNumber,
    );
    citations.push(transformedCitation);
  });

  return citations;
}

/**
 * Transform message metadata by converting citations if present
 */
export function transformMessageMetadata(metadata) {
  if (!metadata) return metadata;

  const transformed = { ...metadata };

  // Transform citations from map format to array format
  if (transformed.citations && typeof transformed.citations === "object") {
    transformed.citations = transformCitationsMap(transformed.citations);
  }

  return transformed;
}
