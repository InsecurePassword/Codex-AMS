#!/usr/bin/env python3
"""Run the shared installer transaction fixtures under native Windows PowerShell."""
from __future__ import annotations
import os
os.environ.pop("PSModulePath", None)
import verify_installers
raise SystemExit(verify_installers.main())
