import streamlit as st
import pandas as pd
import tempfile
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# -------------------------------------------------------------------
# SISENCO LABEL GENERATOR v1.3
# - Different column mappings for Theory and Paper
# - Paper IDs formatted (P - 0001 style)
# - Student ID moved to bottom of label
# - Royal blue themed interface
# -------------------------------------------------------------------

# --- Font setup ---
DEFAULT_FONT = "Helvetica"
BOLD_FONT = "Helvetica-Bold"

# --- Helper functions ---
def split_address(address, max_line_length=30):
    """Split address into 2 lines at last comma if too long."""
    if pd.isna(address) or str(address).strip() == "":
        return [""]
    address = str(address).strip()
    if len(address) <= max_line_length:
        return [address]
    last_comma = address.rfind(',')
    if last_comma == -1:
        return [address]
    first_line = address[:last_comma + 1].strip()
    second_line = address[last_comma + 1:].strip()
    return [first_line, second_line]


def create_labels_pdf_with_text(selected_rows, filename, product_type, col_map):
    """Generate PDF labels from selected rows."""
    ID_COL, NAME_COL, ADDRESS_COL, MOBILE1_COL, MOBILE2_COL = col_map

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    cols_per_page = 2
    rows_per_page = 8
    label_width = width / cols_per_page
    label_height = height / rows_per_page

    for idx, (_, row) in enumerate(selected_rows.iterrows()):
        if idx > 0 and idx % (cols_per_page * rows_per_page) == 0:
            c.showPage()

        pos_in_page = idx % (cols_per_page * rows_per_page)
        col = pos_in_page % cols_per_page
        row_pos = pos_in_page // cols_per_page

        x0 = col * label_width
        y0 = height - ((row_pos + 1) * label_height)

        # Draw border
        c.setStrokeColorRGB(0.2, 0.2, 0.2)
        c.setLineWidth(0.3)
        c.rect(x0 + 5, y0 + 5, label_width - 10, label_height - 10, stroke=1, fill=0)

        # Extract values
        name = str(row.iloc[NAME_COL]).strip()
        student_id = str(row.iloc[ID_COL]).strip()
        address = str(row.iloc[ADDRESS_COL]).strip()
        mobile1 = str(row.iloc[MOBILE1_COL]).strip()
        mobile2 = str(row.iloc[MOBILE2_COL]).strip()

        # Special formatting for paper class IDs
        if product_type.startswith("🔵"):
            if student_id.isdigit():
                student_id = f"P - {int(student_id):04d}"

        # --- NEW ORDER ---
        address_lines = split_address(address)
        label_lines = [name] + address_lines
        if mobile1:
            label_lines.append(mobile1)
        if mobile2:
            label_lines.append(mobile2)
        label_lines.append(student_id)  # Student ID moved to last

        # Clean up and limit lines
        label_lines = [line for line in label_lines if line.strip()]
        max_label_lines = 6
        lines_to_draw = label_lines[:max_label_lines]
        line_count = len(lines_to_draw)

        # Vertical alignment
        available_height = label_height - 12
        line_height = min(available_height / line_count, 12)
        total_text_height = line_height * line_count
        start_y = y0 + (label_height + total_text_height) / 2 - 1

        for i, line in enumerate(lines_to_draw):
            # Bold only the name (first line)
            font = BOLD_FONT if i == 0 else DEFAULT_FONT
            font_size = 9.5
            c.setFont(font, font_size)
            line_x = x0 + 10
            line_y = start_y - i * line_height
            c.drawString(line_x, line_y, line)

    c.save()


# -------------------------------------------------------------------
# STREAMLIT APP
# -------------------------------------------------------------------
st.set_page_config(page_title="Sisenco Label Generator", layout="centered")

# --- Custom Royal Blue Banner ---
st.markdown("""
    <style>
        .main {background-color: #f8f9fa;}
        .stApp header {background: none;}
        .blue-bar {
            background-color: #1e3a8a;
            padding: 0.8rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            text-align: center;
        }
        .blue-bar h1 {
            color: white;
            font-size: 1.7rem;
            margin: 0;
            font-weight: 700;
        }
        .stButton button {
            background-color: #1e3a8a;
            color: white;
            border-radius: 6px;
            font-weight: 600;
        }
        .stButton button:hover {
            background-color: #2448ad;
            color: #fff;
        }
    </style>
    <div class="blue-bar">
        <h1>📦 Sisenco Label Generator v1.3</h1>
    </div>
""", unsafe_allow_html=True)

st.markdown("**Choose the product type below to start printing address labels.**")

# --- Product type ---
product_type = st.radio(
    "Select product type:",
    ["🟢 Theory (Student Labels)", "🔵 Paper (Product Labels)"]
)

# Set column mapping dynamically
if product_type.startswith("🟢"):
    col_map = (0, 2, 3, 8, 9)
else:
    col_map = (0, 2, 3, 7, 8)

st.divider()

# --- File Upload ---
st.subheader(f"Upload {product_type.split()[1]} Excel or CSV File")

uploaded_file = st.file_uploader("Upload the file", type=["csv", "xlsx", "xls"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=None)
        else:
            df = pd.read_excel(uploaded_file, header=None)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

    st.success("✅ File uploaded successfully!")
    st.dataframe(df.head(10))

    st.subheader("Select IDs to Print Labels")
    selection_method = st.radio("Select method", ["Choose from list", "Upload ID list (txt)"])
    input_ids = []

    ID_COL = col_map[0]
    if selection_method == "Choose from list":
        all_ids = df.iloc[:, ID_COL].astype(str).tolist()
        input_ids = st.multiselect("Select IDs", options=all_ids)

    elif selection_method == "Upload ID list (txt)":
        txt_file = st.file_uploader("Upload TXT file", type=["txt"])
        if txt_file:
            try:
                input_ids = [line.decode("utf-8").strip() if isinstance(line, bytes)
                             else line.strip() for line in txt_file.readlines() if line.strip()]
            except Exception as e:
                st.error(f"Error reading text file: {e}")

    if input_ids:
        selected_rows = pd.concat([
            df[df.iloc[:, ID_COL].astype(str) == id_] for id_ in input_ids
        ])

        if selected_rows.empty:
            st.warning("No matching IDs found.")
        else:
            st.success(f"Found {len(selected_rows)} matching records.")
            st.write("Preview of Labels:")
            for _, row in selected_rows.iterrows():
                name = str(row.iloc[col_map[1]]).strip()
                student_id = str(row.iloc[col_map[0]]).strip()
                if product_type.startswith("🔵") and student_id.isdigit():
                    student_id = f"P - {int(student_id):04d}"
                address = str(row.iloc[col_map[2]]).strip()
                mobile1 = str(row.iloc[col_map[3]]).strip()
                mobile2 = str(row.iloc[col_map[4]]).strip()

                # NEW ORDER PREVIEW
                label_preview = [name] + split_address(address)
                if mobile1:
                    label_preview.append(mobile1)
                if mobile2:
                    label_preview.append(mobile2)
                label_preview.append(student_id)
                st.text("\n".join(label_preview))

            if st.button("🎨 Generate Labels PDF"):
                with st.spinner("Generating labels..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
                        pdf_filename = tmpfile.name
                    create_labels_pdf_with_text(selected_rows, pdf_filename, product_type, col_map)
                    with open(pdf_filename, "rb") as f:
                        st.success("✅ Labels generated! Download below:")
                        st.download_button("⬇️ Download PDF", f, file_name="sisenco_labels.pdf")
                    os.remove(pdf_filename)
    else:
        st.info("Please select or upload at least one ID.")
else:
    st.info("Upload your file to begin.")

st.divider()
st.caption("Sisenco Label Generator V.1.3 © 2025 — Developed by Sisenco Digital")
