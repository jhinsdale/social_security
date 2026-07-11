# Social Security Statement Formatter

Formatter for Social Security Adminstration XML Statement File

By John K. Hinsdale of Princeton Junction, NJ.

Copyright (C) 2026 by John K. Hinsdale.

Render a Social Security Administration statement XML file into readable text,
Markdown, HTML, or PDF.

## Why Use The XML

The XML has more information than the SSA-generated PDF.

The PDF is the official human-facing statement, but it can summarize or compress
data for display. The XML is structured data. It can preserve details the PDF
does not show directly.

One clear example is the earnings record. The SSA PDF may compress older
earnings into multi-year ranges such as `1981-1990`, `1991-2000`, and
`2001-2005`. The XML keeps those earnings as individual yearly records. This
tool reads the XML and turns that extra detail into readable tables.

The formatter also makes structured benefit estimates, tax totals, and exact
creation timestamps easier to read, diff, archive, or print. It also adds
cumulative lifetime earnings columns, including cumulative Social
Security-taxed earnings and cumulative Medicare-taxed earnings, so you can see
running totals without doing that math by hand.

## What It Does

- Reads an SSA statement XML file.
- Optionally validates it against the bundled
  `Your_Social_Security_Statement_Data.xsd` file from SSA.
- Shows the XML earnings record year by year instead of using the compressed
  decade-style ranges shown in the SSA PDF.
- Adds cumulative lifetime Social Security-taxed and Medicare-taxed earnings
  columns.
- Outputs one of:
  - plain text
  - Markdown
  - HTML
  - PDF, if `wkhtmltopdf` is installed
- Refuses to overwrite output files unless `-F` / `--force` is used.
- Uses `-o -` to write to stdout.

## Usage

```sh
python3 format_ssa.py statement.xml
```

By default, output is written next to the XML file with a suffix for the selected
format:

```text
statement.txt
statement.md
statement.html
statement.pdf
```

Choose a format:

```sh
python3 format_ssa.py -f markdown statement.xml
python3 format_ssa.py -f html statement.xml
python3 format_ssa.py -f pdf statement.xml
```

Write to a specific file:

```sh
python3 format_ssa.py -f html -o statement.html statement.xml
```

Write to stdout:

```sh
python3 format_ssa.py -f text -o - statement.xml
```

Overwrite an existing file:

```sh
python3 format_ssa.py -F -f html -o statement.html statement.xml
```

Skip schema validation:

```sh
python3 format_ssa.py --no-validate statement.xml
```

## Demo Files

The `demo/` directory contains sanitized example data for John Q. Public. The
demo XML is derived from a real SSA statement XML file with the name and date of
birth changed and all dollar amounts divided by 3.

GitHub can render or preview these files directly:

- [Demo XML](demo/john_q_public.xml)
- [Plain text output](demo/john_q_public.txt)
- [Markdown output](demo/john_q_public.md)
- [HTML output](demo/john_q_public.html)
- [PDF output](demo/john_q_public.pdf)

## PDF Output

PDF output uses `wkhtmltopdf`.

Install it first if needed:

```sh
sudo apt install wkhtmltopdf
```

Then run:

```sh
python3 format_ssa.py -f pdf statement.xml
```

## XML Schema

The package includes `Your_Social_Security_Statement_Data.xsd`, the SSA XML
schema current as of July 2026. By default, the formatter uses that file to
validate statement XML when `xmllint` is installed.

Use another schema file:

```sh
python3 format_ssa.py --schema path/to/Your_Social_Security_Statement_Data.xsd statement.xml
```

Skip schema validation:

```sh
python3 format_ssa.py --no-validate statement.xml
```

## Getting Your SSA PDF And XML

You need access to a personal `my Social Security` account on SSA.gov.

SSA says the online Statement is available through an official `my Social
Security` account. SSA also says account access uses either Login.gov or ID.me.
As of the SSA page checked on 2026-07-11, Login.gov and ID.me are the only
sign-in options for Social Security online services.

Steps:

1. Go to <https://www.ssa.gov/myaccount/>.
2. Create or sign in to your personal `my Social Security` account.
3. Use either Login.gov or ID.me when prompted.
4. Open your Social Security Statement.
5. Download the SSA PDF, often named like `social-security-statement.orig.pdf`
   if you keep the original separate from generated files.
6. Download the statement XML file from the same statement area when SSA offers
   it.
7. Run this formatter on the XML file.

Keep both files:

- The SSA PDF is the official human-facing statement.
- The XML is the structured source used by this tool.
- This formatter output is derived from the XML and is not an SSA document.

## Notes

The formatter intentionally deduplicates retirement estimates that have the same
age and amount. For example, `EarlyRetirementEstimate` and
`Age62RetirementEstimate` can describe the same value, so the rendered table
shows that value once.

## Official SSA References

- SSA: Get Your Social Security Statement: <https://www.ssa.gov/myaccount/statement.html>
- SSA: my Social Security account: <https://www.ssa.gov/myaccount/>
- SSA: Create or access your account: <https://www.ssa.gov/myaccount/create.html>
