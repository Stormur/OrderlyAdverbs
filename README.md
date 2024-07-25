# OrderlyAdverbs

Code and materials associated to the paper "Let's do it orderly: a proposal for a better taxonomy of adverbs in Universal Dependencies, and beyond", by Flavio Massimiliano Cecchini, published on the [Prague Bulletin of Mathematical Linguistics 121 of June 2024](https://ufal.mff.cuni.cz/pbml/121).

## Explanation of files and codes 

The main script is `ADVextractor.py`, which is meant to be launched from this repository by giving the path to a single CoNLL-U file, a folder containing CoNLL-U files, or a mixture of both. The script then proceeds to create a folder which contains different files with statistics about adverbs (`ADV`) in the data. Outputs for all the treebanks discussed in the paper are already provided, plus for the new Latin CIRCSE treebank. 

The script and the tables are admittedly somewhat rough. We notice that, in order to read CoNLL-U files and extract data, an own Python "module" has been deployed, part of a suite developed by the author starting from 2018 which has not been published yet (but hopefully will at some point). Any suggestions to better integrate the code with already existing tools like Udapi are welcome.  

* `ADV_advmod.tsv`: the distribution over parts of speech of all syntactic words receiving the `advmod` relation in the data, and, for every part of speech, the distribution over lemmas.
* `ADV_coinc.tsv`: a list of `ADV` form types coinciding with forms of other parts of speech in the data, with the given part of speech, the lemma and morphological features of the coinciding form.
* `ADV_coord.tsv`: list of groups of `ADV` form types of which one appears co-ordinated to at least another one. Since such occurrences are quite rare, the file might be empty. "Nominal-like" `ADV`s are upper case. 
* `ADV_difflemma.tsv`: list of `ADV`s for which the lemma (third column) differs from the form (second column); the first column shows the transformation that takes the lemma to the form, in terms of deletion and addition of initial and final characters ("prefixes" and "suffixes"). 
    * For example, for Latin UDante, for the couple *fecunde*/*fecundius* the transformation `0||1|ius` means that 0 characters have to be deleted from the beginning of *fecundius* and than the empty string has to be added (so nothing changes at the left margin), while the last character (`e`) has to be deleted, and then the string `ius` appended. This transformation is seen to be quite common, and can be linguistically interpreted as creating a comparative form for a given inflection class. 
* `ADV_distr.tsv`: table showing the patterns of dependencies of an `ADV`. Beside form type, lemma and absolute frequency among the data, the distribution over the head category is shown. The categories are basically the parts of speech of the heads, with two macrocategories and a special category:
    * `ROOT`: the `ADV` is itself at the head of a clause (non-expected non-metapredicating behaviour for non-elliptical clauses) 
    * `PRED`: the head is a predicate, which includes both verbal and nominal ones (i.e. copulae), synthetic or periphrastic constructions, and also any kind of modifier (`ADJ`, `DET`, `NUM`, `ADV`)
    * `NOM`: any nominal element (`NOUN`/`PROPN` and `PRON`) which is not part of a predicate
* `ADV_morpho.tsv`: All single couples of morphological features and values that can be associated to `ADV`s in the data.
* `ADV_nominals.tsv`: all `ADV`s which receive a nominal dependency relation, shown distributed per form according to each such dependency relation.

### Latin adverbs

The subfolder `Latin` contains a single file `ADV_omnia.tsv` where each `ADV` lemma among Latin treebanks is assigned the actual part of sppech of the base it is derived from or instead of which has been mistagged (see §4.4.2 for details). The tag REL, which is not part of UD, but which is discussed in the paper, is also used (and discussed, cf. §5.1.5). Please notice that this enquiry does not take into account the treebank Latin CIRCSE, which appeared after the writing of the paper. 

Also, unfortunately, morphological features of each derivation were part of this overview, but are absent due to data loss. They might be (re)added as future work.

## References

For any question, do not hesitate to contact the author, as specified in the paper!