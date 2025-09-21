import argparse, json, pathlib, re
def extract_semantics(text: str) -> dict:
    contracts=re.findall(r"\\bcontract\\s+([A-Za-z_]\\w*)", text)
    funcs=re.findall(r"\\bfunction\\s+([A-Za-z_]\\w*)", text)
    return {"contracts":contracts,"functions":funcs}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Path to .sol")
    ap.add_argument("--out", required=True, help="Where to write JSON")
    args=ap.parse_args()
    p=pathlib.Path(args.src); text=p.read_text(encoding="utf-8", errors="ignore"); sem=extract_semantics(text)
    data={"path":str(p),"text":text,"semantics":sem}
    pathlib.Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2))
if __name__ == "__main__": main()
