"""テキスト・画像オーバーレイ生成モジュール"""

import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
from . import config


def _load_font(size: int, prefer_latin: bool = False) -> ImageFont.FreeTypeFont:
    """フォントをロードする"""
    font_path = config.get_font_path(prefer_latin=prefer_latin)
    return ImageFont.truetype(font_path, size)


def _parse_inline_colors(text: str, default_color: str) -> list[dict]:
    """
    インラインカラータグを解析してセグメントに分割する。

    書式: {red}衝撃映像{/}がこちら
      → [{"text": "衝撃映像", "color": "red"}, {"text": "がこちら", "color": default_color}]

    対応色: red, yellow, white, または #RRGGBB 形式
    タグがない場合は全テキストを default_color で返す。
    """
    pattern = r"\{(\w+(?:#[0-9A-Fa-f]{6})?)\}(.*?)\{/\}"
    segments = []
    last_end = 0

    for match in re.finditer(pattern, text):
        # タグ前のテキスト
        if match.start() > last_end:
            before = text[last_end:match.start()]
            if before:
                segments.append({"text": before, "color": default_color})
        # タグ内のテキスト
        segments.append({"text": match.group(2), "color": match.group(1)})
        last_end = match.end()

    # タグ後の残りテキスト
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            segments.append({"text": remaining, "color": default_color})

    # タグなしの場合
    if not segments:
        segments = [{"text": text, "color": default_color}]

    return segments


def strip_inline_tags(text: str) -> str:
    """インラインカラータグを除去してプレーンテキストを返す"""
    return re.sub(r"\{(\w+(?:#[0-9A-Fa-f]{6})?)\}(.*?)\{/\}", r"\2", text)


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
            y_positions = config.TEXT_1LINE_Y
        elif num_lines == 2:
            y_positions = config.TEXT_2LINE_Y
        elif num_lines == 3:
            y_positions = config.TEXT_3LINE_Y
        else:
            # 4行以上: 1行目をY=600から開始、200px間隔
            y_positions = [600 + i * config.TEXT_LINE_SPACING for i in range(num_lines)]

    stroke_w = config.TEXT_STROKE_WIDTH
    stroke_color = config.TEXT_STROKE_COLOR
    shadow_rgba = config.TEXT_SHADOW_COLOR
    offset = config.TEXT_SHADOW_OFFSET

    for i, line_info in enumerate(lines):
        text = line_info["text"]
        default_color = line_info.get("color", config.MAIN_TEXT_DEFAULT_COLOR)
        effect = line_info.get("effect", None)

        # インラインカラータグを解析してセグメントに分割
        segments = _parse_inline_colors(text, default_color)

        # 各セグメントの幅を計測
        seg_widths = []
        for seg in segments:
            bbox = draw.textbbox(
                (0, 0), seg["text"], font=font, stroke_width=stroke_w
            )
            seg_widths.append(bbox[2] - bbox[0])

        total_w = sum(seg_widths)
        current_x = (w - total_w) // 2
        y = y_positions[i] if i < len(y_positions) else y_positions[-1] + config.TEXT_LINE_SPACING * (i - len(y_positions) + 1)

        # セグメントごとに描画
        for seg_idx, seg in enumerate(segments):
            seg_text = seg["text"]
            seg_color = seg["color"]
            seg_rgba = _color_to_rgba(seg_color)
            seg_x = current_x

            # 赤グローエフェクト (行レベルまたはセグメント色が赤)
            is_red_seg = seg_color.lower() == "red"
            if is_red_seg or (effect == "red_glow" and len(segments) == 1):
                _draw_red_glow(img, seg_text, font, seg_x, y, stroke_w)
                # drawを再取得 (glow合成後)
                draw = ImageDraw.Draw(img)

            # 黄色テキスト → ゴールドグラデーションで描画
            bold_extra = getattr(config, "TEXT_BOLD_EXTRA", 0)
            is_yellow_seg = seg_color.lower() == "yellow"
            if is_yellow_seg:
                _draw_gold_gradient_text(
                    img, draw, seg_text, font, seg_x, y,
                    stroke_w, stroke_color, shadow_rgba, offset, bold_extra,
                )
                # drawを再取得 (合成後)
                draw = ImageDraw.Draw(img)
            else:
                # ドロップシャドウ (太字化に合わせて重ね描き)
                if bold_extra > 0:
                    for dx in range(-bold_extra, bold_extra + 1):
                        for dy in range(-bold_extra, bold_extra + 1):
                            draw.text(
                                (seg_x + offset + dx, y + offset + dy), seg_text, font=font,
                                fill=shadow_rgba, stroke_width=stroke_w, stroke_fill=shadow_rgba
                            )
                else:
                    draw.text(
                        (seg_x + offset, y + offset), seg_text, font=font,
                        fill=shadow_rgba, stroke_width=stroke_w, stroke_fill=shadow_rgba
                    )

                # 本文を描画 (境界線＝ストローク付き + 重ね描きで太字化)
                if bold_extra > 0:
                    for dx in range(-bold_extra, bold_extra + 1):
                        for dy in range(-bold_extra, bold_extra + 1):
                            draw.text(
                                (seg_x + dx, y + dy), seg_text, font=font,
                                fill=seg_rgba, stroke_width=stroke_w, stroke_fill=stroke_color
                            )
                else:
                    draw.text(
                        (seg_x, y), seg_text, font=font,
                        fill=seg_rgba, stroke_width=stroke_w, stroke_fill=stroke_color
                    )

            current_x += seg_widths[seg_idx]

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


def _draw_gold_gradient_text(
    img: Image.Image,
    draw: ImageDraw.Draw,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    stroke_w: int,
    stroke_color: tuple,
    shadow_rgba: tuple,
    shadow_offset: int,
    bold_extra: int,
) -> None:
    """
    金色グラデーション (上:明るい黄色 → 下:ダークゴールド) でテキストを描画する。
    1. ストローク(黒縁)を先に描画
    2. 白テキストを描画 → そのアルファをマスクにしてグラデーションを合成
    """
    top_color = config.YELLOW_GRADIENT_TOP
    bottom_color = config.YELLOW_GRADIENT_BOTTOM

    # テキストのバウンディングボックスを取得
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
    text_h = bbox[3] - bbox[1]

    # --- ドロップシャドウ ---
    if bold_extra > 0:
        for dx in range(-bold_extra, bold_extra + 1):
            for dy in range(-bold_extra, bold_extra + 1):
                draw.text(
                    (x + shadow_offset + dx, y + shadow_offset + dy), text, font=font,
                    fill=shadow_rgba, stroke_width=stroke_w, stroke_fill=shadow_rgba
                )
    else:
        draw.text(
            (x + shadow_offset, y + shadow_offset), text, font=font,
            fill=shadow_rgba, stroke_width=stroke_w, stroke_fill=shadow_rgba
        )

    # --- ストローク (黒縁) のみ描画 ---
    if bold_extra > 0:
        for dx in range(-bold_extra, bold_extra + 1):
            for dy in range(-bold_extra, bold_extra + 1):
                draw.text(
                    (x + dx, y + dy), text, font=font,
                    fill=(0, 0, 0, 0), stroke_width=stroke_w, stroke_fill=stroke_color
                )
    else:
        draw.text(
            (x, y), text, font=font,
            fill=(0, 0, 0, 0), stroke_width=stroke_w, stroke_fill=stroke_color
        )

    # --- グラデーション付きテキストを一時レイヤーに描画 ---
    # 1. テキスト形状のマスクを作成
    mask_layer = Image.new("L", img.size, 0)
    mask_draw = ImageDraw.Draw(mask_layer)
    if bold_extra > 0:
        for dx in range(-bold_extra, bold_extra + 1):
            for dy in range(-bold_extra, bold_extra + 1):
                mask_draw.text(
                    (x + dx, y + dy), text, font=font,
                    fill=255, stroke_width=stroke_w, stroke_fill=0
                )
    else:
        mask_draw.text(
            (x, y), text, font=font,
            fill=255, stroke_width=stroke_w, stroke_fill=0
        )

    # 2. 縦方向グラデーション画像を作成 (1px幅 → 横に引き伸ばし)
    grad_strip = Image.new("RGB", (1, max(text_h, 1)))
    for row in range(text_h):
        t = row / max(text_h - 1, 1)
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        grad_strip.putpixel((0, row), (r, g, b))

    grad_full = grad_strip.resize(img.size, Image.BILINEAR)

    # Y位置に合わせてグラデーションをシフト (テキスト上端=明るい色)
    shifted = Image.new("RGB", img.size, bottom_color)
    shifted.paste(grad_full.crop((0, 0, img.size[0], img.size[1] - y)), (0, y))

    # 3. マスクでグラデーションを切り抜いてRGBAに変換し合成
    grad_rgba = shifted.copy().convert("RGBA")
    grad_rgba.putalpha(mask_layer)

    img.paste(Image.alpha_composite(Image.new("RGBA", img.size, (0, 0, 0, 0)), grad_rgba), (0, 0), grad_rgba)


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
    bottom_start: int = None,
) -> Image.Image:
    """
    元動画のテキスト/字幕を隠すための黒帯マスクを生成する。

    キャンバス上部+下部に黒い帯を配置し、元動画のテキスト/ロゴを隠しつつ
    日本語テキストのクリーンな背景として機能する。

    Args:
        height: 上部黒帯の高さ (ピクセル)。Noneならconfig値を使用。
        canvas_size: (width, height)
        bottom_start: 下部黒帯の開始Y位置。Noneなら下部マスクなし。

    Returns:
        透過PNG画像（上部・下部が黒で不透明）
    """
    w = canvas_size[0] if canvas_size else config.CANVAS_WIDTH
    h = canvas_size[1] if canvas_size else config.CANVAS_HEIGHT
    mask_h = height if height else config.SOURCE_TEXT_MASK_HEIGHT
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 上部に黒い帯を描画
    draw.rectangle([0, 0, w, mask_h], fill=(0, 0, 0, 255))

    # 下部に黒い帯を描画 (ロゴ隠し)
    if bottom_start is not None:
        draw.rectangle([0, bottom_start, w, h], fill=(0, 0, 0, 255))

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
    プロフィールページのスクリーンショット + フォローボタン赤丸 + フォロー文言

    Args:
        profile_image_path: プロフィールページのスクリーンショット画像パス
        checkmark_image_path: 未使用 (後方互換性のため残す)
        canvas_size: (width, height)

    Returns:
        透過PNG画像
    """
    w = canvas_size[0] if canvas_size else config.CANVAS_WIDTH
    h = canvas_size[1] if canvas_size else config.CANVAS_HEIGHT
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    profile_bottom = 0

    # プロフィールスクリーンショットを上部に配置
    if profile_image_path and os.path.exists(profile_image_path):
        profile = Image.open(profile_image_path).convert("RGBA")

        # キャンバス幅にスケール (アスペクト比維持)
        scale = w / profile.width
        new_h = int(profile.height * scale)

        # 最大高さを制限
        max_h = int(h * config.CTA_PROFILE_MAX_HEIGHT_RATIO)
        if new_h > max_h:
            new_h = max_h

        profile = profile.resize((w, new_h), Image.Resampling.LANCZOS)
        img.paste(profile, (0, config.CTA_PROFILE_Y), profile)
        profile_bottom = config.CTA_PROFILE_Y + new_h

        # フォローボタンに赤丸を描画
        if config.CTA_FOLLOW_CIRCLE_ENABLED:
            draw = ImageDraw.Draw(img)
            cx = int(w * config.CTA_FOLLOW_CIRCLE_X_RATIO)
            cy = config.CTA_PROFILE_Y + int(new_h * config.CTA_FOLLOW_CIRCLE_Y_RATIO)
            rx = config.CTA_FOLLOW_CIRCLE_RX
            ry = config.CTA_FOLLOW_CIRCLE_RY
            draw.ellipse(
                [cx - rx, cy - ry, cx + rx, cy + ry],
                outline=config.CTA_FOLLOW_CIRCLE_COLOR,
                width=config.CTA_FOLLOW_CIRCLE_WIDTH,
            )

    # プロフィール画像の下を黒背景で埋める (テキスト読みやすさのため)
    draw = ImageDraw.Draw(img)
    if profile_bottom > 0:
        draw.rectangle([0, profile_bottom, w, h], fill=(0, 0, 0, 230))

    # CTAテキスト (プロフィール画像の真下に配置、中央揃え)
    font = _load_font(config.CTA_FONT_SIZE)
    text_lines = config.CTA_TEXT_LINES
    shadow_off = config.CTA_TEXT_SHADOW_OFFSET
    stroke_w = config.CTA_TEXT_STROKE_WIDTH

    if profile_bottom > 0:
        text_start_y = profile_bottom + config.CTA_TEXT_MARGIN_TOP
    else:
        # プロフィール画像なし: キャンバス中央にテキスト配置
        total_h = len(text_lines) * config.CTA_TEXT_LINE_SPACING
        text_start_y = (h - total_h) // 2

    for i, text in enumerate(text_lines):
        text_y = text_start_y + i * config.CTA_TEXT_LINE_SPACING
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
        text_w = bbox[2] - bbox[0]
        text_x = (w - text_w) // 2

        # ドロップシャドウ
        draw.text(
            (text_x + shadow_off, text_y + shadow_off),
            text, font=font,
            fill=(0, 0, 0, 180),
            stroke_width=stroke_w,
            stroke_fill=(0, 0, 0, 180),
        )
        # 本文 (ストローク付き + 重ね描きで太字化)
        bold_extra = getattr(config, "TEXT_BOLD_EXTRA", 0)
        fill_color = _color_to_rgba(config.CTA_TEXT_COLOR)
        if bold_extra > 0:
            for dx in range(-bold_extra, bold_extra + 1):
                for dy in range(-bold_extra, bold_extra + 1):
                    draw.text(
                        (text_x + dx, text_y + dy),
                        text, font=font,
                        fill=fill_color,
                        stroke_width=stroke_w,
                        stroke_fill=(0, 0, 0, 255),
                    )
        else:
            draw.text(
                (text_x, text_y),
                text, font=font,
                fill=fill_color,
                stroke_width=stroke_w,
                stroke_fill=(0, 0, 0, 255),
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
