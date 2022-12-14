import logging
from importlib.resources import path
from pyexpat import model
from re import ASCII
from statistics import mode
from tempfile import template
from turtle import dot
from fastapi import FastAPI,Depends,HTTPException,Request
from fastapi.responses import HTMLResponse
from functools import lru_cache
import app.settings as settings
from typing import List,Optional
from app.db import crud
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.query import query as q
import dotenv
logger = logging.getLogger(__name__)

import pathlib

logging.basicConfig(filename='file.log',level=logging.DEBUG,format="%(asctime)s:%(name)s:%(message)s")

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

BASEDIR  = pathlib.Path(__file__).parent
templates = Jinja2Templates(directory= str(BASEDIR / "templates"))

from app.db import  models, schema
from app.db.sessions import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@app.get("/",response_class=HTMLResponse)
def info(request:Request):
   
    return templates.TemplateResponse("home.html",{"request":request})

@app.get("/countries/", response_model=List[schema.CountryRecord])
def read_country(skip: int = 0, limit: int = 2000, db: Session = Depends(get_db)):
    countries =  crud.get_countries(db, skip=skip, limit=limit)
    return countries

@app.get("/query/term", response_model=schema.CountryRecord)
def read_country(term:int,db: Session = Depends(get_db)):
    
    return crud.get_country(db, id=term)
    

@app.get("/search/")
def auto_complate_countries(term:Optional[str],db:Session = Depends(get_db)):
    best_search_terms = term.strip().split(" ")
    print(best_search_terms)
    query = q.query_set(db=db)
    for item in best_search_terms:
        query = query.filter(models.Record.country.contains(term)) 
    countries = query.all()
    suggestions = []

    for item in countries:
        suggestions.append(item.country)
    logging.info(suggestions)
    print(suggestions)
    return suggestions


def load_txt_file():
    text_db = []
    file = "db.txt"
    _file = pathlib.Path(__file__).parent.resolve()

    file_path = _file / file

    with open(str(file_path),encoding="utf-8") as file:
        for item in file:
            text_db.append(" ".join(item.split()))
    return text_db

txt_db = load_txt_file()

@app.post("/add/country", response_model=schema.CountryRecord)
def create_country(cr: schema.CountryRecord, db: Session = Depends(get_db)):
    db_country = crud.get_country(db, id=cr.id)
    if db_country:
        raise HTTPException(status_code=400, detail="already registered")
    return crud.create_country(db=db, item=cr)

@app.delete("/delete/country/{id}")
def delete_country(id:int,db:Session = Depends(get_db)):
    deleted_record = None
    try:
        deleted_record =  crud.delete_country(id=id,db=db)
    except :
        return {f"{id}":"Does Not exist"}
    return deleted_record

def create_data():
    id = 1
    with Session(engine) as session:

        for item in txt_db:
            cr = schema.CountryRecord(id=id,country=item)
            item = models.Record(**cr.dict())
            # crud.create_country(db=session,item=cr)
            if crud.get_country(id = item.id,db = session):
                return {"Alert":"Item alredy there! Please run delte_all "}
            session.add(item)
            session.commit()
            session.refresh(item)
            id+=1
    return {"Ok":True}

def delete_bulk_data():
    with Session(engine) as session:
        id = 1
        db_item = crud.get_country(id=id,db=session)
        while db_item:
            
            db_item = crud.get_country(id=id,db=session)
            
            if not db_item:
                return 
            session.delete(db_item)
            session.commit()
            id+=1
        # return db_hero


# This is for bulk load and bulk delete database 
 
@app.delete("/delete_all_countries/")
def delete_all_countries():
    delete_bulk_data()
    return {"ok":True}

@app.post("/create_all_countries/")
def create_all_countries():
    
    return create_data()