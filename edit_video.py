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

    # 黒ボックス
    parser.add_argument(
        "--blackbox", "-b",
        action="append",
        default=None,
        help="コメント隠し: x,y,w,h (複数指定可)",
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
        )
        print(f"\n編集完了: {result}")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
