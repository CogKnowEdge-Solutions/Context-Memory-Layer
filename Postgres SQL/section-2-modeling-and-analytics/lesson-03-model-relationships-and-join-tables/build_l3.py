"""Build lesson 3 notebook and md."""
import json, sys
import blocks_l3
import sections_l3

LESSON_DIR = "/Users/ayushsingh/Work/Memory/Postgres SQL/section-2-modeling-and-analytics/lesson-03-model-relationships-and-join-tables"
NB_PATH = f"{LESSON_DIR}/lesson-03-model-relationships-and-join-tables.ipynb"
MD_PATH = f"{LESSON_DIR}/lesson-03-model-relationships-and-join-tables.md"
BLOCKS = blocks_l3.BLOCKS

def src(text):
    lines = text.split("\n")
    return [line+"\n" for line in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

def build_nb():
    cells = []
    for i,b in enumerate(BLOCKS):
        cells.append({"cell_type":"code","execution_count":None,"id":f"c{i}","metadata":{},"outputs":[],"source":src(b["code"])})
        cells.append({"cell_type":"markdown","id":f"m{i}","metadata":{},"source":src(b["explain"])})
    nb = {"cells":cells,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python"}},"nbformat":4,"nbformat_minor":5}
    with open(NB_PATH,"w") as fh:
        json.dump(nb,fh,indent=1); fh.write("\n")
    print("nb ok", len(cells))

def render(cell):
    out=[]
    for o in cell.get("outputs",[]):
        if o.get("output_type")=="stream": out.append("".join(o["text"]))
        elif o.get("output_type") in ("execute_result","display_data"):
            t=o.get("data",{}).get("text/plain"); 
            if t: out.append("".join(t))
        elif o.get("output_type")=="error": out.append("\n".join(o["traceback"]))
    return "".join(out).rstrip("\n")

def build_md(exec_path):
    nb=json.load(open(exec_path))
    code=[c for c in nb["cells"] if c["cell_type"]=="code"]
    parts=["## 10. Step-wise Development Instructions\n"]
    for i,b in enumerate(BLOCKS):
        if b["heading"]: parts.append(b["heading"]+"\n")
        parts.append("```python\n"+b["code"]+"\n```\n")
        parts.append(b["explain"]+"\n")
        if i==0: continue
        out=render(code[i])
        if out:
            parts.append("**Output:**\n"); parts.append("```\n"+out+"\n```\n")
    sec10="\n".join(parts)
    # section 5 from showcase? block 8 gives UNION/INTERSECT/EXCEPT outputs, 9 gives report
    step9=next(i for i,b in enumerate(BLOCKS) if "Step 9" in b["heading"])
    out9=render(code[step9])
    sec5="## 5. Output\n\nThe combined report shows each student and the courses they take:\n\n```\n"+out9+"\n```\n"
    md="\n".join([sections_l3.TITLE, sections_l3.SECTION1, sections_l3.SECTION2, sections_l3.SECTION3, sections_l3.SECTION4, sec5, sections_l3.SECTION6, sections_l3.SECTION7, sections_l3.SECTION8, sections_l3.SECTION9, sec10, sections_l3.SECTION11])
    with open(MD_PATH,"w") as fh: fh.write(md)
    print("md ok", len(md.splitlines()))

if __name__=="__main__":
    if sys.argv[1]=="nb": build_nb()
    elif sys.argv[1]=="md": build_md(sys.argv[2])
