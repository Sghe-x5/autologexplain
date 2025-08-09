import uuid
from fastapi import APIRouter
from schema import AnalysisStartRequest, AnalysisStartResponse
from celery_worker import run_analysis_pubsub

router = APIRouter()

@router.post("/start", response_model=AnalysisStartResponse, status_code=202)
def start_analysis(req: AnalysisStartRequest):
    request_id = str(uuid.uuid4())
    run_analysis_pubsub.delay(request_id, req.chat_id, req.filters, req.prompt)
    return AnalysisStartResponse(request_id=request_id, chat_id=req.chat_id)
