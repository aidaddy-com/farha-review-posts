#!/usr/bin/env python3
"""Hook rubric: 1 point each for (1) specific: a number, a time, a named person or a concrete result;
(2) 12 words or fewer; (3) shares no 3-word phrase with another hook in the batch (common roof phrases excepted);
(4) not empty praise. 4/4 passes. Hooks that are the whole review can't be improved and are listed separately.

Usage: python3 check_hooks.py reviews.json   (exit code 1 if any hook is WEAK)"""
import json,re,sys
NUM=r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|same day|every (?:evening|day|night)|week|weeks|hours?|days?)\b"
RESULT=r"\b(fixed|replaced|protect\w*|disruption|closing|life left|buildings|insurance|adjustor|stress-free|landscaping|HOA|commercial|construction|ladders|stars|cleaned up|nails|confidence|schools?|church|warehouse|garage|office|buildings?|porch|skylights?)\b"
# capitalised words that are NOT people's names (sentence starters, brand, places, common review words)
COMMON=set("""a about above after again all also always amazing an and any are as at be been before being best both but by
call came can could did do does done during each even ever every everyone everything excellent extremely fantastic farha
first fix for from great had handled has have he her here highly his how i if in is it its just kansas city knowledge
like made make many more most my never new no not now of on once one only or other our out over please prompt quick
quickly really recommend roof roofing she so some such than thank thanks that the their them then there these they this
those through to too turns two up very was we well went were what when which while who will with work worked would
wow yes you your completed nice good""".split())
GENERIC=r"\b(recommend\w*|best|great|amazing|excellent|first class|fantastic|awesome|professional\w*|knowledgeable)\b"
STOP={("a","new","roof"),("my","new","roof"),("our","new","roof"),("the","roof","was")}
def names(h): return [w for w in re.findall(r"\b[A-Z][a-z]+\b",h) if w.lower() not in COMMON]
def opening(h,q):  # the hook is just the review's first words: the testimonial card would print it twice
    a=re.sub(r"[^a-z0-9 ]","",h.lower()).split(); b=re.sub(r"[^a-z0-9 ]","",q.lower()).split()
    return len(q.split())>32 and b[:len(a)]==a
def grams(h): w=re.findall(r"[a-z’']+",h.lower()); return {tuple(w[i:i+3]) for i in range(len(w)-2)}-STOP
R=json.load(open(sys.argv[1])); H=[(r['name']+'|'+r['location'],r['hook'],r['quote']) for r in R]
rows=[]
for n,h,q in H:
    w=len(h.split()); spec=bool(re.search(NUM,h,re.I) or re.search(RESULT,h,re.I) or names(h))
    rep=any(grams(h)&grams(h2) for n2,h2,_ in H if n2!=n); gen=bool(re.search(GENERIC,h,re.I)) and not spec
    whole=w>=len(q.split())-1; s=int(spec)+int(w<=12)+int(not rep)+int(not gen); rows.append((n,s,spec,w,rep,gen,whole,h,opening(h,q)))
print(f"{len(rows)} hooks | 4/4: {sum(r[1]==4 for r in rows)} | weak with a better line available: {sum(r[1]<4 and not r[6] for r in rows)} | whole-review (no shorter line exists): {sum(r[1]<4 and r[6] for r in rows)}")
for n,s,spec,w,rep,gen,whole,h,op in rows:
    tag='' if s==4 else (' whole review' if whole else ' WEAK')
    print(f"{s}/4{tag:13} {n.split('|')[0]:22}{' REPEAT' if rep else ''}{' GENERIC' if gen else ''}{' OPENING (pick a line from later in the review)' if op else ''} | {h}")
sys.exit(1 if any(r[1] < 4 and not r[6] for r in rows) else 0)
