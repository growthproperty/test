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
    create_logo_overlay,
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
    cuts: list[dict] = None,
    crop: dict = None,
    logo_image: str = None,
    video_offset_y: int = None,
    hide_source_text: bool = False,
    source_text_height: int = None,
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
        cuts: [{"start": float, "end": float}, ...] カットする区間
        crop: {"top": float, "bottom": float, "left": float, "right": float} クロップ率(%)
        logo_image: ロゴ画像パス
        video_offset_y: 映像のY軸オフセット (ピクセル)
        hide_source_text: 元動画のテキストを黒帯で隠す
        source_text_height: 黒帯の高さ (ピクセル, 省略時はconfig値)

    Returns:
        出力動画のパス
    """
    print("=" * 50)
    print("動画編集を開始します")
    print("=" * 50)

    # 1. 動画情報の取得
    print("\n[1/7] 動画情報を取得中...")
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
    current_input = input_path

    try:
        # 2. カット編集 (1-a)
        if cuts:
            print(f"\n[2/7] カット編集中... ({len(cuts)}箇所)")
            cut_output = _cut_video(current_input, cuts)
            temp_files.append(cut_output)
            current_input = cut_output
            # カット後の情報を再取得
            info = get_video_info(current_input)
            print(f"  カット後の再生時間: {info['duration']:.1f}秒")
        else:
            print("\n[2/7] カット編集: スキップ")

        # 3. オーバーレイ画像の生成
        print("\n[3/7] オーバーレイ画像を生成中...")

        # ウォーターマーク
        watermark_img = create_watermark_image()
        watermark_path = _save_temp_image(watermark_img, "watermark")
        temp_files.append(watermark_path)
        print("  ウォーターマーク: OK")

        # ロゴ画像 (2-b)
        logo_path = None
        if logo_image and os.path.exists(logo_image):
            logo_img = create_logo_overlay(logo_image, canvas_size)
            logo_path = _save_temp_image(logo_img, "logo")
            temp_files.append(logo_path)
            print(f"  ロゴ: OK (スケール{config.LOGO_SCALE*100:.0f}%, 不透明度{config.LOGO_OPACITY*100:.0f}%)")

        # ソーステキストマスク (drawboxで直接描画 → PNG透過の問題を回避)
        source_mask_top_h = None
        source_mask_bottom_y = None
        if hide_source_text:
            eff_w, eff_h = info["width"], info["height"]
            if crop:
                ct = crop.get("top", 0) / 100.0
                cb = crop.get("bottom", 0) / 100.0
                cl = crop.get("left", 0) / 100.0
                cr = crop.get("right", 0) / 100.0
                eff_w = int(eff_w * (1.0 - cl - cr))
                eff_h = int(eff_h * (1.0 - ct - cb))

            eff_ratio = eff_w / eff_h
            offset_y_val = video_offset_y if video_offset_y is not None else config.VIDEO_OFFSET_Y

            if eff_ratio > canvas_w / canvas_h:
                # 横長動画: 映像の上端・下端を計算
                video_h = int(canvas_w / eff_ratio)
                video_top = (canvas_h - video_h) // 2 + offset_y_val
                video_bottom = video_top + video_h
                dynamic_top = video_top + config.SOURCE_TEXT_MASK_VIDEO_COVER_TOP
                source_mask_bottom_y = video_bottom - config.SOURCE_TEXT_MASK_VIDEO_COVER_BOTTOM
            else:
                # 縦長/正方形動画
                dynamic_top = config.SOURCE_TEXT_MASK_HEIGHT
                source_mask_bottom_y = canvas_h - config.SOURCE_TEXT_MASK_PORTRAIT_BOTTOM

            source_mask_top_h = source_text_height or max(config.SOURCE_TEXT_MASK_HEIGHT, dynamic_top)
            bottom_info = f" + 下部マスク Y={source_mask_bottom_y}px〜" if source_mask_bottom_y else ""
            print(f"  ソーステキストマスク: OK (上部{source_mask_top_h}px{bottom_info})")

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

        # 4. クロップ + レターボックス化 (1-b, 4-a, 4-b)
        offset_y = video_offset_y if video_offset_y is not None else config.VIDEO_OFFSET_Y
        print(f"\n[4/7] クロップ + レターボックス化中...")
        if crop:
            print(f"  クロップ: 上{crop.get('top',0)}% 下{crop.get('bottom',0)}% 左{crop.get('left',0)}% 右{crop.get('right',0)}%")
        if offset_y != 0:
            print(f"  映像オフセットY: {offset_y}px")
        letterboxed_path = _letterbox_video(
            current_input, info, canvas_w, canvas_h,
            crop=crop, offset_y=offset_y,
        )
        temp_files.append(letterboxed_path)
        print("  レターボックス化: OK")

        # 5. 全オーバーレイを合成
        print("\n[5/7] オーバーレイを合成中...")
        _composite_video(
            letterboxed_path,
            output_path,
            watermark_path=watermark_path,
            blackbox_path=blackbox_path,
            text_path=text_path,
            cta_path=cta_path,
            cta_start=cta_start,
            logo_path=logo_path,
            source_mask_top=source_mask_top_h,
            source_mask_bottom=source_mask_bottom_y,
            duration=info["duration"],
        )

        # 6. 見切れチェック (4-b)
        print("\n[6/7] 見切れチェック...")
        _check_letterbox_fit(info, canvas_w, canvas_h, crop, offset_y)

        # 7. 完了
        print("\n[7/7] 完了!")
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


def _cut_video(input_path: str, cuts: list[dict]) -> str:
    """
    動画から指定区間をリップル削除（カット）する。(1-a)

    複数のカット区間を指定可能。カットされた部分を除外し、
    残りの部分を結合する。

    Args:
        input_path: 入力動画パス
        cuts: [{"start": float, "end": float}, ...] 削除する区間

    Returns:
        カット済み動画の一時ファイルパス
    """
    # カット区間をソート
    sorted_cuts = sorted(cuts, key=lambda c: c["start"])

    # 保持する区間を計算
    info = get_video_info(input_path)
    duration = info["duration"]
    keep_segments = []
    current_pos = 0.0

    for cut in sorted_cuts:
        start = cut["start"]
        end = cut["end"]
        if start > current_pos:
            keep_segments.append({"start": current_pos, "end": start})
        current_pos = max(current_pos, end)

    if current_pos < duration:
        keep_segments.append({"start": current_pos, "end": duration})

    if not keep_segments:
        raise ValueError("すべての区間がカットされました。保持する区間がありません。")

    if len(keep_segments) == 1:
        # 単一セグメント: 単純なトリム
        seg = keep_segments[0]
        fd, output_path = tempfile.mkstemp(suffix=".mp4", prefix="cut_")
        os.close(fd)

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ss", f"{seg['start']:.3f}",
            "-to", f"{seg['end']:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"カット編集に失敗:\n{result.stderr[-500:]}")
        return output_path

    # 複数セグメント: 各セグメントを抽出してconcat
    segment_files = []
    concat_list_path = None
    try:
        for i, seg in enumerate(keep_segments):
            fd, seg_path = tempfile.mkstemp(suffix=".mp4", prefix=f"seg_{i}_")
            os.close(fd)
            segment_files.append(seg_path)

            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-ss", f"{seg['start']:.3f}",
                "-to", f"{seg['end']:.3f}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                output_path,
            ]
            # セグメント用の一時エンコード
            cmd[-1] = seg_path
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"セグメント{i}の抽出に失敗:\n{result.stderr[-500:]}")

        # concat用のリストファイルを作成
        fd, concat_list_path = tempfile.mkstemp(suffix=".txt", prefix="concat_")
        os.close(fd)
        with open(concat_list_path, "w") as f:
            for seg_path in segment_files:
                f.write(f"file '{seg_path}'\n")

        # 結合
        fd, output_path = tempfile.mkstemp(suffix=".mp4", prefix="cut_")
        os.close(fd)

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            "-movflags", "+faststart",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"セグメント結合に失敗:\n{result.stderr[-500:]}")

        return output_path

    finally:
        # セグメント一時ファイルの削除
        for seg_path in segment_files:
            if os.path.exists(seg_path):
                try:
                    os.remove(seg_path)
                except OSError:
                    pass
        if concat_list_path and os.path.exists(concat_list_path):
            try:
                os.remove(concat_list_path)
            except OSError:
                pass


def _letterbox_video(
    input_path: str,
    info: dict,
    canvas_w: int,
    canvas_h: int,
    crop: dict = None,
    offset_y: int = 0,
) -> str:
    """
    動画を指定キャンバスサイズにレターボックス化する。
    クロップ(1-b)、Y軸オフセット(4-a)、自動スケール(4-b)に対応。

    横長動画: 上下に黒帯を追加
    縦長動画: 縮小してフィット
    すでに9:16: そのままリサイズ
    """
    fd, output_path = tempfile.mkstemp(suffix=".mp4", prefix="letterboxed_")
    os.close(fd)

    src_w = info["width"]
    src_h = info["height"]

    # クロップフィルター (1-b)
    crop_filter = ""
    if crop:
        ct = crop.get("top", 0) / 100.0
        cb = crop.get("bottom", 0) / 100.0
        cl = crop.get("left", 0) / 100.0
        cr = crop.get("right", 0) / 100.0

        crop_w = f"iw*{1.0 - cl - cr:.4f}"
        crop_h = f"ih*{1.0 - ct - cb:.4f}"
        crop_x = f"iw*{cl:.4f}"
        crop_y = f"iw*{ct:.4f}"  # intentionally using iw for aspect ratio consistency
        # 正確にはih*ctだがffmpegの式として
        crop_y = f"ih*{ct:.4f}"
        crop_filter = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"

        # クロップ後の実効解像度を計算
        src_w = int(src_w * (1.0 - cl - cr))
        src_h = int(src_h * (1.0 - ct - cb))

    src_ratio = src_w / src_h
    canvas_ratio = canvas_w / canvas_h

    # Y軸オフセットを考慮した配置計算 (4-a)
    # offset_y > 0: 映像を下にずらす
    if offset_y != 0 and config.VIDEO_AUTO_SCALE:
        # 見切れ防止のスケール計算 (4-b)
        # オフセット分だけ余分にスケールを上げる
        extra_scale = _calc_auto_scale(src_w, src_h, canvas_w, canvas_h, offset_y)
    else:
        extra_scale = 1.0

    if abs(src_ratio - canvas_ratio) < 0.01:
        scale_part = f"scale={canvas_w}:{canvas_h}"
    elif src_ratio > canvas_ratio:
        # 横長動画 → 幅をフィットさせて上下に黒帯
        scale_part = f"scale={canvas_w}:-2:force_original_aspect_ratio=decrease"
        if extra_scale > 1.0:
            new_w = int(canvas_w * extra_scale)
            # 偶数にする
            new_w = new_w + (new_w % 2)
            scale_part = f"scale={new_w}:-2"
    else:
        # 縦長動画
        scale_part = f"scale=-2:{canvas_h}:force_original_aspect_ratio=decrease"
        if extra_scale > 1.0:
            new_h = int(canvas_h * extra_scale)
            new_h = new_h + (new_h % 2)
            scale_part = f"scale=-2:{new_h}"

    # padフィルターでキャンバスサイズに合わせる
    # Y軸オフセットの適用
    pad_y = f"(oh-ih)/2+{offset_y}" if offset_y != 0 else "(oh-ih)/2"
    pad_part = f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:{pad_y}:black"

    vf = f"{crop_filter}{scale_part},{pad_part}"

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


def _calc_auto_scale(
    src_w: int, src_h: int,
    canvas_w: int, canvas_h: int,
    offset_y: int,
) -> float:
    """
    映像のY軸オフセット後に見切れが発生しないよう、
    必要なスケール倍率を計算する。(4-b)
    """
    src_ratio = src_w / src_h
    canvas_ratio = canvas_w / canvas_h

    if src_ratio > canvas_ratio:
        # 横長動画: 幅フィット時の映像高さ
        fitted_h = canvas_w / src_ratio
    else:
        fitted_h = canvas_h

    # オフセット分の余白が上下に必要
    abs_offset = abs(offset_y)
    available_h = canvas_h
    needed_h = fitted_h + 2 * abs_offset

    if needed_h > fitted_h:
        return needed_h / fitted_h
    return 1.0


def _check_letterbox_fit(
    info: dict,
    canvas_w: int,
    canvas_h: int,
    crop: dict = None,
    offset_y: int = 0,
):
    """
    見切れが発生していないかチェックし、警告を出す。(4-b)
    """
    src_w = info["width"]
    src_h = info["height"]

    if crop:
        ct = crop.get("top", 0) / 100.0
        cb = crop.get("bottom", 0) / 100.0
        cl = crop.get("left", 0) / 100.0
        cr = crop.get("right", 0) / 100.0
        src_w = int(src_w * (1.0 - cl - cr))
        src_h = int(src_h * (1.0 - ct - cb))

    src_ratio = src_w / src_h
    canvas_ratio = canvas_w / canvas_h

    if src_ratio > canvas_ratio:
        # 横長動画: 幅フィット時の映像高さ
        fitted_h = int(canvas_w / src_ratio)
        gap = canvas_h - fitted_h
        top_gap = gap // 2 - offset_y
        bottom_gap = gap // 2 + offset_y

        if top_gap < 0 or bottom_gap < 0:
            print(f"  ⚠ 見切れ警告: 映像がキャンバスからはみ出しています")
            print(f"    上部余白: {top_gap}px, 下部余白: {bottom_gap}px")
            print(f"    → --video-offset-y の値を調整してください")
        else:
            print(f"  OK: 上部余白 {top_gap}px, 下部余白 {bottom_gap}px")
    else:
        print(f"  OK: 縦長/正方形動画 (見切れなし)")


def _composite_video(
    video_path: str,
    output_path: str,
    watermark_path: str,
    blackbox_path: str = None,
    text_path: str = None,
    cta_path: str = None,
    cta_start: float = None,
    logo_path: str = None,
    source_mask_top: int = None,
    source_mask_bottom: int = None,
    duration: float = 0,
):
    """
    FFmpegで動画にすべてのオーバーレイを合成する。
    黒帯マスクはdrawboxフィルターで直接描画（PNG透過の信頼性問題を回避）。
    """
    inputs = ["-i", video_path]
    overlay_idx = 1
    filter_parts = []
    current_stream = "[0:v]"

    # ソーステキストマスク (drawboxで直接ピクセルを黒塗り → 確実)
    drawbox_filters = []
    if source_mask_top:
        drawbox_filters.append(
            f"drawbox=x=0:y=0:w=iw:h={source_mask_top}:color=black:t=fill"
        )
    if source_mask_bottom:
        drawbox_filters.append(
            f"drawbox=x=0:y={source_mask_bottom}:w=iw:h=ih-{source_mask_bottom}:color=black:t=fill"
        )

    if drawbox_filters:
        chain = ",".join(drawbox_filters)
        filter_parts.append(f"{current_stream}{chain}[masked]")
        current_stream = "[masked]"

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

    # ロゴ画像 (常時表示) (2-b)
    if logo_path:
        inputs.extend(["-i", logo_path])
        filter_parts.append(
            f"{current_stream}[{overlay_idx}:v]overlay=0:0[logo]"
        )
        current_stream = "[logo]"
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
