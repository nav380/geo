"""
Thin wrapper around Vertex AI's Gemini models.

Authenticates using a service-account JSON key file (vertex.json) rather
than application-default credentials, so the whole app is portable and the
credential is explicit and swappable.
"""
import json
import re

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig


class VertexClient:
    def __init__(self, credentials_path: str, project_id: str, location: str, model_name: str):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        vertexai.init(project=project_id, location=location, credentials=credentials)
        self._model = GenerativeModel(model_name)

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        text = text.strip()
        text = re.sub(r"^```(json)?", "", text.strip())
        text = re.sub(r"```$", "", text.strip())
        return text.strip()

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict:
        response = self._model.generate_content(
            [system_prompt, user_prompt],
            generation_config=GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        raw = self._strip_code_fence(response.text)
        return json.loads(raw)

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
        response = self._model.generate_content(
            [system_prompt, user_prompt],
            generation_config=GenerationConfig(temperature=temperature),
        )
        return response.text.strip()
