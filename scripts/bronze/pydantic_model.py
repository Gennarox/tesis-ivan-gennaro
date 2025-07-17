from pydantic import BaseModel, ValidationError, Field, ConfigDict
from datetime import datetime


class categories(BaseModel):
    #key: int
    id: int | str = Field(alias = "reference")
    name: str
    slug: str
    supermarket: str            # Metadata
    ingestion_time: datetime    # Metadata

    model_config = ConfigDict(
        populate_by_name = True,
        extra = "ignore"
    )

class products(BaseModel):
    code: str
    name: str
    price: int
    category: str               # Metadata
    supermarket: str            # Metadata
    ingestion_time: datetime    # Metadata    