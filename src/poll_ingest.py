"""Validated, neutral ingestion of explicitly configured public poll feeds."""
from __future__ import annotations
import csv, hashlib, io, json, re
from dataclasses import dataclass
from datetime import date
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup

ALIASES={
 "PP":"PP","PARTIDO POPULAR":"PP","PSOE":"PSOE","PARTIDO SOCIALISTA OBRERO ESPAÑOL":"PSOE",
 "SUMAR":"SUMAR","PODEMOS":"PODEMOS","VOX":"VOX","ERC":"ERC","JUNTS":"JUNTS",
 "EH BILDU":"EH BILDU","BILDU":"EH BILDU","PNV":"PNV","BNG":"BNG","CC":"CC","UPN":"UPN","PACMA":"PACMA"
}
@dataclass(frozen=True)
class Poll:
    poll_id:str
    publication_date:str
    pollster:str
    source_id:str
    source_url:str
    parties:dict[str,float]
    fieldwork_start:str|None=None
    fieldwork_end:str|None=None
    sample_size:int|None=None
    methodology:str|None=None

def _party(x): return ALIASES.get(re.sub(r"\s+"," ",str(x).strip().upper()),str(x).strip().upper())
def _date(x):
    s=str(x).strip()
    try:
        if "T" in s: return date.fromisoformat(s[:10]).isoformat()
        try: return parsedate_to_datetime(s).date().isoformat()
        except Exception: return date.fromisoformat(s).isoformat()
    except Exception as e: raise ValueError(f"invalid publication_date: {s}") from e

def _poll(obj, source):
    required=("id","publication_date","pollster","parties")
    missing=[k for k in required if not obj.get(k)]
    if missing: raise ValueError("missing fields: "+",".join(missing))
    parties={}
    for k,v in dict(obj["parties"]).items():
        try: val=float(str(v).replace("%","").replace(",","."))
        except Exception as e: raise ValueError(f"invalid percentage for {k}") from e
        if not 0<=val<=100: raise ValueError(f"percentage out of range for {k}")
        parties[_party(k)]=val
    if not parties: raise ValueError("empty parties")
    n=obj.get("sample_size")
    if n is not None:
        n=int(n)
        if n<=0: raise ValueError("sample_size must be positive")
    return Poll(str(obj["id"]),_date(obj["publication_date"]),str(obj["pollster"]).strip(),
                source["id"],source["url"],parties,
                obj.get("fieldwork_start"),obj.get("fieldwork_end"),n,obj.get("methodology"))

def parse_json(body,source):
    data=json.loads(body.decode("utf-8"))
    items=data.get("polls") if isinstance(data,dict) else data
    if not isinstance(items,list): raise ValueError("JSON poll feed must contain a polls array")
    return [_poll(x,source) for x in items]

def parse_csv(body,source):
    rows=csv.DictReader(io.StringIO(body.decode("utf-8")))
    out=[]
    for r in rows:
        parties={k:v for k,v in r.items() if k not in {"id","publication_date","pollster","sample_size","fieldwork_start","fieldwork_end","methodology"} and v not in (None,"")}
        x={k:r.get(k) for k in ("id","publication_date","pollster","sample_size","fieldwork_start","fieldwork_end","methodology")}
        x["parties"]=parties; out.append(_poll(x,source))
    return out

def parse_rss(body,source):
    root=ET.fromstring(body.decode("utf-8"))
    out=[]
    for item in root.findall(".//item"):
        title=(item.findtext("title") or "").strip()
        link=(item.findtext("link") or source["url"]).strip()
        pub=(item.findtext("pubDate") or item.findtext("published") or "").strip()
        guid=(item.findtext("guid") or link or title).strip()
        if title and pub:
            out.append(Poll(guid,_date(pub),source.get("pollster_default","Fuente RSS"),source["id"],link,{}))
    return out


def parse_datoelectoral_html(body, source):
    soup=BeautifulSoup(body.decode("utf-8"),"html.parser")
    months={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
            "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
    out=[]
    for heading in soup.find_all(["h2","h3","h4"]):
        if "Estimación de voto publicada por el sondeo" not in heading.get_text(" ",strip=True):
            continue
        section=[]
        for node in heading.find_all_next():
            if node is not heading and node.name in {"h2","h3","h4"} and section:
                break
            txt=node.get_text(" ",strip=True)
            if txt: section.append(txt)
        meta=[]
        for node in heading.find_all_previous():
            if node.name in {"h2","h3"}:
                break
            txt=node.get_text(" ",strip=True)
            if txt: meta.append(txt)
        parent=" ".join(reversed(meta))
        title=next((h.get_text(" ",strip=True) for h in heading.find_all_previous(["h2","h3"]) if h.get_text(" ",strip=True)), "Encuesta")
        m=re.search(r"publicado el (\d{1,2}) de ([a-záéíóú]+) de (\d{4})",parent,re.I)
        if not m or m.group(2).lower() not in months:
            continue
        publication=f"{m.group(3)}-{months[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
        parties={}
        for line in section:
            pm=re.match(r"^(.+?)\s+([0-9]+(?:[.,][0-9]+)?)\s*%$",line)
            if pm:
                name=_party(pm.group(1))
                if name not in {"OTROS PARTIDOS","OTROS"}:
                    parties[name]=float(pm.group(2).replace(",","."))
        if not parties:
            continue
        pollster=parent.split(" · publicado el ")[0].strip() or "Fuente publicada"
        sample=None
        sm=re.search(r"Tamaño de la muestra\s*[:]?\s*(\d[\d.]*)",parent,re.I)
        if sm: sample=int(sm.group(1).replace(".",""))
        out.append(_poll({"id":source["id"]+"::"+publication+"::"+title,
                          "publication_date":publication,"pollster":pollster,
                          "sample_size":sample,"parties":parties},source))
    return out

def parse_source(body,source):
    kind=source.get("format","json")
    if kind=="json": return parse_json(body,source)
    if kind=="csv": return parse_csv(body,source)
    if kind=="rss": return parse_rss(body,source)
    if kind=="datoelectoral_html": return parse_datoelectoral_html(body,source)
    raise ValueError(f"unsupported source format: {kind}")

def canonical_poll(p):
    return {"id":p.poll_id,"publication_date":p.publication_date,"pollster":p.pollster,
            "source_id":p.source_id,"source_url":p.source_url,"parties":dict(sorted(p.parties.items())),
            "fieldwork_start":p.fieldwork_start,"fieldwork_end":p.fieldwork_end,"sample_size":p.sample_size,
            "methodology":p.methodology}

def poll_hash(p):
    return hashlib.sha256(json.dumps(canonical_poll(p),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
