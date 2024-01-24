import gzip
import logging
import os

from fastapi import HTTPException

logger = logging.getLogger("ascii-video-server")

FILES_DIR = "./files"
DELIMITER = "\\~"

if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)


class VideoFileHandler:
    """
    Reads ascii-coded video files from the disk and provides them as a dictionary of frames.
    """

    def __init__(self, video_name: str):
        """
        Creates a new video reader.
        :param video_name: The name of the video to read
        """
        if video_name.endswith(".txt.gz"):
            self.file = f"{FILES_DIR}/{video_name}"
        elif video_name.endswith(".txt"):
            self.file = f"{FILES_DIR}/{video_name}.gz"
        else:
            self.file = f"{FILES_DIR}/{video_name}.txt.gz"

        if not os.path.exists(self.file):
            raise HTTPException(status_code=404, detail=f"File {video_name} not found")

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
        """
        Returns all frames.
        :return:
        """
        return {i: self.frames[i] for i in range(len(self.frames))}

    def get_frames(self, frame_position: int, frame_count: int) -> dict[int, str]:
        """
        Returns the number of frames starting at the given position.
        :param frame_position: The position to start at
        :param frame_count: The number of frames to return
        :return: A dictionary mapping frame positions to frames
        """
        if frame_position >= len(self.frames):
            return {}

        new_frame = frame_position + frame_count

        if new_frame >= len(self.frames):
            new_frame = len(self.frames) - 1

        return {i: self.frames[i] for i in range(frame_position, new_frame)}

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

        logger.info(f"[{filename}] Saving video with {len(frames)} frames to {file}.")

        if os.path.exists(file):
            os.remove(file)

        with gzip.open(file, "wb", compresslevel=5) as f:
            f.write(f"{original_width}x{original_height}x{fps}\n".encode("utf-8"))
            for frame in frames:
                f.write(frame.encode("utf-8"))
                f.write(f"\n{DELIMITER}\n".encode("utf-8"))
