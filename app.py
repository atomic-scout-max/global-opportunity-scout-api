import os, re, time
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app, origins=os.getenv('CORS_ORIGINS', '*').split(','))
CACHE = {}
TTL = 300

def clean(s):
    return re.sub(r'<[^>]+>', ' ', str(s or '')).strip()

def fetch_sources():
    now=time.time()
    if 'jobs' in CACHE and now-CACHE['jobs'][0] < TTL:
        return CACHE['jobs'][1]
    jobs=[]
    try:
        r=requests.get('https://www.arbeitnow.com/api/job-board-api', timeout=15, headers={'User-Agent':'GlobalOpportunityScout/1.0'})
        r.raise_for_status()
        for x in r.json().get('data',[]):
            jobs.append(dict(title=x.get('title'), company=x.get('company'), location=x.get('location'), url=x.get('url'), description=clean(x.get('description')), tags=x.get('tags',[]), posted=x.get('created_at'), source='Arbeitnow'))
    except Exception as e: print('Arbeitnow:',e)
    try:
        r=requests.get('https://jobicy.com/api/v2/remote-jobs?count=50', timeout=15, headers={'User-Agent':'GlobalOpportunityScout/1.0'})
        r.raise_for_status()
        for x in r.json().get('jobs',[]):
            jobs.append(dict(title=x.get('jobTitle'), company=x.get('companyName'), location=x.get('jobGeo'), url=x.get('url'), description=clean(x.get('jobDescription')), tags=x.get('jobIndustry',[]), posted=x.get('pubDate'), source='Jobicy', companyUrl=x.get('companyUrl')))
    except Exception as e: print('Jobicy:',e)
    seen=set(); unique=[]
    for x in jobs:
        key=(str(x.get('company','')).lower(),str(x.get('title','')).lower())
        if key not in seen and x.get('url'):
            seen.add(key); unique.append(x)
    CACHE['jobs']=(now,unique)
    return unique

@app.get('/')
def root(): return jsonify(name='Global Opportunity Scout API', status='online', endpoints=['/health','/api/jobs'])
@app.get('/health')
def health(): return jsonify(status='ok', service='Global Opportunity Scout API')
@app.get('/api/jobs')
def api_jobs():
    kw=request.args.get('keywords','graphic design logo branding').lower().strip()
    country=request.args.get('country','Worldwide / English speaking markets').strip()
    terms=[t for t in re.split(r'\s+',kw) if t]
    data=fetch_sources()
    def match(x):
        hay=' '.join([str(x.get('title','')),str(x.get('company','')),str(x.get('description','')),str(x.get('tags',''))]).lower()
        if terms and not any(t in hay for t in terms): return False
        loc=str(x.get('location') or '').lower()
        if country and 'worldwide' not in country.lower() and 'english speaking' not in country.lower():
            if loc and not any(z in loc for z in ['remote','worldwide','anywhere',country.lower()]): return False
        return True
    out=[x for x in data if match(x)]
    return jsonify(jobs=out[:100], total=len(out), sources=['Arbeitnow','Jobicy'], cached_seconds=TTL)
if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT',5000)))
