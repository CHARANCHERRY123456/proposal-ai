"""
Quick script to create a test user profile for development.
Run this before testing the frontend.

Usage:
    python scripts/create_test_user.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from models.user_profile import UserProfile, get_user_profiles_collection, ensure_indexes


async def create_test_user():
    """Create a test user profile."""
    await ensure_indexes()
    
    test_profile = UserProfile(
        companyId="test-company-1",
        companyName="SafeGuard Security",
        website="https://safeguard-security.example.com",
        naicsCodes=["541511", "561621"],
        capabilities=[
            "Physical Security",
            "Access Control Systems",
            "Security Consulting",
            "Surveillance Systems"
        ],
        certifications=[
            "Small Business",
            "SDVOSB"
        ],
        setAsideType="SDVOSBC",
        capabilitiesStatement="SafeGuard Security is a veteran-owned security firm specializing in physical security, access control, and surveillance systems. We have 10+ years of experience serving federal and commercial clients.",
        pastPerformance=[
            {
                "projectName": "Federal Building Access Control",
                "client": "GSA",
                "description": "Installed and maintained access control systems for federal building",
                "projectValue": 250000,
                "year": 2023,
                "keywords": ["access control", "federal", "security systems"]
            },
            {
                "projectName": "Military Base Surveillance",
                "client": "Department of Defense",
                "description": "Deployed surveillance and monitoring systems for military installation",
                "projectValue": 500000,
                "year": 2022,
                "keywords": ["surveillance", "military", "security"]
            }
        ],
        yearsOfExperience=10,
        teamSize=25,
        location={
            "city": "Washington",
            "state": "DC",
            "country": "USA"
        }
    )
    
    coll = get_user_profiles_collection()
    
    # Check if already exists
    existing = await coll.find_one({"companyId": test_profile.companyId})
    if existing:
        print(f"User profile with companyId '{test_profile.companyId}' already exists.")
        print("You can use this companyId to login.")
        return
    
    # Insert
    doc = test_profile.to_mongo()
    result = await coll.insert_one(doc)
    print(f"✅ Created test user profile!")
    print(f"   Company ID: {test_profile.companyId}")
    print(f"   Company Name: {test_profile.companyName}")
    print(f"\nYou can now login to the frontend with companyId: {test_profile.companyId}")


if __name__ == "__main__":
    asyncio.run(create_test_user())
