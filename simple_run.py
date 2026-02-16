#!/usr/bin/env python3
"""
簡単実行スクリプト

使い方:
  python simple_run.py

起動するとURLとテキストを聞かれるので入力するだけでOK。
"""

import os
import sys
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """必要なツールがインストールされているか確認"""
    errors = []

    # ffmpeg チェック
    import shutil
    if not shutil.which("ffmpeg"):
        errors.append("ffmpeg が見つかりません。インストールしてください。")
    if not shutil.which("ffprobe"):
        errors.append("ffprobe が見つかりません（ffmpegと一緒にインストールされます）。")

    # yt-dlp チェック
    if not shutil.which("yt-dlp"):
        try:
            import yt_dlp
        except ImportError:
            errors.append("yt-dlp が見つかりません。'pip install yt-dlp' でインストールしてください。")

    # Pillow チェック
    try:
        from PIL import Image
    except ImportError:
        errors.append("Pillow が見つかりません。'pip install Pillow' でインストールしてください。")

    if errors:
        print("\n必要なツールが不足しています:")
        for e in errors:
            print(f"  - {e}")
        print()
        sys.exit(1)


def main():
    print("=" * 50)
    print("  Instagram動画 自動編集ツール")
    print("=" * 50)

    # 依存関係チェック
    check_dependencies()

    from editor.downloader import download_video
    from editor.processor import process_video

    # URL入力
    print("\nInstagramリールのURLを貼り付けてください:")
    url = input("URL > ").strip()
    if not url:
        print("URLが入力されていません。終了します。")
        sys.exit(1)

    # テキスト入力
    print("\n動画に表示するテキストを入力してください。")
    print("（複数行の場合は1行ずつ入力し、空Enterで完了）")

    text_lines = []
    line_num = 1
    while True:
        line = input(f"  {line_num}行目 > ").strip()
        if not line:
            if not text_lines:
                print("  最低1行は入力してください。")
                continue
            break
        text_lines.append(line)
        line_num += 1
        if line_num > 3:
            print("  (最大3行です)")
            break

    # 色の設定
    print("\nテキストの色を選んでください:")
    print("  1. 白 + 黄色 (デフォルト)")
    print("  2. すべて白")
    print("  3. すべて黄色")
    print("  4. 白 + 黄色 + 赤エフェクト")
    print("  5. すべて赤エフェクト")
    color_choice = input("選択 (1/2/3/4/5) [1] > ").strip() or "1"

    default_colors = ["white", "yellow", "white"]
    if color_choice == "2":
        colors = ["white"] * len(text_lines)
        effects = [None] * len(text_lines)
    elif color_choice == "3":
        colors = ["yellow"] * len(text_lines)
        effects = [None] * len(text_lines)
    elif color_choice == "4":
        color_cycle = ["white", "yellow", "red"]
        effect_cycle = [None, None, "red_glow"]
        colors = [color_cycle[i % len(color_cycle)] for i in range(len(text_lines))]
        effects = [effect_cycle[i % len(effect_cycle)] for i in range(len(text_lines))]
    elif color_choice == "5":
        colors = ["red"] * len(text_lines)
        effects = ["red_glow"] * len(text_lines)
    else:
        colors = [default_colors[i % len(default_colors)] for i in range(len(text_lines))]
        effects = [None] * len(text_lines)

    # テキスト行の構築
    lines = []
    for t, c, e in zip(text_lines, colors, effects):
        line_info = {"text": t, "color": c}
        if e:
            line_info["effect"] = e
        lines.append(line_info)

    # クロップ設定 (1-b)
    print("\n不要なロゴを切り取りますか？(クロップ)")
    print("  上下左右の切り取り率(%)を入力。例: 5,0,0,3")
    print("  スキップする場合は空Enterで。")
    crop_input = input("クロップ (top,bottom,left,right) > ").strip()
    crop = None
    if crop_input:
        parts = crop_input.split(",")
        if len(parts) == 4:
            top, bottom, left, right = map(float, parts)
            crop = {"top": top, "bottom": bottom, "left": left, "right": right}
        else:
            print("  形式が正しくありません。クロップをスキップします。")

    # ロゴ画像 (2-b)
    print("\nロゴ画像のパスを入力してください。")
    print("  スキップする場合は空Enterで。")
    logo_input = input("ロゴ画像パス > ").strip()
    logo_image = logo_input if logo_input and os.path.exists(logo_input) else None
    if logo_input and not logo_image:
        print(f"  ファイルが見つかりません: {logo_input}。スキップします。")

    # 映像位置調整 (4-a)
    print("\n映像のY軸オフセットを入力してください。(正=下、負=上)")
    print("  スキップする場合は空Enterで。")
    offset_input = input("Y軸オフセット (px) > ").strip()
    video_offset_y = None
    if offset_input:
        try:
            video_offset_y = int(offset_input)
        except ValueError:
            print("  数値が正しくありません。スキップします。")

    # 出力パス
    os.makedirs("output", exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = f"output/edited_{timestamp}.mp4"

    # 実行
    print(f"\n動画をダウンロード中: {url}")
    try:
        input_path = download_video(url, output_dir="input")
    except Exception as e:
        print(f"\nダウンロードエラー: {e}")
        sys.exit(1)

    print("\n動画を編集中...")
    try:
        result = process_video(
            input_path=input_path,
            output_path=output_path,
            text_lines=lines,
            skip_cta=False,
            profile_image="assets/profile.png",
            checkmark_image="assets/checkmark.png",
            crop=crop,
            logo_image=logo_image,
            video_offset_y=video_offset_y,
        )
        print(f"\n完了！出力ファイル: {result}")
        print(f"  → output フォルダを確認してください")
    except Exception as e:
        print(f"\n編集エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
