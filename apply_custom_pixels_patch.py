from pathlib import Path
import re
import shutil
import sys

TARGET = Path("streamlit_app.py")
BACKUP = Path("streamlit_app_backup_before_custom_pixels.py")

if not TARGET.exists():
    print("ERROR: streamlit_app.py not found in this folder.")
    print("Run this script from your Image-Format-Converter project folder.")
    sys.exit(1)

text = TARGET.read_text(encoding="utf-8")

# ---------------------------------------------------------
# BACKUP
# ---------------------------------------------------------
if not BACKUP.exists():
    shutil.copy2(TARGET, BACKUP)
    print(f"Backup created: {BACKUP}")

changes = 0

# ---------------------------------------------------------
# 1) LIGHT BLUE DASHBOARD COLOR
# ---------------------------------------------------------
old = "background-color: #f6f8fc;"
new = "background-color: #eef4ff;"
if old in text:
    text = text.replace(old, new, 1)
    changes += 1

old = '[data-testid="stSidebar"] {\n    background-color: #ffffff;\n    border-right: 1px solid #e5e7eb;\n}'
new = '[data-testid="stSidebar"] {\n    background-color: #e8f1ff;\n    border-right: 1px solid #bfd3f2;\n}'
if old in text:
    text = text.replace(old, new, 1)
    changes += 1

# ---------------------------------------------------------
# 2) DEFAULT VARIABLES
# ---------------------------------------------------------
if "custom_pixels_enabled = False" not in text:
    old = 'custom_unit = "Pixels"\n\ndpi = 300'
    new = (
        'custom_unit = "Pixels"\n\n'
        'custom_pixels_enabled = False\n'
        'custom_pixel_width = 1920\n'
        'custom_pixel_height = 1080\n\n'
        'dpi = 300'
    )
    if old not in text:
        print("ERROR: Could not find DEFAULTS insertion point.")
        sys.exit(1)
    text = text.replace(old, new, 1)
    changes += 1

# ---------------------------------------------------------
# 3) SEPARATE CUSTOM PIXELS CHANGER IN SIDEBAR
# ---------------------------------------------------------
if '"🔢 Custom Pixels Changer"' not in text:
    marker = (
        '        # -------------------------------------------------\n'
        '        # RESIZE BEHAVIOUR\n'
        '        # -------------------------------------------------\n'
    )

    block = (
        '        # -------------------------------------------------\n'
        '        # SEPARATE CUSTOM PIXELS CHANGER\n'
        '        # -------------------------------------------------\n\n'
        '        st.divider()\n\n'
        '        st.subheader(\n'
        '            "🔢 Custom Pixels Changer"\n'
        '        )\n\n'
        '        custom_pixels_enabled = st.checkbox(\n'
        '            "Use Custom Pixels",\n'
        '            value=False,\n'
        '            help=(\n'
        '                "Enable this to override the selected "\n'
        '                "size preset with any pixel width and height."\n'
        '            )\n'
        '        )\n\n'
        '        pixel_col1, pixel_col2 = (\n'
        '            st.columns(2)\n'
        '        )\n\n'
        '        with pixel_col1:\n'
        '            custom_pixel_width = (\n'
        '                st.number_input(\n'
        '                    "Width (px)",\n'
        '                    min_value=1,\n'
        '                    max_value=50000,\n'
        '                    value=1920,\n'
        '                    step=1,\n'
        '                    disabled=not custom_pixels_enabled\n'
        '                )\n'
        '            )\n\n'
        '        with pixel_col2:\n'
        '            custom_pixel_height = (\n'
        '                st.number_input(\n'
        '                    "Height (px)",\n'
        '                    min_value=1,\n'
        '                    max_value=50000,\n'
        '                    value=1080,\n'
        '                    step=1,\n'
        '                    disabled=not custom_pixels_enabled\n'
        '                )\n'
        '            )\n\n'
        '        st.caption(\n'
        '            "Enter any Width and Height. "\n'
        '            "When enabled, these pixels override "\n'
        '            "the selected size setting."\n'
        '        )\n\n'
    )

    if marker not in text:
        print("ERROR: Could not find sidebar Resize Behaviour section.")
        sys.exit(1)

    text = text.replace(marker, block + marker, 1)
    changes += 1

# ---------------------------------------------------------
# 4) OUTPUT SPECIFICATION OVERRIDE
# ---------------------------------------------------------
if "# CUSTOM PIXELS OVERRIDE - OUTPUT SPEC" not in text:
    old = (
        '        target_width, target_height = (\n'
        '            calculate_target_size(\n'
        '                first_original_size,\n'
        '                size_mode,\n'
        '                screen_preset,\n'
        '                paper_size,\n'
        '                orientation,\n'
        '                custom_width,\n'
        '                custom_height,\n'
        '                custom_unit,\n'
        '                dpi\n'
        '            )\n'
        '        )\n'
    )

    new = old + (
        '        # CUSTOM PIXELS OVERRIDE - OUTPUT SPEC\n'
        '        if custom_pixels_enabled:\n'
        '            target_width = int(\n'
        '                custom_pixel_width\n'
        '            )\n'
        '            target_height = int(\n'
        '                custom_pixel_height\n'
        '            )\n\n'
    )

    if old not in text:
        print("ERROR: Could not find Output Specification target-size block.")
        sys.exit(1)

    text = text.replace(old, new, 1)
    changes += 1

# ---------------------------------------------------------
# 5) ACTUAL CONVERSION OVERRIDE
# ---------------------------------------------------------
if "# CUSTOM PIXELS OVERRIDE - CONVERSION" not in text:
    old = (
        '                target_width, target_height = (\n'
        '                    calculate_target_size(\n'
        '                        original_image.size,\n'
        '                        size_mode,\n'
        '                        screen_preset,\n'
        '                        paper_size,\n'
        '                        orientation,\n'
        '                        custom_width,\n'
        '                        custom_height,\n'
        '                        custom_unit,\n'
        '                        dpi\n'
        '                    )\n'
        '                )\n'
    )

    new = old + (
        '                # CUSTOM PIXELS OVERRIDE - CONVERSION\n'
        '                if custom_pixels_enabled:\n'
        '                    target_width = int(\n'
        '                        custom_pixel_width\n'
        '                    )\n'
        '                    target_height = int(\n'
        '                        custom_pixel_height\n'
        '                    )\n'
    )

    if old not in text:
        print("ERROR: Could not find conversion target-size block.")
        sys.exit(1)

    text = text.replace(old, new, 1)
    changes += 1

# ---------------------------------------------------------
# 6) SESSION SIGNATURE
# ---------------------------------------------------------
if "    custom_pixels_enabled,\n" not in text:
    old = (
        '    custom_width,\n'
        '    custom_height,\n'
        '    custom_unit,\n'
        '    dpi,'
    )

    new = (
        '    custom_width,\n'
        '    custom_height,\n'
        '    custom_unit,\n'
        '    custom_pixels_enabled,\n'
        '    custom_pixel_width,\n'
        '    custom_pixel_height,\n'
        '    dpi,'
    )

    if old not in text:
        print("ERROR: Could not find current_signature block.")
        sys.exit(1)

    text = text.replace(old, new, 1)
    changes += 1

TARGET.write_text(text, encoding="utf-8")

print()
print("PATCH COMPLETE")
print(f"Changes applied: {changes}")
print(f"Updated file: {TARGET}")
print(f"Backup file:  {BACKUP}")
print()
print("Only requested changes were applied:")
print("1. Separate Custom Pixels Changer in sidebar")
print("2. Custom width/height override for output + conversion")
print("3. Dashboard background changed to light blue")
print("4. Sidebar changed to a light blue shade")
print()
print("Now run:")
print("streamlit run streamlit_app.py")
