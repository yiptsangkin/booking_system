DEFAULT_COLOR_HEX = "#d5dde2"

COLOR_OPTIONS = [
    {"name": "象牙白", "hex": "#f7f1df"},
    {"name": "珍珠白", "hex": "#f5f6ef"},
    {"name": "浅杏", "hex": "#ead4b5"},
    {"name": "浅灰", "hex": "#c9ced3"},
    {"name": "中灰", "hex": "#7d8790"},
    {"name": "蓝灰", "hex": "#8094a6"},
    {"name": "米白", "hex": "#efe5cf"},
    {"name": "海盐蓝", "hex": "#8fb7c9"},
    {"name": "薄荷绿", "hex": "#a8d7bf"},
    {"name": "铁红", "hex": "#9d3f32"},
    {"name": "哑黑", "hex": "#22252a"},
]

_COLOR_HEX_BY_NAME = {item["name"]: item["hex"] for item in COLOR_OPTIONS}


def color_hex(color_name: str) -> str:
    return _COLOR_HEX_BY_NAME.get(color_name, DEFAULT_COLOR_HEX)


def is_known_color(color_name: str) -> bool:
    return color_name in _COLOR_HEX_BY_NAME


def color_options(extra_names: list[str] | None = None) -> list[dict[str, str]]:
    options = [dict(item) for item in COLOR_OPTIONS]
    known = {item["name"] for item in options}
    for name in extra_names or []:
        if name and name not in known:
            options.append({"name": name, "hex": DEFAULT_COLOR_HEX})
            known.add(name)
    return options
