"""Helper submodules for the NutriSigno application.

This package groups together utilities for interacting with external
services such as Firebase and OpenAI, for generating PDFs and charts,
and for computing nutrition‑related insights.  Each module encapsulates
an aspect of the application’s logic to keep the top‑level app
readable.
"""

__all__: list[str] = [
    "firebase_utils",
    "openai_utils",
    "pdf_generator",
    "pdf_generator_v2",
    "dashboard_utils",
    "email_utils",
    "plan_post_payment",
    "share_image",
    "instagram_post_image",
    "results_context",
]
