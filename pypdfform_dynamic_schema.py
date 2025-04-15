from fastapi import FastAPI, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, create_model
from PyPDFForm import PdfWrapper, FormWrapper
from pathlib import Path
import json

app = FastAPI()

PDF_PATH = Path("data/sample.pdf")
SCHEMA_PATH = Path("data/form_schema.json")

# Step 1: Generate and save schema (if it doesn't exist)
if not SCHEMA_PATH.exists():
    wrapper = PdfWrapper(str(PDF_PATH))
    with open(SCHEMA_PATH, "w") as f:
        json.dump(wrapper.schema, f)

# Step 2: Load schema
with open(SCHEMA_PATH) as f:
    schema = json.load(f).get("properties", {})

# Step 3: Dynamically create Pydantic model
field_definitions = {}
for field_name, meta in schema.items():
    field_type = str
    if meta.get("type") == "boolean":
        field_type = bool
    elif meta.get("type") == "integer":
        field_type = int
    field_definitions[field_name] = (field_type, Form(...))

DynamicFormModel = create_model("DynamicFormModel", **field_definitions)

# Step 4: Define route to fill PDF
@app.post("/fill-pdf", response_class=FileResponse)
async def fill_pdf(form_data: DynamicFormModel):
    output_path = Path("data/filled_sample.pdf")
    filled_pdf = FormWrapper(str(PDF_PATH)).fill(form_data.dict(), flatten=False)
    with open(output_path, "wb") as f:
        f.write(filled_pdf.read())
    return FileResponse(output_path, filename=output_path.name, media_type="application/pdf")
