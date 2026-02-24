from typing import Literal

from pydantic import BaseModel, Field


class PlanListCommand(BaseModel):
    type: Literal["plan_list"] = "plan_list"


class QuoteCommand(BaseModel):
    type: Literal["quote"] = "quote"


class OneShotCommand(BaseModel):
    type: Literal["one_shot"] = "one_shot"
    message: str = Field(min_length=1)


class OneShotMissingMessageCommand(BaseModel):
    type: Literal["one_shot_missing_message"] = "one_shot_missing_message"


Command = PlanListCommand | QuoteCommand | OneShotCommand | OneShotMissingMessageCommand


class RunResult(BaseModel):
    exit_code: int
    output: str
    timed_out: bool = False
