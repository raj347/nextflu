import time, re, os
from virus_filter import flu_filter
from virus_clean import virus_clean
from tree_refine import tree_refine
from H3N2_process import H3N2_refine as H5_refine
from process import process, virus_config
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.Align import MultipleSeqAlignment
import numpy as np
from itertools import izip

# numbering starting at methionine including the signal peptide
sp = 17
epitope_mask = np.array(['1' if pos in []
						else '0' for pos in xrange(1,1725)])

receptor_binding_sites = [x-1 for x in []]


virus_config.update({
	# data source and sequence parsing/cleaning/processing
	'virus':'H5',
	'auspice_prefix':'H5',
	'fasta_fields':{0:'strain', 1:'isolate_id',2:'na', 3:'passage', 5:'date', 7:'lab', 8:"accession"},
	'alignment_file':'data/H5_gisaid_epiflu_sequence.fasta',
	'outgroup':'A/HongKong/156/97',
	#'force_include':'source-data/HI_strains.txt',
	'force_include_all':False,
	'max_global':True,   # sample as evenly as possible from different geographic regions 
	'cds':[0,None], # define the HA start i n 0 numbering
	# define relevant clades in canonical HA1 numbering (+1)
	# numbering starting at methionine including the signal peptide
	'clade_designations': {},
	'n_iqd':10,
	'min_mutation_frequency':0.45,
	'html_vars': {'coloring': 'host, na, lbi, dfreq, region, date',
				  'gtplaceholder': 'HA1 positions...',
				  'freqdefault': ''},
	'js_vars': {'LBItau': 0.0005, 'LBItime_window': 0.5, 'dfreq_dn':2},
	})


class H5_filter(flu_filter):
	def __init__(self,min_length = 987, **kwargs):
		'''
		parameters
		min_length  -- minimal length for a sequence to be acceptable
		'''
		flu_filter.__init__(self, **kwargs)
		self.min_length = min_length
		self.vaccine_strains =[]
		self.outgroup = {
			'strain': 'A/HongKong/156/97',
			'db': 'GISAID',
			'date': '1997-07-01',
			'country': 'HongKong',
			'region': 'China',
			'seq': 'GATCAGATTTGCATTGGTTACCATGCAAACAACTCGACAGAGCAGGTTGACACAATAATGGAAAAGAATGTTACTGTTACACATGCCCAAGACATACTGGAAAGGACACACAACGGGAAGCTCTGCGATCTAAATGGAGTGAAGCCTCTCATTTTGAGGGATTGTAGTGTAGCTGGATGGCTCCTCGGAAACCCTATGTGTGACGAATTCATCAATGTGCCGGAATGGTCTTACATAGTGGAGAAGGCCAGTCCAGCCAATGACCTCTGTTATCCAGGGAATTTCAACGACTATGAAGAACTGAAACACCTATTGAGCAGAATAAACCATTTTGAGAAAATTCAGATCATCCCCAAAAGTTCTTGGTCCAATCATGATGCCTCATCAGGGGTGAGCTCAGCATGTCCATACCTTGGGAGGTCCTCCTTTTTCAGAAATGTGGTATGGCTTATCAAAAAGAACAGTGCATACCCAACAATAAAGAGGAGCTACAATAATACCAACCAAGAAGATCTTTTGGTACTGTGGGGGATTCACCATCCTAATGATGCGGCAGAGCAGACAAAGCTCTATCAAAATCCAACCACCTACATTTCCGTTGGAACATCAACACTGAACCAGAGATTGGTTCCAGAAATAGCTACTAGACCCAAAGTAAACGGGCAAAGTGGAAGAATGGAGTTCTTCTGGACAATTTTAAAGCCGAATGATGCCATCAATTTCGAGAGTAATGGAAATTTCATTGCTCCAGAATATGCATACAAAATTGTCAAGAAAGGGGACTCAACAATTATGAAAAGTGAATTGGAATATGGTAACTGCAACACCAAGTGTCAAACTCCAATGGGGGCGATAAACTCTAGTATGCCATTCCACAACATACACCCCCTCACCATCGGGGAATGCCCCAAATATGTGAAATCAAACAGATTAGTCCTTGCGACTGGACTCAGAAATACCCCTCAAAGAGAGAGAAGAAGAAAAAAGAGAGGACTATTTGGAGCTATAGCAGGTTTTATAGAGGGAGGATGGCAGGGAATGGTAGATGGTTGGTATGGGTACCACCATAGCAATGAGCAGGGGAGTGGATACGCTGCAGACAAAGAATCCACTCAAAAGGCAATAGATGGAGTCACCAATAAGGTCAACTCGATCATTAACAAAATGAACACTCAGTTTGAGGCCGTTGGAAGGGAATTTAATAACTTGGAAAGGAGGATAGAGAATTTAAACAAGAAGATGGAAGACGGATTCCTAGATGTCTGGACTTACAATGCTGAACTTCTGGTTCTCATGGAAAATGAGAGAACTCTCGACTTTCATGACTCAAATGTCAAGAACCTTTACGACAAGGTCCGACTACAGCTTAGGGATAATGCAAAGGAGCTGGGTAATGGTTGTTTCGAATTCTATCACAAATGTGATAATGAATGTATGGAAAGTGTAAAAAACGGAACGTATGACTACCCGCAGTATTCAGAAGAAGCAAGACTAAACAGAGAGGAAATAAGTGGAGTAAAATTGGAATCAATGGGAACTTACCAAATACTGTCAATTTATTCAACAGTGGCGAGTTCCCTAGCACTGGCAATCATGGTAGCTGGTCTATCTTTATGGATGTGCTCCAATGGATCGTTACAATGCAGAATTTGCATTTAAATTTGTGAGTTCAGATTGTAGTTAAAAACAC',
		}
	def filter(self):
		self.filter_generic(prepend_strains = self.vaccine_strains)	
		self.filter_strain_names()
		print len(self.viruses), "with proper strain names"
		self.filter_passage()
		print len(self.viruses), "without egg passage"
		self.filter_geo(field=2, prune=False)
		self.filter_geo(field=1, prune=False) # redo geo parsing with field one for human strains
		print len(self.viruses), "with geographic information"
		self.filter_host(prune=False)
		print len(self.viruses), "with host information"
		for v in self.viruses:
			v['na'] = v['na'].split('/')[-1].strip()

	def filter_host(self,prune=True, field=1):
		from csv import DictReader
		reader = DictReader(open("source-data/host_synonyms.tsv"), delimiter='\t')		# list of dicts
		label_to_animal = {}
		for line in reader:
			label_to_animal[line['label'].lower()] = line['animal']
		for v in self.viruses:
			v['host'] = 'Unknown'
			try:
				label = re.match(r'^[AB]/([^/]+)/', v['strain']).group(field).lower()	# check first for whole geo match
				if label in label_to_animal:
					v['host'] = label_to_animal[label]
				else:
					label = re.match(r'^[AB]/([^\-^\/]+)[\-\/]', v['strain']).group(field).lower()		# check for partial geo match
					if label in label_to_animal:
						v['host'] = label_to_animal[label]
				if v['host'] == 'Unknown':
					print "couldn't parse host for", v['strain']
			except:
				print "couldn't parse", v['strain']

		reader = DictReader(open("source-data/host_animal_groups.tsv"), delimiter='\t')		# list of dicts
		animal_to_group = {}
		for line in reader:
			animal_to_group[line['animal']] = line['group']
		for v in self.viruses:
			v['group'] = 'Unknown'
			if v['host'] in animal_to_group:
				v['group'] = animal_to_group[v['host']]
			if v['host'] != 'Unknown' and v['group'] == 'Unknown':
				print "couldn't parse group for", v['strain'], "animal:", v["host"]		
		
		if prune:
			self.viruses = filter(lambda v: v['group'] != 'Unknown', self.viruses)



class H5_clean(virus_clean):
	def __init__(self,**kwargs):
		virus_clean.__init__(self, **kwargs)

	def clean_outbreaks(self):
		"""Remove duplicate strains, where the geographic location, date of sampling and sequence are identical"""
		virus_hashes = set()
		new_viruses = []
		for v in self.viruses:
			geo = re.search(r'A/([^/]+)/', v.strain).group(1)
			if geo:
				vhash = (geo, v.date, str(v.seq))
				if vhash not in virus_hashes:
					new_viruses.append(v)
					virus_hashes.add(vhash)

		self.viruses = MultipleSeqAlignment(new_viruses)
		return new_viruses

	def clean(self):
		self.clean_generic()
		print "Number of viruses after outbreak filtering:",len(self.viruses)

class H5_process(process, H5_filter, H5_clean, H5_refine):
	"""docstring for H5_process, H5_filter"""
	def __init__(self,verbose = 0, force_include = None, 
				force_include_all = False, max_global= True, **kwargs):
		self.force_include = force_include
		self.force_include_all = force_include_all
		self.max_global = max_global
		process.__init__(self, **kwargs)
		H5_filter.__init__(self,**kwargs)
		H5_clean.__init__(self,**kwargs)
		H5_refine.__init__(self,**kwargs)
		self.verbose = verbose

	def run(self, steps, viruses_per_month=50, raxml_time_limit = 1.0):
		if 'filter' in steps:
			print "--- Virus filtering at " + time.strftime("%H:%M:%S") + " ---"
			self.filter()
			if self.force_include is not None and os.path.isfile(self.force_include):
				with open(self.force_include) as infile:
					forced_strains = [line.strip().lower() for line in infile]
			else:
				forced_strains = []
			self.subsample(viruses_per_month, 
				prioritize=forced_strains, all_priority=self.force_include_all, 
				region_specific = self.max_global)
			self.dump()
		else:
			self.load()
		if 'align' in steps:
			self.align()   	# -> self.viruses is an alignment object
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
			self.estimate_frequencies(tasks = ["mutations", "clades", "tree"])
			if 'genotype_frequencies' in steps: 
					self.estimate_frequencies(tasks = ["genotypes"])
			self.dump()
		if 'export' in steps:
			self.temporal_regional_statistics()
			# exporting to json, including the H5 specific fields
			self.export_to_auspice(tree_fields = ['host', 'group', 'na', 'aa_muts','accession','isolate_id', 'lab','db', 'country'], 
			                       annotations = [])
			self.generate_indexHTML()

if __name__=="__main__":
	all_steps = ['filter', 'align', 'clean', 'tree', 'ancestral', 'refine', 'frequencies','genotype_frequencies', 'export']
	from process import parser, shift_cds
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

	# modify clade designations
	if not params.ATG:
		virus_config, epitope_mask, receptor_binding_sites = shift_cds(3*sp, virus_config, epitope_mask, receptor_binding_sites)

	# add all arguments to virus_config (possibly overriding)
	virus_config.update(params.__dict__)
	# pass all these arguments to the processor: will be passed down as kwargs through all classes
	myH5 = H5_process(**virus_config) 
	if params.test:
		myH5.load()
	else:
		myH5.run(steps,viruses_per_month = virus_config['viruses_per_month'], 
			raxml_time_limit = virus_config['raxml_time_limit'])