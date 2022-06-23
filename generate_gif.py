#!/usr/bin/env python3

import os
import sys
import argparse
import math
import pickle

import zmq

from utils import GifData, PICKLE_PROTOCOL_VERSION, die
from ffmpeg_utils import get_text_size_info, generate_gif

DEFAULT_FONT_NAME = "./NotoSansMono-SemiBold.ttf"
# This is a cluge to refer to files relative to the script
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


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
    parser.add_argument("--gifpriority",
                        help="GIF playback priority on server (lower is bigger priority)",
                        required=False,
                        type=int,
                        default=127)
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
        g_data = GifData(nloops=args.loops, gif_bytes=gif_bytes, priority=args.gifpriority)
        ctx = zmq.Context.instance()
        g_socket = ctx.socket(zmq.PUSH)
        g_socket.connect(args.socket)

        pickle_gif_bytes = pickle.dumps(g_data, protocol=PICKLE_PROTOCOL_VERSION)
        g_socket.send(pickle_gif_bytes)


if __name__ == "__main__":
    main()
