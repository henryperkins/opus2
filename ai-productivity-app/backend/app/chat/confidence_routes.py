# backend/app/chat/confidence_routes.py
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from app.services.confidence_service import ConfidenceService
from app.dependencies import get_vector_service, CurrentUserRequired
from app.services.knowledge_service import KnowledgeService
from app.embeddings.generator import EmbeddingGenerator
import json

router = APIRouter()

confidence_service = ConfidenceService()


@router.post("/confidence")
async def get_confidence_score(
    query: str, user: CurrentUserRequired, vector_service=Depends(get_vector_service)
):
    """
    Calculates and returns the confidence score for a given query.
    """
    embedding_generator = EmbeddingGenerator()
    knowledge_service = KnowledgeService(vector_service, embedding_generator)

    search_results = await knowledge_service.search_knowledge(
        query, project_ids=[user.current_project_id]
    )

    if not search_results:
        return {"confidence": 0.0, "explanation": "No relevant documents found."}

    confidence = confidence_service.calculate_rag_confidence(search_results)
    explanation = confidence_service.get_confidence_explanation(confidence)

    return {"confidence": confidence, "explanation": explanation}


@router.websocket("/ws/confidence/{project_id}")
async def confidence_websocket(websocket: WebSocket, project_id: int):
    """
    WebSocket endpoint to stream confidence scores for a project.
    """
    await websocket.accept()
    try:
        while True:
            # This is a simplified example. In a real application, you would
            # have a mechanism to trigger confidence updates, for example,
            # after a new message is processed in a chat.
            # For now, we'll just wait for a message from the client.
            message = await websocket.receive_text()
            data = json.loads(message)
            query = data.get("query")

            if query:
                embedding_generator = EmbeddingGenerator()
                vector_service = await get_vector_service()
                knowledge_service = KnowledgeService(
                    vector_service, embedding_generator
                )

                search_results = await knowledge_service.search_knowledge(
                    query, project_ids=[project_id]
                )

                if not search_results:
                    await websocket.send_json(
                        {
                            "confidence": 0.0,
                            "explanation": "No relevant documents found.",
                        }
                    )
                else:
                    confidence = confidence_service.calculate_rag_confidence(
                        search_results
                    )
                    explanation = confidence_service.get_confidence_explanation(
                        confidence
                    )
                    await websocket.send_json(
                        {"confidence": confidence, "explanation": explanation}
                    )

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for project {project_id}")
