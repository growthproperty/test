"""動画処理モジュール - FFmpegを使った動画のレターボックス化とオーバーレイ合成"""

import subprocess
import os
import tempfile
from pathlib import Path

from . import config
from .downloader import get_video_info
from .overlay import (
    create_watermark_image,
    create_text_overlay,
    create_blackbox_overlay,
    create_cta_overlay,
)


def process_video(
    input_path: str,
    output_path: str,
    text_lines: list[dict],
    blackboxes: list[dict] = None,
    y_positions: list[int] = None,
    profile_image: str = None,
    checkmark_image: str = None,
    skip_cta: bool = False,
) -> str:
    """
    動画を編集する。メインのパイプライン。

    Args:
        input_path: 入力動画パス
        output_path: 出力動画パス
        text_lines: [{"text": "テキスト", "color": "white"}, ...]
        blackboxes: [{"x": int, "y": int, "w": int, "h": int}, ...]
        y_positions: テキスト行のY座標リスト (省略時は自動)
        profile_image: CTAプロフィール画像パス
        checkmark_image: CTAチェックマーク画像パス
        skip_cta: CTAを省略するかどうか

    Returns:
        出力動画のパス
    """
    print("=" * 50)
    print("動画編集を開始します")
    print("=" * 50)

    # 1. 動画情報の取得
    print("\n[1/5] 動画情報を取得中...")
    info = get_video_info(input_path)
    print(f"  解像度: {info['width']}x{info['height']}")
    print(f"  再生時間: {info['duration']:.1f}秒")
    print(f"  FPS: {info['fps']:.1f}")
    print(f"  向き: {'横長' if info['is_landscape'] else '縦長'}")

    canvas_w = config.CANVAS_WIDTH
    canvas_h = config.CANVAS_HEIGHT
    canvas_size = (canvas_w, canvas_h)

    # 一時ファイル管理
    temp_files = []

    try:
        # 2. オーバーレイ画像の生成
        print("\n[2/5] オーバーレイ画像を生成中...")

        # ウォーターマーク
        watermark_img = create_watermark_image()
        watermark_path = _save_temp_image(watermark_img, "watermark")
        temp_files.append(watermark_path)
        print("  ウォーターマーク: OK")

        # 黒ボックス (コメント隠し)
        blackbox_path = None
        if blackboxes:
            blackbox_img = create_blackbox_overlay(blackboxes, canvas_size)
            blackbox_path = _save_temp_image(blackbox_img, "blackbox")
            temp_files.append(blackbox_path)
            print(f"  黒ボックス: {len(blackboxes)}個")

        # メインテキスト
        text_img = create_text_overlay(text_lines, canvas_size, y_positions)
        text_path = _save_temp_image(text_img, "text")
        temp_files.append(text_path)
        print(f"  テキスト: {len(text_lines)}行")

        # CTA
        cta_path = None
        cta_start = None
        if not skip_cta:
            cta_img = create_cta_overlay(profile_image, checkmark_image, canvas_size)
            cta_path = _save_temp_image(cta_img, "cta")
            temp_files.append(cta_path)
            cta_start = config.get_cta_start_time(info["duration"])
            print(f"  CTA: {cta_start:.1f}秒から表示")

        # 3. レターボックス化 (横長動画を9:16に)
        print("\n[3/5] 動画をレターボックス化中...")
        letterboxed_path = _letterbox_video(input_path, info, canvas_w, canvas_h)
        temp_files.append(letterboxed_path)
        print("  レターボックス化: OK")

        # 4. 全オーバーレイを合成
        print("\n[4/5] オーバーレイを合成中...")
        _composite_video(
            letterboxed_path,
            output_path,
            watermark_path=watermark_path,
            blackbox_path=blackbox_path,
            text_path=text_path,
            cta_path=cta_path,
            cta_start=cta_start,
            duration=info["duration"],
        )

        # 5. 完了
        print("\n[5/5] 完了!")
        output_size = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  出力: {output_path}")
        print(f"  サイズ: {output_size:.1f} MB")
        print("=" * 50)

        return output_path

    finally:
        # 一時ファイルの削除
        for f in temp_files:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass


def _save_temp_image(img, prefix: str) -> str:
    """PIL画像を一時ファイルとして保存"""
    fd, path = tempfile.mkstemp(suffix=".png", prefix=f"overlay_{prefix}_")
    os.close(fd)
    img.save(path, "PNG")
    return path


def _letterbox_video(
    input_path: str,
    info: dict,
    canvas_w: int,
    canvas_h: int,
) -> str:
    """
    動画を指定キャンバスサイズにレターボックス化する。
    横長動画: 上下に黒帯を追加
    縦長動画: 縮小してフィット
    すでに9:16: そのままリサイズ
    """
    fd, output_path = tempfile.mkstemp(suffix=".mp4", prefix="letterboxed_")
    os.close(fd)

    src_w = info["width"]
    src_h = info["height"]
    src_ratio = src_w / src_h
    canvas_ratio = canvas_w / canvas_h

    if abs(src_ratio - canvas_ratio) < 0.01:
        # すでにほぼ同じアスペクト比 → リサイズのみ
        vf = f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease,pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:black"
    elif src_ratio > canvas_ratio:
        # 横長動画 → 幅をフィットさせて上下に黒帯
        vf = f"scale={canvas_w}:-2:force_original_aspect_ratio=decrease,pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:black"
    else:
        # 縦長動画 → 高さをフィットさせて左右に黒帯 (稀なケース)
        vf = f"scale=-2:{canvas_h}:force_original_aspect_ratio=decrease,pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:black"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"レターボックス化に失敗:\n{result.stderr[-500:]}")

    return output_path


def _composite_video(
    video_path: str,
    output_path: str,
    watermark_path: str,
    blackbox_path: str = None,
    text_path: str = None,
    cta_path: str = None,
    cta_start: float = None,
    duration: float = 0,
):
    """
    FFmpegで動画にすべてのオーバーレイを合成する。
    """
    inputs = ["-i", video_path]
    overlay_idx = 1
    filter_parts = []
    current_stream = "[0:v]"

    # 黒ボックス (常時表示)
    if blackbox_path:
        inputs.extend(["-i", blackbox_path])
        filter_parts.append(
            f"{current_stream}[{overlay_idx}:v]overlay=0:0[bb]"
        )
        current_stream = "[bb]"
        overlay_idx += 1

    # ウォーターマーク (常時表示)
    inputs.extend(["-i", watermark_path])
    wx = config.WATERMARK_X
    wy = config.WATERMARK_Y
    filter_parts.append(
        f"{current_stream}[{overlay_idx}:v]overlay={wx}:{wy}[wm]"
    )
    current_stream = "[wm]"
    overlay_idx += 1

    # テキスト (常時表示)
    if text_path:
        inputs.extend(["-i", text_path])
        filter_parts.append(
            f"{current_stream}[{overlay_idx}:v]overlay=0:0[txt]"
        )
        current_stream = "[txt]"
        overlay_idx += 1

    # CTA (指定時間から表示)
    if cta_path and cta_start is not None:
        inputs.extend(["-i", cta_path])
        filter_parts.append(
            f"{current_stream}[{overlay_idx}:v]overlay=0:0:enable='gte(t,{cta_start:.2f})'[cta]"
        )
        current_stream = "[cta]"
        overlay_idx += 1

    filter_complex = ";".join(filter_parts)

    # 最終ストリーム名のブラケットを除去
    final_stream = current_stream

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", final_stream,
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"オーバーレイ合成に失敗:\n{result.stderr[-500:]}")
