from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..deps import get_db

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.post("/", response_model=schemas.ServerNodeOut, status_code=status.HTTP_201_CREATED)
def create_node(
    data: schemas.ServerNodeCreate,
    db: Session = Depends(get_db),
):
    node = crud.create_node(db, data)
    return node


@router.get("/", response_model=List[schemas.ServerNodeOut])
def list_nodes(db: Session = Depends(get_db)):
    return crud.list_nodes(db)


@router.get("/{node_id}", response_model=schemas.ServerNodeOut)
def get_node(node_id: str, db: Session = Depends(get_db)):
    node = crud.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.patch("/{node_id}", response_model=schemas.ServerNodeOut)
def update_node(
    node_id: str,
    data: schemas.ServerNodeUpdate,
    db: Session = Depends(get_db),
):
    node = crud.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node = crud.update_node(db, node, data)
    return node


@router.post("/{node_id}/heartbeat", response_model=schemas.ServerNodeOut)
def node_heartbeat(
    node_id: str,
    hb: schemas.ServerNodeHeartbeat,
    db: Session = Depends(get_db),
):
    node = crud.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node = crud.update_node_heartbeat(db, node, hb)
    return node
