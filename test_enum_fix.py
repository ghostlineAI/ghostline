#!/usr/bin/env python3
"""Test script to verify enum handling for project creation"""

import sys
from sqlalchemy import create_engine, text
from app.models.project import ProjectStatus, BookGenre

def test_enum_values():
    """Test that enum values are correctly formatted"""
    print("Testing Enum Values:")
    print(f"  ProjectStatus.DRAFT = {ProjectStatus.DRAFT}")
    print(f"  ProjectStatus.DRAFT.value = {ProjectStatus.DRAFT.value}")
    print(f"  BookGenre.FICTION = {BookGenre.FICTION}")
    print(f"  BookGenre.FICTION.value = {BookGenre.FICTION.value}")
    print()
    
    # Test what would be inserted
    print("Testing SQLAlchemy Enum behavior:")
    print(f"  str(ProjectStatus.DRAFT) = {str(ProjectStatus.DRAFT)}")
    print(f"  repr(ProjectStatus.DRAFT) = {repr(ProjectStatus.DRAFT)}")
    
    # Verify all values are lowercase
    print("\nAll ProjectStatus values:")
    for status in ProjectStatus:
        print(f"  {status.name} -> {status.value}")
        
    print("\nAll BookGenre values:")
    for genre in BookGenre:
        print(f"  {genre.name} -> {genre.value}")

if __name__ == "__main__":
    test_enum_values() 