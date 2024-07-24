#The following code has been developed by Flavio Massimiliano Cecchini between 2018 and 2024. A package will hopefully be officially released at some point. Please give credit to the author if you use it. 
#Contact: flaviomassimiliano.cecchini at kuleuven.be

from collections import namedtuple

##Recurrent structures

#Structure of an annotation row in a CoNLL-U file
CoNLLURow = namedtuple('CoNLLURow', 'id form lemma upos xpos feats head deprel deps misc') 
CoNLLURow.__new__.__defaults__ = ('_',)*len(CoNLLURow._fields) 


##Methods to read and write CoNLL-U (plus) files

#Generator of trees represented as directed graphs by means of Networkx; features are stored as named tuples under 'features'. The index of a node can be any positive real number, expressed with a given decimal separator (decsep), which has to be different from the dot or the hyphen. Only order is relevant, indices will be recreated when printing the tree (see method).
#Every node is identified by a couple of real numbers: a positive index (zero only for the formal root) and a negative range for multiword tokens, zero otherwise.
#Also an empty tree, i.e. with no syntax, can be read
#Enhanced dependencies are not yet implemented
def readCoNLLU(conllu,comments='#',sents='sent_id',encoding='utf8', decsep=',',syntax=True,plus=False) : 
	
	from collections import namedtuple
	import regex, networkx
	from networkx.algorithms.cycles import simple_cycles
	from networkx.classes.function import is_empty
	
	if decsep in ('-','.') : #not admitted, already used for ranges and extra nodes in enhanced annotation
		raise Exception('Careful! The decimal separator must differ from . or -.')
	
	separators = regex.compile(r'[.-]') 
	interval = regex.compile(r'\p{{N}}+{}?\p{{N}}*-\p{{N}}+{}?\p{{N}}*'.format(decsep,decsep)) 
	
	sentence = {}

	with open(conllu,'r',encoding=encoding) as document :
		
		#Definition of fields and rows
		fields = ('id', 'form', 'lemma', 'upos', 'xpos', 'feats', 'head', 'deprel', 'deps', 'misc')
		plusfields = ()
		if plus :
			plusfields = tuple(map(lambda x : x.replace(':','_'),document.readline()[len('# global.columns = '):].strip(' \n').split(' ')))
		else :
			plusfields = tuple(fields)
		#
		nfields = len(plusfields)
		CoNLLURow = 	namedtuple('CoNLLURow', ' '.join(map(str.lower,plusfields)))
		CoNLLURow.__new__.__defaults__ = tuple(('_' if c in fields else '*') for c in plusfields)  
		#
		
		tree = networkx.DiGraph() 
		
		for row in document :
			
			row = row.strip('\n\r ')
			
			if row.startswith(comments) : 
			
				comm, _, value = row[1:].partition('=')
				sentence[comm.strip()] = value.strip()
				
				if comm.strip() == sents :
					tree = networkx.DiGraph() #syntactic tree: rooted, oriented tree with linear order on the nodes
					tree.add_node((0,0), features = CoNLLURow(id=(0,0))) #artificial node root from which the tree descends
			#	
			elif row.startswith(('1','2','3','4','5','6','7','8','9')) : #token of any kind #this is the most specific condition possible, made explicit

				node = CoNLLURow._make(row.split('\t')[:nfields])
				
				for f in {'feats','misc'}.intersection(plusfields) : #Plus files do not necessarily have feats nor misc
					node = node._replace(**{f : readUDfeatures(getattr(node,f))}) #We need to convert feats-like strings into dictionaries, and viceversa
					#node = node._replace(feats=readUDfeatures(node.feats),\
					#					 misc=readUDfeatures(node.misc)\
					#					) 
				#
			
				index = list(map(lambda  x : float(x.replace(decsep,'.')),regex.split(separators,node.id))) #the dot is needed by Python floats
				index += [0]*(2-len(index)) #ordering always works on couples; zero is the default value for regular words
				if regex.fullmatch(interval,node.id) : #treatment of multiword tokens
					index[1] = index[0] - index[1] #the span of the range is given by a negative number
				node = node._replace(id=tuple(index))
				
				try : 
					node = node._replace(head=int(node.head)) #we prefer an integer instead of a string
				except (ValueError) : #when there is no syntax
					pass 
				
				tree.add_node(node.id, features=node._replace(head=(node.head,0) if isinstance(node.head,int) else node.head)) #option for headless nodes, e.g. multiword tokens
				if isinstance(node.head,int) :
					tree.add_edge((node.head,0),node.id) 
			#
			elif not is_empty(tree) or (not syntax and tree.nodes()) : 
				yield sentence, tree
				tree = networkx.DiGraph() #we re-imitialise the syntactic tree
				sentence = {}
			#
			
		#to print the final tree	
		if not is_empty(tree) or (not syntax and tree.nodes()) :
			yield sentence, tree
#

#Produces a dictionary out of a feats-like string, taking into account possible multiple values for a feature with tuples
def readUDfeatures(ftstring,null=('_',),sepfeat='|',sepval='=',sepint=',') : 
	
	if ftstring in null :
		return {}
	else :
		return { f:tuple(v.split(sepint)) for f,v in [ft.split(sepval,maxsplit=1) for ft in ftstring.split(sepfeat) if ft not in null and sepval in ft]} #tries to make up for faulty strings (e.g. e,pty values)
#

#The inverse of the previous method, either from a dictionary or a named tuple
def writeUDfeatures(tfeats,sepfeat='|',sepval='=',sepint=',') : 
	
	if not any(tfeats.values()) : #even if we have feature names, if they are empty it means they have not to be annotated
		return '_'
	else : 
		return sepfeat.join([sepval.join([f,sepint.join(sorted(( (v,) if isinstance(v,str) else v )))])\
						 for f,v in sorted(tfeats.items(), key = lambda x : x[0].lower()) if v]) #we need to be able to treat at the same time values expressed as bare strings or as tuples
#	

#Prints with correct formatting a tree as represented in CoNLL-U (plus) files, from the output of readCoNLLU
#If needed, nodes with given attributes can be ignored 
#Enhanced annotation is still not stably implemented
def printCoNLLUtree(tree,data='features',ignored={},syntax=True) :
	
	import networkx,regex
	from operator import itemgetter	
	from collections import namedtuple
	
	#the set of conditions for ignoring are meant as a disjunction
	no = lambda x : any(bool(regex.search(cond,getattr(x,val))) for val,cond in ignored.items()) if ignored else False  
		
	rows = []	
	deltas = {0:0} #we need a way to track the progressive ids of tokens of any type, starting from the root
	for nprog,nid in enumerate([ n[0][0] for n in sorted(list(tree.nodes(data)),key=itemgetter(0)) if n[0]!=(0,0) and n[0][1] == 0 and not no(n[1])]) :
		deltas[nid] = nprog + 1 - nid  
	
	#Warning: what follows is pure index madness
	for nd in [ n[1] for n in sorted(list(tree.nodes(data)),key=itemgetter(0)) if n[0]!=(0,0) and not no(n[1])] :  
		if nd.id[1] < 0 : #multiword tokens
			nd = nd._replace(id=(nd.id[0]+deltas[nd.id[0]],  nd.id[1] - ( deltas[nd.id[0]-nd.id[1]] - deltas[nd.id[0]] ))) 
			nd = nd._replace(id='-'.join(map(str,[int(nd.id[0]),int(nd.id[0]-nd.id[1])]))) #we produce the correct range to be printed
		else :
			nd = nd._replace(id='.'.join(map(str,[int(i+deltas[nd.id[0]]) for i in nd.id if i != 0])),\
							 head=(int(nd.head[0]+deltas[nd.head[0]]),0) if syntax else '_' ) 
		#
		nd = nd._replace(head=str(nd.head[0]))
		
		#Treatment of feats and misc, if any
		for f in {'feats','misc'}.intersection(nd._fields) : 
			nd = nd._replace(**{f : writeUDfeatures(getattr(nd,f))})
		#nd = nd._replace(feats=stampa_stringa_morphoUD(nd.feats),misc=stampa_stringa_morphoUD(nd.misc))

		#Finally, the row
		rows.append('\t'.join(nd))
	#
	
	return '\n'.join(rows)+'\n\n'
#



##Secondary extractive methods

#Returns only syntactic words
def syntacticwords(tree) : 
	
	for n in sorted(tree) : 
		if n[0] > 0 and n[1] == 0 :
			yield tree.nodes[n]['features']
#

#Given a node in a syntactic trees, it extracts a subtree satisfying all conditions for dependency relations and/or parts of speech (set as functional by default, returning it in form of a named tuple combining and counting forms/lemmas/POS/relations/features
#The node is represented just by the index
def extractnucleus(tree,node,funcrel=('expl','advmod','discourse','aux','cop','mark','nummod','det','clf','case','cc','punct'),funcpos=('ADV','ADP','AUX','CCONJ','DET','INTJ','NUM','PART','PRON','SCONJ','PUNCT')) : 
	
	import networkx as nx
	from itertools import chain
	from collections import Counter, namedtuple
	
	Nucleus = namedtuple('Nucleus', 'ids forms lemmas upos feats deprels') 

	criteria = lambda x : (tree.nodes[x]['features'].deprel.split(':')[0] in funcrel if funcrel else True) and (tree.nodes[x]['features'].upos in funcpos if funcpos else True)
	
	nucleus = [node]
	corona = list(filter(criteria, nx.descendants_at_distance(tree,node,1) ))  
	nucleus.extend(corona)
	
	while corona :
		corona = list(chain.from_iterable([filter(criteria, nx.descendants_at_distance(tree,c,1)) for c in corona])) 
		nucleus.extend(corona)
	#
	
	nucleus = sorted(nucleus) #it might be useful to keep the linear order of the nucleus, especially for printing the form sequence
	
	combonucleus = Nucleus(ids = nucleus,\
						   forms = tuple([tree.nodes[i]['features'].form for i in nucleus]),\
						   lemmas = tuple([tree.nodes[i]['features'].lemma for i in nucleus]),\
						   upos = tuple([tree.nodes[i]['features'].upos for i in nucleus]),\
						   feats = featsfusion([tree.nodes[i]['features'].feats for i in nucleus]),\
						   deprels = tuple([tree.nodes[i]['features'].deprel for i in set(nucleus) - {node}]) ) #we usually do not want the relation of our subtree's root, as it is "external"
	
	return combonucleus
#	

#Starting from a node in a syntactic tree expressed in the CoNLL-U format, it climbs it until it reaches a given dependency relation, and returns the corresponding chain of nodes, including the starting one. It can be made to handle co-ordinative or other horizontal relations
#The node is represented by the index only
def treeclimb(tree,node,stop=set(),conj=()) : 
	
	stop = stop | {'root'}	
	i = node
	
	while ( truehead(tree,tree.nodes[i]['features'].id,conj=conj).deprel if conj else tree.nodes[i]['features'].deprel ) not in stop :
		i = tree.nodes[i]['features'].head
		
	return i
#

#It retrieves the actual head of a node modulo co-ordinations or other flat relations
#The node is represented just by the index, but a complete node is returned
def truehead(tree,node,conj=(),sub=False) : 

	i = node
	
	while (tree.nodes[i]['features'].deprel.split(':')[0] if not sub else tree.nodes[i]['features'].deprel) in conj : 
		i = tree.nodes[i]['features'].head
	
	return tree.nodes[i]['features'] 
#



##Other manipulations of data

#It takes a list of feats-like dictionaries and fuses it in one, taking into count the multiplicity of feature values (e.g. Polarity=Neg appearing twice as opposed to once, which can make a difference in some languages)
def featsfusion(flist) : 

	from collections import defaultdict,Counter
	import collections.abc
	
	fusion = defaultdict(Counter)
	
	for d in flist :
		for k,v in d.items() :
			
			multi = isinstance(v,collections.abc.Iterable) and not isinstance(v,str) #we accept both bare values, or tuples of values
			
			fusion[k].update(v if multi else tuple(v,))
	#
	
	return dict(**fusion) #better than a defaultdict as absent values will return a KeyError
#



