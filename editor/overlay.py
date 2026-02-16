"""テキスト・画像オーバーレイ生成モジュール"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
from . import config


def _load_font(size: int, prefer_latin: bool = False) -> ImageFont.FreeTypeFont:
    """フォントをロードする"""
    font_path = config.get_font_path(prefer_latin=prefer_latin)
    return ImageFont.truetype(font_path, size)


def create_watermark_image() -> Image.Image:
    """
    @business_ai_times ウォーターマーク画像を生成する。
    透過PNG。不透明度20%の白テキスト。
    """
    font_size = int(config.WATERMARK_FONT_SIZE * config.WATERMARK_SCALE)
    font = _load_font(font_size, prefer_latin=True)

    # テキストサイズを計測
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), config.WATERMARK_TEXT, font=font)
    text_w = bbox[2] - bbox[0] + 20
    text_h = bbox[3] - bbox[1] + 10

    # 透過画像にテキストを描画
    img = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    alpha = int(255 * config.WATERMARK_OPACITY)
    draw.text((10, 5), config.WATERMARK_TEXT, font=font, fill=(255, 255, 255, alpha))

    return img


def create_text_overlay(
    lines: list[dict],
    canvas_size: tuple[int, int] = None,
    y_positions: list[int] = None,
) -> Image.Image:
    """
    メインテキストのオーバーレイ画像を生成する。

    Args:
        lines: [{"text": "テキスト", "color": "white"}, ...]
                各行に "effect": "red_glow" を指定すると赤グローエフェクトを適用
        canvas_size: (width, height)
        y_positions: 各行のY位置 (ピクセル)。Noneなら自動計算。

    Returns:
        透過PNG画像
    """
    w = canvas_size[0] if canvas_size else config.CANVAS_WIDTH
    h = canvas_size[1] if canvas_size else config.CANVAS_HEIGHT
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(config.MAIN_TEXT_FONT_SIZE)

    num_lines = len(lines)

    # Y位置の決定
    if y_positions is None:
        if num_lines == 1:
            y_positions = [config.TEXT_2LINE_Y[0]]
        elif num_lines == 2:
            y_positions = config.TEXT_2LINE_Y
        else:
            y_positions = config.TEXT_3LINE_Y

    for i, line_info in enumerate(lines):
        text = line_info["text"]
        color = line_info.get("color", config.MAIN_TEXT_DEFAULT_COLOR)
        effect = line_info.get("effect", None)

        # 色名をRGBAに変換
        rgba = _color_to_rgba(color)
        shadow_rgba = config.TEXT_SHADOW_COLOR
        stroke_w = config.TEXT_STROKE_WIDTH
        stroke_color = config.TEXT_STROKE_COLOR

        # テキスト幅を計測して中央揃え (ストローク幅も考慮)
        bbox = draw.textbbox(
            (0, 0), text, font=font, stroke_width=stroke_w
        )
        text_w = bbox[2] - bbox[0]
        x = (w - text_w) // 2
        y = y_positions[i] if i < len(y_positions) else y_positions[-1] + config.TEXT_LINE_SPACING * (i - len(y_positions) + 1)

        # 赤グローエフェクト
        if effect == "red_glow":
            _draw_red_glow(img, text, font, x, y, stroke_w)

        # ドロップシャドウ (読みやすさ向上)
        offset = config.TEXT_SHADOW_OFFSET
        draw.text(
            (x + offset, y + offset), text, font=font,
            fill=shadow_rgba, stroke_width=stroke_w, stroke_fill=shadow_rgba
        )

        # 本文を描画 (境界線＝ストローク付き)
        draw.text(
            (x, y), text, font=font,
            fill=rgba, stroke_width=stroke_w, stroke_fill=stroke_color
        )

    return img


def _draw_red_glow(
    img: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    stroke_w: int,
) -> None:
    """
    赤いグロー（光彩）エフェクトをテキストの背景に描画する。
    テキストの周囲に半透明の赤い光を広げる。
    """
    glow_radius = config.RED_GLOW_RADIUS
    glow_color = config.RED_GLOW_COLOR
    passes = config.RED_GLOW_PASSES

    # グロー用の一時レイヤーを作成
    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    # 赤いテキストを描画 (太めのストロークでグロー範囲を広げる)
    glow_stroke = stroke_w + glow_radius
    glow_draw.text(
        (x, y), text, font=font,
        fill=glow_color, stroke_width=glow_stroke, stroke_fill=glow_color
    )

    # ガウシアンブラーで光彩をぼかす (複数回重ねて強調)
    for _ in range(passes):
        glow_layer = glow_layer.filter(
            ImageFilter.GaussianBlur(radius=glow_radius)
        )

    # グローレイヤーを合成
    img.paste(Image.alpha_composite(
        Image.new("RGBA", img.size, (0, 0, 0, 0)),
        glow_layer
    ), (0, 0), glow_layer)


def create_logo_overlay(
    logo_path: str,
    canvas_size: tuple[int, int] = None,
) -> Image.Image:
    """
    ロゴ画像のオーバーレイを生成する。(2-b)

    ロゴをスケール・不透明度を適用してキャンバス上に配置する。
    設定値: config.LOGO_X, LOGO_Y, LOGO_SCALE, LOGO_OPACITY

    Args:
        logo_path: ロゴ画像のファイルパス
        canvas_size: (width, height)

    Returns:
        透過PNG画像
    """
    w = canvas_size[0] if canvas_size else config.CANVAS_WIDTH
    h = canvas_size[1] if canvas_size else config.CANVAS_HEIGHT
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # ロゴ画像を読み込み
    logo = Image.open(logo_path).convert("RGBA")

    # スケール適用
    scale = config.LOGO_SCALE
    new_w = int(logo.width * scale)
    new_h = int(logo.height * scale)
    logo = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 不透明度を適用
    opacity = config.LOGO_OPACITY
    alpha = logo.split()[3]
    alpha = alpha.point(lambda p: int(p * opacity))
    logo.putalpha(alpha)

    # 配置
    x = config.LOGO_X
    y = config.LOGO_Y
    img.paste(logo, (x, y), logo)

    return img


def create_source_text_mask(
    height: int = None,
    canvas_size: tuple[int, int] = None,
) -> Image.Image:
    """
    元動画のテキスト/字幕を隠すための黒帯マスクを生成する。

    キャンバス上部に黒い帯を配置し、元動画のテキストを隠しつつ
    日本語テキストのクリーンな背景として機能する。

    Args:
        height: 黒帯の高さ (ピクセル)。Noneならconfig値を使用。
        canvas_size: (width, height)

    Returns:
        透過PNG画像（上部が黒で不透明）
    """
    w = canvas_size[0] if canvas_size else config.CANVAS_WIDTH
    h = canvas_size[1] if canvas_size else config.CANVAS_HEIGHT
    mask_h = height if height else config.SOURCE_TEXT_MASK_HEIGHT
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 上部に黒い帯を描画
    draw.rectangle([0, 0, w, mask_h], fill=(0, 0, 0, 255))

    return img


def create_blackbox_overlay(
    boxes: list[dict],
    canvas_size: tuple[int, int] = None,
) -> Image.Image:
    """
    黒い四角形のオーバーレイを生成する（コメント隠し用）。

    Args:
        boxes: [{"x": int, "y": int, "w": int, "h": int}, ...]
        canvas_size: (width, height)

    Returns:
        透過PNG画像（黒四角部分のみ不透明）
    """
    w = canvas_size[0] if canvas_size else config.CANVAS_WIDTH
    h = canvas_size[1] if canvas_size else config.CANVAS_HEIGHT
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for box in boxes:
        x1 = box["x"]
        y1 = box["y"]
        x2 = x1 + box["w"]
        y2 = y1 + box["h"]
        draw.rectangle([x1, y1, x2, y2], fill=config.BLACKBOX_COLOR)

    return img


def create_cta_overlay(
    profile_image_path: str = None,
    checkmark_image_path: str = None,
    canvas_size: tuple[int, int] = None,
) -> Image.Image:
    """
    CTA (コール・トゥ・アクション) オーバーレイを生成する。
    プロフィール画像 + チェックマーク + フォロー文言

    Args:
        profile_image_path: プロフィールのスクリーンショット画像パス
        checkmark_image_path: チェックマーク画像パス
        canvas_size: (width, height)

    Returns:
        透過PNG画像
    """
    w = canvas_size[0] if canvas_size else config.CANVAS_WIDTH
    h = canvas_size[1] if canvas_size else config.CANVAS_HEIGHT
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    padding = config.CTA_PADDING
    cta_y = config.CTA_Y_POSITION
    current_x = padding + 20

    # プロフィール画像
    if profile_image_path and os.path.exists(profile_image_path):
        profile = Image.open(profile_image_path).convert("RGBA")
        profile = profile.resize(config.CTA_PROFILE_SIZE, Image.Resampling.LANCZOS)
        img.paste(profile, (current_x, cta_y), profile)
        current_x += config.CTA_PROFILE_SIZE[0] + padding

    # チェックマーク
    if checkmark_image_path and os.path.exists(checkmark_image_path):
        check = Image.open(checkmark_image_path).convert("RGBA")
        check = check.resize(config.CTA_CHECKMARK_SIZE, Image.Resampling.LANCZOS)
        check_y = cta_y + (config.CTA_PROFILE_SIZE[1] - config.CTA_CHECKMARK_SIZE[1]) // 2
        img.paste(check, (current_x, check_y), check)
        current_x += config.CTA_CHECKMARK_SIZE[0] + padding

    # テキスト
    font = _load_font(config.CTA_FONT_SIZE)
    draw = ImageDraw.Draw(img)
    text_y = cta_y + (config.CTA_PROFILE_SIZE[1] - config.CTA_FONT_SIZE) // 2
    # 影
    draw.text(
        (current_x + 2, text_y + 2),
        config.CTA_TEXT,
        font=font,
        fill=(0, 0, 0, 160),
    )
    draw.text(
        (current_x, text_y),
        config.CTA_TEXT,
        font=font,
        fill=_color_to_rgba(config.CTA_TEXT_COLOR),
    )

    return img


def _color_to_rgba(color) -> tuple:
    """色名またはHEXコードをRGBAタプルに変換"""
    if isinstance(color, tuple):
        if len(color) == 3:
            return color + (255,)
        return color

    color_map = {
        "white": (255, 255, 255, 255),
        "yellow": (255, 215, 0, 255),
        "red": (255, 0, 0, 255),
        "black": (0, 0, 0, 255),
    }

    if color.lower() in color_map:
        return color_map[color.lower()]

    # HEXコード
    if color.startswith("#"):
        color = color.lstrip("#")
        if len(color) == 6:
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            return (r, g, b, 255)
        elif len(color) == 8:
            r, g, b, a = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16), int(color[6:8], 16)
            return (r, g, b, a)

    return (255, 255, 255, 255)
