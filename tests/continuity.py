"""Screen a rendered Wash Day film for short return shots and mismatched voice-gate pictures."""
import argparse
import csv
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

WIDTH, HEIGHT = 320, 180
FIELDS = ("mean", "changed", "block_max", "block_high")


def differences(a, b):
    # Captions occupy the lower 19% of the frame. Preserve head, body, hands and
    # background in the comparison while omitting the expected text change.
    rgb = cv2.absdiff(a[:144], b[:144])
    energy = rgb.mean(axis=2, dtype=np.float32)
    tiles = cv2.resize(energy, (16, 9), interpolation=cv2.INTER_AREA)
    return dict(mean=round(float(energy.mean()), 3),
                changed=round(float(np.mean(energy >= 20)), 5),
                block_max=round(float(tiles.max()), 3),
                block_high=round(float(np.partition(tiles.ravel(), -5)[-5]), 3))


def hard_cut(row):
    # Broad image change should involve several blocks, unlike a facial gesture.
    return row["mean"] > 16 and row["changed"] > .23 and row["block_high"] > 40


def presentation_times(media, expected):
    data = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v", "-show_packets",
        "-show_entries", "packet=pts_time", "-of", "json", str(media)]))
    pts = np.sort([float(p["pts_time"]) for p in data["packets"]])
    if len(pts) != expected or not np.isfinite(pts).all() or np.any(np.diff(pts) <= 0):
        raise ValueError("Unexpected frame count, duplicated PTS, or nonfinite timestamps")
    return pts


def read_frames(media):
    cmd = ["ffmpeg", "-v", "error", "-threads", "2", "-i", str(media), "-an",
           "-filter_threads", "1", "-vf", f"scale={WIDTH}:{HEIGHT}:flags=area",
           "-fps_mode", "passthrough", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:
        for raw in iter(lambda: proc.stdout.read(WIDTH * HEIGHT * 3), b""):
            if len(raw) != WIDTH * HEIGHT * 3:
                raise ValueError("Short decoded frame")
            yield np.frombuffer(raw, np.uint8).reshape(HEIGHT, WIDTH, 3)
        if proc.wait():
            raise ValueError("FFmpeg decoder failed")


def gate_windows(turns, pts):
    windows = []
    for a, b, line in turns:
        # The player pauses, rewinds if over .06 s late, then resumes with a
        # seek. Include a frame before either nominal point because episode
        # times and demux timestamps have independent decimal rounding.
        guard = lambda sec: int(np.searchsorted(pts, sec, side="right") - 1)
        an, bn = guard(a), guard(b)
        hold = list(range(an - 1, an + 3))
        land = list(range(bn - 1, bn + 3))
        windows.append((line, a, b, hold, land))
    return windows


def measure(media, timeline, tag, output):
    edit = json.loads(timeline.read_text())
    fps = edit["fps"]
    pts = presentation_times(media, edit["frames"])
    if np.abs(pts - np.arange(len(pts)) / fps).max() > .003:
        raise ValueError("Unexpected frame timing drift")
    turns = gate_windows(edit["episode"]["turns"], pts)
    needed = {frame for _, _, _, holds, lands in turns for frame in holds + lands}
    retained = {}
    rows = []
    prev = None
    for n, frame in enumerate(read_frames(media)):
        if n in needed:
            retained[n] = frame
        if prev is not None:
            rows.append({"frame": n, "time": round(float(pts[n]), 6), **differences(prev, frame)})
        prev = frame
    if len(rows) + 1 != edit["frames"]:
        raise ValueError("Decoded picture count differs from timeline count")
    cuts = [0] + [r["frame"] for r in rows if hard_cut(r)] + [len(rows) + 1]
    flashes = [{"first_frame": a, "last_frame": b - 1, "time": round(float(pts[a]), 4),
                "frames": b - a} for a, b in zip(cuts, cuts[1:]) if b - a < 6]
    jumps = []
    for i, (line, a, b, hold, land) in enumerate(turns):
        pairs = [dict(held=h, landed=l, **differences(retained[h], retained[l]))
                 for h in hold for l in land]
        target_h = int(round(fps*a))
        target_l = int(round(fps*b))
        center = next(p for p in pairs if p["held"] == target_h and p["landed"] == target_l)
        jumps.append(dict(turn=i + 1, line=line, pause=a, resume=b, nominal=center,
                          largest=max(pairs, key=lambda p:p["mean"]),
                          largest_tile=max(pairs, key=lambda p:p["block_max"]),
                          hard_pairs=sum(map(hard_cut, pairs)), pairs=pairs))
    cutset = set(cuts)
    jolts = []
    for i in range(3, len(rows)-3):
        row = rows[i]
        if row["frame"] in cutset:
            continue
        others = [r["block_high"] for r in rows[i-3:i]+rows[i+1:i+4] if r["frame"] not in cutset]
        if not others:
            continue
        ratio = row["block_high"] / max(2.5, float(np.median(others)))
        if row["block_high"] > 12 and ratio > 2.25:
            jolts.append(dict(**row, neighbor_ratio=round(ratio, 2)))
    result = dict(film=str(media), frames=len(pts), fps=fps,
                  first_pts=float(pts[0]), last_pts=float(pts[-1]),
                  cuts=cuts[1:-1], possible_flashes=flashes,
                  local_outliers=jolts, voice_gates=jumps)
    (output / f"{tag}.json").write_text(json.dumps(result, indent=2) + "\n")
    with (output / f"{tag}-frames.csv").open("w") as f:
        writer = csv.DictWriter(f, ("frame", "time", *FIELDS))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{tag}: {len(pts)} pictures, {len(cuts)-2} picture cuts, {len(flashes)} short glimpses")
    print("Short glimpses:", [(s["time"], s["frames"]) for s in flashes])
    print("Exact voice-gate changes (mean, block max, hard pairs / 16):",
          [(g["turn"], g["nominal"]["mean"], g["nominal"]["block_max"], g["hard_pairs"]) for g in jumps])
    print("Local, non-cut movement outliers:", sorted(jolts, key=lambda r:-r["block_high"])[:12])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("film", type=Path)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(exist_ok=True, parents=True)
    report = measure(args.film, args.timeline, args.tag, args.output)
    if args.strict and (report["possible_flashes"] or any(g["hard_pairs"] for g in report["voice_gates"])):
        raise SystemExit("FAIL: a short camera glimpse or an abrupt pause/resume change needs review")
