"""Named presentation presets shared by the interface and exported figures.

Pastel presets prioritize a soft appearance. The Okabe–Ito preset is the
recommended color-vision-aware option; shapes and labels remain in every preset.
"""

PALETTES = {
    "soft": {
        "name": "Soft pastels",
        "description": "Gentle mixed colors with distinct shapes and labels.",
        "colors": ["#82B0CB", "#DEB386", "#9DBB9A", "#B6A4C8", "#B8B7B1", "#85C6C1", "#D4A6B5", "#C6C58D"],
        "accent": "#386D8A", "surface": "#EAF1F4", "background": "#FAFBFC", "heatmap": "cividis",
    },
    "ocean": {
        "name": "Ocean & sand",
        "description": "Soft blue, teal and sand tones. Use shapes to distinguish similar hues.",
        "colors": ["#77A9C8", "#D9B382", "#78B8B0", "#B8A2C8", "#A7BDCE", "#C99484", "#ADB899", "#929CAA"],
        "accent": "#286B76", "surface": "#E4F1F0", "background": "#F7FBFA", "heatmap": "Blues",
    },
    "lavender": {
        "name": "Lavender & sage",
        "description": "Muted purple, sage and blue for a softer presentation.",
        "colors": ["#A79AC6", "#94B5A2", "#D8B98A", "#84ADC8", "#C49EAF", "#9DA7AE", "#80B9B4", "#B8B590"],
        "accent": "#695383", "surface": "#EFEAF5", "background": "#FBF9FD", "heatmap": "Purples",
    },
    "accessible": {
        "name": "Colorblind contrast (Okabe–Ito)",
        "description": "Recommended when color separation matters more than a pastel appearance. Shapes and labels add a second cue.",
        "colors": ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#000000"],
        "accent": "#005B8E", "surface": "#E8F0F6", "background": "#FAFCFE", "heatmap": "cividis",
    },
    "grayscale": {
        "name": "Grayscale / print",
        "description": "Gray tones plus shapes, line styles and hatching for printing.",
        "colors": ["#4D4D4D", "#BBBBBB", "#777777", "#D0D0D0", "#969696", "#303030", "#AAAAAA", "#626262"],
        "accent": "#454545", "surface": "#EEEEEE", "background": "#FAFAFA", "heatmap": "Greys",
    },
}


def get_palette(key="soft"):
    if not isinstance(key, str) or key not in PALETTES:
        raise ValueError(f"Unknown palette. Choose one of: {', '.join(PALETTES)}")
    return PALETTES[key]
