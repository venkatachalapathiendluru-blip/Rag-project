"""Create a fictional two-page PDF for acceptance tests. It needs no libraries."""

import sys

PAGES = [
    [
        "Northwind Field Handbook",
        "Remote stations must file a safety report every 14 days.",
        "The station lead for Harbor Point is Tamsin Okoro.",
        "Fuel deliveries to Harbor Point arrive on the first Monday of each month.",
    ],
    [
        "Equipment Rules",
        "Survey drones must be recharged after 45 minutes of flight.",
        "The spare parts depot is located in Cedar Falls.",
        "Damaged equipment must be logged within 24 hours.",
    ],
]


def build(path):
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", None, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []

    for lines in PAGES:
        text = "BT /F1 12 Tf 72 720 Td 18 TL " + " ".join(f"({line}) Tj T*" for line in lines) + " ET"
        objects.append(f"<< /Length {len(text)} >>\nstream\n{text}\nendstream")
        content = len(objects)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content} 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
        )
        kids.append(f"{len(objects)} 0 R")

    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    output = b"%PDF-1.4\n"
    offsets = []

    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n{body}\nendobj\n".encode()

    start = len(output)
    output += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    output += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    output += f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()

    with open(path, "wb") as file:
        file.write(output)


if __name__ == "__main__":
    build(sys.argv[1])
