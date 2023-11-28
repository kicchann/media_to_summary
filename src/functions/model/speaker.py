from pydantic import BaseModel


class Speaker(BaseModel):
    id: str = ""
    email: str = ""
    name: str = "unknown"
    # feature_vector_file_path: str = ""
