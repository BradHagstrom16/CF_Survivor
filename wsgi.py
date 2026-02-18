"""WSGI entry point for PythonAnywhere and production servers."""

from app import create_app

app = create_app()
