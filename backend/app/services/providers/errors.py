class ProviderNotConfigured(Exception):
    """Raised instead of fabricating output when a required external provider (LLM, speech-
    to-text) has no credentials configured. The worker turns this into an honest, visible
    job failure rather than silent fake success."""
