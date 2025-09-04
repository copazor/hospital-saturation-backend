from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, schemas, crud, protocol_logic
from .database import SessionLocal, engine
from datetime import timedelta, datetime, timezone # Importar datetime y timezone
from typing import List, Optional # Importar List y Optional
import json # Importar json para serializar input_data
from fastapi.encoders import jsonable_encoder # Importar jsonable_encoder
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

import pdfkit
from fastapi.responses import Response, StreamingResponse # Added StreamingResponse
import io # Added io

# Importar funciones de seguridad
from . import security # Changed import

# Crear las tablas de la base de datos
models.create_db()

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware # Import SessionMiddleware

# Import your models for SQLAdmin
from .models import User, Evaluation, WhatsAppContact, DistributionList, EmailContact, EmailDistributionList, ActionStatus

from .database import SessionLocal # Add this import at the top of main.py
from .security import authenticate_user # Add this import at the top of main.py

# Define ModelViews for your models
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.role]
    column_searchable_list = [User.username]
    column_sortable_list = [User.id, User.username, User.role]
    column_details_list = [User.id, User.username, User.role, User.hashed_password] # For details view
    name_plural = "Usuarios"
    icon = "fa-solid fa-user"

class EvaluationAdmin(ModelView, model=Evaluation):
    column_list = [
        Evaluation.id,
        Evaluation.timestamp,
        Evaluation.protocol_type,
        Evaluation.alert_level,
        Evaluation.total_score,
        Evaluation.evaluator_name,
    ]
    column_searchable_list = [Evaluation.protocol_type, Evaluation.alert_level, Evaluation.evaluator_name]
    column_sortable_list = [
        Evaluation.id,
        Evaluation.timestamp,
        Evaluation.protocol_type,
        Evaluation.alert_level,
        Evaluation.total_score,
    ]
    name_plural = "Evaluaciones"
    icon = "fa-solid fa-chart-line"

class WhatsAppContactAdmin(ModelView, model=WhatsAppContact):
    column_list = [WhatsAppContact.id, WhatsAppContact.name, WhatsAppContact.phone_number, WhatsAppContact.user_id]
    column_searchable_list = [WhatsAppContact.name, WhatsAppContact.phone_number]
    name_plural = "Contactos de WhatsApp"
    icon = "fa-brands fa-whatsapp"

class DistributionListAdmin(ModelView, model=DistributionList):
    column_list = [DistributionList.id, DistributionList.name, DistributionList.user_id]
    column_searchable_list = [DistributionList.name]
    name_plural = "Listas de Distribución"
    icon = "fa-solid fa-list"

class EmailContactAdmin(ModelView, model=EmailContact):
    column_list = [EmailContact.id, EmailContact.name, EmailContact.email, EmailContact.user_id]
    column_searchable_list = [EmailContact.name, EmailContact.email]
    name_plural = "Contactos de Email"
    icon = "fa-solid fa-envelope"

class EmailDistributionListAdmin(ModelView, model=EmailDistributionList):
    column_list = [EmailDistributionList.id, EmailDistributionList.name, EmailDistributionList.user_id]
    column_searchable_list = [EmailDistributionList.name]
    name_plural = "Listas de Distribución de Email"
    icon = "fa-solid fa-mail-bulk"

class ActionStatusAdmin(ModelView, model=ActionStatus):
    column_list = [ActionStatus.id, ActionStatus.evaluation_id, ActionStatus.measure_description, ActionStatus.status]
    column_searchable_list = [ActionStatus.measure_description, ActionStatus.status]
    name_plural = "Estados de Acción"
    icon = "fa-solid fa-check-double"


# SQLAdmin Authentication Backend
class AdminAuth(AuthenticationBackend):
    async def login(self, request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # Use your existing authentication logic
        with SessionLocal() as db: # Get a database session
            user = authenticate_user(db, username, password)
            if user and user.role == "administrador": # Check if user exists and has admin role
                request.session["token"] = user.username # Store something to identify the user in session
                return True
        return False

    async def logout(self, request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request) -> RedirectResponse | bool:
        token = request.session.get("token")

        if not token:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        # In a real app, validate the token (e.g., check expiration, against DB)
        # For this example, just checking presence of token
        return True

# Initialize FastAPI app
app = FastAPI(
    title="Hospital Saturation Protocol API",
    description="API para gestionar el protocolo de saturación hospitalaria.",
    version="0.2.0", # Version bump for new features
)

# Add SessionMiddleware for SQLAdmin authentication
# The secret_key should be a strong, randomly generated string
app.add_middleware(SessionMiddleware, secret_key="Inicio.2024") # CHANGE THIS!

# Configuración de CORS para permitir la comunicación con el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Initialize SQLAdmin
admin = Admin(app, engine, authentication_backend=AdminAuth(secret_key="Inicio.2024")) # Use the same secret key or a different one

# Add your ModelViews to the admin instance
admin.add_view(UserAdmin)
admin.add_view(EvaluationAdmin)
admin.add_view(WhatsAppContactAdmin)
admin.add_view(DistributionListAdmin)
admin.add_view(EmailContactAdmin)
admin.add_view(EmailDistributionListAdmin)
admin.add_view(ActionStatusAdmin)


# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API del Protocolo de Saturación Hospitalaria"}

# --- User Management Endpoints ---

@app.post("/users/", response_model=schemas.User)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)




@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username, "role": user.role}, # Include role in token
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(security.get_current_active_user)):
    return current_user

# --- Protocol Calculation Endpoints ---

@app.post("/calculate-medico-quirurgico", response_model=schemas.MedicoQuirurgicoResult)
async def calculate_medico_quirurgico(
    data: schemas.MedicoQuirurgicoInput,
    current_user: schemas.User = Depends(security.get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role == 'viewer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los usuarios con rol de visualizador no tienen permiso para realizar nuevos cálculos."
        )
    result_calc = protocol_logic.calculate_medico_quirurgico_score(**data.dict(exclude={'timestamp', 'evaluator_name'}))
    measures = protocol_logic.get_medico_quirurgico_measures(result_calc["alert_level"])
    reevaluation_note = protocol_logic.get_medico_quirurgico_reevaluation_note(result_calc["alert_level"])
    
    evaluation_create = schemas.EvaluationCreate(
        protocol_type="medico_quirurgico",
        mq_scenario=data.scenario,
        input_data=json.dumps(data.dict(exclude={'timestamp', 'evaluator_name'})),
        total_score=result_calc["score"],
        alert_level=result_calc["alert_level"],
        timestamp=data.timestamp,
        evaluator_name=data.evaluator_name
    )
    
    db_evaluation = crud.create_evaluation(db=db, evaluation=evaluation_create, evaluator_id=current_user.id)

    saved_actions = []
    for index, measure_description in enumerate(measures):
        action_status_create = schemas.ActionStatusCreate(measure_description=measure_description, original_order_index=index)
        db_action = crud.create_action_status(db=db, action=action_status_create, evaluation_id=db_evaluation.id)
        saved_actions.append(db_action)

    return {"score": result_calc["score"], "alert_level": result_calc["alert_level"], "measures": saved_actions, "reevaluation_note": reevaluation_note}

# --- Prediction and Statistics Endpoints ---

@app.post("/predict", response_model=schemas.PredictionResult)
async def predict_saturation(
    current_user: schemas.User = Depends(security.get_current_active_user),
    db: Session = Depends(get_db)
):
    evaluations = crud.get_evaluations(db, limit=1000)
    if len(evaluations) < 10:
        raise HTTPException(status_code=400, detail="Not enough data for prediction.")

    df = pd.DataFrame([e.__dict__ for e in evaluations])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp').sort_index()
    ts_data = df['total_score'].resample('D').mean().fillna(method='ffill')

    if len(ts_data) < 10:
        raise HTTPException(status_code=400, detail="Not enough historical data for prediction.")

    model = SARIMAX(ts_data, order=(1, 1, 1), seasonal_order=(1, 1, 1, 7))
    results = model.fit(disp=False)
    forecast = results.get_forecast(steps=7)
    
    prediction_list = [
        schemas.PredictionPoint(
            timestamp=ts,
            predicted_value=val,
            confidence_min=forecast.conf_int().loc[ts][0],
            confidence_max=forecast.conf_int().loc[ts][1]
        ) for ts, val in forecast.predicted_mean.items()
    ]

    return schemas.PredictionResult(predictions=prediction_list)

# --- Evaluation History Endpoints ---

@app.get("/evaluations/", response_model=schemas.PaginatedEvaluationsHistory)
async def read_evaluations(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: Optional[int] = None,
    last_n: Optional[int] = None, # New parameter for fetching last N evaluations
    current_user: schemas.User = Depends(security.get_current_active_user),
    db: Session = Depends(get_db)
):
    # All roles can use filters and pagination
    evaluations = crud.get_evaluations(
        db,
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        last_n=last_n # Pass the new parameter to crud
    )
    total_count = crud.get_evaluations_count(
        db,
        start_date=start_date,
        end_date=end_date,
        last_n=last_n # Pass the new parameter to crud
    )
    return schemas.PaginatedEvaluationsHistory(evaluations=[schemas.EvaluationHistory.from_orm(e) for e in evaluations], total_count=total_count)

@app.get("/export-evaluations-excel")
async def export_evaluations_to_excel(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: schemas.User = Depends(security.get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only administrators and editors can export
    if current_user.role not in ["administrador", "editor_gestor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para exportar evaluaciones."
        )

    evaluations = crud.get_evaluations(db, start_date=start_date, end_date=end_date)

    if not evaluations:
        raise HTTPException(status_code=404, detail="No se encontraron evaluaciones para exportar.")

    # Prepare data for DataFrame
    data_for_df = []
    for eval_obj in evaluations:
        # Convert SQLAlchemy model to dictionary
        eval_dict = eval_obj.__dict__
        
        # Parse input_data and evaluation_results JSON strings
        input_data = json.loads(eval_dict.get('input_data', '{}') or '{}')
        evaluation_results = json.loads(eval_dict.get('evaluation_results', '{}') or '{}')

        # Flatten the dictionary for DataFrame
        row = {
            "ID Evaluación": eval_dict.get('id'),
            "Fecha y Hora": eval_dict.get('timestamp'),
            "Tipo de Protocolo": eval_dict.get('protocol_type'),
            "Nivel de Alerta": eval_dict.get('alert_level'),
            "Puntaje Total": eval_dict.get('total_score'),
            "Evaluador ID": eval_dict.get('evaluator_id'),
            "Nombre Evaluador": eval_dict.get('evaluator_name'),
            "Escenario MQ": eval_dict.get('mq_scenario'),
            "Pacientes Ventilados": eval_dict.get('ventilated_patients'),
            # Input Data
            "Input - Pacientes Hospitalizados": input_data.get('hospitalized_patients'),
            "Input - Pacientes ESI C2": input_data.get('esi_c2_patients'),
            "Input - Pacientes Reanimador": input_data.get('reanimador_patients'),
            "Input - Protocolo Paciente Crítico": input_data.get('critical_patient_protocol'),
            "Input - Pacientes Espera > 72h": input_data.get('waiting_72_hours_patients'),
            "Input - SAR Activo": input_data.get('sar_active'),
            "Input - Pacientes SAR": input_data.get('sar_patients'),
            # Evaluation Results
            "Resultados - Hora Reevaluación": evaluation_results.get('re_evaluation_time'),
            "Resultados - Análisis Texto": evaluation_results.get('analysis_text'),
            "Resultados - Decisión Final": evaluation_results.get('final_decision'),
            "Resultados - Próxima Evaluación": evaluation_results.get('next_evaluation_timestamp'),
            "Resultados - Movimientos Efectivos": evaluation_results.get('effective_movements'),
            "Resultados - Movimientos Potenciales Adicionales": evaluation_results.get('potential_additional_add_movements'),
            "Resultados - Dificultades Principales": evaluation_results.get('main_difficulties'),
            "Resultados - Factores Facilitadores": evaluation_results.get('facilitating_factors'),
            "Resultados - Comentarios Adicionales": evaluation_results.get('additional_comments'),
        }
        data_for_df.append(row)

    df = pd.DataFrame(data_for_df)

    # Ensure all columns are present, fill missing with None or empty string
    # This helps if some evaluations don't have all fields
    expected_columns = [
        "ID Evaluación", "Fecha y Hora", "Tipo de Protocolo", "Nivel de Alerta", "Puntaje Total",
        "Evaluador ID", "Nombre Evaluador", "Escenario MQ", "Pacientes Ventilados",
        "Input - Pacientes Hospitalizados", "Input - Pacientes ESI C2", "Input - Pacientes Reanimador",
        "Input - Protocolo Paciente Crítico", "Input - Pacientes Espera > 72h",
        "Input - SAR Activo", "Input - Pacientes SAR",
        "Resultados - Hora Reevaluación", "Resultados - Análisis Texto", "Resultados - Decisión Final",
        "Resultados - Próxima Evaluación", "Resultados - Movimientos Efectivos",
        "Resultados - Movimientos Potenciales Adicionales", "Resultados - Dificultades Principales",
        "Resultados - Factores Facilitadores", "Resultados - Comentarios Adicionales",
    ]
    for col in expected_columns:
        if col not in df.columns:
            df[col] = None # Or "" depending on desired default

    # Reorder columns for better readability in Excel
    df = df[expected_columns]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Evaluaciones')
    output.seek(0)

    filename = f"evaluaciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return StreamingResponse(output, headers=headers)


@app.get("/evaluations/{evaluation_id}", response_model=schemas.EvaluationHistory)
async def read_single_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    db_evaluation = crud.get_evaluation(db, evaluation_id=evaluation_id)
    if db_evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # Visor can only see last 3, this check is a bit tricky here.
    # A simpler approach is to let them fetch by ID but the frontend won't show them links to older ones.
    # For now, we allow it if they have the ID.
    return db_evaluation

@app.get("/evaluations/{evaluation_id}", response_model=schemas.EvaluationHistory)
async def read_single_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    db_evaluation = crud.get_evaluation(db, evaluation_id=evaluation_id)
    if db_evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # Visor can only see last 3, this check is a bit tricky here.
    # A simpler approach is to let them fetch by ID but the frontend won't show them links to older ones.
    # For now, we allow it if they have the ID.
    return db_evaluation

# New endpoint to generate temporary token for an evaluation
@app.get("/evaluations/{evaluation_id}/temp-token", response_model=schemas.Token)
async def get_evaluation_temp_token(
    evaluation_id: int,
    current_user: schemas.User = Depends(security.get_current_active_user), # Ensure user is authenticated to request temp token
    db: Session = Depends(get_db)
):
    db_evaluation = crud.get_evaluation(db, evaluation_id=evaluation_id)
    if db_evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    temp_token_data = {
        "sub": str(db_evaluation.id), # Subject is evaluation ID
        "type": "temp_report_access",
        "user_id": current_user.id # Include user ID for auditing/logging if needed
    }
    temp_token = security.create_temporary_token(temp_token_data)
    return {"access_token": temp_token, "token_type": "bearer"}


@app.post("/report/generate-pdf", response_class=Response)
async def generate_pdf_from_html(
    report_html: schemas.ReportHTML,
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    try:
        html_with_style = report_html.html_content

        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None
        }
        
        pdf_bytes = pdfkit.from_string(html_with_style, False, options=options)
        
        return Response(content=pdf_bytes, media_type="application/pdf")

    except Exception as e:
        print(f"Error generating PDF with pdfkit: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {e}")


@app.put("/evaluations/{evaluation_id}", response_model=schemas.Evaluation)
async def update_evaluation(
    evaluation_id: int,
    evaluation: schemas.EvaluationUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    db_evaluation = crud.get_evaluation(db, evaluation_id=evaluation_id)
    if db_evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada.")

    is_admin = current_user.role == 'administrador'
    is_editor = current_user.role == 'editor_gestor'

    # Solo administradores y editores pueden editar
    if not is_admin and not is_editor:
        raise HTTPException(status_code=403, detail="No tiene permisos para editar evaluaciones.")

    # Restricciones para el rol de editor_gestor
    if is_editor and not is_admin:
        # 1. Verificar propiedad de la evaluación
        if db_evaluation.evaluator_id != current_user.id:
            raise HTTPException(status_code=403, detail="No puede editar evaluaciones de otros usuarios.")

        # 2. Verificar que la evaluación sea de las últimas 24 horas
        # (db_evaluation.timestamp es naive, se le asigna UTC)
        db_timestamp_aware = db_evaluation.timestamp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - db_timestamp_aware > timedelta(hours=24):
            raise HTTPException(
                status_code=403, 
                detail="Como editor, solo puede editar evaluaciones con menos de 24 horas de antigüedad."
            )

    # 3. Validar la nueva fecha y hora si se proporciona
    if evaluation.timestamp:
        # evaluation.timestamp ya es aware gracias al validador que corregimos
        new_timestamp_aware = evaluation.timestamp

        # No se puede poner una fecha en el futuro
        if new_timestamp_aware > datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="La nueva fecha y hora no puede ser en el futuro.")
        
        # Restricción adicional para editores sobre la nueva fecha
        if is_editor and not is_admin:
            if datetime.now(timezone.utc) - new_timestamp_aware > timedelta(hours=24):
                raise HTTPException(
                    status_code=400, 
                    detail="Como editor, la nueva fecha no puede tener más de 24 horas de antigüedad."
                )

    return crud.update_evaluation(db=db, db_evaluation=db_evaluation, evaluation=evaluation)


@app.delete("/evaluations/{evaluation_id}", response_model=schemas.Evaluation)
async def delete_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    db_evaluation = crud.get_evaluation(db, evaluation_id=evaluation_id)
    if db_evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    if current_user.role == 'editor_gestor':
        if db_evaluation.evaluator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not allowed to delete evaluations from other users.")
        # Ensure db_evaluation.timestamp is timezone-aware (UTC) for comparison
        db_evaluation_timestamp_aware = db_evaluation.timestamp.replace(tzinfo=timezone.utc) if db_evaluation.timestamp.tzinfo is None else db_evaluation.timestamp
        if datetime.now(timezone.utc) - db_evaluation_timestamp_aware > timedelta(hours=24):
            raise HTTPException(status_code=403, detail="Can only delete evaluations from the last 24 hours.")
            
    return crud.delete_evaluation(db=db, db_evaluation=db_evaluation)

@app.put("/actions/{action_id}", response_model=schemas.ActionStatus)
async def update_action_status(
    action_id: int,
    action_update: schemas.ActionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    db_action = crud.get_action_status(db, action_id)
    if db_action is None:
        raise HTTPException(status_code=404, detail="ActionStatus not found")

    # Check if the evaluation is one of the last 2, regardless of role
    evaluation = db_action.evaluation
    latest_evaluations = crud.get_evaluations(db, limit=2)
    latest_evaluation_ids = [e.id for e in latest_evaluations]

    if evaluation.id not in latest_evaluation_ids:
        raise HTTPException(status_code=403, detail="Solo se pueden editar las medidas de las últimas 2 claves activadas.")

    # Existing editor_gestor restrictions (if applicable)
    if current_user.role == 'editor_gestor':
        if evaluation.evaluator_id != current_user.id:
            raise HTTPException(status_code=403, detail="No tiene permitido actualizar medidas de evaluaciones de otros usuarios.")
        # Ensure evaluation.timestamp is timezone-aware (UTC) for comparison
        evaluation_timestamp_aware = evaluation.timestamp.replace(tzinfo=timezone.utc) if evaluation.timestamp.tzinfo is None else evaluation.timestamp
        if datetime.now(timezone.utc) - evaluation_timestamp_aware > timedelta(hours=24):
            raise HTTPException(status_code=403, detail="Solo puede actualizar medidas de evaluaciones con menos de 24 horas de antigüedad.")

    return crud.update_action_status(db=db, db_action=db_action, action_update=action_update)


# --- WhatsApp Contact Endpoints ---

@app.post("/whatsapp-contacts/", response_model=schemas.WhatsAppContact)
async def create_whatsapp_contact(
    contact: schemas.WhatsAppContactCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    return crud.create_whatsapp_contact(db=db, contact=contact, user_id=current_user.id)

@app.get("/whatsapp-contacts/", response_model=List[schemas.WhatsAppContact])
async def read_whatsapp_contacts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    contacts = crud.get_whatsapp_contacts_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return contacts

@app.get("/whatsapp-contacts/{contact_id}", response_model=schemas.WhatsAppContact)
async def read_whatsapp_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    db_contact = crud.get_whatsapp_contact(db, contact_id=contact_id, user_id=current_user.id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="WhatsApp Contact not found")
    return db_contact

@app.put("/whatsapp-contacts/{contact_id}", response_model=schemas.WhatsAppContact)
async def update_whatsapp_contact(
    contact_id: int,
    contact: schemas.WhatsAppContactCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    db_contact = crud.update_whatsapp_contact(db, contact_id=contact_id, contact=contact, user_id=current_user.id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="WhatsApp Contact not found or you don't have permission to update it")
    return db_contact

@app.delete("/whatsapp-contacts/{contact_id}", response_model=schemas.WhatsAppContact)
async def delete_whatsapp_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    db_contact = crud.delete_whatsapp_contact(db, contact_id=contact_id, user_id=current_user.id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="WhatsApp Contact not found or you don't have permission to delete it")
    return db_contact

# --- Distribution List Endpoints ---

@app.post("/distribution-lists/", response_model=schemas.DistributionList)
async def create_distribution_list(
    dist_list: schemas.DistributionListCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    return crud.create_distribution_list(db=db, dist_list=dist_list, user_id=current_user.id)

@app.get("/distribution-lists/", response_model=List[schemas.DistributionList])
async def read_distribution_lists(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    dist_lists = crud.get_distribution_lists_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return dist_lists

@app.get("/distribution-lists/{list_id}", response_model=schemas.DistributionList)
async def read_distribution_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    db_list = crud.get_distribution_list(db, list_id=list_id, user_id=current_user.id)
    if db_list is None:
        raise HTTPException(status_code=404, detail="Distribution List not found")
    return db_list

@app.put("/distribution-lists/{list_id}", response_model=schemas.DistributionList)
async def update_distribution_list(
    list_id: int,
    dist_list: schemas.DistributionListCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    db_list = crud.update_distribution_list(db, list_id=list_id, dist_list=dist_list, user_id=current_user.id)
    if db_list is None:
        raise HTTPException(status_code=404, detail="Distribution List not found or you don't have permission to update it")
    return db_list

@app.delete("/distribution-lists/{list_id}", response_model=schemas.DistributionList)
async def delete_distribution_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_active_user)
):
    db_list = crud.delete_distribution_list(db, list_id=list_id, user_id=current_user.id)
    if db_list is None:
        raise HTTPException(status_code=404, detail="Distribution List not found or you don't have permission to delete it")
    return db_list