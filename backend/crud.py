from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from . import models, schemas
from passlib.context import CryptContext
import datetime
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password, role=user.role.lower())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_evaluation(db: Session, evaluation: schemas.EvaluationCreate, evaluator_id: int):
    evaluation_data = evaluation.dict(exclude_unset=True)
    # Remove timestamp if it's None, so the model's default is used
    if 'timestamp' in evaluation_data and evaluation_data['timestamp'] is None:
        del evaluation_data['timestamp']

    db_evaluation = models.Evaluation(
        **evaluation_data,
        evaluator_id=evaluator_id
    )
    db.add(db_evaluation)
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation

def get_evaluation(db: Session, evaluation_id: int):
    return db.query(models.Evaluation).options(joinedload(models.Evaluation.actions)).filter(models.Evaluation.id == evaluation_id).first()

def get_evaluations(
    db: Session,
    skip: int = 0,
    limit: Optional[int] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    last_n: Optional[int] = None # New parameter
):
    query = db.query(models.Evaluation).options(joinedload(models.Evaluation.actions))

    if start_date:
        query = query.filter(models.Evaluation.timestamp >= start_date)
    if end_date:
        query = query.filter(models.Evaluation.timestamp <= end_date)

    query = query.order_by(models.Evaluation.timestamp.desc()) # Order by timestamp descending

    if last_n is not None and start_date is None and end_date is None:
        # If last_n is provided and no date range, fetch the last_n records first
        query = query.limit(last_n)
        # Then apply pagination to these last_n records
        if limit is not None:
            query = query.offset(skip).limit(limit)
    elif limit is not None: # Apply limit only if it's not None
        query = query.offset(skip).limit(limit)

    return query.all()

def get_evaluations_count(
    db: Session,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    last_n: Optional[int] = None
) -> int:
    query = db.query(models.Evaluation)

    if start_date:
        query = query.filter(models.Evaluation.timestamp >= start_date)
    if end_date:
        query = query.filter(models.Evaluation.timestamp <= end_date)

    if last_n is not None and start_date is None and end_date is None:
        # If last_n is provided and no date range, count only up to last_n
        return min(query.count(), last_n)
    else:
        return query.count()


def update_evaluation(db: Session, db_evaluation: models.Evaluation, evaluation: schemas.EvaluationUpdate):
    # Actualizar solo los campos que se proporcionan en la actualización
    update_data = evaluation.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_evaluation, key, value)
    db.add(db_evaluation)
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation

def delete_evaluation(db: Session, db_evaluation: models.Evaluation):
    db.delete(db_evaluation)
    db.commit()
    return db_evaluation

def create_action_status(db: Session, action: schemas.ActionStatusCreate, evaluation_id: int):
    db_action = models.ActionStatus(**action.dict(), evaluation_id=evaluation_id)
    db.add(db_action)
    db.commit()
    db.refresh(db_action)
    return db_action

def get_action_status(db: Session, action_id: int):
    return db.query(models.ActionStatus).filter(models.ActionStatus.id == action_id).first()

def update_action_status(db: Session, db_action: models.ActionStatus, action_update: schemas.ActionStatusUpdate):
    if db_action:
        db_action.status = action_update.status
        db.commit()
        db.refresh(db_action)
    return db_action

def get_whatsapp_contact(db: Session, contact_id: int, user_id: int):
    return db.query(models.WhatsAppContact).filter(models.WhatsAppContact.id == contact_id, models.WhatsAppContact.user_id == user_id).first()

def get_whatsapp_contacts_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.WhatsAppContact).filter(models.WhatsAppContact.user_id == user_id).offset(skip).limit(limit).all()

def create_whatsapp_contact(db: Session, contact: schemas.WhatsAppContactCreate, user_id: int):
    # Check if a contact with the same phone_number already exists for this user
    existing_contact = db.query(models.WhatsAppContact).filter(
        models.WhatsAppContact.phone_number == contact.phone_number,
        models.WhatsAppContact.user_id == user_id
    ).first()

    if existing_contact:
        # If it exists, return the existing contact
        return existing_contact
    else: # Only create and commit if no existing contact is found
        db_contact = models.WhatsAppContact(**contact.dict(), user_id=user_id)
        db.add(db_contact)
        try:
            db.commit()
            db.refresh(db_contact)
            return db_contact
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Phone number already registered")

def update_whatsapp_contact(db: Session, contact_id: int, contact: schemas.WhatsAppContactCreate, user_id: int):
    db_contact = get_whatsapp_contact(db, contact_id, user_id)
    if db_contact:
        for key, value in contact.dict().items():
            setattr(db_contact, key, value)
        db.commit()
        db.refresh(db_contact)
    return db_contact

def delete_whatsapp_contact(db: Session, contact_id: int, user_id: int):
    db_contact = get_whatsapp_contact(db, contact_id, user_id)
    if db_contact:
        db.delete(db_contact)
        db.commit()
    return db_contact

def get_distribution_list(db: Session, list_id: int, user_id: int):
    return db.query(models.DistributionList).filter(models.DistributionList.id == list_id, models.DistributionList.user_id == user_id).first()

def get_distribution_lists_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.DistributionList).filter(models.DistributionList.user_id == user_id).offset(skip).limit(limit).all()

def create_distribution_list(db: Session, dist_list: schemas.DistributionListCreate, user_id: int):
    db_list = models.DistributionList(name=dist_list.name, user_id=user_id)
    db.add(db_list)
    db.commit()
    db.refresh(db_list)
    for contact_id in dist_list.contact_ids:
        contact = get_whatsapp_contact(db, contact_id, user_id)
        if contact:
            db_list.contacts.append(contact)
    db.commit()
    db.refresh(db_list)
    return db_list

def update_distribution_list(db: Session, list_id: int, dist_list: schemas.DistributionListCreate, user_id: int):
    db_list = get_distribution_list(db, list_id, user_id)
    if db_list:
        db_list.name = dist_list.name
        db_list.contacts.clear()
        for contact_id in dist_list.contact_ids:
            contact = get_whatsapp_contact(db, contact_id, user_id)
            if contact:
                db_list.contacts.append(contact)
        db.commit()
        db.refresh(db_list)
    return db_list

def delete_distribution_list(db: Session, list_id: int, user_id: int):
    db_list = get_distribution_list(db, list_id, user_id)
    if db_list:
        db.delete(db_list)
        db.commit()
    return db_list

def get_email_contact(db: Session, contact_id: int, user_id: int):
    return db.query(models.EmailContact).filter(models.EmailContact.id == contact_id, models.EmailContact.user_id == user_id).first()

def get_email_contacts_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.EmailContact).filter(models.EmailContact.user_id == user_id).offset(skip).limit(limit).all()

def create_email_contact(db: Session, contact: schemas.EmailContactCreate, user_id: int):
    db_contact = models.EmailContact(**contact.dict(), user_id=user_id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def update_email_contact(db: Session, contact_id: int, contact: schemas.EmailContactCreate, user_id: int):
    db_contact = get_email_contact(db, contact_id, user_id)
    if db_contact:
        for key, value in contact.dict().items():
            setattr(db_contact, key, value)
        db.commit()
        db.refresh(db_contact)
    return db_contact

def delete_email_contact(db: Session, contact_id: int, user_id: int):
    db_contact = get_email_contact(db, contact_id, user_id)
    if db_contact:
        db.delete(db_contact)
        db.commit()
    return db_contact

def get_email_distribution_list(db: Session, list_id: int, user_id: int):
    return db.query(models.EmailDistributionList).filter(models.EmailDistributionList.id == list_id, models.EmailDistributionList.user_id == user_id).first()

def get_email_distribution_lists_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.EmailDistributionList).filter(models.EmailDistributionList.user_id == user_id).offset(skip).limit(limit).all()

def create_email_distribution_list(db: Session, dist_list: schemas.EmailDistributionListCreate, user_id: int):
    db_list = models.EmailDistributionList(name=dist_list.name, user_id=user_id)
    db.add(db_list)
    db.commit()
    db.refresh(db_list)
    for contact_id in dist_list.contact_ids:
        contact = get_email_contact(db, contact_id, user_id)
        if contact:
            db_list.contacts.append(contact)
    db.commit()
    db.refresh(db_list)
    return db_list

def update_email_distribution_list(db: Session, list_id: int, dist_list: schemas.EmailDistributionListCreate, user_id: int):
    db_list = get_email_distribution_list(db, list_id, user_id)
    if db_list:
        db_list.name = dist_list.name
        db_list.contacts.clear()
        for contact_id in dist_list.contact_ids:
            contact = get_email_contact(db, contact_id, user_id)
            if contact:
                db_list.contacts.append(contact)
        db.commit()
        db.refresh(db_list)
    return db_list

def delete_email_distribution_list(db: Session, list_id: int, user_id: int):
    db_list = get_email_distribution_list(db, list_id, user_id)
    if db_list:
        db.delete(db_list)
        db.commit()
    return db_list