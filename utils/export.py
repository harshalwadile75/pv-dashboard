from fpdf import FPDF
import io

def export_pdf(lat, lon, energy_df, roi_df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Solar System Simulation Report", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Location: {lat}, {lon}", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, txt="Monthly Energy Output (kWh):", ln=True)
    for i, row in energy_df.iterrows():
        pdf.cell(200, 10, txt=f"{i}: {row['Energy (kWh)']:.2f}", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, txt="ROI Summary:", ln=True)
    for col in roi_df.columns:
        pdf.cell(200, 10, txt=f"{col}: {roi_df[col].values[0]}", ln=True)

    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output
