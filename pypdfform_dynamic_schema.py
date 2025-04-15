from fastapi import FastAPI, Form
from fastapi.responses import FileResponse
from PyPDFForm import PdfWrapper, FormWrapper
from pathlib import Path
import json
import inspect

app = FastAPI()

PDF_PATH = Path("data/sample.pdf")
SCHEMA_PATH = Path("data/form_schema.json")

# Generate and save schema if not present
if not SCHEMA_PATH.exists():
    wrapper = PdfWrapper(str(PDF_PATH))
    with open(SCHEMA_PATH, "w") as f:
        json.dump(wrapper.schema, f)

# Load schema
with open(SCHEMA_PATH) as f:
    schema = json.load(f).get("properties", {})

# Build dynamic form parameters
form_args = {}
field_name_map = {}
import re

for field_name, meta in schema.items():
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', field_name.lower()).lstrip('_')
    if not safe_name or safe_name[0].isdigit():
        safe_name = f"field_{safe_name}"
    field_name_map[safe_name] = field_name
    field_type = str
    if meta.get("type") == "boolean":
        field_type = bool
    elif meta.get("type") == "integer":
        field_type = int
    form_args[safe_name] = (field_type, Form(..., description=field_name))

# Create function signature dynamically
def create_fill_pdf_view():
    async def fill_pdf_func(**kwargs):
        output_path = Path("data/filled_sample.pdf")
        original_data = {field_name_map.get(k, k): v for k, v in kwargs.items()}
        filled_pdf = FormWrapper(str(PDF_PATH)).fill(original_data, flatten=False)
        with open(output_path, "wb") as f:
            f.write(filled_pdf.read())
        return FileResponse(output_path, filename=output_path.name, media_type="application/pdf")

    sig = inspect.signature(fill_pdf_func)
    new_params = [
        inspect.Parameter(
            name, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=default, annotation=annotation
        ) for name, (annotation, default) in form_args.items()
    ]
    fill_pdf_func.__signature__ = sig.replace(parameters=new_params)
    return fill_pdf_func

app.post("/fill-pdf", response_class=FileResponse)(create_fill_pdf_view())