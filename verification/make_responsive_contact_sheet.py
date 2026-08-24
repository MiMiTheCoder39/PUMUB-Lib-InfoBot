from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent / "admin_preview"
items = []
for page in ("borrows", "fines"):
    for size in ("1440x900", "768x1024", "390x844", "360x800"):
        path = root / f"{page}_{size}.png"
        image = Image.open(path).convert("RGB")
        image.thumbnail((420, 420))
        items.append((page.title() + " " + size, image.copy()))

font = ImageFont.load_default()
cell_w, cell_h = 440, 460
sheet = Image.new("RGB", (cell_w * 2, cell_h * 4), "#e9eef2")
draw = ImageDraw.Draw(sheet)
for index, (label, image) in enumerate(items):
    x = (index % 2) * cell_w + 10
    y = (index // 2) * cell_h + 10
    draw.text((x, y), label, fill="#14263d", font=font)
    sheet.paste(image, (x, y + 20))
sheet.save(root / "borrow_fine_responsive_contact_sheet.png")
print(root / "borrow_fine_responsive_contact_sheet.png")
