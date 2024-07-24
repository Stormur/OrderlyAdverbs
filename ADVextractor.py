#Code to extract adverbs (ADV) from CoNLL-U files, and to present their distribution and various statistics. Please refer to 
#Edition note: some slight improvements and tweaks have been implemented, so the data produced could not coincide 100% with those presented in the paper, but substantially it does

import os, sys
from collections import namedtuple, Counter, defaultdict

#Importing own scripts for CoNLL-U manipulations
sys.path.insert(0, './Tools/')
import CoNLLUTools
#TECHNICAL NOTE: Theoretically, Udapi could be used for this. But because of inaccessibility and impenetrability of its documentation, 
#at the moment I find it easier to do very simple tree-search operations as the ones performed here, 
#by means of own-created code. Every suggestion to make the script more open is welcome.

#Input
try :
	folder = sys.argv[1]
except (IndexError) :
	print("Please insert the CoNLL-U files you want to analyse, either as a single document, a folder path, or an orderly comma-separated list of file/paths (can be mixed).")
	quit()
	
#Hardcoded CoNNL-U extension, but the code might possibly include Plus, too
extensions = ('.conllu',)

#Extraction of documents
texts = []
for doc in folder.strip().split(',') :
	if os.path.isdir(doc) :
		for t , _, fili in os.walk(doc) :
			texts.extend([os.path.join(t,f) for f in fili if os.path.splitext(f)[1]  in extensions ])
	else : 
		if os.path.splitext(doc)[1] in extensions :
			texts.append(doc)	
#

#Creation of output name
from pathlib import Path
output = 'ADV_' + '_'.join(map(lambda x : Path(x).stem,texts))
if not os.path.exists(output):
    os.makedirs(output)

#Specific named tuples to handle adverbs
ADV = namedtuple('ADV','form lemma pos morpho deprel head ddeprel') 
ADV.__new__.__defaults__ = ('','_','ADV','','',None,(),(),None,None,None,None)#*len(ADV._fields)

#Lits which will be used
adverbs = []
adverbials = []
forms = set() 
obliques = []
advcoord = []

#Definitions of relations classes we need, hardcoded from UD tools 
alldeprel = {'acl','advcl','advmod','amod','appos','aux','case','cc','ccomp','clf','compound','conj','cop','csubj','dep','det','discourse','dislocated','expl','fixed','flat','goeswith','iobj','list','mark','nmod','nsubj','nummod','obj','obl','orphan','parataxis','punct','reparandum','root','vocative','xcomp'} #taken from UD folder tools/data/deprel.ud, as of v2.14
clauseheads = {'root','parataxis','csubj','ccomp','xcomp','advcl','acl'} #conj copying the function if it depends on another clause head
verbfunc = {'aux','cop'}
roots = {'root','parataxis','acl'}
horizontal = {'conj','flat','fixed','list'}
nonrelations = {'dep','orphan','punct','reparandum','goeswith'}

#Collection of data
for text in texts :

	print(text)

	for s,a in CoNLLUTools.readCoNLLU(text) :
		
		print(s['sent_id'],end='\r')
		
		for n in CoNLLUTools.syntacticwords(a) :
			
			#We act modulo horizontal (i.e. co-ordinative) structures
			tnode = CoNLLUTools.truehead(a,n.id,conj=horizontal)
			trel = tnode.deprel.split(':')[0] #no subtypes
			thead = tnode.head
			
			if n.upos == 'ADV' and trel not in nonrelations : 
				
				#Basic features
				adv = ADV(form = n.form.lower(), lemma = n.lemma.lower(), morpho = CoNLLUTools.writeUDfeatures(n.feats), deprel = tnode.deprel.split(':')[0])
				
				#If it the ADV is not the head of a predicate, we fetch some context...
				if tnode.deprel not in clauseheads :

					#We consider the (true) head of the node
					hnode = a.nodes[thead]['features']
					hnucleus = CoNLLUTools.extractnucleus(a,hnode.id)
					
					#We define some macrocategories for the head of the ADV: PRED for a (synthetic or periphrastic) predication, NOM for nominals
					hpos = 'PRED' if (hnode.deprel.split(':')[0] in clauseheads or hnode.upos in ('VERB','AUX') or {'cop','aux'}.intersection(hnucleus.deprels)) else hnode.upos
					hpos = 'NOM' if hpos in ('NOUN','PROPN','PRON') else hpos 
					
					#We collect the data about the ADV head and syntactic distances
					adv = adv._replace(head = hpos)		
					
					#Co-ordinated ADVs
					if n.deprel.split(':')[0] == 'conj' and hnode.upos == 'ADV' :
						advcoord.append((n.lemma.lower(), hnode.lemma.lower()))
					
				else : #The ADV is itself the head of a clause
					adv = adv._replace(head = 'ROOT') 
					
				#We collect information about possible ADV's dependents	with meaningful relations #In horizontal constructions, we look only at "local dependents", not at possible common dependents of the whole construction
				adv = adv._replace(ddeprel = tuple(sorted(CoNLLUTools.extractnucleus(a,n.id,funcrel = alldeprel - (horizontal | nonrelations)).deprels))) #ddeprel = tuple(sorted([a.nodes[nn]['features'].deprel for nn in a.successors(tnode.id) if not a.nodes[nn]['features'].deprel.startswith(horizontal+('punct',)) and a.nodes[nn]['features'].id != n.id]))
				
				#We add the ADV profile we have so found to the list
				adverbs.append(adv)
				#
				
					
			#We save all forms of non-ADV elements to compare them with ADVs
			elif n.upos != 'ADV' :
				forms.add((n.form.lower(), n.upos, n.lemma.lower(), CoNLLUTools.writeUDfeatures(n.feats)))
				
			#We save any other elements tagged with adverbial relations
			if tnode.deprel.split(':')[0] == 'advmod' :		
				adverbials.append(ADV(form = n.form.lower(), lemma = n.lemma.lower(), pos=n.upos, morpho = CoNLLUTools.writeUDfeatures(n.feats), deprel = tnode.deprel.split(':')[0]))
#

	
#We prepare and lay out the data collected so far
cadv = Counter(ad.form for ad in adverbs) #forms over lemmas, because not every treebank has lemmas
#
ladv = defaultdict(set)
for ad in adverbs :
	ladv[ad.form].add(ad.lemma)
#
radv = defaultdict(Counter)
for ad in adverbs :
	radv[ad.form][ad.deprel] += 1
#	
tadv = defaultdict(Counter)
for ad in adverbs :
	tadv[ad.form]['PRED' if ad.head in ('ADJ','DET','NUM','ADV') else ad.head] += 1 #We conflate into the PRED macrocategory also all modifiers
#
dadv = defaultdict(Counter)
for ad in adverbs :
	for d in ad.ddeprel :
		dadv[ad.form][d] += 1
#

	
#General distribution of ADV types	
with open(os.path.join(output,'ADV_distr.tsv'),'w',encoding='utf8') as advex :

	modified = sorted(filter(None,set().union(*[t.keys() for _,t in tadv.items()]))) #All UPOS appearing as heads of an ADV
	
	advex.write('Form type\tLemmas\tFrequency\t{}\n'.format('\t'.join(modified)))
	
	for dv in cadv : 
		
		advex.write('{}\t{}\t{}\t{}\n'.format( dv,\
												  ','.join(ladv[dv]),\
												  str(cadv[dv]),\
												  '\t'.join(str(tadv[dv].get(t,0)/cadv[dv]) for t in modified),\
												 ))	
#

#We investigate ADV form types coinciding with forms of other parts of speech	 			 
coincidences = {a.form for a in adverbs} & {f[0] for f in forms}

with open(os.path.join(output,'ADV_coinc.tsv'),'w',encoding='utf8') as advex :
	for fc in [f for f in forms if f[0] in coincidences] :
		advex.write('{}\n'.format('\t'.join(fc)))
#

#We investigate nominal-like dependents of ADVs
dnom = ('nmod', 'appos', 'nummod', 'acl', 'amod', 'det', 'clf', 'case', 'cop') #nominal dependents + the copula, which implies the ADV is not metapredicating

nomdependents = defaultdict(dict)
nominallike = set()
threshold = 5 #we want to avoid noise and find some regular patterns

for adv,ddiz in dadv.items() :
	for dr,dc in ddiz.items() :
		if dr.startswith(dnom) and cadv[adv] > threshold : 
			nomdependents[dr][adv] = dc/cadv[adv]
			nominallike.add(adv)

with open(os.path.join(output,'ADV_nominals.tsv'),'w',encoding='utf8') as advex :
	for d in nomdependents :
		advex.write('{}\t{}\n\n'.format(d, ' '.join(['/'.join(map(str,i)) for i in sorted(nomdependents[d].items(), key = lambda x : x[1], reverse=True)])  ))
#

#We print ADVs having a form different from the lemma
difforms = defaultdict(lambda : defaultdict(set))

#The transformation in terms of prefixoid and suffixoid substitution to go from A to B is found
def findstringtransformation(AB) : 
	import difflib
	from collections import namedtuple
	A,B = AB
	Transformation = namedtuple('Transformation', 'Apref Bpref Asuff Bsuff') 
	Transformation.__new__.__defaults__ = ('','','','')
	commons = difflib.SequenceMatcher(None, A, B).find_longest_match(0,len(A),0,len(B))
	return Transformation(len(A[:commons.a]),B[:commons.b],len(A[commons.a+commons.size:]),B[commons.b+commons.size:]) 
#

for af,al in ladv.items() :
	for aall in set(map(str.lower,al)) - {af.lower()} :
		difforms['|'.join(map(str,findstringtransformation((aall,af.lower()))))][af.lower()].add(aall)
		
with open(os.path.join(output,'ADV_difflemma.tsv'),'w',encoding='utf8') as advex :
	for df,fl in difforms.items() :
		for f,ll in fl.items() : 
			advex.write('{}\t{}\t{}\n'.format( df, f, ','.join(ll) ))
#
		  
#We print all morpholexical properties associated to ADVs
advmorph = set().union(*[adv.morpho.split('|') for adv in adverbs])

with open(os.path.join(output,'ADV_morpho.tsv'),'w',encoding='utf8') as advex :
	for m in sorted(advmorph) :
		advex.write('{}\n'.format(m))
#


#Overview of what takes the relation advmod

##Outputs a Counter with normalised counts 
def counternormalisation(c) : 
	from collections import Counter
	nc = {}
	total = sum(c.values())
	for x,n in c.items() :
		nc[x] = n / total
	return nc
#

advmodcont = counternormalisation(Counter([adv.pos for adv in adverbials]))

posmod = defaultdict(Counter)
for adv in adverbials :
	posmod[adv.pos][adv.lemma] += 1
posmod = {p:counternormalisation(cmod) for p,cmod in posmod.items()}

with open(os.path.join(output,'ADV_advmod.tsv'),'w',encoding='utf8') as advex :
	
	advex.write('{}\n\n\n'.format('\n'.join(['\t'.join(map(str,c)) for c in sorted(advmodcont.items(),key = lambda x :x[1],reverse=True)])))
	
	for p,c in posmod.items() :
		advex.write('{}\t{}\n\n'.format(p,  ' '.join([','.join(map(str,pc)) for pc in sorted(c.items(),key=lambda x : x[1],reverse=True)])))
#

#Groups of co-ordinated adverbs
import networkx as nx
from networkx.algorithms import connected_components

ADVconj = nx.Graph(advcoord)
connadv = connected_components(ADVconj)

with open(os.path.join(output,'ADV_coord.tsv'),'w',encoding='utf8') as advex :
	for ac in sorted(list(connadv),key = lambda x : len(x),reverse=True) :
		advex.write('{}\n\n'.format('\t'.join(map(lambda x : x.upper() if x in nominallike else x,ac))))
#







