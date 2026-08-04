#!/usr/bin/env python3
"""Repair malformed named channels in UE 5.3 Linux multilayer EXRs.

UE 5.3's EXR writer passes an ANSI channel suffix to a TCHAR ``%s`` format.
On Linux this can append garbage to named channels such as
``ActorHitProxyMask00.R`` and ``FinalImageMovieRenderQueue_WorldDepth.R``.
This script rewrites only those channel names, preserving pixels and metadata.
Files are replaced atomically after the repaired temporary file validates.
"""

import argparse
import os
from pathlib import Path
import re

import OpenEXR


CHANNEL_PATTERN = re.compile(
    r"^(ActorHitProxyMask\d{2}|"
    r"FinalImageMovieRenderQueue_(?:WorldDepth|CameraNormal|WorldNormal))"
    r"\.([RGBA])"
)


def clean_name(name):
    match = CHANNEL_PATTERN.match(name)
    if match:
        return f"{match.group(1)}.{match.group(2)}"
    return name


def repair_file(path):
    temporary_path = path.with_name(f".{path.name}.repairing")

    with OpenEXR.File(str(path), separate_channels=True) as source:
        header = dict(source.header())
        header.pop("channels", None)
        channels = {}
        changed = False

        for name, channel in source.channels().items():
            repaired_name = clean_name(name)
            changed |= repaired_name != name
            if repaired_name in channels:
                raise RuntimeError(
                    f"Duplicate repaired channel {repaired_name!r} in {path}"
                )
            channels[repaired_name] = OpenEXR.Channel(
                repaired_name,
                channel.pixels,
                channel.xSampling,
                channel.ySampling,
                channel.pLinear,
            )

        if not changed:
            return False

        OpenEXR.File(header, channels).write(str(temporary_path))

    with OpenEXR.File(str(temporary_path), separate_channels=True) as repaired:
        repaired_names = set(repaired.channels())
        required = {
            "ActorHitProxyMask00.R",
            "FinalImageMovieRenderQueue_WorldDepth.R",
        }
        if not required.issubset(repaired_names):
            raise RuntimeError(
                f"Repaired EXR failed channel validation: {temporary_path}"
            )
        if "unreal/camera/curPos/x" not in repaired.header():
            raise RuntimeError(
                f"Repaired EXR failed metadata validation: {temporary_path}"
            )

    os.replace(temporary_path, path)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    args = parser.parse_args()

    paths = (
        sorted(args.input.rglob("*.exr"))
        if args.input.is_dir()
        else [args.input]
    )
    repaired_count = 0
    for index, path in enumerate(paths, 1):
        if repair_file(path):
            repaired_count += 1
        if index % 25 == 0 or index == len(paths):
            print(
                f"Checked {index}/{len(paths)}; repaired {repaired_count}",
                flush=True,
            )


if __name__ == "__main__":
    main()
