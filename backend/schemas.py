from pydantic import BaseModel, EmailStr, validator, ConfigDict
from datetime import datetime, timezone
from typing import Optional, List

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    role: str = "viewer"

class User(UserBase):
    id: int
    role: str

    model_config = ConfigDict(from_attributes=True)



class ActionStatusBase(BaseModel):
    measure_description: str
    status: str = "not_applied" # "not_applied", "in_process", "applied"
    original_order_index: int

class ActionStatusCreate(ActionStatusBase):
    pass

class ActionStatusUpdate(BaseModel):
    status: str

class ActionStatus(ActionStatusBase):
    id: int
    evaluation_id: int
    original_order_index: int

    model_config = ConfigDict(from_attributes=True)

class EvaluationBase(BaseModel):
    protocol_type: str
    mq_scenario: Optional[str] = None
    ventilated_patients: Optional[int] = None
    input_data: str # JSON string of inputs

class EvaluationCreate(EvaluationBase):
    timestamp: Optional[datetime] = None # Add timestamp field
    total_score: Optional[int] = None
    alert_level: str
    evaluator_name: Optional[str] = None

class EvaluationUpdate(BaseModel):
    timestamp: Optional[datetime] = None
    total_score: Optional[int] = None
    alert_level: Optional[str] = None
    input_data: Optional[str] = None
    evaluation_results: Optional[str] = None

    @validator("timestamp", pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            # FastAPI/Pydantic v2 handles ISO string parsing automatically.
            # For v1, explicit parsing is safer.
            try:
                # Attempt to parse the ISO string, handling the 'Z' for UTC.
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                # Let Pydantic handle other potential errors.
                return v
        if isinstance(v, datetime):
            # If it's already a datetime object, ensure it's timezone-aware for consistency.
            if v.tzinfo is None:
                # If it's a naive datetime, assume it's in UTC, as that's our standard.
                return v.replace(tzinfo=timezone.utc)
        return v

class Evaluation(EvaluationBase):
    id: int
    timestamp: datetime
    evaluation_results: Optional[str] = None # Add this line

    @validator('timestamp', pre=True)
    def convert_datetime_to_iso_utc(cls, v):
        if isinstance(v, datetime):
            # Asegurarse de que la fecha sea consciente de la zona horaria (UTC)
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc) # Asumir UTC si no tiene tzinfo
            return v.isoformat().replace('+00:00', 'Z') # Formatear a ISO y reemplazar +00:00 por Z
        return v
    total_score: Optional[int] = None
    alert_level: str
    evaluator_id: int
    evaluator_name: Optional[str] = None
    actions: List[ActionStatus] = []

    model_config = ConfigDict(from_attributes=True)

class WhatsAppContactBase(BaseModel):
    name: str
    phone_number: str

class WhatsAppContactCreate(WhatsAppContactBase):
    pass

class WhatsAppContact(WhatsAppContactBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

class DistributionListBase(BaseModel):
    name: str

class DistributionListCreate(DistributionListBase):
    contact_ids: List[int] = []

class DistributionList(DistributionListBase):
    id: int
    user_id: int
    contacts: List[WhatsAppContact] = []

    model_config = ConfigDict(from_attributes=True)

class EmailContactBase(BaseModel):
    name: str
    email: EmailStr

class EmailContactCreate(EmailContactBase):
    pass

class EmailContact(EmailContactBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

class EmailDistributionListBase(BaseModel):
    name: str

class EmailDistributionListCreate(EmailDistributionListBase):
    contact_ids: List[int] = []

class EmailDistributionList(EmailDistributionListBase):
    id: int
    user_id: int
    contacts: List[EmailContact] = []

    model_config = ConfigDict(from_attributes=True)

class MedicoQuirurgicoInput(BaseModel):
    scenario: str
    hospitalized_patients: int
    esi_c2_patients: int
    reanimador_patients: int
    critical_patient_protocol: str
    waiting_72_hours_patients: int
    sar_active: bool = False
    sar_patients: Optional[int] = None
    timestamp: Optional[datetime] = None # Add timestamp field
    evaluator_name: str

class MedicoQuirurgicoResult(BaseModel):
    score: int
    alert_level: str
    measures: List[ActionStatus]
    reevaluation_note: Optional[str] = None

class PredictionPoint(BaseModel):
    timestamp: datetime
    predicted_value: float
    confidence_min: float
    confidence_max: float

class PredictionResult(BaseModel):
    predictions: List[PredictionPoint]

class HospitalSaturation(BaseModel):
    hospital_id: int
    saturation_level: int

class HospitalSaturationUpdate(BaseModel):
    saturations: List[HospitalSaturation]

class PaginatedEvaluations(BaseModel):
    evaluations: List[Evaluation]
    total_count: int

class ReportHTML(BaseModel):
    html_content: str

class EvaluationHistory(Evaluation):
    evaluator_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class PaginatedEvaluationsHistory(BaseModel):
    evaluations: List[EvaluationHistory]
    total_count: int