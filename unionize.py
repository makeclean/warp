try:
	import ace
	ace_available = True
except ImportError:
	from pyne import ace
	ace_available = False
import numpy
import sys
import glob
#import pylab
import re

##
#  \class cross_section_data
#  \brief handles cross section data

class cross_section_data:

	##
	# \brief cross section data class to hold it all together with the functions necessary for WARP
	# \details initializes number of isotopes to zero; isotope list as an empty
	# array; temperature extension as '.03c'; tables, libraries, AWR list, and Q
	# as empty arrays; main energy as zero; reaction numbers and total reaction
	# numbers as empty arrays; number of reactions to zero. sets the MT energy grid	       # and array as empty. 
	# @param[in] self - this cross_section_data object
	def __init__(self):
		## number of isotopes
		self.num_isotopes     = 0
		## isotope list
		self.isotope_list     = []
		## data path
		self.datapath         = ''
		## cross section tables
		self.tables           = []
		## cross section libraries
		self.libraries        = {}
		## AWR array
		self.awr 	      = []
		## temp array
		self.temp 	      = []
		## Q-value array
		self.Q 		      = []
		## main energy
		self.num_main_E	      = 0
		## reaction numbers array
		self.reaction_numbers = []
		## total reaction numbers array
		self.reaction_numbers_total = []
		## number of reactions
		self.num_reactions    = 0
		## MT energy grid
		self.MT_E_grid        = numpy.array([],dtype=numpy.float32,order='C')
		## MT number array
		self.MT_array	      = numpy.array([],dtype=numpy.float32,order='C')
		## Last valid table loaded 
		self.last_loaded 	 = 0
		## isotropic tolerance
		self.isotropic_tol = 1e-5

	##
	# \brief initializes material from isotope list string
	# @param[in] self - this cross_section_data object
	# @param[in] this_string - comma-separated isotope list
	def _init_from_string(self,this_string):
		self.isotope_list = this_string.split(',')

	##
	# \brief appends the input isotope the the input material's list of isotopes
	# @param[in] self - this cross_section_data object
	# @param[in] isotope - isotope to be appended
	def _add_isotope(self,  isotope):
		self.isotope_list.append(isotope)
	##
	# \brief reads in cross section tables
	# \details for each isotope in the material, the acefile is appended to the 
	# library list, then all of the libraries are read in. the material's number
	# of isotopes is set to how many libraries were retrieved.
	# @param[in] self - this cross_section_data object
	# @param[in] datapath_in - the input datapath for the xs data
	def _read_tables(self, datapath_in):

		self.datapath = datapath_in

		print "  ----------- data paths ------------ "
		try:
			if re.search('xsdir',self.datapath):   #path is a xsdir file, don't append xsdir
				f=open(self.datapath,'r')
				firstline=f.readline()
				match = re.match('(datapath=)*(/[a-zA-Z0-9/_.+-]+)',firstline,re.IGNORECASE)  #datapath is specified, use it.
				if match:
					print "  USING DATAPATH '"+match.group(2)+"' as specified in '"+self.datapath+"'."
					self.datapath=match.group(2)
				else:
					print "  NO DATAPATH specified in '"+self.datapath+"', assuming full path specified."
					self.datapath=''
			else:
				f=open(self.datapath+'/xsdir','r')
				print "  using xsdir in '"+self.datapath+"'."
		except :
			print "!  unable to open '"+self.datapath+"[/xsdir]'!"
			exit(0)

                #self.datapath = "/home/dc-davi4/xsdata/ENDF-B-VII.1-neutron-293.6K/"
                self.datapath = "/home/dc-davi4/xsdata/endfvi/"
		self.xsdirstring=f.read()
		f.close()

		self.num_isotopes = 0

		#  make map of file -> isotop
		for tope in self.isotope_list:
			librarypath = self._resolve_library(tope)
                        print librarypath 
			if librarypath in self.libraries:
				self.libraries[librarypath].append(tope)
			else:
				self.libraries[librarypath]=[tope]

		# open the libraries, read all isotopes present in that library
		print "  ---------  loading data  ---------- "
		lib={}
                print librarypath
		for librarypath in self.libraries:
			print "  loading "+librarypath
			lib[librarypath] = ace.Library(librarypath)
			print librarypath
			lib[librarypath].read()

		print "  --------- extracting data --------- "

		# preserve list order!
		for tope in self.isotope_list:
			librarypath = self._resolve_library(tope)
			print "  extracting "+tope+' from '+librarypath
			self.tables.append(lib[librarypath].find_table(tope))
			self.num_isotopes=self.num_isotopes+1

	##
	# \brief finds path the isotope files
	# \details finds the relative path from DATAPATH to a file that contains 
	# the specified isotope cross sections.  It reads the xsdir file to do this.
	# @param[in] self - this cross_section_data object
	# @param[in] tope - isotope to seach for 
	def _resolve_library(self,tope):
		exp = re.compile(tope+" +[0-9. a-z]+ ([a-zA-Z0-9/_.+-]+)")
		a = exp.search(self.xsdirstring)
               
		if a:
			if self.datapath != "" :
				return self.datapath+'/'+a.group(1)
			else:
				return a.group(1)
		else:
			print " ERROR: nuclide '"+tope+"' not found in '"+self.datapath+"/xsdir'!"
			#exit(0)
			return 0


	##
	# \brief unionization function
	# \details unionizes MT energy grid.
	# @param[in] self - this cross_section_data object
	def _unionize(self):

		print "  --------- unionizing grid --------- "

		for table in self.tables:
			# main xs
			self.MT_E_grid=numpy.union1d(self.MT_E_grid,table.energy)
			# nu if present
			if hasattr(table,"nu_t_energy"):
				self.MT_E_grid=numpy.union1d(self.MT_E_grid,table.nu_t_energy)
			if hasattr(table,"nu_d_energy"):
				self.MT_E_grid=numpy.union1d(self.MT_E_grid,table.nu_d_energy)
			if hasattr(table,"nu_p_energy"):
				self.MT_E_grid=numpy.union1d(self.MT_E_grid,table.nu_p_energy)
			# unionize the scattering energies in as well!  if present of course
			for MT in table.reactions:
				rxn = table.reactions[MT]
				if hasattr(rxn,"ang_energy_in"):
					self.MT_E_grid=numpy.union1d(self.MT_E_grid,rxn.ang_energy_in)
				if hasattr(rxn,"energy_dist"):# and rxn.energy_dist.law!=3 and rxn.energy_dist.law!=66:
					if hasattr(rxn.energy_dist,"energy_in"):
						self.MT_E_grid=numpy.union1d(self.MT_E_grid,rxn.energy_dist.energy_in)
					if hasattr(rxn.energy_dist,"energya_in"):
						self.MT_E_grid=numpy.union1d(self.MT_E_grid,rxn.energy_dist.energya_in)
					if hasattr(rxn.energy_dist,"energyb_in"):
						self.MT_E_grid=numpy.union1d(self.MT_E_grid,rxn.energy_dist.energyb_in)
                        print table.reactions.keys()
                        print table.reactions[2].ang_energy_in

		self.num_main_E   = self.MT_E_grid.__len__()
		print "  -------------- done --------------- "

		#print self.MT_E_grid.shape
		#print self.MT_E_grid

	##
	# \brief insert reactions function
	# \details appends ones to the front, appends the isotope's AWR to the table,
	# appends the isotope's total reaction numbers to the table. appends all 
	# reaction numbers to the reaction list.
	# @param[in] self - this cross_section_data object
	def _insert_reactions(self):
		
		for table in self.tables:
			#append ones to front
			self.reaction_numbers.append(1)
			self.Q.append(0)
			#append this topes AWR
			self.awr.append(table.awr)
			#append this topes temp
			self.temp.append(table.temp)

		#append reaction numbers
		for table in self.tables:
			total_good_reactions = 0
			for MT in table.reactions: # reactions is a dict
				if MT <200 and MT!=3 and MT!=4 and MT!=5 and MT!=10 and MT!=27:
					rxn = table.reactions[MT]
					self.reaction_numbers.append(MT)
					self.Q.append(rxn.Q)
					self.num_reactions += 1
					total_good_reactions += 1
			#append totals
			self.reaction_numbers_total.append(total_good_reactions)

		#print self.num_reactions
		#print self.reaction_numbers
		#print self.Q
		#print self.reaction_numbers_total

	##
	# \brief array allocation function
	# \details allocates a 2D array of size number of all reactions x number of
	# energy points
	# @param[in] self - this cross_section_data object
	def _allocate_arrays(self):

		n_columns  = self.num_isotopes + self.num_reactions  # totals + ( all other reactions (elastic scatter included) )
		n_rows     = self.num_main_E

		self.MT_array  = numpy.zeros((n_rows,n_columns),dtype=float,order='C')

	##
	# \brief interpolation function
	# \details linearly interpolates the cross sections for each isotope in a 
	# material
	# @param[in] self - this cross_section_data object
	def _interpolate(self):

		tope_index  = 0
		MT_array_dex  = self.num_isotopes  #(total xs block + any previous reaction blocks)

		for table in self.tables:

			#print "interpolating isotope "+str(tope_index), self.isotope_list[tope_index], table.name
			#print "grid length =",len(table.energy)

			#do this isotopes entry in the total block
			this_array = numpy.interp( self.MT_E_grid, table.energy, table.sigma_t , left=0.0 )
			self.MT_array[:,tope_index]=this_array

			for MT in table.reactions:
				if MT <200 and MT!=3 and MT!=4 and MT!=5 and MT!=10 and MT!=27:
					rxn        = table.reactions[MT]
					#if rxn.IE>0:
					#	IE = rxn.IE-1       #convert form fortran to python/C indexing 
					#else:
					IE = rxn.IE # in post 9/2014 pyne, -1 is already done?
					#print MT, IE
					#print table.energy[IE:]
					#print rxn.sigma
					#if hasattr(rxn,'ang_energy_in'): 
					#	print rxn.ang_energy_in
					#else:
					#	print "no angular"
					#print rxn.threshold()
					#print len(table.energy[IE:]), len(rxn.sigma)
					this_array = numpy.interp( self.MT_E_grid, table.energy[IE:], rxn.sigma , left=0.0 )  #interpolate MT cross section, left means xs below 	threshold is 0
					self.MT_array[:,MT_array_dex] = this_array  # insert into the MT array
                                        print MT 
                                        print this_array
					#  this MT is done, increment counter
					MT_array_dex = MT_array_dex +1

			#this isotope is done, increment counter
			tope_index  = tope_index+1

	##
	# \brief gets pointer to MT numbers
	# @param[in] self - this cross_section_data object
	# \returns MT_num_array - array of MT numbers
	def _get_MT_numbers_pointer(self):
		MT_num_array = numpy.ascontiguousarray(numpy.array(self.reaction_numbers,order='C'),dtype=numpy.uint32)
		# shift elastic to 49, fission +800, shift captures +1000
		for n in range(0,len(MT_num_array)):
			if MT_num_array[n] == 2:
				MT_num_array[n] = 50
			elif (MT_num_array[n] >= 18 and MT_num_array[n] <= 21) or MT_num_array[n] == 38 :
				MT_num_array[n] = MT_num_array[n]+800
			elif MT_num_array[n] > 100:
				MT_num_array[n] = MT_num_array[n]+1000
		print "  ----- MT reaction number list ----- "
		print MT_num_array
		#print len(MT_num_array)
		return MT_num_array

	##
	# \brief gets pointer to AWR values
	# @param[in] self - this cross_section_data object
	# \returns AWR_array - array of AWR values
	def _get_awr_pointer(self):
		awr_array = numpy.ascontiguousarray(numpy.array(self.awr,order='C'),dtype=numpy.float32)
		return awr_array

	##
	# \brief gets pointer to temperature values
	# @param[in] self - this cross_section_data object
	# \returns temp_array - array of temperature values
	def _get_temp_pointer(self):
		temp_array = numpy.ascontiguousarray(numpy.array(self.temp,order='C'),dtype=numpy.float32)
		return temp_array

	##
	# \brief gets pointer to Q-values
	# @param[in] self - this cross_section_data object
	# \returns Q_array - array of Q-values
	def _get_Q_pointer(self):
		Q_array = numpy.ascontiguousarray(numpy.array(self.Q,order='C'),dtype=numpy.float32)
		return Q_array

	##
	# \brief gets pointer to MT numbers
	# @param[in] self - this cross_section_data object
	# \returns MT_array - array of MT numbers
	def _get_MT_array_pointer(self):
		self.MT_array = numpy.ascontiguousarray(self.MT_array,dtype=numpy.float32)
		return self.MT_array

	##
	# \brief gets pointer to main energy grid
	# @param[in] self - this cross_section_data object
	# \returns E_grid - array of energy grid points
	def _get_main_Egrid_pointer(self):
		E_grid = numpy.ascontiguousarray(self.MT_E_grid,dtype=numpy.float32)
		return E_grid

	##
	# \brief creates array of size number of isotopes + main energy grid + number 
	# of reactions
	# @param[in] self - this cross_section_data object
	# \returns lengths - lengths array
	def _get_length_numbers_pointer(self):
		lengths = numpy.ascontiguousarray( numpy.array([self.num_isotopes, self.num_main_E, self.num_reactions], order='C') ,dtype=numpy.uint32)
		#print lengths
		return lengths

	##
	# \brief gets pointer to total MT numbers
	# @param[in] self - this cross_section_data object
	# \returns numbers - array of total MT numbers
	def _get_MT_numbers_total_pointer(self):
		numbers = numpy.array(self.reaction_numbers_total,order='C')
		numbers = numpy.cumsum(numbers)
		numbers = numpy.insert(numbers,0,0)
		numbers = numpy.ascontiguousarray(numbers,dtype=numpy.uint32)
		#print numbers
		return numbers

	##
	# \brief prints list of isotopes in a material
	# @param[in] self - material for which to print isotope list
	def _print_isotopes(self):
		for tope in self.isotope_list:
			print tope
	##
	# \brief gets table of scattering data
	# \details if scattering data exists, table returned in form of [nextDex,
	# length, mu, cdf]
	# @param[in] self - this cross_section_data object
	# @param[in] row - point in energy grid
	# @param[in] col - MT number
	def _get_scatter_data(self,row,col):
		# scatter table returned in this form
		# returns [nextDex, length, mu, cdf] if scattering data exists

		#find the isotope we are in
		numbers = numpy.cumsum(self.reaction_numbers_total)  #list of how many reactions in each isotope
		isotope = numpy.argmax( (col - self.num_isotopes) < numbers )
		table = self.tables[isotope]
		MTnum = self.reaction_numbers[col]
		rxn   = table.reactions[MTnum]

		# get the energy of this index
		this_E = self.MT_E_grid[row]

		#print MTnum

		# do the cases
		if hasattr(table,"nu_t_energy") and rxn.multiplicity>10:
			# this is a fission reaction
			# scattering dist is actually nu + precursor energy distributions

			# find indicies
			nu_t_upper_index = next((i for i, x in enumerate(this_E < table.nu_t_energy) if x), None)
			nu_d_upper_index = next((i for i, x in enumerate(this_E < table.nu_d_energy) if x), None)

			# if above upper nu grid value
			if  nu_t_upper_index == None:
				nu_t_upper_index = len(table.nu_t_energy)-1
				nu_t_lower_index = len(table.nu_t_energy)-1
				above_last_t = True
			else:
				nu_t_lower_index = nu_t_upper_index - 1
				above_last_t = False

			if  nu_d_upper_index == None:
				nu_d_upper_index = len(table.nu_d_energy)-1
				nu_d_lower_index = len(table.nu_d_energy)-1
				above_last_d = True
			else:
				nu_d_lower_index = nu_d_upper_index - 1
				above_last_d = False

			# make sure above threshold
			if nu_t_lower_index < 0:

				# set all to zero
				lower_law	= 0
				upper_law	= 0
				lower_intt	= 0
				upper_intt	= 0
				lower_erg	= 0
				upper_erg	= 0
				lower_len	= 0
				upper_len	= 0
				lower_var 	= numpy.array([0.0])
				upper_var 	= numpy.array([0.0])
				lower_pdf 	= numpy.array([0.0])
				upper_pdf 	= numpy.array([0.0])
				lower_cdf 	= numpy.array([0.0])
				upper_cdf 	= numpy.array([0.0])

				# next index
				threshold = numpy.max([rxn.threshold(),table.nu_t_energy[0]])
				next_dex = next((i for i, x in enumerate(threshold <= self.MT_E_grid) if x), None)
				
			else:

				# get upper/lower grid values
				lower_nu_t_grid	= table.nu_t_value[ nu_t_lower_index]
				lower_nu_d_grid	= table.nu_d_value[ nu_d_lower_index]
				upper_nu_t_grid	= table.nu_t_value[ nu_t_upper_index]
				upper_nu_d_grid	= table.nu_d_value[ nu_d_upper_index]
				lower_e_t		= table.nu_t_energy[nu_t_lower_index]
				lower_e_d		= table.nu_d_energy[nu_d_lower_index]
				upper_e_t		= table.nu_t_energy[nu_t_upper_index]
				upper_e_d		= table.nu_d_energy[nu_d_upper_index]

				# get intts
				if numpy.isscalar(table.nu_p_interp_INT):
					lower_nu_d_intt = table.nu_p_interp_INT
					upper_nu_d_intt = table.nu_p_interp_INT
				else:
					lower_nu_d_intt = table.nu_p_interp_INT[nu_d_lower_index]
					upper_nu_d_intt = table.nu_p_interp_INT[nu_d_upper_index]
				if numpy.isscalar(table.nu_t_interp_INT):
					lower_nu_t_intt = table.nu_t_interp_INT
					upper_nu_t_intt = table.nu_t_interp_INT
				else:
					lower_nu_t_intt = table.nu_t_interp_INT[nu_p_lower_index]
					upper_nu_t_intt = table.nu_t_interp_INT[nu_p_upper_index]
				lower_pre_intt = table.nu_d_energy_dist[0].intt[0]
				upper_pre_intt = table.nu_d_energy_dist[0].intt[1]
				lower_pre_law  = table.nu_d_energy_dist[0].law
				upper_pre_law  = table.nu_d_energy_dist[0].law  

				# set values in vars
				lower_law	= -1
				upper_law	= -1
				lower_intt	= lower_nu_t_intt + lower_nu_d_intt*10 + lower_pre_intt*100 + lower_pre_law*1000  # encode intts and laws, assuming no difference between dists
				upper_intt	= upper_nu_t_intt + upper_nu_d_intt*10 + upper_pre_intt*100 + upper_pre_law*1000  # encode intts and laws, assuming no difference between dists
				lower_erg	= max(lower_e_t,lower_e_d)  # take narrowest interval
				upper_erg	= min(upper_e_t,upper_e_d)  # take narrowest interval
				
				# evaluate nu on this interval 
				if above_last_t:
					lower_nu_t	= upper_nu_t_grid
					upper_nu_t	= upper_nu_t_grid
				else:
					lower_nu_t	= lower_nu_t_grid + (lower_erg - lower_e_t)/(upper_e_t - lower_e_t) * (upper_nu_t_grid - lower_nu_t_grid)
					upper_nu_t	= lower_nu_t_grid + (upper_erg - lower_e_t)/(upper_e_t - lower_e_t) * (upper_nu_t_grid - lower_nu_t_grid)
				if above_last_d:
					lower_nu_d	= upper_nu_d_grid
					upper_nu_d	= upper_nu_d_grid
				else:
					lower_nu_d	= lower_nu_d_grid + (lower_erg - lower_e_d)/(upper_e_d - lower_e_d) * (upper_nu_d_grid - lower_nu_d_grid)
					upper_nu_d	= lower_nu_d_grid + (upper_erg - lower_e_d)/(upper_e_d - lower_e_d) * (upper_nu_d_grid - lower_nu_d_grid)
				lower_len	= numpy.array([lower_nu_t,lower_nu_d])
				upper_len	= numpy.array([upper_nu_t,upper_nu_d])

				# mux vectors
				lower_var	= numpy.hstack((table.nu_d_precursor_prob[0][0],table.nu_d_precursor_prob[1][0],table.nu_d_precursor_prob[2][0],table.nu_d_precursor_prob[3][0],table.nu_d_precursor_prob[4][0],table.nu_d_precursor_prob[5][0])) # probabilities
				upper_var	= numpy.hstack((table.nu_d_precursor_prob[0][1],table.nu_d_precursor_prob[1][1],table.nu_d_precursor_prob[2][1],table.nu_d_precursor_prob[3][1],table.nu_d_precursor_prob[4][1],table.nu_d_precursor_prob[5][1])) # probabilities
				lower_var	= numpy.cumsum(lower_var) # given as individual, accumulate for ease
				upper_var	= numpy.cumsum(upper_var) # given as individual, accumulate for ease
				lower_cdf	= []
				upper_cdf	= []
				lower_pdf	= numpy.array([0])
				upper_pdf	= numpy.array([0])
				for i in range(0,len(table.nu_d_energy_dist)):
					lower_cdf 	= numpy.hstack((lower_cdf,table.nu_d_energy_dist[i].energy_out[0]))  # mux data, energy first
					upper_cdf 	= numpy.hstack((upper_cdf,table.nu_d_energy_dist[i].energy_out[1]))  # mux data, energy first
					lower_pdf 	= numpy.hstack((lower_pdf,len(lower_cdf)))  # compute muxed indicies
					upper_pdf 	= numpy.hstack((upper_pdf,len(upper_cdf)))  # compute muxed indicies
				for i in range(0,len(table.nu_d_energy_dist)):
					lower_cdf 	= numpy.hstack((lower_cdf,table.nu_d_energy_dist[i].cdf[0]))  # mux data, CDF second
					upper_cdf 	= numpy.hstack((upper_cdf,table.nu_d_energy_dist[i].cdf[1]))  # mux data, CDF second
				for i in range(0,len(table.nu_d_energy_dist)):
					lower_cdf 	= numpy.hstack((lower_cdf,table.nu_d_energy_dist[i].pdf[0]))  # mux data, PDF third
					upper_cdf 	= numpy.hstack((upper_cdf,table.nu_d_energy_dist[i].pdf[1]))  # mux data, PDF third

				# next index
				if above_last_d and above_last_t:
					next_dex = len(self.MT_E_grid)
				else:
					next_dex = next((i for i, x in enumerate(upper_erg <= self.MT_E_grid) if x), len(self.MT_E_grid))
				

		elif hasattr(rxn,"ang_energy_in"):
			# get the data, easy.
			# find where this energy lies on this grid, if above, return 
			upper_index = next((i for i, x in enumerate(this_E < rxn.ang_energy_in) if x), len(rxn.ang_energy_in))
			lower_index = upper_index - 1

			# if above upper index, return two of the last
			if upper_index == len(rxn.ang_energy_in):
				upper_index = len(rxn.ang_energy_in)-1
				lower_index = len(rxn.ang_energy_in)-1

			# make sure above threshold
			if lower_index < 0:

				# set all to zero
				lower_law	= -2
				upper_law	= -2
				lower_intt	= 0
				upper_intt	= 0
				lower_erg	= 0
				upper_erg	= 0
				lower_len	= 0
				upper_len	= 0
				lower_var 	= numpy.array([0.0])
				upper_var 	= numpy.array([0.0])
				lower_pdf 	= numpy.array([0.0])
				upper_pdf 	= numpy.array([0.0])
				lower_cdf 	= numpy.array([0.0])
				upper_cdf 	= numpy.array([0.0])

				# next index
				threshold = numpy.max([rxn.threshold(),rxn.ang_energy_in[0]])
				next_dex = next((i for i, x in enumerate(threshold <= self.MT_E_grid) if x), None)

			else:

				# law
				lower_law  = 3
				upper_law  = 3

				#intt
				lower_intt = rxn.ang_intt[lower_index]
				upper_intt = rxn.ang_intt[upper_index]

				# have energies
				lower_erg = rxn.ang_energy_in[lower_index]
				upper_erg = rxn.ang_energy_in[upper_index]

				# get angular distribution values, else write zeros
				lower_var = rxn.ang_cos[lower_index]
				upper_var = rxn.ang_cos[upper_index]
				lower_pdf = rxn.ang_pdf[lower_index]
				upper_pdf = rxn.ang_pdf[upper_index]
				lower_cdf = rxn.ang_cdf[lower_index]
				upper_cdf = rxn.ang_cdf[upper_index]

				# len
				lower_len = len(lower_var)
				upper_len = len(upper_var)

				# check if basically isotropic, then mark law=0 to save warp checking.  
				# short distirbutions cause numerical roundoff errors without double precision
				if lower_len == 3 and abs(lower_cdf[1]-0.5)<=self.isotropic_tol:
					lower_law = 0
				if upper_len == 3 and abs(upper_cdf[1]-0.5)<=self.isotropic_tol:
					upper_law = 0

				# next index
				if upper_index == lower_index == len(rxn.ang_energy_in)-1:  # above last dist energy bin
					next_dex = len(self.MT_E_grid)
				else:
					next_dex = next((i for i, x in enumerate(upper_erg <= self.MT_E_grid) if x), len(self.MT_E_grid))

		elif hasattr(rxn,"energy_dist") and hasattr(rxn.energy_dist,"energy_in") and hasattr(rxn.energy_dist,"a_dist_cdf"):
			# probably law 61!  There are angular distributions for each energy.  flatten array and pass back
			# find where this energy lies on this grid
			upper_index = next((i for i, x in enumerate(this_E < rxn.energy_dist.energy_in) if x), len(rxn.energy_dist.energy_in))
			lower_index = upper_index - 1

			#print this_E, upper_index, lower_index

			# if above upper index, return two of the last
			if upper_index == len(rxn.energy_dist.energy_in):
				upper_index = len(rxn.energy_dist.energy_in)-1
				lower_index = len(rxn.energy_dist.energy_in)-1

			# make sure above threshold
			if lower_index < 0:

				# set all to zero
				lower_law	= -2
				upper_law	= -2
				lower_intt	= 0
				upper_intt	= 0
				lower_erg	= 0
				upper_erg	= 0
				lower_len	= 0
				upper_len	= 0
				lower_var 	= numpy.array([0.0])
				upper_var 	= numpy.array([0.0])
				lower_pdf 	= numpy.array([0.0])
				upper_pdf 	= numpy.array([0.0])
				lower_cdf 	= numpy.array([0.0])
				upper_cdf 	= numpy.array([0.0])

				# next index
				threshold = numpy.max([rxn.threshold(),rxn.energy_dist.energy_in[0]])
				next_dex = next((i for i, x in enumerate(threshold <= self.MT_E_grid) if x), None)
				
			else:

				# law
				lower_law  = rxn.energy_dist.law
				upper_law  = rxn.energy_dist.law

				# interpolation type
				if hasattr(rxn.energy_dist,"intt"):
					lower_intt = rxn.energy_dist.a_dist_intt[lower_index][0]
					upper_intt = rxn.energy_dist.a_dist_intt[upper_index][0]
				else:
					lower_intt = 2
					upper_intt = 2

				# energies
				lower_erg = rxn.energy_dist.energy_in[lower_index]
				upper_erg = rxn.energy_dist.energy_in[upper_index]
	
				# get angular distribution values, else write zeros
				# mux vectors
				lower_var	= numpy.array([0]) # nothing, index determined by energy dist sampling
				upper_var	= numpy.array([0]) # nothing, index determined by energy dist sampling
				lower_cdf	= []
				upper_cdf	= []
				lower_pdf	= numpy.array([0]) # pdf is lengths
				upper_pdf	= numpy.array([0]) 
				# check
				assert(len(rxn.energy_dist.a_dist_mu_out[lower_index]) == len(rxn.energy_dist.energy_out[lower_index]))
				# do lower dist 
				for i in range(0,len(rxn.energy_dist.a_dist_mu_out[lower_index])):  # can be replaced with a flatten command
					lower_cdf 	= numpy.hstack((lower_cdf,rxn.energy_dist.a_dist_mu_out[lower_index][i]))  # mux data, energy first
					lower_pdf 	= numpy.hstack((lower_pdf,len(lower_cdf)))  # compute muxed indicies
				for i in range(0,len(rxn.energy_dist.a_dist_mu_out[lower_index])):
					lower_cdf 	= numpy.hstack((lower_cdf,rxn.energy_dist.a_dist_cdf[lower_index][i]))  # mux data, CDF second
				for i in range(0,len(rxn.energy_dist.a_dist_mu_out[lower_index])):
					lower_cdf 	= numpy.hstack((lower_cdf,rxn.energy_dist.a_dist_pdf[lower_index][i]))  # mux data, PDF third
				# do upper dist 
				for i in range(0,len(rxn.energy_dist.a_dist_mu_out[upper_index])):
					upper_cdf 	= numpy.hstack((upper_cdf,rxn.energy_dist.a_dist_mu_out[upper_index][i]))  # mux data, energy first
					upper_pdf 	= numpy.hstack((upper_pdf,len(upper_cdf)))  # compute muxed indicies
				for i in range(0,len(rxn.energy_dist.a_dist_mu_out[upper_index])):
					upper_cdf 	= numpy.hstack((upper_cdf,rxn.energy_dist.a_dist_cdf[upper_index][i]))  # mux data, CDF second
				for i in range(0,len(rxn.energy_dist.a_dist_mu_out[upper_index])):
					upper_cdf 	= numpy.hstack((upper_cdf,rxn.energy_dist.a_dist_pdf[upper_index][i]))  # mux data, PDF third

				# len
				lower_len = len(lower_cdf)/3
				upper_len = len(upper_cdf)/3

				# next index
				if upper_index == lower_index == len(rxn.energy_dist.energy_in)-1:  # above last dist energy bin
					next_dex = len(self.MT_E_grid)
				else:
					next_dex = next((i for i, x in enumerate(upper_erg <= self.MT_E_grid) if x), len(self.MT_E_grid))


		elif hasattr(rxn,"energy_dist") and hasattr(rxn.energy_dist,"energy_in"):
			# there is no higher level angular table, everything is in energy_dist
			# find where this energy lies on this grid
			upper_index = next((i for i, x in enumerate(this_E < rxn.energy_dist.energy_in) if x), len(rxn.energy_dist.energy_in))
			lower_index = upper_index - 1

			#print this_E, upper_index, lower_index

			# if above upper index, return two of the last
			if upper_index == len(rxn.energy_dist.energy_in):
				upper_index = len(rxn.energy_dist.energy_in)-1
				lower_index = len(rxn.energy_dist.energy_in)-1

			# make sure above threshold
			if lower_index < 0:

				# set all to zero
				lower_law	= -2
				upper_law	= -2
				lower_intt	= 0
				upper_intt	= 0
				lower_erg	= 0
				upper_erg	= 0
				lower_len	= 0
				upper_len	= 0
				lower_var 	= numpy.array([0.0])
				upper_var 	= numpy.array([0.0])
				lower_pdf 	= numpy.array([0.0])
				upper_pdf 	= numpy.array([0.0])
				lower_cdf 	= numpy.array([0.0])
				upper_cdf 	= numpy.array([0.0])

				# next index
				threshold = numpy.max([rxn.threshold(),rxn.energy_dist.energy_in[0]])
				next_dex = next((i for i, x in enumerate(threshold <= self.MT_E_grid) if x), None)
				
			else:

				# law
				lower_law  = rxn.energy_dist.law
				upper_law  = rxn.energy_dist.law

				# interpolation type
				if hasattr(rxn.energy_dist,"intt"):
					lower_intt = rxn.energy_dist.intt[lower_index]
					upper_intt = rxn.energy_dist.intt[upper_index]
				else:
					lower_intt = 2
					upper_intt = 2

				# energies
				lower_erg = rxn.energy_dist.energy_in[lower_index]
				upper_erg = rxn.energy_dist.energy_in[upper_index]
	
				# get angular distribution values, else write zeros
				if hasattr(rxn.energy_dist,"ang"):
					lower_var = rxn.energy_dist.ang[lower_index]
					upper_var = rxn.energy_dist.ang[upper_index]
				elif hasattr(rxn.energy_dist,"var"):
					lower_var = numpy.zeros(rxn.energy_dist.var[lower_index].shape)
					upper_var = numpy.zeros(rxn.energy_dist.var[upper_index].shape)
				else:
					lower_var = numpy.array([0])
					upper_var = numpy.array([0])
	
				# cdf can be law 44 fractions
				if hasattr(rxn.energy_dist,"frac"):
					lower_cdf = rxn.energy_dist.frac[lower_index]
					upper_cdf = rxn.energy_dist.frac[upper_index]
				elif hasattr(rxn.energy_dist,"cdf"):
					lower_cdf = numpy.zeros(rxn.energy_dist.cdf[lower_index].shape)
					upper_cdf = numpy.zeros(rxn.energy_dist.cdf[upper_index].shape)
				else:
					lower_cdf = numpy.array([0])
					upper_cdf = numpy.array([0])

				# pdf zeros
				if hasattr(rxn.energy_dist,"pdf"):
					lower_pdf = numpy.zeros(rxn.energy_dist.pdf[lower_index].shape)
					upper_pdf = numpy.zeros(rxn.energy_dist.pdf[upper_index].shape)
				else:
					lower_pdf = numpy.array([0])
					upper_pdf = numpy.array([0])

				# len
				lower_len = len(lower_var)
				upper_len = len(upper_var)

				# next index
				if upper_index == lower_index == len(rxn.energy_dist.energy_in)-1:  # above last dist energy bin
					next_dex = len(self.MT_E_grid)
				else:
					next_dex = next((i for i, x in enumerate(upper_erg <= self.MT_E_grid) if x), len(self.MT_E_grid))

		else:
			# no distributions
			# set all to isotropic and write law if there is one
			if hasattr(rxn,"energy_dist"):
				lower_law = rxn.energy_dist.law
				upper_law = rxn.energy_dist.law
			else:
				lower_law	= 0
				upper_law	= 0
			lower_intt	= 1
			upper_intt	= 1
			lower_erg	= self.MT_E_grid[0]
			upper_erg	= self.MT_E_grid[-1]
			lower_len	= 3
			upper_len	= 3
			lower_var 	= numpy.array([-1.0,0.0,1.0])
			upper_var 	= numpy.array([-1.0,0.0,1.0])
			lower_pdf 	= numpy.array([0.5,0.5,0.5])
			upper_pdf 	= numpy.array([0.5,0.5,0.5])
			lower_cdf 	= numpy.array([0.0,0.5,1.0])
			upper_cdf 	= numpy.array([0.0,0.5,1.0])

			# next index
			next_dex = len(self.MT_E_grid)
		
		#print "unionize.py:   erg ",lower_erg," len ", lower_len, " var ", lower_var, " pdf ", lower_pdf , " cdf ",lower_cdf

		# return values in order as float32 arrays
		return [numpy.ascontiguousarray(lower_erg,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_len,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_law,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_intt,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_var,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_pdf,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_cdf,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_erg,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_len,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_law,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_intt,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_var,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_pdf,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_cdf,	dtype=numpy.float32),
				numpy.ascontiguousarray(next_dex,	dtype=numpy.float32)]

	##
	# \brief gets table of energy data
	# \details table returned in form of [nextDex, length, mu, cdf]
	# @param[in] self - this cross_section_data object
	# @param[in] row - point in energy grid
	# @param[in] col - MT number
	def _get_energy_data(self,row,col):
		# energy table returned

		#find the isotope we are in
		numbers = numpy.cumsum(self.reaction_numbers_total)
		isotope = numpy.argmax( (col - self.num_isotopes) < numbers )
		table 	= self.tables[isotope]
		MTnum 	= self.reaction_numbers[col]
		rxn   	= table.reactions[MTnum]

		# get the energy of this index
		this_E = self.MT_E_grid[row]

		#print MTnum

		# do the cases
		if hasattr(rxn,"energy_dist") and ( hasattr(rxn.energy_dist,"energy_in") or hasattr(rxn.energy_dist,"energya_in")):
			# unionize a/b for law 11 and set it as energy_in, interpolate a/b values to new grid
			# just in case they have differrent grids...
			if hasattr(rxn.energy_dist,"energya_in"):
				rxn.energy_dist.energy_in	= numpy.union1d(rxn.energy_dist.energya_in,rxn.energy_dist.energyb_in)
				rxn.energy_dist.a			= numpy.interp( rxn.energy_dist.energy_in, rxn.energy_dist.energya_in, rxn.energy_dist.a )
				rxn.energy_dist.b			= numpy.interp( rxn.energy_dist.energy_in, rxn.energy_dist.energyb_in, rxn.energy_dist.b )
			# there is no higher level table, everything is in energy_dist
			# find where this energy lies on this grid
			upper_index = next((i for i, x in enumerate(this_E < rxn.energy_dist.energy_in) if x), len(rxn.energy_dist.energy_in))
			lower_index = upper_index - 1

			#print this_E, upper_index, lower_index

			# if above upper index, return two of the last
			if upper_index == len(rxn.energy_dist.energy_in):
				upper_index = len(rxn.energy_dist.energy_in)-1
				lower_index = len(rxn.energy_dist.energy_in)-1

			# make sure above threshold
			if lower_index < 0:

				# set all to zero
				lower_law	= 0
				upper_law	= 0
				lower_intt	= 0
				upper_intt	= 0
				lower_erg	= 0
				upper_erg	= 0
				lower_len	= 0
				upper_len	= 0
				lower_var 	= numpy.array([0.0])
				upper_var 	= numpy.array([0.0])
				lower_pdf 	= numpy.array([0.0])
				upper_pdf 	= numpy.array([0.0])
				lower_cdf 	= numpy.array([0.0])
				upper_cdf 	= numpy.array([0.0])

				# next index
				threshold = numpy.max([rxn.threshold(),rxn.energy_dist.energy_in[0]])
				next_dex = next((i for i, x in enumerate(threshold <= self.MT_E_grid) if x), None)
				
			else:

				# law
				lower_law  = rxn.energy_dist.law
				upper_law  = rxn.energy_dist.law

				# interpolation type
				if hasattr(rxn.energy_dist,"intt"):
					lower_intt = rxn.energy_dist.intt[lower_index]
					upper_intt = rxn.energy_dist.intt[upper_index]
				else:
					lower_intt = 2
					upper_intt = 2

				# energies
				lower_erg = rxn.energy_dist.energy_in[lower_index]
				upper_erg = rxn.energy_dist.energy_in[upper_index]
	
				# tabular distributions
				if hasattr(rxn.energy_dist,"energy_out"):
					lower_var = rxn.energy_dist.energy_out[lower_index]
					upper_var = rxn.energy_dist.energy_out[upper_index]
					lower_pdf = rxn.energy_dist.pdf[lower_index]
					upper_pdf = rxn.energy_dist.pdf[upper_index]
					lower_cdf = rxn.energy_dist.cdf[lower_index]
					upper_cdf = rxn.energy_dist.cdf[upper_index]
				elif hasattr(rxn.energy_dist,"T"):  #evaporation 
					lower_var = numpy.array([rxn.energy_dist.T[lower_index]])
					upper_var = numpy.array([rxn.energy_dist.T[upper_index]])
					lower_cdf = numpy.array([rxn.energy_dist.U])
					upper_cdf = numpy.array([rxn.energy_dist.U])
					lower_pdf = numpy.array([0])
					upper_pdf = numpy.array([0])
				elif hasattr(rxn.energy_dist,"a"):  # e dep maxwellian 
					lower_var = numpy.array([rxn.energy_dist.a[lower_index]])
					upper_var = numpy.array([rxn.energy_dist.a[upper_index]])
					lower_cdf = numpy.array([rxn.energy_dist.b[lower_index]])
					upper_cdf = numpy.array([rxn.energy_dist.b[upper_index]])
					lower_pdf = numpy.array([rxn.energy_dist.U])
					upper_pdf = numpy.array([rxn.energy_dist.U])
				else:
					print "UNHANDLED ENERGY DIST CONTENTS"

				# len
				lower_len = len(lower_var)
				upper_len = len(upper_var)

				# next index
				if upper_index == lower_index == len(rxn.energy_dist.energy_in)-1:  # above last dist energy bin
					next_dex = len(self.MT_E_grid)
				else:
					next_dex = next((i for i, x in enumerate(upper_erg <= self.MT_E_grid) if x), len(self.MT_E_grid))

		else:
			# no distributions
			# set all to zero (except law if there is one)
			if hasattr(rxn,"energy_dist"):
				lower_law = rxn.energy_dist.law
				upper_law = rxn.energy_dist.law
			else:
				lower_law = 0
				upper_law = 0
			lower_intt	= 1
			upper_intt	= 1
			lower_erg	= self.MT_E_grid[0]
			upper_erg	= self.MT_E_grid[-1]
			lower_len	= 1
			upper_len	= 1
			lower_var 	= numpy.array([0.0])
			upper_var 	= numpy.array([0.0])
			lower_pdf 	= numpy.array([0.0])
			upper_pdf 	= numpy.array([0.0])
			lower_cdf 	= numpy.array([0.0])
			upper_cdf 	= numpy.array([0.0])

			# next index
			next_dex = len(self.MT_E_grid)

		# return values in order as float32 arrays
		return [numpy.ascontiguousarray(lower_erg,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_len,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_law,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_intt,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_var,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_pdf,	dtype=numpy.float32),
				numpy.ascontiguousarray(lower_cdf,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_erg,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_len,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_law,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_intt,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_var,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_pdf,	dtype=numpy.float32),
				numpy.ascontiguousarray(upper_cdf,	dtype=numpy.float32),
				numpy.ascontiguousarray(next_dex,	dtype=numpy.float32)]

