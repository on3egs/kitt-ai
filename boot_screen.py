#!/usr/bin/env python3
"""
KYRONEX Boot Screen - Retro 1980s Terminal Style
Author: Manix
"""
import sys
import time
import random
import os

# ANSI Colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'
WHITE = '\033[97m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'
CLEAR = '\033[2J\033[H'

KYRONEX_ASCII = r"""
    ██╗  ██╗██╗   ██╗██████╗  ██████╗ ██╗  ██╗███████╗██╗  ██╗
    ██║ ██╔╝╚██╗ ██╔╝██╔══██╗██╔═══██╗████╗ ██║██╔════╝╚██╗██╔╝
    █████╔╝  ╚████╔╝ ██████╔╝██║   ██║██╔██╗██║█████╗   ╚███╔╝
    ██╔═██╗   ╚██╔╝  ██╔══██╗██║   ██║██║╚████║██╔══╝   ██╔██╗
    ██║  ██╗   ██║   ██║  ██║╚██████╔╝██║ ╚███║███████╗██╔╝╚██╗
    ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚══╝╚══════╝╚═╝  ╚═╝
"""

SUBTITLE = "KINETIC YIELDING RESPONSIVE ONBOARD NEURAL EXPERT"

def typewriter(text, delay=0.03, color=WHITE):
    """Print text with typewriter effect"""
    for char in text:
        sys.stdout.write(color + char + RESET)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def scanner_line(width=60, color=RED):
    """Animated scanner line (Knight Rider style)"""
    print(f"\n{color}{'═' * width}{RESET}")

    # Forward
    for i in range(width):
        sys.stdout.write(f"\r{color}{'─' * i}{'█'}{'─' * (width - i - 1)}{RESET}")
        sys.stdout.flush()
        time.sleep(0.02)

    # Backward
    for i in range(width - 1, -1, -1):
        sys.stdout.write(f"\r{color}{'─' * i}{'█'}{'─' * (width - i - 1)}{RESET}")
        sys.stdout.flush()
        time.sleep(0.02)

    print(f"\r{color}{'═' * width}{RESET}\n")

def boot_sequence():
    """Main boot sequence"""
    # Clear screen
    print(CLEAR)

    # Title
    print(f"\n{RED}{BOLD}{KYRONEX_ASCII}{RESET}")
    print(f"{DIM}{' ' * 8}{SUBTITLE}{RESET}\n")

    # Scanner animation
    scanner_line(60, RED)

    # Boot messages
    messages = [
        ("SYSTEM BOOT SEQUENCE INITIATED...", GREEN, 0.8),
        ("", WHITE, 0.2),
        ("[✓] NVIDIA Jetson Orin Nano Super 8GB", CYAN, 0.3),
        ("[✓] CUDA 12.6 Graphics Subsystem", CYAN, 0.3),
        ("[✓] Neural Processing Unit", CYAN, 0.3),
        ("", WHITE, 0.2),
        ("[⚡] Loading LLM Engine (Qwen 2.5 3B)...", YELLOW, 1.2),
        ("[✓] Language Model Online", GREEN, 0.3),
        ("", WHITE, 0.2),
        ("[⚡] Initializing Speech Recognition...", YELLOW, 0.8),
        ("[✓] Whisper STT Ready", GREEN, 0.3),
        ("", WHITE, 0.2),
        ("[⚡] Loading Voice Synthesis...", YELLOW, 0.8),
        ("[✓] Piper TTS Online", GREEN, 0.3),
        ("", WHITE, 0.2),
        ("[⚡] Calibrating Vision Systems...", YELLOW, 0.8),
        ("[✓] YOLOX-S Object Detection Ready", GREEN, 0.3),
        ("", WHITE, 0.5),
        ("═" * 60, RED, 0.3),
        ("", WHITE, 0.3),
        (f"{BOLD}KYRONEX NEURAL EXPERT SYSTEM{RESET}", RED, 0.5),
        (f"{DIM}Created by Manix - Belgium 2026{RESET}", WHITE, 0.5),
        ("", WHITE, 0.3),
        ("STATUS: ALL SYSTEMS OPERATIONAL", GREEN, 0.8),
        ("", WHITE, 0.5),
        ("Launching Web Interface...", CYAN, 1.0),
    ]

    for msg, color, delay in messages:
        if msg:
            print(f"{color}{msg}{RESET}")
        else:
            print()
        time.sleep(delay)

    # Final countdown
    print()
    for i in range(3, 0, -1):
        sys.stdout.write(f"\r{YELLOW}Starting in {i}...{RESET}")
        sys.stdout.flush()
        time.sleep(1)
    print(f"\r{GREEN}{'░' * 60}{RESET}")
    print()

if __name__ == "__main__":
    try:
        boot_sequence()
    except KeyboardInterrupt:
        print(f"\n{RED}Boot sequence interrupted.{RESET}")
        sys.exit(0)
