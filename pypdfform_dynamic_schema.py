from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, JSONResponse
from PyPDFForm import PdfWrapper, FormWrapper
from pathlib import Path
import re
import json
import inspect
import uuid
from typing import Optional, Literal

app = FastAPI()

PDF_PATH = Path("data/sample.pdf")
SCHEMA_PATH = Path("data/form_schema.json")
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

# hgenerate and save schema
if not SCHEMA_PATH.exists():
    wrapper = PdfWrapper(str(PDF_PATH))
    with open(SCHEMA_PATH, "w") as f:
        json.dump(wrapper.schema, f)

with open(SCHEMA_PATH) as f:
    schema = json.load(f).get("properties", {})

# make dynamic form
form_args = {}
field_name_map = {}

bool_field_names = set()

for field_name, meta in schema.items(): # TODO handle duplicate or conflicting names as well as clean names?
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', field_name.lower()).lstrip('_')
    if not safe_name or safe_name[0].isdigit():
        safe_name = f"field_{safe_name}"
    field_name_map[safe_name] = field_name
    is_boolean = meta.get("type") == "boolean"
    field_type = Literal["True", "False"] if is_boolean else str
    if is_boolean:
        bool_field_names.add(safe_name)
    elif meta.get("type") == "integer":
        field_type = int
    default_val = "False" if is_boolean else None
    form_args[safe_name] = (Optional[field_type], Form(default_val, description=field_name))

# build function so it thinks its static
def create_fill_pdf_view():
    async def fill_pdf_func(**kwargs):
        file_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"filled_{file_id}.pdf"
        original_data = {
            field_name_map.get(k, k): (v == "True" if k in bool_field_names else v)
            for k, v in kwargs.items()
        }
        filled_pdf = FormWrapper(str(PDF_PATH)).fill(original_data, flatten=False)
        with open(output_path, "wb") as f:
            f.write(filled_pdf.read())
        return JSONResponse(content={"file_url": f"/download-pdf/{file_id}"})

    sig = inspect.signature(fill_pdf_func)
    new_params = [
        inspect.Parameter(
            name, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=default, annotation=annotation
        ) for name, (annotation, default) in form_args.items()
    ]
    fill_pdf_func.__signature__ = sig.replace(parameters=new_params)
    return fill_pdf_func

@app.get("/download-pdf/{file_id}", response_class=FileResponse)
async def download_filled_pdf(file_id: str):
    file_path = OUTPUT_DIR / f"filled_{file_id}.pdf"
    return FileResponse(file_path, filename=f"filled_form_{file_id}.pdf", media_type="application/pdf")

app.post("/fill-pdf")(create_fill_pdf_view())