#!/usr/bin/env python3
"""Formatter for Social Security Adminstration XML Statement File.

By John K. Hinsdale of Princeton Junction, NJ.
Copyright (C) 2026 by John K. Hinsdale.
"""

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from xml.etree import ElementTree


DEFAULT_XSD = "Your_Social_Security_Statement_Data.xsd"


def local_name(tag):
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def child_text(node, name, default=""):
    child = node.find("./{*}" + name)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def parse_integer(text):
    text = (text or "").strip()
    if text == "":
        return None
    return int(text)


def money(value):
    if value is None:
        return ""
    return "${:,}".format(value)


def format_timestamp(value):
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError:
        return value

    zone_names = {
        -4 * 60 * 60: "EDT",
        -5 * 60 * 60: "EST",
    }
    zone = ""
    if stamp.utcoffset() is not None:
        zone = zone_names.get(int(stamp.utcoffset().total_seconds()), stamp.strftime("%z"))
    return "{} {}".format(stamp.strftime("%Y-%m-%d %H:%M:%S"), zone).rstrip()


def format_date(value):
    try:
        stamp = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return value
    return "{} {}, {}".format(stamp.strftime("%B"), stamp.day, stamp.year)


def parse_age(node):
    years = parse_integer(child_text(node, "Years"))
    months = parse_integer(child_text(node, "Months"))
    return years, months


def format_age(age):
    years, months = age
    if years is None:
        return ""
    if months:
        return "{}y,{}m".format(years, months)
    return "{}y".format(years)


def label(name):
    age_retirement = re.fullmatch(r"Age(\d+)RetirementEstimate", name)
    if age_retirement:
        return "Retire at {}".format(age_retirement.group(1))

    replacements = {
        "DelayedRetirementEstimate": "Delayed retire",
        "DisabilityEstimate": "Disability",
        "EarlyRetirementEstimate": "Early retire",
        "FullRetirementEstimate": "Full retire",
        "FicaTaxTotalEmployer": "FICA employer",
        "FicaTaxTotalIndividual": "FICA individual",
        "MedicareTaxTotalEmployer": "Medicare employer",
        "MedicareTaxTotalIndividual": "Medicare individual",
        "OneTimeDeathBenefit": "Death benefit",
        "SurvivorsEstimateChild": "Survivor child",
        "SurvivorsEstimateFamily": "Survivor family max",
        "SurvivorsEstimateRetired": "Survivor spouse",
        "SurvivorsEstimateSpouseChild": "Survivor spouse child",
    }
    if name in replacements:
        return replacements[name]

    words = []
    word = ""
    for char in name:
        if word and char.isupper() and not word[-1].isupper():
            words.append(word)
            word = char
        else:
            word += char
    if word:
        words.append(word)
    return " ".join(words)


def parse_statement(xmlfn):
    tree = ElementTree.parse(xmlfn)
    root = tree.getroot()
    if local_name(root.tag) != "OnlineSocialSecurityStatementData":
        raise ValueError("Unexpected root element: {}".format(local_name(root.tag)))

    data = {
        "file_creation_date": "",
        "user": {},
        "retirement_benefits": [],
        "other_benefits": [],
        "earnings": [],
        "tax_totals": [],
    }

    for section in root:
        tag = local_name(section.tag)
        if tag == "FileCreationDate":
            data["file_creation_date"] = (section.text or "").strip()
        elif tag == "UserInformation":
            data["user"] = {
                local_name(child.tag): (child.text or "").strip()
                for child in list(section)
            }
        elif tag == "EstimatedBenefits":
            for child in list(section):
                benefit_name = local_name(child.tag)
                retirement_age = child.find("./{*}RetirementAge")
                if retirement_age is not None:
                    data["retirement_benefits"].append(
                        {
                            "name": benefit_name,
                            "age": parse_age(retirement_age),
                            "estimate": parse_integer(child_text(child, "Estimate")),
                        }
                    )
                else:
                    data["other_benefits"].append(
                        {
                            "name": benefit_name,
                            "estimate": parse_integer(child.text),
                        }
                    )
        elif tag == "EarningsRecord":
            for child in list(section):
                child_tag = local_name(child.tag)
                if child_tag == "Earnings":
                    data["earnings"].append(
                        {
                            "start_year": int(child.attrib["startYear"]),
                            "end_year": int(child.attrib["endYear"]),
                            "fica": parse_integer(child_text(child, "FicaEarnings")),
                            "medicare": parse_integer(child_text(child, "MedicareEarnings")),
                        }
                    )
                else:
                    data["tax_totals"].append(
                        {
                            "name": child_tag,
                            "amount": parse_integer(child.text),
                        }
                    )
        else:
            raise ValueError("Unknown top-level element: {}".format(tag))

    return data


def table_text(headers, rows, alignments):
    header_lines = [header.split() for header in headers]
    header_height = max(len(lines) for lines in header_lines)
    widths = [max(len(word) for word in lines) for lines in header_lines]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def format_cell(index, cell):
        if alignments[index] == "right":
            return cell.rjust(widths[index])
        return cell.ljust(widths[index])

    def format_row(row):
        cells = []
        for index, cell in enumerate(row):
            cells.append(format_cell(index, cell))
        return "  ".join(cells)

    lines = []
    for line_index in range(header_height):
        header_row = []
        for index, lines_for_header in enumerate(header_lines):
            offset = header_height - len(lines_for_header)
            word = ""
            if line_index >= offset:
                word = lines_for_header[line_index - offset]
            header_row.append(format_cell(index, word))
        lines.append("  ".join(header_row))
    lines.append(format_row(tuple("-" * width for width in widths)))
    for row in rows:
        lines.append(format_row(row))
    return lines


def escape_markdown_cell(cell):
    return cell.replace("|", "\\|")


def markdown_header(header):
    return "<br>".join(escape_markdown_cell(word) for word in header.split())


def table_markdown(headers, rows, alignments):
    divider = []
    for alignment in alignments:
        if alignment == "right":
            divider.append("---:")
        else:
            divider.append("---")

    lines = [
        "| {} |".format(" | ".join(markdown_header(header) for header in headers)),
        "| {} |".format(" | ".join(divider)),
    ]
    for row in rows:
        lines.append("| {} |".format(" | ".join(escape_markdown_cell(cell) for cell in row)))
    return lines


def table_html(headers, rows, alignments):
    lines = ["<table>", "  <thead>", "    <tr>"]
    for index, header in enumerate(headers):
        class_attr = ' class="num"' if alignments[index] == "right" else ""
        stacked_header = "<br>".join(html.escape(word) for word in header.split())
        lines.append("      <th{}>{}</th>".format(class_attr, stacked_header))
    lines.extend(["    </tr>", "  </thead>", "  <tbody>"])
    for row in rows:
        lines.append("    <tr>")
        for index, cell in enumerate(row):
            class_attr = ' class="num"' if alignments[index] == "right" else ""
            lines.append("      <td{}>{}</td>".format(class_attr, html.escape(cell)))
        lines.append("    </tr>")
    lines.extend(["  </tbody>", "</table>"])
    return lines


def build_view(data):
    deduped_retirement_benefits = {}
    for index, item in enumerate(data["retirement_benefits"]):
        key = (item["age"], item["estimate"])
        current = deduped_retirement_benefits.get(key)
        if current is None or current[1]["name"].startswith("Age"):
            deduped_retirement_benefits[key] = (index, item)

    retirement_benefits = sorted(
        deduped_retirement_benefits.values(),
        key=lambda row: (
            row[1]["age"][0] if row[1]["age"][0] is not None else -1,
            row[1]["age"][1] if row[1]["age"][1] is not None else 0,
            row[0],
        ),
    )
    retirement_rows = [
        (label(item["name"]), format_age(item["age"]), money(item["estimate"]))
        for index, item in retirement_benefits
    ]
    other_rows = [
        (label(item["name"]), money(item["estimate"]))
        for item in data["other_benefits"]
    ]
    earnings_with_totals = []
    cumulative_fica = 0
    cumulative_medicare = 0
    for item in sorted(data["earnings"], key=lambda row: (row["end_year"], row["start_year"])):
        cumulative_fica += item["fica"] or 0
        cumulative_medicare += item["medicare"] or 0
        earnings_with_totals.append((item, cumulative_fica, cumulative_medicare))

    earnings_rows = []
    for item, cumulative_fica, cumulative_medicare in reversed(earnings_with_totals):
        year = str(item["start_year"])
        if item["start_year"] != item["end_year"]:
            year = "{}-{}".format(item["start_year"], item["end_year"])
        earnings_rows.append(
            (
                year,
                money(item["fica"]),
                money(item["medicare"]),
                money(cumulative_fica),
                money(cumulative_medicare),
            )
        )
    tax_rows = [(label(item["name"]), money(item["amount"])) for item in data["tax_totals"]]

    return {
        "title": "Social Security Statement",
        "summary": [
            ("Created", format_timestamp(data["file_creation_date"])),
            ("Name", data["user"].get("Name", "")),
            ("Date of Birth", format_date(data["user"].get("DateOfBirth", ""))),
        ],
        "sections": [
            {
                "title": "Estimated Monthly Benefits",
                "headers": ("Benefit", "Age", "Amount"),
                "alignments": ("left", "right", "right"),
                "rows": retirement_rows,
            },
            {
                "title": "Other Benefits",
                "headers": ("Benefit", "Amount"),
                "alignments": ("left", "right"),
                "rows": other_rows,
            },
            {
                "title": "Earnings Record",
                "headers": (
                    "Year",
                    "Social Security Earnings",
                    "Medicare Earnings",
                    "Cumulative Social Security Earnings",
                    "Cumulative Medicare Earnings",
                ),
                "alignments": ("right", "right", "right", "right", "right"),
                "rows": earnings_rows,
            },
            {
                "title": "Tax Totals",
                "headers": ("Tax", "Amount"),
                "alignments": ("left", "right"),
                "rows": tax_rows,
            },
        ],
    }


def render_text(view, schema_status=None):
    lines = [
        view["title"],
        "=" * len(view["title"]),
    ]
    if schema_status:
        lines.extend(["Schema: {}".format(schema_status), ""])
    lines.extend("{}: {}".format(name, value) for name, value in view["summary"])
    lines.append("")

    for index, section in enumerate(view["sections"]):
        if index:
            lines.append("")
        lines.extend([section["title"], "-" * len(section["title"])])
        lines.extend(table_text(section["headers"], section["rows"], section["alignments"]))
    return "\n".join(lines)


def render_markdown(view, schema_status=None):
    lines = ["# {}".format(view["title"]), ""]
    if schema_status:
        lines.extend(["Schema: {}".format(schema_status), ""])
    lines.extend("- {}: {}".format(name, value) for name, value in view["summary"])

    for section in view["sections"]:
        lines.extend(["", "## {}".format(section["title"]), ""])
        lines.extend(table_markdown(section["headers"], section["rows"], section["alignments"]))
    return "\n".join(lines)


def render_html(view, schema_status=None):
    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        "  <title>{}</title>".format(html.escape(view["title"])),
        "  <style>",
        "    body { font-family: sans-serif; line-height: 1.4; margin: 2rem; }",
        "    table { border-collapse: collapse; margin: 0 0 1.5rem; }",
        "    th, td { border: 1px solid #ccc; padding: 0.25rem 0.5rem; text-align: left; }",
        "    th.num, td.num { text-align: right; }",
        "    th { background: #dbeafe; vertical-align: bottom; }",
        "    table.summary td { border: 0; padding: 0.1rem 0.75rem 0.1rem 0; }",
        "    .page-break-before { break-before: page; page-break-before: always; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>{}</h1>".format(html.escape(view["title"])),
    ]
    if schema_status:
        lines.append("  <p><strong>Schema:</strong> {}</p>".format(html.escape(schema_status)))
    lines.append('  <table class="summary">')
    lines.append("    <tbody>")
    for name, value in view["summary"]:
        lines.append("      <tr>")
        lines.append("        <td><strong>{}:</strong></td>".format(html.escape(name)))
        lines.append("        <td>{}</td>".format(html.escape(value)))
        lines.append("      </tr>")
    lines.append("    </tbody>")
    lines.append("  </table>")

    for section in view["sections"]:
        class_attr = ' class="page-break-before"' if section["title"] == "Earnings Record" else ""
        lines.append("  <h2{}>{}</h2>".format(class_attr, html.escape(section["title"])))
        lines.extend("  " + line for line in table_html(section["headers"], section["rows"], section["alignments"]))

    lines.extend(["</body>", "</html>"])
    return "\n".join(lines)


def render_statement(data, output_format="text", schema_status=None):
    view = build_view(data)
    renderers = {
        "text": render_text,
        "markdown": render_markdown,
        "html": render_html,
    }
    return renderers[output_format](view, schema_status=schema_status)


OUTPUT_EXTENSIONS = {
    "text": "txt",
    "markdown": "md",
    "html": "html",
    "pdf": "pdf",
}


def default_output_filename(xml_filename, output_format):
    base, _extension = os.path.splitext(xml_filename)
    return "{}.{}".format(base, OUTPUT_EXTENSIONS[output_format])


def ensure_output_file_available(output_filename, force=False):
    if not force and output_filename != "-" and os.path.exists(output_filename):
        raise ValueError(
            "Refusing to overwrite existing file: {} (use -F/--force to overwrite)".format(
                output_filename
            )
        )


def write_text_output(content, output_filename):
    if output_filename == "-":
        print(content)
    else:
        with open(output_filename, "w", encoding="utf-8") as output_file:
            output_file.write(content)
            output_file.write("\n")


def write_pdf_output(html_content, output_filename):
    wkhtmltopdf = shutil.which("wkhtmltopdf")
    if not wkhtmltopdf:
        raise ValueError("PDF format requires wkhtmltopdf in PATH")

    temp_filename = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            suffix=".html",
        ) as temp_file:
            temp_file.write(html_content)
            temp_file.write("\n")
            temp_filename = temp_file.name

        if output_filename == "-":
            result = subprocess.run(
                [wkhtmltopdf, temp_filename, "-"],
                stdout=sys.stdout.buffer,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
        else:
            result = subprocess.run(
                [wkhtmltopdf, temp_filename, output_filename],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if result.returncode != 0:
                raise ValueError(result.stdout.strip())
    finally:
        if temp_filename:
            os.unlink(temp_filename)


def validate_with_xmllint(xmlfn, xsdfn):
    if not xsdfn:
        return None
    if not os.path.isfile(xsdfn):
        raise ValueError("Cannot find schema: {}".format(xsdfn))
    if not shutil.which("xmllint"):
        return "not checked: xmllint not found"

    result = subprocess.run(
        ["xmllint", "--noout", "--schema", xsdfn, xmlfn],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(result.stdout.strip())
    return "valid"


def main(argv):
    parser = argparse.ArgumentParser(description="Render SSA statement XML readably.")
    output_formats = ["text", "markdown", "html"]
    if shutil.which("wkhtmltopdf"):
        output_formats.append("pdf")

    parser.add_argument("xmlfile")
    parser.add_argument(
        "-s",
        "--schema",
        default=DEFAULT_XSD if os.path.isfile(DEFAULT_XSD) else None,
        help="XSD file to validate with xmllint before rendering",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip XSD validation",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=output_formats,
        default="text",
        help="Output format. Default: text",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output filename. Use '-' for stdout. Default: XML filename with format suffix.",
    )
    parser.add_argument(
        "-F",
        "--force",
        action="store_true",
        help="Overwrite output file if it already exists.",
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(args.xmlfile):
        raise ValueError("Cannot find XML file: {}".format(args.xmlfile))

    schema_status = None
    if not args.no_validate:
        validate_with_xmllint(args.xmlfile, args.schema)

    output_filename = args.output or default_output_filename(args.xmlfile, args.format)
    ensure_output_file_available(output_filename, force=args.force)

    data = parse_statement(args.xmlfile)
    if args.format == "pdf":
        write_pdf_output(
            render_statement(data, output_format="html", schema_status=schema_status),
            output_filename,
        )
    else:
        write_text_output(
            render_statement(data, output_format=args.format, schema_status=schema_status),
            output_filename,
        )
    return True


if __name__ == "__main__":
    try:
        success = main(sys.argv[1:])
    except Exception as exc:
        print("error: {}".format(exc), file=sys.stderr)
        sys.exit(1)
    sys.exit(0 if success else 1)
