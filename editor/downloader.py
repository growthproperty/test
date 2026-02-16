"""Instagram動画ダウンロードモジュール"""

import subprocess
import json
import os
from pathlib import Path


def download_video(url: str, output_dir: str = "input") -> str:
    """
    Instagram URLから動画をダウンロードする。

    Args:
        url: Instagram動画のURL
        output_dir: 保存先ディレクトリ

    Returns:
        ダウンロードされた動画のファイルパス
    """
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", output_template,
        "--print", "after_move:filepath",
        "--no-warnings",
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"動画のダウンロードに失敗しました:\n{result.stderr}"
        )

    filepath = result.stdout.strip().split("\n")[-1]
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"ダウンロードしたファイルが見つかりません: {filepath}")

    print(f"  ダウンロード完了: {filepath}")
    return filepath


def get_video_info(filepath: str) -> dict:
    """
    FFprobeで動画のメタデータを取得する。

    Returns:
        dict: {
            'width': int,
            'height': int,
            'duration': float,
            'fps': float,
            'codec': str,
            'is_landscape': bool,  # 横長かどうか
        }
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        filepath,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"動画情報の取得に失敗: {result.stderr}")

    data = json.loads(result.stdout)

    # 動画ストリームを探す
    video_stream = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            video_stream = stream
            break

    if not video_stream:
        raise ValueError("動画ストリームが見つかりません")

    width = int(video_stream["width"])
    height = int(video_stream["height"])

    # FPSの取得
    fps_str = video_stream.get("r_frame_rate", "30/1")
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) != 0 else 30.0
    else:
        fps = float(fps_str)

    # 再生時間の取得
    duration = float(
        video_stream.get("duration")
        or data.get("format", {}).get("duration", 0)
    )

    return {
        "width": width,
        "height": height,
        "duration": duration,
        "fps": fps,
        "codec": video_stream.get("codec_name", "unknown"),
        "is_landscape": width > height,
    }
