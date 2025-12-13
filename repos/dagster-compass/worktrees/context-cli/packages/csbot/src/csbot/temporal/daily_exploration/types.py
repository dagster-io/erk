"""Type definitions for daily exploration workflow."""

from pydantic import BaseModel


class DailyExplorationInput(BaseModel):
    bot_id: str
    channel_name: str


class DailyExplorationSuccess(BaseModel):
    pass


DailyExplorationResult = DailyExplorationSuccess
