"""Read-only source/doc/privacy audit plus local dependency inventory; redacted findings."""
import argparse
import importlib.metadata
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
EXCLUDED={"__pycache__",".venv",".tools-venv",".tools-zig",".checks",".release",".native-build",".pio",".git",
          ".pytest_cache",".ruff_cache",".mypy_cache","node_modules"}


def source_files(root=ROOT):
    files=[]
    for base in (root/"jetson/app",root/"jetson/tools",root/"jetson/tests",root/"ai",root/"esp32",root/"scripts",root/"docs"):
        for path in base.rglob("*"):
            relative=path.relative_to(root)
            if not path.is_file() or EXCLUDED.intersection(relative.parts): continue
            if relative.parts[:2] in (("ai","datasets"),("ai","models"),("ai","reports")) or "runs" in relative.parts or "local" in relative.parts: continue
            if path.suffix.lower() not in (".py",".h",".cpp",".ini",".ps1",".sh",".md",".json",".csv",".toml",".txt"): continue
            if not path.resolve().is_relative_to(root.resolve()): continue
            files.append(path)
    files.extend(p for p in root.iterdir() if p.is_file() and (p.name in ("README.md",".gitignore",".env.example","pytest.ini","ruff.toml") or p.name.startswith("requirements") and p.suffix==".txt"))
    files.extend(p for p in (root/"jetson").glob("requirements*.txt"))
    return sorted(set(files))


def anchors(text):
    result=set(); counts={}; fenced=False
    for line in text.splitlines():
        if line.startswith("```"): fenced=not fenced; continue
        if fenced: continue
        match=re.match(r"^#{1,6}\s+(.+)",line)
        if match:
            title=unicodedata.normalize("NFC",match.group(1).strip().lower())
            title=re.sub(r"[^\w\- ]","",title).replace(" ","-")
            count=counts.get(title,0); counts[title]=count+1
            result.add(title+(f"-{count}" if count else ""))
    return result


def docs_audit(files):
    failures=[]; mermaid=[]; claims=[]
    for path in files:
        if path.suffix!=".md": continue
        text=path.read_text(encoding="utf-8")
        relative=path.relative_to(ROOT).as_posix()
        for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)",text):
            link=match.group(1).split(' "',1)[0]
            if re.match(r"(?:https?://|mailto:)",link): continue
            name,_,anchor=link.partition("#")
            target=(path.parent/name).resolve() if name else path
            if not target.exists(): failures.append({"file":relative,"type":"MISSING_LINK","target":name})
            elif anchor and target.suffix==".md" and anchor not in anchors(target.read_text(encoding="utf-8")):
                failures.append({"file":relative,"type":"MISSING_ANCHOR","target":link})
        # Filename references in prose; wildcards/placeholders/code examples are not links.
        for name in set(re.findall(r"`([A-Z][A-Z0-9_]*\.md)`",text)):
            if not (path.parent/name).exists() and not (ROOT/"docs"/name).exists() and not (ROOT/name).exists():
                failures.append({"file":relative,"type":"MISSING_DOC_REFERENCE","target":name})
        for block in re.findall(r"```mermaid\s*\n(.*?)```",text,re.S):
            lines=[line.strip() for line in block.splitlines() if line.strip()]
            valid=bool(lines) and (lines[0].startswith("flowchart ") or lines[0]=="sequenceDiagram")
            if lines and lines[0].startswith("flowchart "):
                valid=valid and block.count("[")==block.count("]") and block.count("{")==block.count("}")
            if lines and lines[0]=="sequenceDiagram":
                opens=sum(line.startswith(("alt ","opt ","loop ","par ","critical ","rect ","break ")) for line in lines)
                valid=valid and opens==sum(line=="end" for line in lines)
            mermaid.append({"file":relative,"structural_status":"PASS" if valid else "FAIL","rendered":False})
            if not valid: failures.append({"file":relative,"type":"MERMAID_STRUCTURE"})
        if path.name in ("THESIS_DRAFT_VI.md","FINAL_PRESENTATION_STRUCTURE_VI.md","PRESENTATION_TALK_TRACK_VI.md"):
            for n,line in enumerate(text.splitlines(),1):
                if re.search(r"accurate|real.time|validated|successful|reliable|FPS|accuracy|automatic|chính xác|thành công",line,re.I):
                    claims.append({"file":relative,"line":n,"status":"REQUIRES_CONTEXT_REVIEW_NOT_AUTOMATIC_PERFORMANCE_EVIDENCE"})
    return {"failures":failures,"mermaid":mermaid,"claim_context_locations":claims,
            "scope":"internal Markdown links, named doc references, GitHub-style headings; structural Mermaid only"}


def secret_scan(files):
    findings=[]
    patterns={"PRIVATE_KEY":r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
              "PROVIDER_TOKEN":r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{32,})\b",
              "LITERAL_CREDENTIAL":r"(?i)\b(?:password|api_key|wifi_password|wifi_ssid|access_token|auth_token)\s*[:=]\s*[\"'][^\"'\r\n]{8,}[\"']",
              "URL_CREDENTIAL":r"https?://[^\s\"'<>/:]+:[^\s\"'<>/@]+@",
              "PRIVATE_LAN_URL":r"https?://(?:192\.168\.[0-9.]+|10\.[0-9.]+|172\.(?:1[6-9]|2[0-9]|3[01])\.[0-9.]+)",
              "PERSONAL_HOME_PATH":r"[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_.-]+[\\/]"}
    for path in files:
        if path.stat().st_size>2_000_000: continue
        try: text=path.read_text(encoding="utf-8")
        except UnicodeError: continue
        for kind,pattern in patterns.items():
            for match in re.finditer(pattern,text):
                findings.append({"file":path.relative_to(ROOT).as_posix(),"type":kind,"line":text[:match.start()].count("\n")+1,
                                 "remediation":"REVIEW_REQUIRED; value redacted"})
    return {"status":"NO_LIKELY_SECRETS_FOUND" if not findings else "REVIEW_REQUIRED","findings":findings,
            "scope":"allowlisted source/docs/config; private data/venvs/builds excluded; not a proof of no secrets"}


def dependency_inventory():
    packages=[]
    for dist in sorted(importlib.metadata.distributions(),key=lambda d:d.metadata["Name"].lower()):
        license_value=dist.metadata.get("License-Expression") or dist.metadata.get("License")
        packages.append({"name":dist.metadata["Name"],"version":dist.version,
            "license_metadata":license_value.splitlines()[0][:160] if license_value else "NOT_DISCOVERABLE_IN_LOCAL_METADATA"})
    home=Path.home()/".platformio"; tools=[]
    # A cache can contain unrelated platform versions. Match the active pinned version.
    for path in sorted((home/"platforms").glob("espressif32*/platform.json")):
        data=json.loads(path.read_text(encoding="utf-8"))
        version=str(data.get("version",""))
        if version and all(part.isdigit() for part in version.split(".")) and tuple(map(int,version.split(".")))==(55,3,311):
            tools.append({"name":data.get("name"),"version":version,"configured_version":"55.3.311",
                          "license_metadata":data.get("license","NOT_DISCOVERABLE_IN_LOCAL_METADATA")})
    for name in ("packages/framework-arduinoespressif32/package.json",
                 "packages/framework-arduinoespressif32-libs/package.json","packages/toolchain-xtensa-esp-elf/package.json",
                 "packages/tool-esptoolpy/package.json"):
        path=home/name
        if path.is_file():
            data=json.loads(path.read_text(encoding="utf-8"))
            tools.append({"name":data.get("name",name),"version":data.get("version"),
                          "license_metadata":data.get("license","NOT_DISCOVERABLE_IN_LOCAL_METADATA")})
    return {"python":packages,"build_packages":tools,"license_scope":"metadata only; compatibility/compliance not certified"}


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--write",action="store_true")
    p.add_argument("--write-sbom",action="store_true"); a=p.parse_args()
    files=source_files(); docs=docs_audit(files); secrets=secret_scan(files)
    report={"schema_version":1,"files_checked":len(files),"documentation":docs,"security":secrets,
        "dependencies":dependency_inventory(),"generated_areas_present":[name for name in (".venv",".tools-venv",".tools-zig",".pio",".native-build",".checks",".release","jetson/data","esp32/.pio") if (ROOT/name).exists()],
        "source_control_status":"NO_GIT_REPOSITORY" if not (ROOT/".git").exists() else "REVIEW_GIT_STATUS_SEPARATELY"}
    if a.write:
        folder=ROOT/".release"; folder.mkdir(exist_ok=True)
        (folder/"audit.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    if a.write_sbom:
        inventory=report["dependencies"]
        lines=["# Software bill of materials — locally observed inventory","",
            "Generated from installed metadata; not legal compatibility, vulnerability or Jetson support certification. Core requirements remain separate from developer/test/quality tools.","",
            "| Python distribution | Installed version | Discoverable license metadata |","| --- | --- | --- |"]
        for row in inventory["python"]:
            license_value=str(row["license_metadata"]).replace("|","/").replace("\n"," ")
            lines.append(f"| {row['name']} | {row['version']} | {license_value} |")
        lines.extend(["","## Build packages (local PlatformIO manifests)","",
                      "| Package | Version metadata | License metadata |","| --- | --- | --- |"])
        for row in inventory["build_packages"]:
            lines.append(f"| {row['name']} | {row['version']} | {str(row['license_metadata']).replace('|','/')} |")
        lines.extend(["","Important tools: observed Python3.14.3, PlatformIO Core6.2.0, Zig0.16.0; pinned espressif32 platform55.3.311 and Arduino3.3.11 compile environment.",
            "Quality tooling is pinned separately in requirements-quality.txt (Ruff/mypy), never a production dependency. Missing/ambiguous license fields require review of actual distribution license files; no license was guessed.",
            "No model/dataset is bundled. See THIRD_PARTY_ATTRIBUTION.md and REPRODUCIBLE_ENVIRONMENT.md.",""])
        (ROOT/"docs/SOFTWARE_BOM.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"files_checked":len(files),"documentation_failures":docs["failures"],"secret_scan":secrets,
                      "mermaid_structural_blocks":len(docs["mermaid"]),"browser_render_performed":False},indent=2))
    return bool(docs["failures"] or secrets["findings"])


if __name__=="__main__": sys.exit(main())
