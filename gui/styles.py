"""Styles module - Color schemes"""

COLORS = {
    'bg': '#f5f5f5', 'card_bg': '#ffffff', 'primary': '#2196F3',
    'success': '#4CAF50', 'warning': '#FF9800', 'error': '#F44336',
    'text': '#212121', 'text_secondary': '#757575', 'accent': '#00BCD4',
    'register': '#E3F2FD', 'stack': '#FFF3E0', 'memory': '#F3E5F5',
    'flag_on': '#4CAF50', 'flag_off': '#9E9E9E',
}

def darken_color(color: str) -> str:
    if color.startswith('#'):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        r, g, b = max(0, r-30), max(0, g-30), max(0, b-30)
        return f'#{r:02x}{g:02x}{b:02x}'
    return color
