#!/usr/bin/env python3
from fpdf import FPDF
import re


SOURCE_FILE = "software_expert_answers.md"
OUTPUT_FILE = "software_expert_answers.pdf"


class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def strip_inline_markup(text):
    text = text.replace("**", "")
    text = text.replace("`", "")
    return text


def add_wrapped(pdf, text, font="Arial", style="", size=11, leading=6, indent=0):
    pdf.set_font(font, style, size)
    if indent:
        pdf.set_x(indent)
    pdf.multi_cell(0, leading, text)


def main():
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)

    title = "CTI RAG Chatbot: Software Expert Question Answers"
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, title, align="C")
    pdf.ln(4)

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            pdf.ln(2)
            continue

        if line.startswith("# "):
            pdf.set_font("Arial", "B", 15)
            pdf.multi_cell(0, 8, strip_inline_markup(line[2:].strip()))
            pdf.ln(1)
        elif line.startswith("## "):
            pdf.set_font("Arial", "B", 13)
            pdf.multi_cell(0, 7, strip_inline_markup(line[3:].strip()))
            pdf.ln(1)
        elif line.startswith("**Question:**"):
            pdf.set_font("Arial", "B", 11)
            pdf.multi_cell(0, 6, strip_inline_markup(line))
        elif line.startswith("**Answer:**"):
            pdf.set_font("Arial", "B", 11)
            pdf.multi_cell(0, 6, strip_inline_markup(line))
        elif re.match(r"^\d+\.\s", line):
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 6, strip_inline_markup(line))
        else:
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 6, strip_inline_markup(line))

    pdf.output(OUTPUT_FILE)
    print(f"Created {OUTPUT_FILE}")


if __name__ == "__main__":
    main()