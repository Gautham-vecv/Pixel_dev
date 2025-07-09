from pydantic import BaseModel, Field


class SQLResponse(BaseModel):
    valid_request: bool = Field(
        ...,
        description="True if the user's request was successfully translated into a valid SQL query; False otherwise."
    )
    query: str = Field(
        ...,
        description="The generated SQL query when valid_request is True, or an empty string otherwise."
    )
    reason: str = Field(
        ...,
        description="If valid_request is False, a brief explanation of why the request is invalid; otherwise an empty string."
    )