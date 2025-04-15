import streamlit as st
from PyPDFForm import PdfWrapper, FormWrapper
import tempfile
from pathlib import Path

st.set_page_config(page_title="Fill PDF Form", layout="centered")
st.title("Fill PDF Form")

uploaded_file = st.file_uploader("Upload a fillable PDF", type=["pdf"])

if uploaded_file:
    tmp_file = Path(tempfile.gettempdir()) / uploaded_file.name
    with open(tmp_file, "wb") as f:
        f.write(uploaded_file.read())

    wrapper = PdfWrapper(str(tmp_file))
    schema = wrapper.schema.get("properties", {})
    fields = list(schema.keys())

    if not fields:
        st.write("No fields found in the uploaded PDF.")
    else:
        input_values = {}
        for field in fields:
            field_data = schema.get(field, {})
            field_kind = field_data.get("type", "string")
            if field_kind == "boolean":
                input_values[field] = st.checkbox(field)
            else:
                input_values[field] = st.text_input(field)

        if st.button("Generate filled PDF"):
            output_file = tmp_file.with_stem(f"filled_{tmp_file.stem}")
            form = FormWrapper(str(tmp_file))
            filled = form.fill(input_values, flatten=False)
            with open(output_file, "wb") as filled_out:
                filled_out.write(filled.read())

            with open(output_file, "rb") as filled_out:
                st.download_button(
                    label="Download result",
                    data=filled_out,
                    file_name=output_file.name,
                    mime="application/pdf"
                )
