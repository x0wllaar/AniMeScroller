#!/usr/bin/env python3

import subprocess
import argparse
import tempfile
import pickle
import threading
import logging

import zmq

from queue import PriorityQueue
from utils import GifData

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


def play_gif(gif_data:GifData):
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


def gif_playback_loop(gif_queue:PriorityQueue, force_clear_matrix:bool):
    while True:
        _, gif_data = gif_queue.get()
        play_gif(gif_data)
        if force_clear_matrix:
            clear_matrix()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", 
                        help="ZMQ PULL to receive GIFs from",
                        type=str,
                        required=True)
    parser.add_argument("--queuesize",
                        help="Size of GIF playback queue (0 is infinite)",
                        required=False,
                        type=int,
                        default=0)
    parser.add_argument("--forceclearmatrix",
                        help="Force matrix to black after GIF playback",
                        required=False,
                        type=bool,
                        default=True)
    parser.add_argument("--loglevel",
                        help="Logging level for server",
                        required=False,
                        type=str,
                        default="INFO")
    args = parser.parse_args()

    numeric_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.loglevel}")
    logging.basicConfig(level=numeric_level)

    gif_queue = PriorityQueue(args.queuesize)

    gif_player_thread = threading.Thread(target=gif_playback_loop, daemon=True, 
                                         args=(gif_queue,args.forceclearmatrix))
    gif_player_thread.start()

    ctx = zmq.Context.instance()
    g_socket = ctx.socket(zmq.PULL)
    g_socket.bind(args.socket)
    logging.info(f"GIF playback server listening on {args.socket}")
    while True:
        msg = g_socket.recv()
        logging.info(f"Received {len(msg)} bytes")
        gif_data: GifData = pickle.loads(msg)
        gif_queue.put((gif_data.priority, gif_data))

if __name__ == "__main__":
    main()