#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
import math
import tempfile
import pickle

import zmq

from utils import GifData, PICKLE_PROTOCOL_VERSION

DEFAULT_FONT_NAME = "./NotoSansMono-SemiBold.ttf"
# This is a cluge to refer to files relative to the script
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def die(*args, **kwargs):
    print("ERROR:", *args, file=sys.stderr, **kwargs)
    exit(1)

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


def main():
    parser = argparse.ArgumentParser()
    srcg = parser.add_mutually_exclusive_group(required=True)
    srcg.add_argument("-t", "--text",
                        help="Text to scroll")
    srcg.add_argument("--textfile",
                        help="File from which to get the text to scroll (pass - to read from stdin)")
    outg = parser.add_mutually_exclusive_group(required=True)
    outg.add_argument("-o", "--output",
                        help="Name of the output file (pass - to write to stdout)")
    outg.add_argument("--socket", 
                        help="ZMQ PULL socket of GIF playback server")
    parser.add_argument("--font",
                        help="Font to use",
                        required=False,
                        default=os.path.join(SCRIPT_DIR, DEFAULT_FONT_NAME))
    parser.add_argument("--fontsize",
                        help="Size of the font",
                        required=False,
                        type=int,
                        default=40)
    speedg = parser.add_argument_group(title="Control scrolling speed or time")
    speedg.add_argument("--scrollspeedtype", 
                        help="The type of scrolling speed control to use",
                        required=False,
                        type=str,
                        choices=["pixelpersecond", "charpersecond", "second"],
                        default="charpersecond")
    speedg.add_argument("--scrollspeed",
                        help="Scroll speed or time in units specifed by --scrollspeedtype",
                        required=False,
                        type=int,
                        default=6)
    parser.add_argument("--vmarginsize",
                        help="Vertical margin size (in pixels)",
                        required=False,
                        type=int,
                        default=5)
    widthg = parser.add_argument_group(title="Control the width of the generated GIF")
    widthg.add_argument("--windowwidthunit",
                        help="The unit of window width",
                        required=False,
                        type=str,
                        choices=["character", "pixel"],
                        default="character")
    widthg.add_argument("--windowwidth",
                        help="Width (in units specified by --windowwidthunit) of the generated GIF",
                        required=False,
                        type=int,
                        default=4)
    parser.add_argument("--delayafter",
                        help="Artificial delay after the text has scrolled",
                        required=False,
                        type=float,
                        default=0)
    parser.add_argument("--loops",
                        help="When sending GIF to a server, for how many loops to play it",
                        required=False,
                        type=int,
                        default=1)
    args = parser.parse_args()

    if args.text is not None:
        gif_text = args.text
    if args.textfile is not None:
        if args.textfile == "-":
            gif_text = sys.stdin.read()
        else:
            with open(args.textfile, "r", encoding="utf-8") as tf:
                gif_text = tf.read()
    gif_text = " ".join(gif_text.split("\n")).strip()

    if args.scrollspeed <= 0:
        die("Cannot set scroll speed or time to be less or equal to zero")
    if args.windowwidth <= 0:
        die("Cannot set window width to be less or equal to zero")
    if args.loops < 1:
        die("Refusing to send infinite or negative loops to server")


    text_height = get_text_size_info(
        info_type="height",
        text=gif_text,
        font=args.font,
        fontsize=args.fontsize
    )

    text_width = get_text_size_info(
        info_type="width",
        text=gif_text,
        font=args.font,
        fontsize=args.fontsize
    )

    gif_height = 2 * args.vmarginsize + math.ceil(text_height)
    if args.windowwidthunit == "pixel":
        gif_width = args.windowwidth
    elif args.windowwidthunit == "character":
        gif_width = args.windowwidth * text_width / len(gif_text)
        gif_width = math.ceil(gif_width)
    else:
        die("Impossible combination of width args")

    if args.scrollspeedtype == "second":
        gif_time = args.scrollspeed
        gif_speed = (text_width + gif_width) / args.scrollspeed
    elif args.scrollspeedtype == "pixelpersecond":
        gif_time = (text_width + gif_width) / args.scrollspeed
        gif_speed = args.scrollspeed
    elif args.scrollspeedtype == "charpersecond":
        gif_speed = args.scrollspeed * text_width / len(gif_text)
        gif_time = (text_width + gif_width) / gif_speed
    else:
        die("Impossible combination of time/speed args")
    gif_time += args.delayafter

    gif_bytes = generate_gif(
        gif_width=gif_width,
        gif_height=gif_height,
        gif_time=gif_time,
        gif_speed=gif_speed,
        text=gif_text,
        font=args.font,
        fontsize=args.fontsize,
        vmarginsize=args.vmarginsize,
    )
    if args.output is not None:
        if args.output == "-":
            sys.stdout.buffer.write(gif_bytes)
        else:
            with open(args.output, "wb") as giff:
                giff.write(gif_bytes)
    elif args.socket is not None:
        g_data = GifData(nloops=args.loops, gif_bytes=gif_bytes)
        ctx = zmq.Context.instance()
        g_socket = ctx.socket(zmq.PUSH)
        g_socket.connect(args.socket)

        pickle_gif_bytes = pickle.dumps(g_data, protocol=PICKLE_PROTOCOL_VERSION)
        g_socket.send(pickle_gif_bytes)


if __name__ == "__main__":
    main()
