from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET, json, re, html, os

BUYER_TERMS = [
 "request for proposal", "request for quotation", "freelance graphic designer",
 "logo design needed", "branding project", "website redesign contract",
 "business plan writer", "shopify store setup", "design tender", "creative services tender"
]
def fetch_rss(q):
    url="https://news.google.com/rss/search?q="+quote(q)+"&hl=en&gl=US&ceid=US:en"
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 GlobalOpportunityScout/1.0"})
    with urlopen(req,timeout=18) as resp: raw=resp.read()
    root=ET.fromstring(raw)
    rows=[]
    for item in root.findall(".//item"):
        title=item.findtext("title","")
        link=item.findtext("link","")
        desc=item.findtext("description","")
        pub=item.findtext("pubDate","")
        source=item.find("source")
        rows.append({"title":html.unescape(title),"url":link,"description":re.sub("<[^>]+>"," ",html.unescape(desc)).strip(),"posted":pub,"source":source.text if source is not None else "Google News RSS","location":"Search market"})
    return rows
def search(keywords,country,typ):
    kw=keywords or "graphic design request for proposal branding"
    market="" if "worldwide" in (country or "").lower() else (country or "")
    queries=[kw+" "+market]
    if typ and typ.lower() not in ("any opportunity",""):
        queries.append(typ+" "+kw+" "+market)
    results=[];errors=[]
    for q in queries:
        try: results.extend(fetch_rss(q))
        except Exception as e: errors.append(str(e))
    seen=set(); out=[]
    for x in results:
        k=x["url"]
        if k in seen: continue
        seen.add(k)
        blob=(x["title"]+" "+x["description"]).lower()
        # Keep results that appear to signal service requests, contracts or procurement.
        intent=("request for proposal","rfp","rfq","tender","contract","freelance","seeking","looking for","designer","design services","branding","logo","website","business plan","shopify","supplier","procurement","bid")
        if not any(t in blob for t in intent): continue
        x["country"]=country or "Worldwide"
        out.append(x)
    return out[:60],errors
class Handler(BaseHTTPRequestHandler):
    def sendj(self,status,obj):
        b=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Access-Control-Allow-Origin","*");self.send_header("Access-Control-Allow-Methods","GET, OPTIONS");self.send_header("Access-Control-Allow-Headers","Content-Type");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def do_OPTIONS(self): self.sendj(200,{})
    def do_GET(self):
        p=urlparse(self.path); qs=parse_qs(p.query)
        if p.path in ("/","/health","/api/health"):
            self.sendj(200,{"ok":True,"service":"Global Opportunity Scout Buyer Finder API","endpoint":"/api/opportunities"});return
        if p.path=="/api/opportunities":
            kw=qs.get("keywords",[""])[0]; country=qs.get("country",[""])[0]; typ=qs.get("type",[""])[0]
            rows,errors=search(kw,country,typ)
            self.sendj(200,{"results":rows,"count":len(rows),"errors":errors,"note":"Public search-feed matches are leads, not verified buyer commitments."});return
        self.sendj(404,{"error":"Not found"})
    def log_message(self,*args): pass
port=int(os.environ.get("PORT","10000"))
ThreadingHTTPServer(("0.0.0.0",port),Handler).serve_forever()
