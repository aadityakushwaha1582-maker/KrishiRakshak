import os, math, secrets, json
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import inspect, text
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./krishirakshak.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET = os.getenv("APP_SECRET", "dev-secret-change-me")
if os.getenv("APP_ENV", "development").lower() == "production" and SECRET == "dev-secret-change-me":
    raise RuntimeError("Set a strong APP_SECRET before running in production.")

class Farmer(Base):
    __tablename__ = "farmers"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(30), default="")
    language = Column(String(30), default="English")
    state = Column(String(80), default="")
    district = Column(String(100), default="")
    land_area = Column(Float, default=0)
    land_unit = Column(String(30), default="acre")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_consent = Column(Boolean, nullable=False, default=False)
    location_consent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    farms = relationship("Farm", back_populates="farmer", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="farmer", cascade="all, delete-orphan")

class Farm(Base):
    __tablename__ = "farms"
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"))
    farm_name = Column(String(120), default="My Farm")
    crop = Column(String(100), default="")
    sowing_date = Column(String(30), default="")
    area_acres = Column(Float, default=0)
    soil_type = Column(String(80), default="Unknown")
    irrigation = Column(String(80), default="Rainfed")
    polygon_json = Column(Text, default="[]")
    farmer = relationship("Farmer", back_populates="farms")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"))
    title = Column(String(180), nullable=False)
    due_date = Column(String(30), default="")
    category = Column(String(50), default="General")
    done = Column(Integer, default=0)
    farmer = relationship("Farmer", back_populates="tasks")

Base.metadata.create_all(bind=engine)
# Small forward-only migration for existing SQLite installations.
if DATABASE_URL.startswith("sqlite"):
    existing = {col["name"] for col in inspect(engine).get_columns("farmers")}
    with engine.begin() as conn:
        if "location_consent" not in existing:
            conn.execute(text("ALTER TABLE farmers ADD COLUMN location_consent BOOLEAN NOT NULL DEFAULT 0"))
        if "location_consent_at" not in existing:
            conn.execute(text("ALTER TABLE farmers ADD COLUMN location_consent_at DATETIME"))

app = FastAPI(title="KrishiRakshak", description="Farmer-first agricultural assistance platform")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET,
    session_cookie="kr_session",
    max_age=60 * 60 * 24 * 14,
    same_site="lax",
    https_only=os.getenv("COOKIE_SECURE", "false").lower() == "true",
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

LANGUAGES = [
    "Assamese", "Bengali", "Bodo", "Dogri", "Gujarati", "Hindi", "Kannada",
    "Kashmiri", "Konkani", "Maithili", "Malayalam", "Manipuri", "Marathi",
    "Nepali", "Odia", "Punjabi", "Sanskrit", "Santali", "Sindhi", "Tamil",
    "Telugu", "Urdu"
]

# Indicative regional conversions only. Confirm local revenue-record definition.
LAND_UNITS = {
    "acre": 1.0, "hectare": 2.47105, "square_yard": 0.000206612,
    "gaj": 0.000206612, "kanal_punjab": 0.125, "marla_punjab": 0.00625,
    "bigha_up_approx": 0.625, "bigha_bihar_approx": 0.625,
    "bigha_wb_approx": 0.3306, "guntha": 0.025,
    "cent": 0.01, "katha_bihar_approx": 0.03125
}
CROPS = [
    {"name":"Rice", "season":"Kharif", "min_temp":22, "max_temp":35, "rain":900, "duration":120, "seed":25, "fertilizer":120, "water":1200, "states":["Punjab","Haryana","West Bengal","Bihar","Odisha","Assam","Uttar Pradesh"]},
    {"name":"Maize", "season":"Kharif", "min_temp":18, "max_temp":32, "rain":500, "duration":100, "seed":20, "fertilizer":100, "water":500, "states":["Karnataka","Madhya Pradesh","Bihar","Uttar Pradesh","Rajasthan"]},
    {"name":"Wheat", "season":"Rabi", "min_temp":10, "max_temp":25, "rain":350, "duration":120, "seed":100, "fertilizer":120, "water":450, "states":["Punjab","Haryana","Uttar Pradesh","Madhya Pradesh","Rajasthan","Bihar"]},
    {"name":"Mustard", "season":"Rabi", "min_temp":10, "max_temp":27, "rain":250, "duration":110, "seed":5, "fertilizer":80, "water":250, "states":["Rajasthan","Haryana","Uttar Pradesh","Madhya Pradesh"]},
    {"name":"Chickpea", "season":"Rabi", "min_temp":10, "max_temp":30, "rain":300, "duration":110, "seed":75, "fertilizer":50, "water":250, "states":["Madhya Pradesh","Rajasthan","Maharashtra","Uttar Pradesh"]},
    {"name":"Millets", "season":"Kharif", "min_temp":20, "max_temp":35, "rain":300, "duration":90, "seed":5, "fertilizer":40, "water":250, "states":["Rajasthan","Karnataka","Maharashtra","Gujarat"]},
    {"name":"Groundnut", "season":"Kharif", "min_temp":20, "max_temp":30, "rain":500, "duration":120, "seed":100, "fertilizer":80, "water":500, "states":["Gujarat","Andhra Pradesh","Tamil Nadu","Karnataka"]},
    {"name":"Soybean", "season":"Kharif", "min_temp":20, "max_temp":32, "rain":600, "duration":100, "seed":75, "fertilizer":80, "water":450, "states":["Madhya Pradesh","Maharashtra","Rajasthan"]}
]

def current_farmer(request: Request, db):
    # SessionMiddleware signs the cookie; a client cannot change farmer_id undetected.
    fid = request.session.get("farmer_id")
    if not fid: return None
    try: return db.query(Farmer).filter(Farmer.id == int(fid)).first()
    except (TypeError, ValueError): return None

def acres(area, unit):
    return float(area) * LAND_UNITS.get(unit, 1.0)

def area_unit_options():
    return [{"id":k,"label":k.replace("_"," ").replace(" approx"," (approx.)").title()} for k in LAND_UNITS]

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    db=SessionLocal()
    farmer=current_farmer(request,db)
    if farmer:
        return RedirectResponse("/dashboard",status_code=303)
    return templates.TemplateResponse("index.html", {"request":request,"languages":LANGUAGES})

@app.post("/api/register")
def register(request: Request, name: str=Form(...), email: str=Form(...), password: str=Form(...), phone: str=Form(""), language: str=Form("English"), state: str=Form(""), district: str=Form(""), land_area: float=Form(0), land_unit: str=Form("acre")):
    if len(password)<8: raise HTTPException(400,"Password must be at least 8 characters.")
    db=SessionLocal()
    if db.query(Farmer).filter(Farmer.email==email.lower()).first(): raise HTTPException(409,"An account with this email already exists.")
    f=Farmer(name=name,email=email.lower(),password_hash=pwd_context.hash(password),phone=phone,language=language,state=state,district=district,land_area=land_area,land_unit=land_unit)
    db.add(f); db.commit(); db.refresh(f)
    request.session.clear()
    request.session["farmer_id"] = f.id
    return JSONResponse({"ok":True,"redirect":"/dashboard"})

@app.post("/api/login")
def login(email: str=Form(...), password: str=Form(...)):
    db=SessionLocal(); f=db.query(Farmer).filter(Farmer.email==email.lower()).first()
    if not f or not pwd_context.verify(password,f.password_hash): raise HTTPException(401,"Incorrect email or password.")
    request.session.clear()
    request.session["farmer_id"] = f.id
    return JSONResponse({"ok":True,"redirect":"/dashboard"})

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/",status_code=303)

@app.get("/dashboard",response_class=HTMLResponse)
def dashboard(request:Request):
    db=SessionLocal(); f=current_farmer(request,db)
    if not f: return RedirectResponse("/",status_code=303)
    farms=db.query(Farm).filter(Farm.farmer_id==f.id).all()
    tasks=db.query(Task).filter(Task.farmer_id==f.id).order_by(Task.due_date.asc()).all()
    return templates.TemplateResponse("dashboard.html",{"request":request,"farmer":f,"farms":farms,"tasks":tasks,"languages":LANGUAGES,"units":area_unit_options()})

@app.post("/api/profile")
def update_profile(
    request: Request,
    name: Optional[str] = Form(None), phone: Optional[str] = Form(None),
    language: Optional[str] = Form(None), state: Optional[str] = Form(None),
    district: Optional[str] = Form(None), land_area: Optional[float] = Form(None),
    land_unit: Optional[str] = Form(None), latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
):
    db=SessionLocal(); f=current_farmer(request,db)
    if not f: raise HTTPException(401,"Please log in.")
    # Partial update: omitted fields remain unchanged.
    for field, value in {"name":name,"phone":phone,"language":language,"state":state,
                         "district":district,"land_area":land_area,"land_unit":land_unit}.items():
        if value is not None:
            setattr(f, field, value)
    if (latitude is None) != (longitude is None):
        raise HTTPException(400,"Latitude and longitude must be supplied together.")
    if latitude is not None:
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise HTTPException(400,"Coordinates are outside valid ranges.")
        f.latitude, f.longitude = latitude, longitude
    db.commit()
    return {"ok":True}

@app.post("/api/location")
def save_location(
    request: Request,
    latitude: float = Form(...), longitude: float = Form(...),
    consent: str = Form(...), state: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
):
    db=SessionLocal(); f=current_farmer(request,db)
    if not f: raise HTTPException(401,"Please log in.")
    if consent.lower() not in {"true", "yes", "1", "on"}:
        raise HTTPException(400,"Please provide consent before saving farm location.")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(400,"Coordinates are outside valid ranges.")
    f.latitude, f.longitude = latitude, longitude
    if state is not None: f.state = state
    if district is not None: f.district = district
    f.location_consent = True
    f.location_consent_at = datetime.utcnow()
    db.commit()
    return {"ok":True,"message":"Farm location saved with your consent."}

@app.delete("/api/location")
def delete_location(request: Request):
    db=SessionLocal(); f=current_farmer(request,db)
    if not f: raise HTTPException(401,"Please log in.")
    f.latitude = None; f.longitude = None
    f.location_consent = False; f.location_consent_at = None
    db.commit()
    return {"ok":True,"message":"Saved location deleted."}

@app.post("/api/farm")
def add_farm(request:Request, farm_name:str=Form("My Farm"), crop:str=Form(""), sowing_date:str=Form(""), area_acres:float=Form(0), soil_type:str=Form("Unknown"), irrigation:str=Form("Rainfed"), polygon_json:str=Form("[]")):
    db=SessionLocal(); f=current_farmer(request,db)
    if not f: raise HTTPException(401,"Please log in.")
    farm=Farm(farmer_id=f.id,farm_name=farm_name,crop=crop,sowing_date=sowing_date,area_acres=area_acres,soil_type=soil_type,irrigation=irrigation,polygon_json=polygon_json)
    db.add(farm); db.commit(); return {"ok":True}

@app.get("/api/weather")
async def weather(request:Request, latitude:float, longitude:float):
    # Live forecast from Open-Meteo. Weather data is forecast, not an official warning.
    url="https://api.open-meteo.com/v1/forecast"
    params={"latitude":latitude,"longitude":longitude,"current":"temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m","daily":"temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,et0_fao_evapotranspiration","timezone":"auto","forecast_days":7}
    async with httpx.AsyncClient(timeout=15) as client:
        resp=await client.get(url,params=params)
        if resp.status_code!=200: raise HTTPException(502,"Weather service is temporarily unavailable.")
        return resp.json()

@app.get("/api/crops")
def crop_recommendations(state:str="", month:int=0, temp:float=25, rainfall:float=50, land_acres:float=1):
    month=month or datetime.now().month
    season="Kharif" if month in [6,7,8,9] else ("Rabi" if month in [10,11,12,1,2,3] else "Zaid")
    results=[]
    for c in CROPS:
        score=60
        if c["season"]==season: score+=20
        if c["min_temp"]<=temp<=c["max_temp"]: score+=10
        if rainfall*30>=c["rain"]*0.65: score+=5
        if state and state in c["states"]: score+=10
        results.append({**c,"score":min(score,98),"seed_total_kg":round(c["seed"]*land_acres,1),"fertilizer_total_kg":round(c["fertilizer"]*land_acres,1),"water_total_m3_approx":round(c["water"]*land_acres,1)})
    return sorted(results,key=lambda x:x["score"],reverse=True)[:5]

@app.get("/api/land")
def land_convert(value:float,unit:str):
    if unit not in LAND_UNITS: raise HTTPException(400,"Unknown land unit.")
    return {"input":value,"unit":unit,"acres":round(acres(value,unit),4),"hectares":round(acres(value,unit)/2.47105,4),"note":"Approximate conversion. Verify bigha/katha/kanal definitions with local land records."}

@app.post("/api/task")
def add_task(request:Request,title:str=Form(...),due_date:str=Form(""),category:str=Form("General")):
    db=SessionLocal(); f=current_farmer(request,db)
    if not f: raise HTTPException(401,"Please log in.")
    db.add(Task(farmer_id=f.id,title=title,due_date=due_date,category=category)); db.commit(); return {"ok":True}

@app.post("/api/task/{task_id}/toggle")
def toggle_task(request:Request,task_id:int):
    db=SessionLocal(); f=current_farmer(request,db)
    t=db.query(Task).filter(Task.id==task_id,Task.farmer_id==f.id).first() if f else None
    if not t: raise HTTPException(404,"Task not found.")
    t.done=0 if t.done else 1; db.commit(); return {"ok":True}

@app.post("/api/disease-check")
async def disease_check(request:Request, photo:UploadFile=File(...)):
    db=SessionLocal(); f=current_farmer(request,db)
    if not f: raise HTTPException(401,"Please log in.")
    if not photo.content_type or photo.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(400,"Please upload a JPG, PNG or WebP image.")
    content=await photo.read(8*1024*1024 + 1)
    if len(content)>8*1024*1024: raise HTTPException(413,"Image must be smaller than 8 MB.")
    # Check file signatures; MIME headers alone can be spoofed.
    valid = ((photo.content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff")) or
             (photo.content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n")) or
             (photo.content_type == "image/webp" and content.startswith(b"RIFF") and content[8:12] == b"WEBP"))
    if not valid: raise HTTPException(400,"The uploaded file does not match its image type.")
    # Honest MVP behaviour: image accepted, no trained classifier bundled.
    return {"status":"preliminary","message":"Photo received. A validated crop-disease AI model is not connected in this MVP, so no disease diagnosis is being claimed.","next_steps":["Photograph the whole plant and a close-up of affected leaves in daylight.","Check both sides of leaves and inspect nearby plants.","Avoid spraying chemicals until the cause is identified by a local agriculture officer/KVK.","If you share crop name, district and symptoms, an expert can narrow down possible causes."]}

@app.get("/api/markets")
def markets(crop:str="Wheat", state:str="Punjab"):
    # Demo rows only until data.gov.in API key + exact AGMARKNET resource are configured.
    return {"mode":"demo","notice":"Illustrative sample prices only — not live or tradable quotes. Connect the AGMARKNET/data.gov.in resource for current prices.","markets":[
        {"name":f"{state} APMC sample market","crop":crop,"modal_price":"₹2,275 / quintal","distance_km":"—","updated":"Illustrative sample"},
        {"name":"Nearby regulated mandi (sample)","crop":crop,"modal_price":"₹2,310 / quintal","distance_km":"—","updated":"Illustrative sample"},
        {"name":"Regional wholesale market (sample)","crop":crop,"modal_price":"₹2,245 / quintal","distance_km":"—","updated":"Illustrative sample"}
    ]}

@app.get("/api/health")
def health():
    return {"status":"ok","app":"KrishiRakshak","authentication":"signed session cookie",
            "weather":"Open-Meteo live forecast when reachable","market_data":"demo until configured",
            "disease_model":"not connected","translations":"fallback until Bhashini adapter configured",
            "flood_alerts":"official links and static guidance; no live feed"}

@app.get("/api/flood-guidance")
def flood_guidance():
    return {"before":["Follow official IMD and Central Water Commission alerts; do not rely on this app as the sole warning source.","Move seed, fertilizer, pesticides, machinery and livestock to raised safe storage.","Clear drainage channels and harvest mature crops early where safe.","Keep important documents, medicines, drinking water and emergency contacts ready."],
    "during":["Never walk or drive through moving floodwater.","Switch off electricity where safe; move people and animals to higher ground.","Do not touch submerged electrical equipment or use contaminated water."],
    "after":["Wait for official all-clear before returning to fields.","Photograph crop, input and infrastructure damage for insurance/relief claims.","Drain stagnant water safely; avoid entering fields with hidden pits or live wires.","Test soil and irrigation water before replanting; consult KVK/state agriculture staff for crop choice."]}

@app.get("/api/translate")
async def translate(text:str, target:str):
    # Bhashini credentials and pipeline configuration are required for production translation.
    if not os.getenv("BHASHINI_USER_ID") or not os.getenv("BHASHINI_API_KEY"):
        return {"translated":text,"mode":"fallback","notice":"Bhashini credentials are not configured; showing original text."}
    return {"translated":text,"mode":"configured","notice":"Connect your approved Bhashini pipeline endpoint in this adapter to enable translation."}
