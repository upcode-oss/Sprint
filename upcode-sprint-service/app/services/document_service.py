from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import APIError
from app.models.collaboration import Document
from app.schemas.collaboration import DocumentCreate, DocumentUpdate


def _document_options():
    return (
        selectinload(Document.created_by),
        selectinload(Document.updated_by),
    )


def list_documents(db: Session, project_id: str, search: str | None = None) -> list[Document]:
    statement = (
        select(Document).options(*_document_options()).where(Document.project_id == project_id)
    )
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(Document.title.ilike(term), Document.markdown_content.ilike(term))
        )
    return list(db.scalars(statement.order_by(Document.updated_at.desc())))


def get_document(db: Session, project_id: str, document_id: str) -> Document:
    document = db.scalar(
        select(Document)
        .options(*_document_options())
        .where(Document.id == document_id, Document.project_id == project_id)
    )
    if document is None:
        raise APIError(404, "document_not_found", "Document not found")
    return document


def create_document(
    db: Session, project_id: str, user_id: str, payload: DocumentCreate
) -> Document:
    if payload.parent_id:
        get_document(db, project_id, payload.parent_id)
    document = Document(
        project_id=project_id,
        created_by_id=user_id,
        updated_by_id=user_id,
        **payload.model_dump(),
    )
    db.add(document)
    db.commit()
    return get_document(db, project_id, document.id)


def update_document(
    db: Session, document: Document, user_id: str, payload: DocumentUpdate
) -> Document:
    if payload.parent_id:
        parent = get_document(db, document.project_id, payload.parent_id)
        if parent.id == document.id:
            raise APIError(422, "invalid_parent", "A document cannot be its own parent")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, key, value)
    document.updated_by_id = user_id
    db.commit()
    return get_document(db, document.project_id, document.id)
