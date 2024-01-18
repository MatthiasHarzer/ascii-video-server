import gzip
import logging
import os

from fastapi import HTTPException

FILES_DIR = "./files"
DELIMITER = "\\~"

if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)


class VideoWorker:
    def __init__(self, filename: str):
        self.file = f"{FILES_DIR}/{filename}.txt.gz"

        if not os.path.exists(self.file):
            raise HTTPException(status_code=404, detail=f"File {filename} not found")

        with gzip.open(self.file, "rb", compresslevel=5) as f:
            content = f.read().decode("utf-8")

        self.original_width, self.original_height, self.fps = content.split("\n")[0].split("x")
        self.original_width = int(self.original_width)
        self.original_height = int(self.original_height)
        self.fps = int(self.fps)

        self.frames = content.split(f"\n{DELIMITER}\n")

        if len(self.frames) == 0:
            raise HTTPException(status_code=400, detail="No frames found")

        self.frames[0] = "\n".join(self.frames[0].split("\n")[1:])

        self.memory: dict[str, int] = {}
        """
        Maps reference ids to the current frame.
        """

    def get_all_frames(self) -> dict[int, str]:
        return {i: self.frames[i] for i in range(len(self.frames))}

    def get_frames(self, frame_position: int, frame_count: int) -> dict[int, str]:
        if frame_position >= len(self.frames):
            return {}

        new_frame = frame_position + frame_count

        if new_frame >= len(self.frames):
            new_frame = len(self.frames) - 1

        return {i: self.frames[i] for i in range(frame_position, new_frame)}

    def advance_frames(self, reference_id: str, frames_count: int) -> list[str]:
        """
        Advances the frame for the reference id.
        :param reference_id: The reference id
        :param frames_count: The number of frames to advance
        :return: The frames
        """
        current_frame = self.memory.get(reference_id, 0)

        if current_frame >= len(self.frames):
            return []

        new_frame = current_frame + frames_count

        if new_frame >= len(self.frames):
            new_frame = len(self.frames) - 1

        self.memory[reference_id] = new_frame

        return self.frames[current_frame:new_frame]

    def completed(self, reference_id: str) -> bool:
        """
        Checks if the reference id has completed.
        :param reference_id: The reference id
        :return: True if the reference id has completed, False otherwise
        """
        return self.memory[reference_id] >= len(self.frames)

    @staticmethod
    def save_video(frames: list[str], filename: str, original_width: int, original_height: int, fps: int) -> None:
        """
        Saves the ascii art to a file.
        :param fps:
        :param original_height:
        :param original_width:
        :param frames: The ascii art to save
        :param filename: The filename to save to
        """
        file = f"{FILES_DIR}/{filename}.txt.gz"

        logging.info(f"[{filename}] Saving video with {len(frames)} frames to {file}.")

        if os.path.exists(file):
            os.remove(file)

        with gzip.open(file, "wb", compresslevel=5) as f:
            f.write(f"{original_width}x{original_height}x{fps}\n".encode("utf-8"))
            for frame in frames:
                f.write(frame.encode("utf-8"))
                f.write(f"\n{DELIMITER}\n".encode("utf-8"))
