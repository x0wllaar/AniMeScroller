#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
import math

DEFAULT_FONT_NAME = "./NotoSansMono-SemiBold.ttf"
# This is a cluge to refer to files relative to the script
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def die(*args, **kwargs):
    print("ERROR:", *args, file=sys.stderr, **kwargs)
    exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--text",
                        help="Text to scroll",
                        required=True)
    parser.add_argument("-o", "--output",
                        help="Name of the output file",
                        required=True)
    parser.add_argument("--font",
                        help="Font to use",
                        required=False,
                        default=os.path.join(SCRIPT_DIR, DEFAULT_FONT_NAME))
    parser.add_argument("--fontsize",
                        help="Size of the font",
                        required=False,
                        type=int,
                        default=40)
    parser.add_argument("--scrollspeedp",
                        help="Scroll speed in pixels per second",
                        required=False,
                        type=int,
                        default=-1)
    parser.add_argument("--scrollspeedc",
                        help="Scroll speed in characters per second",
                        required=False,
                        type=int,
                        default=6)
    parser.add_argument("--scrolltime",
                        help="Time (in seconds) for which to scroll the text",
                        required=False,
                        type=float,
                        default=-1)
    parser.add_argument("--vmarginsize",
                        help="Vertical margin size (in pixels)",
                        required=False,
                        type=int,
                        default=5)
    parser.add_argument("--windowwidthp",
                        help="Width (in pixels) of the generated GIF",
                        required=False,
                        type=int,
                        default=-1)
    parser.add_argument("--windowwidthc",
                        help="Width (in charachets) of the generated GIF",
                        required=False,
                        type=int,
                        default=4)
    parser.add_argument("--delayafter",
                        help="Artificial delay after the text has scrolled",
                        required=False,
                        type=float,
                        default=0)
    args = parser.parse_args()

    if args.scrollspeedp < 0 and args.scrolltime < 0 and args.scrollspeedc < 0:
        die("Either scroll speed in pixels / characters or scroll time should be set to a value >0")
    if int(args.scrollspeedp > 0) + int(args.scrolltime > 0) + int(args.scrollspeedc > 0) > 1:
        die("Only one of scroll time or scroll speed in pixels / characters can be set to value >0")

    if args.windowwidthp < 0 and args.windowwidthc < 0:
        die("Either window width in pixels or in characters should be set to a value >0")
    if args.windowwidthp > 0 and args.windowwidthc > 0:
        die("Only one of window width in pixels or in characters can be set to value >0")

    # Get text height for current font size with FFmpeg magic
    # https://stackoverflow.com/a/63448868
    height_process = subprocess.run([
        "ffmpeg",
        "-v", "24",
        "-hide_banner",
        "-f", "lavfi",
        "-i", "color",
        "-vf",
        f"drawtext='{args.font}':fontsize={args.fontsize}:text='{args.text}':x=W/2:y=print(th\,24)",
        "-vframes", "1",
        "-f", "null", "-"
    ], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    if height_process.returncode != 0:
        die("FFmpeg error when getting height, code",
            height_process.returncode)
    text_height = float(height_process.stderr.decode("utf-8").strip())

    # Get text width for current font size with FFmpeg magic
    # https://stackoverflow.com/a/63448868
    width_process = subprocess.run([
        "ffmpeg",
        "-v", "24",
        "-hide_banner",
        "-f", "lavfi",
        "-i", "color",
        "-vf",
        f"drawtext='{args.font}':fontsize={args.fontsize}:text='{args.text}':x=W/2:y=print(tw\,24)",
        "-vframes", "1",
        "-f", "null", "-"
    ], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    if width_process.returncode != 0:
        die("FFmpeg error when getting width, code",
            width_process.returncode)
    text_width = float(width_process.stderr.decode("utf-8").strip())

    gif_height = 2 * args.vmarginsize + math.ceil(text_height)
    if args.windowwidthp > 0:
        gif_width = args.windowwidthp
    elif args.windowwidthc > 0:
        gif_width = args.windowwidthc * text_width / len(args.text)
        gif_width = math.ceil(gif_width)
    else:
        die("Impossible combination of width args")

    if args.scrolltime > 0:
        gif_time = args.scrolltime
        gif_speed = (text_width + gif_width) / args.scrolltime
    elif args.scrollspeedp > 0:
        gif_time = (text_width + gif_width) / args.scrollspeed
        gif_speed = args.scrollspeed
    elif args.scrollspeedc > 0:
        gif_speed = args.scrollspeedc * text_width / len(args.text)
        gif_time = (text_width + gif_width) / gif_speed
    else:
        die("Impossible combination of time/speed args")
    gif_time += args.delayafter

    gif_process = subprocess.run([
        "ffmpeg",
        "-y",
        "-t", str(gif_time),
        "-f", "lavfi",
        "-i", f"color=c=black:s={gif_width}x{gif_height}:r=25/1",
        "-vf",
        f"drawtext='{args.font}':fontsize={args.fontsize}:text='{args.text}':y={args.vmarginsize}:x=w-t*{gif_speed}:fontcolor=white",
        args.output
    ], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    if gif_process.returncode != 0:
        die("FFmpeg exited with error status", gif_process.returncode,
            "when creating GIF,",
            "FFmpeg output:", gif_process.stderr.decode("utf-8").strip())


if __name__ == "__main__":
    main()
