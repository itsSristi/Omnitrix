from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.company import Company
from app.models.job import Job

router = APIRouter(prefix="/companies", tags=["Companies"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def list_companies(db: Session = Depends(get_db)):
    """List hiring partner companies."""
    companies = db.query(Company).all()
    if not companies:
        # Seed initial demo companies
        demo_companies = [
            Company(
                name="Google",
                industry="Technology",
                website="https://google.com",
                location="Mountain View, CA",
                description="Global leader in search, cloud computing, and artificial intelligence.",
                size="10000+",
            ),
            Company(
                name="Microsoft",
                industry="Software & Cloud",
                website="https://microsoft.com",
                location="Redmond, WA",
                description="Empowering every person and organization on the planet to achieve more.",
                size="10000+",
            ),
            Company(
                name="Amazon",
                industry="E-commerce & Cloud",
                website="https://amazon.com",
                location="Seattle, WA",
                description="Earth's most customer-centric company and AWS cloud leader.",
                size="10000+",
            ),
        ]
        for comp in demo_companies:
            db.add(comp)
        db.commit()
        companies = db.query(Company).all()

    return [
        {
            "id": c.id,
            "name": c.name,
            "industry": c.industry,
            "website": c.website,
            "location": c.location,
            "description": c.description,
            "size": c.size,
        }
        for c in companies
    ]


@router.get("/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db)):
    """Get company profile and open job postings."""
    comp = db.query(Company).filter(Company.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Company not found")

    jobs = db.query(Job).filter(Job.company_id == comp.id).all()
    return {
        "id": comp.id,
        "name": comp.name,
        "industry": comp.industry,
        "website": comp.website,
        "location": comp.location,
        "description": comp.description,
        "size": comp.size,
        "jobs": [
            {
                "id": j.id,
                "title": j.title,
                "description": j.description,
                "required_skills": j.required_skills,
                "location": j.location,
                "salary_range": j.salary_range,
                "job_type": j.job_type,
            }
            for j in jobs
        ],
    }
