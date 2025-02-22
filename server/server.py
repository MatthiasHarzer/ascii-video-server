import os
import tempfile

import cv2
from fastapi import FastAPI, UploadFile, HTTPException, Depends

from server import auth, log
from server.video_cache import get_video_worker
from server.video_file_handler import VideoFileHandler
from server.video_renderer import VideoRenderer

RUNNER: dict[str, VideoRenderer] = {}
ALWAYS_LOADED_FILES = os.environ.get("ALWAYS_LOADED_FILES", "").split(",")
MAX_PARALLEL_RUNS = int(os.environ.get("MAX_PARALLEL_RUNS", 5))

app = FastAPI()

for _filename in ALWAYS_LOADED_FILES:
    if not _filename:
        continue
    try:
        get_video_worker(_filename, True)
        log.info(f"Loaded file {_filename}")
    except Exception as e:
        log.warning(f"Failed to load file {_filename}: {e}")


def _clear_dead_runners():
    """
    Clears all dead runners.
    """
    global RUNNER
    RUNNER = {k: v for k, v in RUNNER.items() if v.running and not k in ALWAYS_LOADED_FILES}


@app.post("/convert", dependencies=[Depends(auth.api_key_auth)])
async def convert_uploaded(file: UploadFile, width: int = 240):
    """
    Converts the given file to ascii art.
    :param file: The file to convert
    :param width: The width (number of characters) of the ascii art. Height is calculated automatically.
    :return: The ascii art
    """
    _clear_dead_runners()
    filename = ".".join(file.filename.split(".")[:-1])

    log.info(f"Received file {file.filename}.")

    if filename in RUNNER:
        raise HTTPException(status_code=409, detail="File is already processing")

    if len(RUNNER) >= MAX_PARALLEL_RUNS:
        raise HTTPException(status_code=409, detail="Too many parallel runs")

    with tempfile.NamedTemporaryFile() as temp:
        temp.write(file.file.read())
        temp.flush()

        video = cv2.VideoCapture(temp.name)

        renderer = VideoRenderer(video, width, filename)
        renderer.start_render()

        RUNNER[filename] = renderer

        return {
            "state": "processing",
            "filename": filename
        }


@app.get("/files/{filename}")
async def get_file(filename: str, start_frame: int = 0, frames: int = 0):
    worker = try_get_worker(filename)

    if frames <= 0:
        frames_to_send = worker.get_all_frames()
    else:
        frames_to_send = worker.get_frames(start_frame, frames)

    return {
        "frames": frames_to_send,
        "fps": worker.fps,
        "original_width": worker.original_width,
        "original_height": worker.original_height
    }


def try_get_worker(filename) -> VideoFileHandler:
    _clear_dead_runners()
    runner = RUNNER.get(filename)
    if runner:
        raise HTTPException(status_code=409, detail={
            "state": "processing",
            "progress": f"{round(runner.progress * 10000) / 100} %",
            "message": "File is still processing"
        })

    return get_video_worker(filename)


@app.get("/files/{filename}/info")
async def get_file_info(filename: str):
    worker = try_get_worker(filename)

    return {
        "frames_count": len(worker.frames),
        "fps": worker.fps,
        "original_width": worker.original_width,
        "original_height": worker.original_height
    }
