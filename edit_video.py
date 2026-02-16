#!/usr/bin/env python3
"""
Instagram動画自動編集ツール

使い方:
  # Instagram URLからダウンロード＆編集
  python edit_video.py --url "https://www.instagram.com/reel/xxx/" \
      --text "1行目のテキスト" "2行目のテキスト" \
      --colors white yellow

  # ローカルファイルを編集
  python edit_video.py --file input/video.mp4 \
      --text "中国で製作されたAI動画" "リアルすぎてもはや怖い" \
      --colors yellow white

  # 3行テキスト + コメント隠し
  python edit_video.py --file input/video.mp4 \
      --text "1行目" "2行目" "3行目" \
      --colors white yellow white \
      --blackbox 50,600,400,80

  # 赤グローエフェクト付き
  python edit_video.py --file input/video.mp4 \
      --text "1行目" "2行目" "3行目" \
      --colors white yellow red \
      --effects none none red_glow

  # カット編集 (5〜10秒を削除)
  python edit_video.py --file input/video.mp4 \
      --text "テキスト" --colors white \
      --cut 5.0,10.0

  # クロップ (上5%、右3%を切り取ってロゴを隠す)
  python edit_video.py --file input/video.mp4 \
      --text "テキスト" --colors white \
      --crop 5,0,0,3

  # ロゴ画像配置 + 映像位置調整
  python edit_video.py --file input/video.mp4 \
      --text "テキスト" --colors white \
      --logo assets/logo.png \
      --video-offset-y 50

  # CTA付き
  python edit_video.py --file input/video.mp4 \
      --text "テキスト1" "テキスト2" \
      --colors white yellow \
      --profile assets/profile.png \
      --checkmark assets/checkmark.png
"""

import argparse
import os
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from editor.downloader import download_video, get_video_info
from editor.processor import process_video
from editor import config


def parse_args():
    parser = argparse.ArgumentParser(
        description="Instagram動画自動編集ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # 入力ソース (URL or ファイル)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--url", "-u",
        help="Instagram動画のURL",
    )
    input_group.add_argument(
        "--file", "-f",
        help="ローカル動画ファイルのパス",
    )

    # テキスト設定
    parser.add_argument(
        "--text", "-t",
        nargs="+",
        required=True,
        help="オーバーレイテキスト (1-3行、スペース区切り)",
    )
    parser.add_argument(
        "--colors", "-c",
        nargs="+",
        default=None,
        help="各行の色 (white, yellow, red, #RRGGBB)。省略時: 1行目=white",
    )
    parser.add_argument(
        "--effects", "-e",
        nargs="+",
        default=None,
        help="各行のエフェクト (none, red_glow)。省略時: none",
    )

    # カット編集 (1-a)
    parser.add_argument(
        "--cut",
        action="append",
        default=None,
        help="カットする区間: start,end (秒)。複数指定可。例: 5.0,10.0",
    )

    # クロップ (1-b)
    parser.add_argument(
        "--crop",
        default=None,
        help="クロップ率(%%): top,bottom,left,right。例: 5,0,0,3",
    )

    # 黒ボックス
    parser.add_argument(
        "--blackbox", "-b",
        action="append",
        default=None,
        help="コメント隠し: x,y,w,h (複数指定可)",
    )

    # ロゴ画像 (2-b)
    parser.add_argument(
        "--logo",
        default=None,
        help="自社ロゴ画像のパス (スケール40%%, 不透明度20%%で配置)",
    )

    # CTA
    parser.add_argument(
        "--profile",
        default=None,
        help="CTAプロフィール画像のパス",
    )
    parser.add_argument(
        "--checkmark",
        default=None,
        help="CTAチェックマーク画像のパス",
    )
    parser.add_argument(
        "--no-cta",
        action="store_true",
        help="CTAを省略する",
    )

    # テキスト位置のカスタマイズ
    parser.add_argument(
        "--y-positions",
        nargs="+",
        type=int,
        default=None,
        help="テキスト行のY座標 (ピクセル)。例: 460 560",
    )

    # 元テキスト隠し (デフォルトON)
    parser.add_argument(
        "--no-hide-source-text",
        action="store_true",
        help="元動画テキスト隠しを無効にする (デフォルトは隠す)",
    )
    parser.add_argument(
        "--source-text-height",
        type=int,
        default=None,
        help="黒帯の高さ (ピクセル)。--hide-source-text と併用。デフォルト: 650",
    )

    # 映像位置調整 (4-a)
    parser.add_argument(
        "--video-offset-y",
        type=int,
        default=None,
        help="映像のY軸オフセット (ピクセル)。正=下、負=上。例: 50",
    )

    # 出力
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="出力ファイルパス (省略時: output/<タイムスタンプ>.mp4)",
    )

    # フォント
    parser.add_argument(
        "--font",
        default=None,
        help="カスタムフォントファイルのパス",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # カスタムフォント
    if args.font:
        config.CUSTOM_FONT_PATH = args.font

    # 入力動画の取得
    if args.url:
        print(f"\n動画をダウンロード中: {args.url}")
        input_path = download_video(args.url, output_dir="input")
    else:
        input_path = args.file
        if not os.path.exists(input_path):
            print(f"エラー: ファイルが見つかりません: {input_path}")
            sys.exit(1)

    # テキスト行の構築
    colors = args.colors or []
    effects = args.effects or []
    # デフォルト色: 交互に white, yellow
    default_colors = ["white", "yellow", "white"]
    text_lines = []
    for i, text in enumerate(args.text):
        color = colors[i] if i < len(colors) else default_colors[i % len(default_colors)]
        line_info = {"text": text, "color": color}

        # エフェクト設定
        if i < len(effects) and effects[i] != "none":
            line_info["effect"] = effects[i]
        elif color.lower() == "red" and (not effects or i >= len(effects)):
            # 色が red の場合、自動的に red_glow エフェクトを適用
            line_info["effect"] = "red_glow"

        text_lines.append(line_info)

    # カット区間の解析 (1-a)
    cuts = None
    if args.cut:
        cuts = []
        for cut_str in args.cut:
            parts = cut_str.split(",")
            if len(parts) != 2:
                print(f"エラー: --cut は start,end 形式で指定してください: {cut_str}")
                sys.exit(1)
            start, end = float(parts[0]), float(parts[1])
            if start >= end:
                print(f"エラー: --cut の開始時間は終了時間より前にしてください: {cut_str}")
                sys.exit(1)
            cuts.append({"start": start, "end": end})

    # クロップの解析 (1-b)
    crop = None
    if args.crop:
        parts = args.crop.split(",")
        if len(parts) != 4:
            print(f"エラー: --crop は top,bottom,left,right 形式で指定してください: {args.crop}")
            sys.exit(1)
        top, bottom, left, right = map(float, parts)
        crop = {"top": top, "bottom": bottom, "left": left, "right": right}

    # 黒ボックスの解析
    blackboxes = None
    if args.blackbox:
        blackboxes = []
        for box_str in args.blackbox:
            parts = box_str.split(",")
            if len(parts) != 4:
                print(f"エラー: --blackbox は x,y,w,h 形式で指定してください: {box_str}")
                sys.exit(1)
            x, y, w, h = map(int, parts)
            blackboxes.append({"x": x, "y": y, "w": w, "h": h})

    # 出力パス
    if args.output:
        output_path = args.output
    else:
        os.makedirs("output", exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f"output/edited_{timestamp}.mp4"

    # 動画編集の実行
    try:
        result = process_video(
            input_path=input_path,
            output_path=output_path,
            text_lines=text_lines,
            blackboxes=blackboxes,
            y_positions=args.y_positions,
            profile_image=args.profile,
            checkmark_image=args.checkmark,
            skip_cta=args.no_cta,
            cuts=cuts,
            crop=crop,
            logo_image=args.logo,
            video_offset_y=args.video_offset_y,
            hide_source_text=not args.no_hide_source_text,
            source_text_height=args.source_text_height,
        )
        print(f"\n編集完了: {result}")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
