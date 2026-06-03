#!/usr/bin/env python3
from fpdf import FPDF


SOURCE_FILE = "five_members_dialogue.md"
OUTPUT_FILE = "five_members_dialogue.pdf"


class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def clean(text):
    return text.replace("**", "").replace("`", "")


def main():
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)

    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, "5-Member Presentation Script for CTI RAG Chatbot", align="C")
    pdf.ln(4)

    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(2)
            continue

        if line.startswith("# "):
            pdf.set_font("Arial", "B", 15)
            pdf.multi_cell(0, 8, clean(line[2:]))
            pdf.ln(1)
        elif line.startswith("## "):
            pdf.set_font("Arial", "B", 13)
            pdf.multi_cell(0, 7, clean(line[3:]))
            pdf.ln(1)
        elif line.startswith("- "):
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 6, clean(line))
        else:
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 6, clean(line))

    pdf.output(OUTPUT_FILE)
    print(f"Created {OUTPUT_FILE}")


if __name__ == "__main__":
    main()