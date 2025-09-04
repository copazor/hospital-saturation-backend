from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
from datetime import timezone # Import timezone

from .database import SessionLocal, engine
Base = declarative_base()

# --- Modelos de la Aplicación ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="viewer")  # Roles: "editor", "viewer"
    evaluations = relationship("Evaluation", back_populates="evaluator")

class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.now(timezone.utc))
    protocol_type = Column(String, nullable=False) # "medico_quirurgico" o "paciente_critico"
    
    # Para Medico/Quirurgico
    mq_scenario = Column(String) # "capacidad_reducida" o "capacidad_completa"
    total_score = Column(Integer)
    
    # Para Paciente Critico
    ventilated_patients = Column(Integer)

    alert_level = Column(String, nullable=False) # "Verde", "Amarilla", "Naranja", "Roja"
    
    evaluator_id = Column(Integer, ForeignKey("users.id"))
    evaluator_name = Column(String, nullable=True)
    evaluator = relationship("User", back_populates="evaluations")
    
    input_data = Column(Text) # Guardaremos los inputs del usuario como un JSON string
    evaluation_results = Column(Text, nullable=True) # Guardaremos los resultados y el análisis como un JSON string
    actions = relationship("ActionStatus", back_populates="evaluation", cascade="all, delete-orphan")

class ActionStatus(Base):
    __tablename__ = "action_status"
    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"))
    evaluation = relationship("Evaluation", back_populates="actions")
    
    measure_description = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="not_applied") # "not_applied", "in_process", "applied"
    original_order_index = Column(Integer, nullable=False)

from sqlalchemy import Table

distribution_list_contacts = Table('distribution_list_contacts', Base.metadata,
    Column('list_id', Integer, ForeignKey('distribution_lists.id'), primary_key=True),
    Column('contact_id', Integer, ForeignKey('whatsapp_contacts.id'), primary_key=True)
)

class WhatsAppContact(Base):
    __tablename__ = "whatsapp_contacts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    phone_number = Column(String, index=True, nullable=False)

    __table_args__ = (UniqueConstraint('user_id', 'phone_number', name='uq_user_phone'),)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")

class DistributionList(Base):
    __tablename__ = "distribution_lists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")
    contacts = relationship("WhatsAppContact", secondary=distribution_list_contacts)

email_distribution_list_contacts = Table('email_distribution_list_contacts', Base.metadata,
    Column('list_id', Integer, ForeignKey('email_distribution_lists.id'), primary_key=True),
    Column('contact_id', Integer, ForeignKey('email_contacts.id'), primary_key=True)
)

class EmailContact(Base):
    __tablename__ = "email_contacts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")

class EmailDistributionList(Base):
    __tablename__ = "email_distribution_lists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")
    contacts = relationship("EmailContact", secondary=email_distribution_list_contacts)

# --- Función para crear la base de datos ---
def create_db():
    print("Attempting to create database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables creation attempt finished.")