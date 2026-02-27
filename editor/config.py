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
WATERMARK_OPACITY = 0.25  # 25%
WATERMARK_SCALE = 0.50    # 50%
WATERMARK_FONT_SIZE = 52  # スケール適用前のベースサイズ
# CapCut座標: X=-525, Y=1630
# → 左上寄り、上部に配置
WATERMARK_X = 15   # キャンバス左端近く
WATERMARK_Y = 50   # キャンバス上部

# === メインテキスト ===
MAIN_TEXT_FONT_SIZE = 68  # 参考画像に合わせたサイズ
MAIN_TEXT_DEFAULT_COLOR = "white"
MAIN_TEXT_ACCENT_COLOR = "#FFD700"  # 黄色

# テキスト位置 (ピクセル座標)
# 黒帯 (0〜650px) の下寄りに配置し、動画との間隔を詰める
# 1行構成
TEXT_1LINE_Y = [500]
# 2行構成 (標準)
TEXT_2LINE_Y = [400, 530]
# 3行構成
TEXT_3LINE_Y = [270, 400, 530]
# 3行構成 (視点が中央の場合)
TEXT_3LINE_CENTER_Y = [270, 400, 530]

# テキスト行間 (4行以上のフォールバック用)
TEXT_LINE_SPACING = 130

# テキストの影 (読みやすさのため)
TEXT_SHADOW_OFFSET = 5
TEXT_SHADOW_COLOR = (0, 0, 0, 200)

# テキストの境界線（ストローク） - 黒い太い縁取り
TEXT_STROKE_WIDTH = 15
# 文字を太くする追加オフセット描画の範囲 (0=無効)
TEXT_BOLD_EXTRA = 3
TEXT_STROKE_COLOR = (0, 0, 0, 255)

# === 黄色 (ゴールドグラデーション) エフェクト ===
YELLOW_GRADIENT_TOP = (255, 245, 50)      # 上部: 鮮やかなイエロー
YELLOW_GRADIENT_BOTTOM = (210, 150, 0)    # 下部: リッチゴールド

# === 赤エフェクトテキスト ===
# 赤い文字にグロー（光彩）エフェクトを適用
RED_EFFECT_COLOR = (255, 0, 0, 255)
RED_GLOW_COLOR = (255, 0, 0, 80)    # グローの色 (半透明の赤)
RED_GLOW_RADIUS = 8                   # グローの広がり（ピクセル）
RED_GLOW_PASSES = 3                   # グローの重ね描き回数

# === CTA (コール・トゥ・アクション) ===
CTA_TEXT_LINES = ["海外の最新事例を", "知りたい方はフォロー"]
CTA_FONT_SIZE = 68                     # メインテキストと同サイズ
CTA_TEXT_COLOR = "white"
CTA_TEXT_STROKE_WIDTH = 25             # メインテキストと同じ縁取り
CTA_TEXT_SHADOW_OFFSET = 4             # メインテキストと同じ影
CTA_TEXT_MARGIN_TOP = 40               # プロフィール画像下端からテキストまでの余白
CTA_TEXT_LINE_SPACING = 110            # テキスト行間
CTA_MIN_DURATION = 2.0                 # 最低表示秒数
# CTA表示タイミング: 動画尾から何秒前に開始するか
CTA_TIMING_RULES = {
    10: 2.0,   # 10秒動画 → 残り2秒
    30: 5.0,   # 30秒動画 → 残り5秒
}
CTA_DEFAULT_RATIO = 0.15  # デフォルト: 動画の最後15%

# CTA配置: プロフィールスクリーンショットを上部に表示
CTA_PROFILE_Y = 0                      # プロフィール画像Y位置 (キャンバス上端)
CTA_PROFILE_MAX_HEIGHT_RATIO = 0.40    # プロフィール画像最大高さ (キャンバス比率)

# フォローボタン赤丸 (プロフィール画像上に赤い楕円を描画)
CTA_FOLLOW_CIRCLE_ENABLED = False       # 赤丸は不要
CTA_FOLLOW_CIRCLE_X_RATIO = 0.33      # フォローボタン中心X (プロフィール幅に対する比率)
CTA_FOLLOW_CIRCLE_Y_RATIO = 0.42      # フォローボタン中心Y (プロフィール高さに対する比率)
CTA_FOLLOW_CIRCLE_RX = 120            # 楕円の水平半径 (ピクセル)
CTA_FOLLOW_CIRCLE_RY = 28             # 楕円の垂直半径 (ピクセル)
CTA_FOLLOW_CIRCLE_COLOR = (255, 0, 0, 255)  # 赤
CTA_FOLLOW_CIRCLE_WIDTH = 6           # 線の太さ

# === カット編集 (1-a) ===
# --cut で指定された区間をリップル削除する
# 形式: "開始秒,終了秒" (例: "5.0,10.0" → 5〜10秒を削除)

# === クロップ (1-b) ===
# 不要なロゴを切り取るための上下左右のクロップ率 (%)
# 例: CROP_TOP=5 → 上端5%を切り取り
CROP_DEFAULT = {"top": 0, "bottom": 0, "left": 0, "right": 0}

# === ロゴ画像 (2-b) ===
# 「Business AI Times」ロゴ画像の配置設定
# CapCut座標: X=-525, Y=1630 → ピクセル: X=15, Y=50
LOGO_X = 15
LOGO_Y = 50
LOGO_SCALE = 0.40       # 40%
LOGO_OPACITY = 0.20     # 20%

# === 映像位置調整 (4-a, 4-b) ===
# 動画をキャンバス内で上下にオフセット (ピクセル)
# 正の値 → 下へ移動、負の値 → 上へ移動
VIDEO_OFFSET_Y = 0
# 見切れ防止: 移動後にスケールを自動調整して黒余白を消す
VIDEO_AUTO_SCALE = True

# === ソーステキストマスク (元動画の字幕/テキスト隠し) ===
# キャンバス上部+下部に黒帯を配置して元動画のテキスト/ロゴを隠す
SOURCE_TEXT_MASK_HEIGHT = 650  # 最低限の上部マスク高さ
# 動的計算: 映像がキャンバス上で始まるY位置より下まで黒帯を伸ばす
SOURCE_TEXT_MASK_VIDEO_COVER_TOP = 100    # 映像上端から何px分を覆うか
SOURCE_TEXT_MASK_VIDEO_COVER_BOTTOM = 200  # 映像下端から何px分を覆うか (横長動画・ロゴ隠し)
SOURCE_TEXT_MASK_PORTRAIT_BOTTOM = 400    # 縦長動画: キャンバス下端から400px分を覆う (ロゴ隠し)

# === ブラックボックス (コメント隠し) ===
BLACKBOX_COLOR = (0, 0, 0, 255)

# === フォント ===
import os

# 日本語フォントのパス (利用可能なものを優先順に試す)
FONT_PATHS = [
    # Windows (太字を優先)
    "C:/Windows/Fonts/YuGothB.ttc",     # 游ゴシック Bold
    "C:/Windows/Fonts/meiryob.ttc",     # メイリオ Bold
    "C:/Windows/Fonts/YuGothM.ttc",     # 游ゴシック Medium
    "C:/Windows/Fonts/meiryo.ttc",      # メイリオ
    "C:/Windows/Fonts/msgothic.ttc",    # MS ゴシック
    "C:/Windows/Fonts/YuGothR.ttc",     # 游ゴシック Regular
    # Linux (最も太いウェイトを優先)
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",  # Noto Sans CJK Black (最太)
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",  # Noto Sans CJK Bold
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
