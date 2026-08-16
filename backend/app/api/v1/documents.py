from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.models.collaboration import Document
from app.models.identity import User
from app.permissions.catalog import PermissionKey
from app.schemas.collaboration import DocumentCreate, DocumentResponse, DocumentUpdate
from app.schemas.common import MessageResponse, UUIDString
from app.services.access_service import require_project_access
from app.services.document_service import (
    create_document,
    get_document,
    list_documents,
    update_document,
)

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def documents_list(
    project_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.DOCUMENTS_VIEW)),
    search: str | None = Query(default=None, max_length=200),
) -> list[Document]:
    require_project_access(db, current, project_id)
    return list_documents(db, project_id, search)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def document_create(
    project_id: UUIDString,
    payload: DocumentCreate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.DOCUMENTS_CREATE)),
) -> Document:
    require_project_access(db, current, project_id)
    return create_document(db, project_id, current.id, payload)


@router.get("/{document_id}", response_model=DocumentResponse)
def document_detail(
    project_id: UUIDString,
    document_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.DOCUMENTS_VIEW)),
) -> Document:
    require_project_access(db, current, project_id)
    return get_document(db, project_id, document_id)


@router.patch("/{document_id}", response_model=DocumentResponse)
def document_update(
    project_id: UUIDString,
    document_id: UUIDString,
    payload: DocumentUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.DOCUMENTS_EDIT)),
) -> Document:
    require_project_access(db, current, project_id)
    return update_document(db, get_document(db, project_id, document_id), current.id, payload)


@router.delete("/{document_id}", response_model=MessageResponse)
def document_delete(
    project_id: UUIDString,
    document_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.DOCUMENTS_DELETE)),
) -> MessageResponse:
    require_project_access(db, current, project_id)
    document = get_document(db, project_id, document_id)
    db.delete(document)
    db.commit()
    return MessageResponse(message="Document deleted")
