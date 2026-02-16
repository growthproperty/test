"""
動画編集の設定値。CapCutの設定に基づく。

座標系:
  CapCutの座標系 → ピクセル座標への変換
  - CapCut: 原点=キャンバス中央, X右が正, Y上が正
  - ピクセル: 原点=左上, X右が正, Y下が正
  - pixel_x = canvas_w / 2 + capcut_x
  - pixel_y = canvas_h / 2 - capcut_y
"""

# === キャンバス設定 ===
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

# === ウォーターマーク (@business_ai_times) ===
WATERMARK_TEXT = "@business_ai_times"
WATERMARK_OPACITY = 0.20  # 20%
WATERMARK_SCALE = 0.40    # 40%
WATERMARK_FONT_SIZE = 28  # スケール適用前のベースサイズ
# CapCut座標: X=-525, Y=1630
# → 左上寄り、上部に配置
WATERMARK_X = 15   # キャンバス左端近く
WATERMARK_Y = 50   # キャンバス上部

# === メインテキスト ===
MAIN_TEXT_FONT_SIZE = 52  # スケール65%を反映したサイズ
MAIN_TEXT_DEFAULT_COLOR = "white"
MAIN_TEXT_ACCENT_COLOR = "#FFD700"  # 黄色

# テキスト位置 (ピクセル座標 - キャンバス中央基準のY位置)
# 2行構成 (標準)
TEXT_2LINE_Y = [460, 560]       # Y=1000, Y=800 相当
# 3行構成 (横長動画)
TEXT_3LINE_Y = [360, 460, 560]  # Y=1200, Y=1000, Y=800 相当
# 3行構成 (視点が中央の場合)
TEXT_3LINE_CENTER_Y = [460, 560, 660]  # Y=1000, Y=800, Y=600 相当

# テキスト行間
TEXT_LINE_SPACING = 100

# テキストの影 (読みやすさのため)
TEXT_SHADOW_OFFSET = 3
TEXT_SHADOW_COLOR = (0, 0, 0, 180)

# === CTA (コール・トゥ・アクション) ===
CTA_TEXT = "最新の海外AI事例を知りたい方はフォロー"
CTA_FONT_SIZE = 28
CTA_TEXT_COLOR = "white"
CTA_MIN_DURATION = 2.0    # 最低表示秒数
# CTA表示タイミング: 動画尾から何秒前に開始するか
CTA_TIMING_RULES = {
    10: 2.0,   # 10秒動画 → 残り2秒
    30: 5.0,   # 30秒動画 → 残り5秒
}
CTA_DEFAULT_RATIO = 0.15  # デフォルト: 動画の最後15%

# CTA配置 (キャンバス下部)
CTA_PROFILE_SIZE = (80, 80)     # プロフィール画像サイズ
CTA_CHECKMARK_SIZE = (30, 30)   # チェックマークサイズ
CTA_Y_POSITION = 1700           # キャンバス上のY位置 (ピクセル)
CTA_PADDING = 15

# === ブラックボックス (コメント隠し) ===
BLACKBOX_COLOR = (0, 0, 0, 255)

# === フォント ===
import os

# 日本語フォントのパス (利用可能なものを優先順に試す)
FONT_PATHS = [
    # Windows
    "C:/Windows/Fonts/msgothic.ttc",    # MS ゴシック
    "C:/Windows/Fonts/meiryo.ttc",      # メイリオ
    "C:/Windows/Fonts/YuGothR.ttc",     # 游ゴシック Regular
    "C:/Windows/Fonts/YuGothM.ttc",     # 游ゴシック Medium
    "C:/Windows/Fonts/YuGothB.ttc",     # 游ゴシック Bold
    # Linux
    "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",   # IPA Pゴシック
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",     # IPAゴシック
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    # macOS
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]

# 英字フォント (ウォーターマーク用)
LATIN_FONT_PATHS = [
    # Windows
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

# カスタムフォントパス (ユーザーが後から指定)
CUSTOM_FONT_PATH = None


def get_font_path(prefer_latin=False):
    """利用可能な日本語フォントのパスを返す"""
    if CUSTOM_FONT_PATH and os.path.exists(CUSTOM_FONT_PATH):
        return CUSTOM_FONT_PATH

    paths = LATIN_FONT_PATHS if prefer_latin else FONT_PATHS
    for path in paths:
        if os.path.exists(path):
            return path

    # フォールバック: 全リストを試す
    for path in FONT_PATHS + LATIN_FONT_PATHS:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        "日本語フォントが見つかりません。CUSTOM_FONT_PATH を設定してください。"
    )


def get_cta_start_time(video_duration: float) -> float:
    """動画の長さからCTA表示開始時間を計算"""
    # ルールに基づいて計算
    for max_dur, offset in sorted(CTA_TIMING_RULES.items()):
        if video_duration <= max_dur:
            start = video_duration - offset
            return max(0, start)

    # ルールに該当しない場合: 最後の15%
    offset = video_duration * CTA_DEFAULT_RATIO
    offset = max(offset, CTA_MIN_DURATION)
    start = video_duration - offset
    return max(0, start)
