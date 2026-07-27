from fpdf import FPDF


def generate_pdf(report: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "ModelGate - MGS Audit Report", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Audit ID     : {report['audit_id']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Dataset ID   : {report['dataset_id']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Spec version : MGS {report['spec_version']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Status       : {report['audit_status']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Completed    : {report['completed_at'] or '-'}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # The authoritative result: overall_verdict, computed from each MGS
    # Requirement's own PASS/FAIL/NOT_EVALUATED verdict — not the health
    # score below, which is informative only (F4/C3, BACKLOG.md).
    if report["overall_verdict"]:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"Overall verdict: {report['overall_verdict']}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    if report["health_score"] is not None:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(
            0, 8,
            f"Health score (informative, not normative): {report['health_score']:.4f}",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 9)
        comp = report["health_score_components"]
        if comp:
            pdf.cell(
                0, 6,
                f"  I={comp['I']}  U={comp['U']}  D={comp['D']}  Q={comp['Q']}",
                new_x="LMARGIN", new_y="NEXT",
            )
        pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Per-requirement detail", new_x="LMARGIN", new_y="NEXT")

    for r in report["requirements"]:
        pdf.set_font("Helvetica", "B", 11)
        verdict = r.get("verdict") or "ERROR"
        pdf.cell(0, 8, f"{r['id']}  [{verdict}]", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        metrics = r.get("metrics") or {}
        for k, v in metrics.items():
            if isinstance(v, dict):
                continue
            pdf.cell(0, 5, f"  {k}: {v}", new_x="LMARGIN", new_y="NEXT")
        if r.get("error"):
            pdf.cell(0, 5, f"  Error: {r['error']}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    return bytes(pdf.output())
