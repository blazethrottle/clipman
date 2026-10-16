from dataclasses import asdict

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.capture import Selection
from app.wrappers import ffmpeg, ytdlp


class CaptureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    video_id: str
    url: str
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)
    quality: str = "best"

    @model_validator(mode="after")
    def valid_selection(self):
        self.selection()
        ytdlp.format_selector(self.quality)
        return self

    def selection(self):
        return Selection(self.video_id, self.url, self.start_sec, self.end_sec)


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    trim_start: float | None = Field(default=None, ge=0)
    trim_end: float | None = Field(default=None, gt=0)
    mode: ffmpeg.EncodeMode = ffmpeg.EncodeMode.CROP
    crop_x: int | None = Field(default=None, ge=0)

    def options(self):
        return ffmpeg.EditOptions(**self.model_dump())
