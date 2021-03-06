import time, re, os
from virus_filter import virus_filter
from virus_clean import virus_clean
from tree_refine import tree_refine
from process import process, virus_config
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.Align import MultipleSeqAlignment
import numpy as np
from itertools import izip

virus_config.update({
	# data source and sequence parsing/cleaning/processing
	'virus':'Zika',
	'fasta_fields':{0:'strain', 2:'accession', 3:'date', 5:'country', 5:'region', 8:'db', 10:'authors'},
	# 0         1    2        3          4            5      6    7     8       9      10
	#>BeH818995|Zika|KU365777|2015-07-21|SouthAmerica|Brazil|Para|Belem|Genbank|Genome|Azevedo et al|?|
	'alignment_file':'data/zika.fasta',
	'outgroup':'H/PF/2013',
	'aggregate_regions':[('global', None)],
	'force_include_all':False,
	'max_global':True,   # sample as evenly as possible from different geographic regions 
	'cds':[0,None], # define the HA start i n 0 numbering
	# define relevant clades in canonical HA1 numbering (+1)
	# numbering starting at methionine including the signal peptide
	'min_mutation_frequency':0.499,
	'min_genotype_frequency':0.499,
	'html_vars': {'coloring': 'lbi, dfreq, region, date',
				   'gtplaceholder': 'Genomic positions...',
					'freqdefault': ''},
	'js_vars': {'LBItau': 0.0005, 'LBItime_window': 0.5, 'dfreq_dn':2},
	})


class zika_filter(virus_filter):
	def __init__(self,min_length = 987, **kwargs):
		'''
		parameters
		min_length  -- minimal length for a sequence to be acceptable
		'''
		virus_filter.__init__(self, **kwargs)
		self.min_length = min_length
		self.vaccine_strains =[]
		tmp_outgroup = SeqIO.read('source-data/Zika_outgroup.gb', 'genbank')
		genome_annotation = tmp_outgroup.features
		self.cds = {x.qualifiers['product'][0]:x for x in genome_annotation
				if 'product' in x.qualifiers and x.type=='CDS' and
				x.qualifiers['product'][0] in ['polyprotein']}		
		self.outgroup = {
			'strain': 'H/PF/2013',
			'country': 'FrenchPolynesia',
			'date': '2013-11-28',
			'seq': 'AGTATCAACAGGTTTTATTTTGGATTTGGAAACGAGAGTTTCTGGTCATGAAAAACCCAAAAAAGAAATCCGGAGGATTCCGGATTGTCAATATGCTAAAACGCGGAGTAGCCCGTGTGAGCCCCTTTGGGGGCTTGAAGAGGCTGCCAGCCGGACTTCTGCTGGGTCATGGGCCCATCAGGATGGTCTTGGCGATTCTAGCCTTTTTGAGATTCACGGCAATCAAGCCATCACTGGGTCTCATCAATAGATGGGGTTCAGTGGGGAAAAAAGAGGCTATGGAAATAATAAAGAAGTTCAAGAAAGATCTGGCTGCCATGCTGAGAATAATCAATGCTAGGAAGGAGAAGAAGAGACGAGGCGCAGATACTAGTGTCGGAATTGTTGGCCTCCTGCTGACCACAGCTATGGCAGCGGAGGTCACTAGACGTGGGAGTGCATACTATATGTACTTGGACAGAAACGACGCTGGGGAGGCCATATCTTTTCCAACCACATTGGGGATGAATAAGTGTTATATACAGATCATGGATCTTGGACACATGTGTGATGCCACCATGAGCTATGAATGCCCTATGCTGGATGAGGGGGTGGAACCAGATGACGTCGATTGTTGGTGCAACACGACGTCAACTTGGGTTGTGTACGGAACCTGCCATCACAAAAAAGGTGAAGCACGGAGATCTAGAAGAGCTGTGACGCTCCCCTCCCATTCCACTAGGAAGCTGCAAACGCGGTCGCAAACCTGGTTGGAATCAAGAGAATACACAAAGCACTTGATTAGAGTCGAAAATTGGATATTCAGGAACCCTGGCTTCGCGTTAGCAGCAGCTGCCATCGCTTGGCTTTTGGGAAGCTCAACGAGCCAAAAAGTCATATACTTGGTCATGATACTGCTGATTGCCCCGGCATACAGCATCAGGTGCATAGGAGTCAGCAATAGGGACTTTGTGGAAGGTATGTCAGGTGGGACTTGGGTTGATGTTGTCTTGGAACATGGAGGTTGTGTCACCGTAATGGCACAGGACAAACCGACTGTCGACATAGAGCTGGTTACAACAACAGTCAGCAACATGGCGGAGGTAAGATCCTACTGCTATGAGGCATCAATATCGGACATGGCTTCGGACAGCCGCTGCCCAACACAAGGTGAAGCCTACCTTGACAAGCAATCAGACACTCAATATGTCTGCAAAAGAACGTTAGTGGACAGAGGCTGGGGAAATGGATGTGGACTTTTTGGCAAAGGGAGCCTGGTGACATGCGCTAAGTTTGCATGCTCCAAGAAAATGACCGGGAAGAGCATCCAGCCAGAGAATCTGGAGTACCGGATAATGCTGTCAGTTCATGGCTCCCAGCACAGTGGGATGATCGTTAATGACACAGGACATGAAACTGATGAGAATAGAGCGAAGGTTGAGATAACGCCCAATTCACCAAGAGCCGAAGCCACCCTGGGGGGTTTTGGAAGCCTAGGACTTGATTGTGAACCGAGGACAGGCCTTGACTTTTCAGATTTGTATTACTTGACTATGAATAACAAGCACTGGTTGGTTCACAAGGAGTGGTTCCACGACATTCCATTACCTTGGCACGCTGGGGCAGACACCGGAACTCCACACTGGAACAACAAAGAAGCACTGGTAGAGTTCAAGGACGCACATGCCAAAAGGCAAACTGTCGTGGTTCTAGGGAGTCAAGAAGGAGCAGTTCACACGGCCCTTGCTGGAGCTCTGGAGGCTGAGATGGATGGTGCAAAGGGAAGGCTGTCCTCTGGCCACTTGAAATGTCGCCTGAAAATGGATAAACTTAGATTGAAGGGCGTGTCATACTCCTTGTGTACCGCAGCGTTCACATTCACCAAGATCCCGGCTGAAACACTGCACGGGACAGTCACAGTGGAGGTACAGTACGCAGGGACAGATGGACCTTGCAAGGTTCCAGCTCAGATGGCGGTGGACATGCAAACTCTGACCCCAGTTGGGAGGTTGATAACCGCTAACCCCGTAATCACTGAAAGCACTGAGAACTCTAAGATGATGCTGGAACTTGATCCACCATTTGGGGACTCTTACATTGTCATAGGAGTCGGGGAGAAGAAGATCACCCACCACTGGCACAGGAGTGGCAGCACCATTGGAAAAGCATTTGAAGCCACTGTGAGAGGTGCCAAGAGAATGGCAGTCTTGGGAGACACAGCCTGGGACTTTGGATCAGTTGGAGGCGCTCTCAACTCATTGGGCAAGGGCATCCATCAAATTTTTGGAGCAGCTTTCAAATCATTGTTTGGAGGAATGTCCTGGTTCTCACAAATTCTCATTGGAACGTTGCTGATGTGGTTGGGTCTGAACACAAAGAATGGATCTATTTCCCTTATGTGCTTGGCCTTAGGGGGAGTGTTGATCTTCTTATCCACAGCTGTCTCTGCTGATGTGGGGTGCTCGGTGGACTTCTCAAAGAAGGAGACGAGATGCGGTACAGGGGTGTTCGTCTATAACGACGTTGAAGCCTGGAGGGACAGGTACAAGTACCATCCTGACTCCCCCCGTAGATTGGCAGCAGCAGTCAAGCAAGCCTGGGAAGATGGTATCTGTGGGATCTCCTCTGTTTCAAGAATGGAAAACATCATGTGGAGATCAGTAGAAGGGGAGCTCAACGCAATCCTGGAAGAGAATGGAGTTCAACTGACGGTCGTTGTGGGATCTGTAAAAAACCCCATGTGGAGAGGTCCACAGAGATTGCCCGTGCCTGTGAACGAGCTGCCCCACGGCTGGAAGGCTTGGGGGAAATCGTACTTCGTCAGAGCAGCAAAGACAAATAACAGCTTTGTCGTGGATGGTGACACACTGAAGGAATGCCCACTCAAACATAGAGCATGGAACAGCTTTCTTGTGGAGGATCATGGGTTCGGGGTATTTCACACTAGTGTCTGGCTCAAGGTTAGAGAAGATTATTCATTAGAGTGTGATCCAGCCGTTATTGGAACAGCTGTTAAGGGAAAGGAGGCTGTACACAGTGATCTAGGCTACTGGATTGAGAGTGAGAAGAATGACACATGGAGGCTGAAGAGGGCCCATCTGATCGAGATGAAAACATGTGAATGGCCAAAGTCCCACACATTGTGGACAGATGGAATAGAAGAGAGTGATCTGATCATACCCAAGTCTTTAGCTGGGCCACTCAGCCATCACAATACCAGAGAGGGCTACAGGACCCAAATGAAAGGGCCATGGCACAGTGAAGAGCTTGAAATTCGGTTTGAGGAATGCCCAGGCACTAAGGTCCACGTGGAGGAAACATGTGGAACAAGAGGACCATCTCTGAGATCAACCACTGCAAGCGGAAGGGTGATCGAGGAATGGTGCTGCAGGGAGTGCACAATGCCCCCACTGTCGTTCCGGGCTAAAGATGGCTGTTGGTATGGAATGGAGATAAGGCCCAGGAAAGAACCAGAAAGTAACTTAGTAAGGTCAATGGTGACTGCAGGATCAACTGATCACATGGATCACTTCTCCCTTGGAGTGCTTGTGATTCTGCTCATGGTGCAGGAAGGGCTGAAGAAGAGAATGACCACAAAGATCATCATAAGCACATCGATGGCAGTGCTGGTAGCTATGATCCTGGGAGGATTTTCAATGAGTGACCTGGCTAAGCTTGCAATTTTGATGGGTGCCACCTTCGCGGAAATGAACACTGGAGGAGATGTAGCTCATCTGGCGCTGATAGCGGCATTCAAAGTCAGACCAGCGTTGCTGGTATCTTTCATCTTCAGAGCTAATTGGACACCCCGTGAAAGCATGCTGCTGGCCTTGGCCTCGTGTCTTTTGCAAACTGCGATCTCCGCCTTGGAAGGCGACCTGATGGTTCTCATCAATGGTTTTGCTTTGGCCTGGTTGGCAATACGAGCGATGGTTGTTCCACGCACTGATAACATCACCTTGGCAATCCTGGCTGCTCTGACACCACTGGCCCGGGGCACACTGCTTGTGGCGTGGAGAGCAGGCCTTGCTACTTGCGGGGGGTTTATGCTCCTCTCTCTGAAGGGAAAAGGCAGTGTGAAGAAGAACTTACCATTTGTCATGGCCCTGGGACTAACCGCTGTGAGGCTGGTCGACCCCATCAACGTGGTGGGACTGCTGTTGCTCACAAGGAGTGGGAAGCGGAGCTGGCCCCCTAGCGAAGTACTCACAGCTGTTGGCCTGATATGCGCATTGGCTGGAGGGTTCGCCAAGGCAGATATAGAGATGGCTGGGCCCATGGCCGCGGTCGGTCTGCTAATTGTCAGTTACGTGGTCTCAGGAAAGAGTGTGGACATGTACATTGAAAGAGCAGGTGACATCACATGGGAAAAAGATGCGGAAGTCACTGGAAACAGTCCCCGGCTCGATGTGGCGCTAGATGAGAGTGGTGATTTCTCCCTGGTGGAGGATGACGGTCCCCCCATGAGAGAGATCATACTCAAGGTGGTCCTGATGACCATCTGTGGCATGAACCCAATAGCCATACCCTTTGCAGCTGGAGCGTGGTACGTATACGTGAAGACTGGAAAAAGGAGTGGTGCTCTATGGGATGTGCCTGCTCCCAAGGAAGTAAAAAAGGGGGAGACCACAGATGGAGTGTACAGAGTAATGACTCGTAGACTGCTAGGTTCAACACAAGTTGGAGTGGGAGTTATGCAAGAGGGGGTCTTTCACACTATGTGGCACGTCACAAAAGGATCCGCGCTGAGAAGCGGTGAAGGGAGACTTGATCCATACTGGGGAGATGTCAAGCAGGATCTGGTGTCATACTGTGGTCCATGGAAGCTAGATGCCGCCTGGGACGGGCACAGCGAGGTGCAGCTCTTGGCCGTGCCCCCCGGAGAGAGAGCGAGGAACATCCAGACTCTGCCCGGAATATTTAAGACAAAGGATGGGGACATTGGAGCGGTTGCGCTGGATTACCCAGCAGGAACTTCAGGATCTCCAATCCTAGACAAGTGTGGGAGAGTGATAGGACTTTATGGCAATGGGGTCGTGATCAAAAATGGGAGTTATGTTAGTGCCATCACCCAAGGGAGGAGGGAGGAAGAGACTCCTGTTGAGTGCTTCGAGCCTTCGATGCTGAAGAAGAAGCAGCTAACTGTCTTAGACTTGCATCCTGGAGCTGGGAAAACCAGGAGAGTTCTTCCTGAAATAGTCCGTGAAGCCATAAAAACAAGACTCCGTACTGTGATCTTAGCTCCAACCAGGGTTGTCGCTGCTGAAATGGAGGAAGCCCTTAGAGGGCTTCCAGTGCGTTATATGACAACAGCAGTCAATGTCACCCACTCTGGAACAGAAATCGTCGACTTAATGTGCCATGCCACCTTCACTTCACGTCTACTACAGCCAATCAGAGTCCCCAACTATAATCTGTATATTATGGATGAGGCCCACTTCACAGATCCCTCAAGTATAGCAGCAAGAGGATACATTTCAACAAGGGTTGAGATGGGCGAGGCGGCTGCCATCTTCATGACCGCCACGCCACCAGGAACCCGTGACGCATTTCCGGACTCCAACTCACCAATTATGGACACCGAAGTGGAAGTCCCAGAGAGAGCCTGGAGCTCAGGCTTTGATTGGGTGACGGATCATTCTGGAAAAACAGTTTGGTTTGTTCCAAGCGTGAGGAACGGCAATGAGATCGCAGCTTGTCTGACAAAGGCTGGAAAACGGGTCATACAGCTCAGCAGAAAGACTTTTGAGACAGAGTTCCAGAAAACAAAACATCAAGAGTGGGACTTTGTCGTGACAACTGACATTTCAGAGATGGGCGCCAACTTTAAAGCTGACCGTGTCATAGATTCCAGGAGATGCCTAAAGCCGGTCATACTTGATGGCGAGAGAGTCATTCTGGCTGGACCCATGCCTGTCACACATGCCAGCGCTGCCCAGAGGAGGGGGCGCATAGGCAGGAATCCCAACAAACCTGGAGATGAGTATCTGTATGGAGGTGGGTGCGCAGAGACTGACGAAGACCATGCACACTGGCTTGAAGCAAGAATGCTCCTTGACAATATTTACCTCCAAGATGGCCTCATAGCCTCGCTCTATCGACCTGAGGCCGACAAAGTAGCAGCCATTGAGGGAGAGTTCAAGCTTAGGACGGAGCAAAGGAAGACCTTTGTGGAACTCATGAAAAGAGGAGATCTTCCTGTTTGGCTGGCCTATCAGGTTGCATCTGCCGGAATAACCTACACAGATAGAAGATGGTGCTTTGATGGCACGACCAACAACACCATAATGGAAGACAGTGTGCCGGCAGAGGTGTGGACCAGACACGGAGAGAAAAGAGTGCTCAAACCGAGGTGGATGGACGCCAGAGTTTGTTCAGATCATGCGGCCCTGAAGTCATTCAAGGAGTTTGCCGCTGGGAAAAGAGGAGCGGCTTTTGGAGTGATGGAAGCCCTGGGAACACTGCCAGGACACATGACAGAGAGATTCCAGGAAGCCATTGACAACCTCGCTGTGCTCATGCGGGCAGAGACTGGAAGCAGGCCTTACAAAGCCGCGGCGGCCCAATTGCCGGAGACCCTAGAGACCATTATGCTTTTGGGGTTGCTGGGAACAGTCTCGCTGGGAATCTTTTTCGTCTTGATGAGGAACAAGGGCATAGGGAAGATGGGCTTTGGAATGGTGACTCTTGGGGCCAGCGCATGGCTCATGTGGCTCTCGGAAATTGAGCCAGCCAGAATTGCATGTGTCCTCATTGTTGTGTTCCTATTGCTGGTGGTGCTCATACCTGAGCCAGAAAAGCAAAGATCTCCCCAGGACAACCAAATGGCAATCATCATCATGGTAGCAGTAGGTCTTCTGGGCTTGATTACCGCCAATGAACTCGGATGGTTGGAGAGAACAAAGAGTGACCTAAGCCATCTAATGGGAAGGAGAGAGGAGGGGGCAACCATAGGATTCTCAATGGACATTGACCTGCGGCCAGCCTCAGCTTGGGCCATCTATGCTGCCTTGACAACTTTCATTACCCCAGCCGTCCAACATGCAGTGACCACTTCATACAACAACTACTCCTTAATGGCGATGGCCACGCAAGCTGGAGTGTTGTTTGGTATGGGCAAAGGGATGCCATTCTACGCATGGGACTTTGGAGTCCCGCTGCTAATGATAGGTTGCTACTCACAATTAACACCCCTGACCCTAATAGTGGCCATCATTTTGCTCGTGGCGCACTACATGTACTTGATCCCAGGGCTGCAGGCAGCAGCTGCGCGTGCTGCCCAGAAGAGAACGGCAGCTGGCATCATGAAGAACCCTGTTGTGGATGGAATAGTGGTGACTGACATTGACACAATGACAATTGACCCCCAAGTGGAGAAAAAGATGGGACAGGTGCTACTCATAGCAGTAGCCGTCTCCAGCGCCATACTGTCGCGGACCGCCTGGGGGTGGGGGGAGGCTGGGGCCCTGATCACAGCGGCAACTTCCACTTTGTGGGAAGGCTCTCCGAACAAGTACTGGAACTCCTCTACAGCCACTTCACTGTGTAACATTTTTAGGGGAAGTTACTTGGCTGGAGCTTCTCTAATCTACACAGTAACAAGAAACGCTGGCTTGGTCAAGAGACGTGGGGGTGGAACAGGAGAGACCCTGGGAGAGAAATGGAAGGCCCGCTTGAACCAGATGTCGGCCCTGGAGTTCTACTCCTACAAAAAGTCAGGCATCACCGAGGTGTGCAGAGAAGAGGCCCGCCGCGCCCTCAAGGACGGTGTGGCAACGGGAGGCCATGCTGTGTCCCGAGGAAGTGCAAAGCTGAGATGGTTGGTGGAGCGGGGATACCTGCAGCCCTATGGAAAGGTCATTGATCTTGGATGTGGCAGAGGGGGCTGGAGTTACTACGCCGCCACCATCCGCAAAGTTCAAGAAGTGAAAGGATACACAAAAGGAGGCCCTGGTCATGAAGAACCCATGTTGGTGCAAAGCTATGGGTGGAACATAGTCCGTCTTAAGAGTGGGGTGGACGTCTTTCATATGGCGGCTGAGCCGTGTGACACGTTGCTGTGTGACATAGGTGAGTCATCATCTAGTCCTGAAGTGGAAGAAGCACGGACGCTCAGAGTCCTCTCCATGGTGGGGGATTGGCTTGAAAAAAGACCAGGAGCCTTTTGTATAAAAGTGTTGTGCCCATACACCAGCACTATGATGGAAACCCTGGAGCGACTGCAGCGTAGGTATGGGGGAGGACTGGTCAGAGTGCCACTCTCCCGCAACTCTACACATGAGATGTACTGGGTCTCTGGAGCGAAAAGCAACACCATAAAAAGTGTGTCCACCACGAGCCAGCTCCTCTTGGGGCGCATGGACGGGCCCAGGAGGCCAGTGAAATATGAGGAGGATGTGAATCTCGGCTCTGGCACGCGGGCTGTGGTAAGCTGCGCTGAAGCTCCCAACATGAAGATCATTGGTAACCGCATTGAAAGGATCCGCAGTGAGCACGCGGAAACGTGGTTCTTTGACGAGAACCACCCATATAGGACATGGGCTTACCATGGAAGCTATGAGGCCCCCACACAAGGGTCAGCGTCCTCTCTAATAAACGGGGTTGTCAGGCTCCTGTCAAAACCCTGGGATGTGGTGACTGGAGTCACAGGAATAGCCATGACCGACACCACACCGTATGGTCAGCAAAGAGTTTTCAAGGAAAAAGTGGACACTAGGGTGCCAGACCCCCAAGAAGGCACTCGTCAGGTTATGAGCATGGTCTCTTCCTGGTTGTGGAAAGAGCTAGGCAAACACAAACGGCCACGAGTCTGTACCAAAGAAGAGTTCATCAACAAGGTTCGTAGCAATGCAGCATTAGGGGCAATATTTGAAGAGGAAAAAGAGTGGAAGACTGCAGTGGAAGCTGTGAACGATCCAAGGTTCTGGGCTCTAGTGGACAAGGAAAGAGAGCACCACCTGAGAGGAGAGTGCCAGAGTTGTGTGTACAACATGATGGGAAAAAGAGAAAAGAAACAAGGGGAATTTGGAAAGGCCAAGGGCAGCCGCGCCATCTGGTATATGTGGCTAGGGGCTAGATTTCTAGAGTTCGAAGCCCTTGGATTCTTGAACGAGGATCACTGGATGGGGAGAGAGAACTCAGGAGGTGGTGTTGAAGGGCTGGGATTACAAAGACTCGGATATGTCCTAGAAGAGATGAGTCGCATACCAGGAGGAAGGATGTATGCAGATGACACTGCTGGCTGGGACACCCGCATCAGCAGGTTTGATCTGGAGAATGAAGCTCTAATCACCAACCAAATGGAGAAAGGGCACAGGGCCTTGGCATTGGCCATAATCAAGTACACATACCAAAACAAAGTGGTAAAGGTCCTTAGACCAGCTGAAAAAGGGAAGACAGTTATGGACATTATTTCGAGACAAGACCAAAGGGGGAGCGGACAAGTTGTCACTTACGCTCTTAACACATTTACCAACCTAGTGGTGCAACTCATTCGGAATATGGAGGCTGAGGAAGTTCTAGAGATGCAAGACTTGTGGCTGCTGCGGAGGTCAGAGAAAGTGACCAACTGGTTGCAGAGCAACGGATGGGATAGGCTCAAACGAATGGCAGTCAGTGGAGATGATTGCGTTGTGAAGCCAATTGATGATAGGTTTGCACATGCCCTCAGGTTCTTGAATGATATGGGAAAAGTTAGGAAGGACACACAAGAGTGGAAACCCTCAACTGGATGGGACAACTGGGAAGAAGTTCCGTTTTGCTCCCACCACTTCAACAAGCTCCATCTCAAGGACGGGAGGTCCATTGTGGTTCCCTGCCGCCACCAAGATGAACTGATTGGCCGGGCCCGCGTCTCTCCAGGGGCGGGATGGAGCATCCGGGAGACTGCTTGCCTAGCAAAATCATATGCGCAAATGTGGCAGCTCCTTTATTTCCACAGAAGGGACCTCCGACTGATGGCCAATGCCATTTGTTCATCTGTGCCAGTTGACTGGGTTCCAACTGGGAGAACTACCTGGTCAATCCATGGAAAGGGAGAATGGATGACCACTGAAGACATGCTTGTGGTGTGGAACAGAGTGTGGATTGAGGAGAACGACCACATGGAAGACAAGACCCCAGTTACGAAATGGACAGACATTCCCTATTTGGGAAAAAGGGAAGACTTGTGGTGTGGATCTCTCATAGGGCACAGACCGCGCACCACCTGGGCTGAGAACATTAAAAACACAGTCAACATGGTGCGCAGGATCATAGGTGATGAAGAAAAGTACATGGACTACCTATCCACCCAAGTTCGCTACTTGGGTGAAGAAGGGTCTACACCTGGAGTGCTGTAAGCACCAATCTTAGTGTTGTCAGGCCTGCTAGTCAGCCACAGCTTGGGGAAAGCTGTGCAGCCTGTGACCCCCCCAGGAGAAGCTGGGAAACCAAGCCTATAGTCAGGCCGAGAACGCCATGGCACGGAAGAAGCCATGCTGCCTGTGAGCCCCTCAGAGGACACTGAGTCAAAAAACCCCACGCGCTTGGAGGCGCAGGATGGGAAAAGAAGGTGGCGACCTTCCCCACCCTTCAATCTGGGGCCTGAACTGGAGATCAGCTGTGGATCTCCAGAAGAGGGACTAGTGGTTAGAGGAG',
		}

	def filter_outlier_strains(self):
		"""Remove single outlying viruses"""
		remove_viruses = []
		outlier_strains = ["VE_Ganxian", "THA/2014/SV0127_14", "SZ01/2016", "Dominican_Republic/2016/PD2", "MEX/InDRE/Lm/2016", "PLCal_ZV", "PAN/CDC_259364_V1_Vx/2015", "PAN/CDC_259249_V1_Vx/2015", "PAN/CDC_259359_V1_Vx/2015"]
		for outlier_strain in outlier_strains:
			for v in self.viruses:
				if (v['strain'] == outlier_strain):
					remove_viruses.append(v)
					if self.verbose > 1:
						print "\tremoving", v['strain']
		self.viruses = [v for v in self.viruses if v not in remove_viruses]

	def filter(self):
		print "Number of viruses before filtering:",len(self.viruses)	
		self.filter_length(self.min_length)
		print "Number of viruses after length filtering:",len(self.viruses)
#		self.filter_noncanoncial_nucleotides()
#		print "Number of viruses after filtering for noncanonical nucleotides:",len(self.viruses)		
		self.filter_unique()
		print "Number of viruses after filtering unique:",len(self.viruses)
		self.filter_outlier_strains()	
		print "Number of viruses after filtering outliers:",len(self.viruses)
		self.sort_length()
		regexp = re.compile(r'[A-Za-z]')
		for virus in self.viruses:
			if regexp.search(virus['strain']) is None:
				virus['strain'] = "V" + virus['strain']
		print "Number of viruses after filtering:",len(self.viruses)


class zika_clean(virus_clean):
	def __init__(self,**kwargs):
		virus_clean.__init__(self, **kwargs)

	def clean(self):
		self.unique_date()	
		self.remove_insertions()
		self.clean_ambiguous()
		print "Number of viruses after cleaning:",len(self.viruses)

class zika_refine(tree_refine):
	def refine(self):
		from Bio.SeqRecord import SeqRecord
		self.node_lookup = {node.taxon.label:node for node in self.tree.leaf_iter()}
		self.node_lookup.update({node.taxon.label.lower():node for node in self.tree.leaf_iter()})
		self.node_lookup.update({node.taxon.label.upper():node for node in self.tree.leaf_iter()})

		self.collapse()
		self.ladderize()
		self.add_node_attributes()
		self.add_nuc_mutations()
		if self.cds is not None:
			self.translate_all()
		self.reduce()
		self.layout()

		tmp_nucseqs = [SeqRecord(Seq(node.seq), id=node.strain, 
					  annotations = {'num_date':node.num_date, 'region':node.region}) 
					  for node in self.tree.leaf_iter()]
		tmp_nucseqs.sort(key = lambda x:x.annotations['num_date'])
		self.nuc_aln = MultipleSeqAlignment(tmp_nucseqs)

class zika_process(process, zika_filter, zika_clean, zika_refine):
	"""docstring for zika, """
	def __init__(self,verbose = 0, force_include = None, 
				force_include_all = False, max_global= True, **kwargs):
		self.force_include = force_include
		self.force_include_all = force_include_all
		self.max_global = max_global
		process.__init__(self, **kwargs)
		zika_filter.__init__(self,**kwargs)
		zika_clean.__init__(self,**kwargs)
		zika_refine.__init__(self,**kwargs)
		self.verbose = verbose

	def run(self, steps, viruses_per_month=50, raxml_time_limit = 1.0):
		if 'filter' in steps:
			print "--- Virus filtering at " + time.strftime("%H:%M:%S") + " ---"
			self.filter()
			self.dump()
		else:
			self.load()
		if 'align' in steps:
			self.align()   	# -> self.viruses is an alignment object
			self.dump()			
		if 'clean' in steps:
			print "--- Clean at " + time.strftime("%H:%M:%S") + " ---"
			self.clean()   # -> every node as a numerical date
			self.dump()
		if 'tree' in steps:
			print "--- Tree	 infer at " + time.strftime("%H:%M:%S") + " ---"
			self.infer_tree(raxml_time_limit)  # -> self has a tree
			self.dump()
		if 'ancestral' in steps:
			print "--- Infer ancestral sequences " + time.strftime("%H:%M:%S") + " ---"
			self.infer_ancestral()  # -> every node has a sequence
		if 'refine' in steps:
			print "--- Tree refine at " + time.strftime("%H:%M:%S") + " ---"
			self.refine()
			self.dump()
		if 'frequencies' in steps:
			print "--- Estimating frequencies at " + time.strftime("%H:%M:%S") + " ---"
			self.determine_variable_positions()
			#self.estimate_frequencies(tasks = ["mutations", "tree"])
			self.dump()
		if 'export' in steps:
			#self.temporal_regional_statistics()
			# exporting to json, including the H1N1pdm specific fields
			self.export_to_auspice(tree_fields = ['nuc_muts', 'accession', 'country', 'db', 'authors'], annotations = [])
			self.export_fasta_alignment()
			self.export_newick_tree()			
			#self.generate_indexHTML()

if __name__=="__main__":
	all_steps = ['filter', 'align', 'clean', 'tree', 'ancestral', 'refine', 'frequencies', 'export']
	from process import parser
	params = parser.parse_args()

	lt = time.localtime()
	num_date = round(lt.tm_year+(lt.tm_yday-1.0)/365.0,2)
	params.time_interval = (num_date-params.years_back, num_date) 
	if params.interval is not None and len(params.interval)==2 and params.interval[0]<params.interval[1]:
		params.time_interval = (params.interval[0], params.interval[1])
	dt= params.time_interval[1]-params.time_interval[0]
	params.pivots_per_year = 12.0 if dt<5 else 6.0 if dt<10 else 3.0
	steps = all_steps[all_steps.index(params.start):(all_steps.index(params.stop)+1)]
	if params.skip is not None:
		for tmp_step in params.skip:
			if tmp_step in steps:
				print "skipping",tmp_step
				steps.remove(tmp_step)

	# add all arguments to virus_config (possibly overriding)
	virus_config.update(params.__dict__)
	# pass all these arguments to the processor: will be passed down as kwargs through all classes
	zika = zika_process(**virus_config) 
	if params.test:
		zika.load()
	else:
		zika.run(steps,viruses_per_month = virus_config['viruses_per_month'], 
			raxml_time_limit = virus_config['raxml_time_limit'])
