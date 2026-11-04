"""Saved evaluation results. These routes never run an evaluation."""

from fastapi import APIRouter, Depends

from backend import reports
from backend.security import require_token


router = APIRouter(tags=["evaluation"], dependencies=[Depends(require_token)])


@router.get("/evaluations/")
def list_evaluations():
    return reports.list_evaluations()


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: str):
    return reports.get_evaluation(evaluation_id)


@router.get("/experiments/comparison/")
def comparison():
    return reports.experiments_comparison()
