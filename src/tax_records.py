"""Show-linked mileage and tax-year bookkeeping exports.

No deductions, estimated tax, entity classification, or 1099 filing decisions.
This module stores factual records only.
"""
import csv
import io
import datetime
from fastapi import APIRouter,HTTPException,Response
from pydantic import BaseModel,Field
router=APIRouter()
class Trip(BaseModel):
    date:datetime.date
    purpose:str=Field(min_length=1,max_length=240)
    origin:str=Field(min_length=1,max_length=200)
    destination:str=Field(min_length=1,max_length=200)
    miles:float=Field(gt=0,le=5000)
    event_id:int|None=None
def setup(con):
    con.execute("""CREATE TABLE IF NOT EXISTS business_trips (
      id INTEGER PRIMARY KEY,band_id INTEGER NOT NULL REFERENCES bands(id),
      event_id INTEGER REFERENCES events(id),trip_date TEXT NOT NULL,
      purpose TEXT NOT NULL,origin TEXT NOT NULL,destination TEXT NOT NULL,
      miles REAL NOT NULL CHECK(miles>0 AND miles<=5000),
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
def attach(db):
    def band(con,band_id):
        if not con.execute('SELECT 1 FROM bands WHERE id=?',(band_id,)).fetchone():
            raise HTTPException(404,"Band not found")
    @router.post('/api/bands/{band_id}/trips',status_code=201)
    def record_trip(band_id:int,data:Trip):
        with db() as con:
            band(con,band_id)
            if data.event_id is not None and not con.execute(
                'SELECT 1 FROM events WHERE band_id=? AND id=?',(band_id,data.event_id)).fetchone():
                raise HTTPException(422,"Show must belong to band")
            row=con.execute("""INSERT INTO business_trips
                (band_id,event_id,trip_date,purpose,origin,destination,miles)
                VALUES(?,?,?,?,?,?,?)""",(band_id,data.event_id,str(data.date),
                  data.purpose,data.origin,data.destination,data.miles))
            return {"id":row.lastrowid}
    @router.get('/api/bands/{band_id}/trips')
    def trips(band_id:int,year:int|None=None):
        with db() as con:
            band(con,band_id)
            if year is not None and not 2000<=year<=2100:raise HTTPException(422,"Invalid year")
            sql='SELECT * FROM business_trips WHERE band_id=?'
            args=[band_id]
            if year is not None:
                sql+=' AND trip_date>=? AND trip_date<?'
                args.extend([f'{year}-01-01',f'{year+1}-01-01'])
            return [dict(r) for r in con.execute(sql+' ORDER BY trip_date,id',args)]
    @router.get('/api/bands/{band_id}/tax-export/{year}')
    def tax_export(band_id:int,year:int):
        if not 2000<=year<=2100:raise HTTPException(422,"Invalid year")
        with db() as con:
            band(con,band_id)
            trips=list(con.execute("""SELECT trip_date,purpose,origin,destination,miles,event_id
               FROM business_trips WHERE band_id=? AND trip_date>=? AND trip_date<?
               ORDER BY trip_date,id""",(band_id,f'{year}-01-01',f'{year+1}-01-01')))
            transactions=list(con.execute("""SELECT date,kind,description,category,
               amount_cents,event_id FROM transactions WHERE band_id=?
               AND date>=? AND date<? ORDER BY date,id""",
               (band_id,f'{year}-01-01',f'{year+1}-01-01')))
        sink=io.StringIO()
        writer=csv.writer(sink)
        writer.writerow(['record_type','date','description','category','amount_usd',
                         'miles','origin','destination','event_id'])
        for x in transactions:
            writer.writerow(['ledger',x['date'],x['description'],x['category'],
                f"{x['amount_cents']/100:.2f}",'','','',x['event_id'] or ''])
        for x in trips:
            writer.writerow(['mileage',x['trip_date'],x['purpose'],'','','%.2f'%x['miles'],
                x['origin'],x['destination'],x['event_id'] or ''])
        return Response(sink.getvalue(),media_type='text/csv',
            headers={'Content-Disposition':f'attachment; filename="backline-records-{year}.csv"',
                     'Cache-Control':'no-store'})
    return router
