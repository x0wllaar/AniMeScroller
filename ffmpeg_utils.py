import tempfile
import subprocess
import logging

from utils import GifData

# Get text height or width for current font size with FFmpeg magic
# https://stackoverflow.com/a/63448868
def get_text_size_info(info_type:str, text:str, font:str, fontsize:int) -> float:
    allowed_types = {"width", "height"}
    if info_type not in allowed_types:
        raise ValueError("Bad info_type argument")
    ffmpeg_info_type = "tw" if info_type == "width" else "th"
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as textf:
        print(text, end='', sep='', file=textf)
        textf.flush()
        info_process = subprocess.run([
            "ffmpeg",
            "-v", "24",
            "-hide_banner",
            "-f", "lavfi",
            "-i", "color",
            "-vf",
            f"drawtext='{font}':fontsize={fontsize}:textfile='{textf.name}':x=W/2:y=print({ffmpeg_info_type}\,24)",
            "-vframes", "1",
            "-f", "null", "-"
        ], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if info_process.returncode != 0:
            raise RuntimeError(f"FFmpeg error when getting info {info_type}, code {info_process.returncode}")
        text_info = float(info_process.stderr.decode("utf-8").strip())
        return text_info

def generate_gif(gif_width:int, gif_height:int, gif_time:float, 
                 gif_speed:float, text:str, font:str, fontsize:int,
                 vmarginsize:int) -> bytes:
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as textf:
        print(text, end='', sep='', file=textf)
        textf.flush()
        gif_process = subprocess.run([
            "ffmpeg",
            "-y",
            "-t", str(gif_time),
            "-f", "lavfi",
            "-i", f"color=c=black:s={gif_width}x{gif_height}:r=25/1",
            "-vf",
            f"drawtext='{font}':fontsize={fontsize}:textfile='{textf.name}':y={vmarginsize}:x=w-t*{gif_speed}:fontcolor=white",
            "-f", "gif",
            "-"
        ], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if gif_process.returncode != 0:
            raise RuntimeError(f"FFmpeg exited with error status {gif_process.returncode} when creating GIF" + 
                f"FFmpeg output:" + gif_process.stderr.decode("utf-8").strip())
        return gif_process.stdout

def clear_matrix():
    with tempfile.NamedTemporaryFile(mode="rb", suffix=".png", delete=True) as blackf:
        gen_blackf_process = subprocess.run([
            "ffmpeg",
            "-y", 
            "-t", "1",
            "-f", "lavfi",
            "-i", "color=c=black:s=100x50",
            "-frames:v", "1",
            blackf.name
        ], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if gen_blackf_process.returncode != 0:
            logging.error(f"GIF playback error, code {gen_blackf_process.returncode} error " 
                           + gen_blackf_process.stderr.decode("utf-8").strip())
        black_matrix_process = subprocess.run([
            "asusctl", "anime",
            "image", "-p", blackf.name
        ], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if black_matrix_process.returncode != 0:
            logging.error(f"GIF playback error, code {black_matrix_process.returncode} error " 
                           + black_matrix_process.stderr.decode("utf-8").strip())


def play_gif_data(gif_data: GifData):
    if gif_data.nloops < 1:
            logging.warn(f"Too low loop count {gif_data.nloops}")
            return
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".gif", delete=True) as giff:
        giff.write(gif_data.gif_bytes)
        giff.flush()
        gif_play_process = subprocess.run([
            "asusctl", "anime", 
            "gif", "-p", giff.name,
            "-l", str(gif_data.nloops)
        ], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if gif_play_process.returncode != 0:
            logging.error(f"GIF playback error, code {gif_play_process.returncode} error " 
                           + gif_play_process.stderr.decode("utf-8").strip())