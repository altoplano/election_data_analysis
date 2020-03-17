#!usr/bin/python3
import db_routines as dbr
import db_routines.Create_CDF_db as db_cdf
import munge_routines as mr
import pandas as pd
import numpy as np
from sqlalchemy.orm import sessionmaker
import os
import states_and_files as sf
import random


def pick_one(df,return_col,item='row',required=False):
	"""Returns index and <return_col> value of item chosen by user"""
	# TODO check that index entries are positive ints (and handle error)
	if df.empty:
		return None, None
	print(df)
	choice = max(df.index) + 1  # guaranteed not to be in df.index at start

	while choice not in df.index:
		if not required:
			req_str=' (or nothing, if your choice is not on the list)'
		else:
			req_str=''
		choice_str = input(f'Enter the number of the desired {item}{req_str}:\n')
		if choice_str == '' and not required:
			return None,None
		else:
			try:
				choice = int(choice_str)
				if choice not in df.index:
					print(f'Enter an option from the leftmost column. Please try again.')
			except ValueError:
				print(f'You must enter a number {req_str}, then hit return. Please try again.')
	print(f'Chosen {item} is {df.loc[choice,return_col]}\n\n')
	return choice, df.loc[choice,return_col]


def show_sample(st,items,condition,outfile='shown_items.txt',dir=None):
	print(f'There are {len(st)} {items} that {condition}:')
	if len(st) == 0:
		return
	st = list(st)
	st.sort()

	if len(st) < 11:
		show_list = st
	else:
		print('(sample)')
		show_list = random.sample(st,10)
		show_list.sort()
	for r in show_list:
		print(r)
	if len(st) > 10:
		show_all = input(f'Show all {len(st)} {items} that {condition} (y/n)?\n')
		if show_all == 'y':
			for r in st:
				print(f'\t{r}')
	if dir is None:
		dir = input(f'Export all {len(st)} {items} that {condition}? If so, enter directory for export\n'
					f'(Current directory is {os.getcwd()})\n')
	elif os.path.isdir(dir):
		export = input(f'Export all {len(st)} {items} that {condition} to {outfile} (y/n)?\n')
		if export == 'y':
			with open(os.path.join(dir,outfile),'a') as f:
				f.write('\n'.join(st))
			print(f'{items} exported to {os.path.join(dir,outfile)}')
	elif dir != '':
		print(f'Directory {dir} does not exist.')

	return


def pick_database(paramfile,state_name=None):
	if state_name:
		print(f'WARNING: will use db {state_name} '
			  f'and state directory {state_name}, both of which are assumed to exist.\n\n')
		return state_name
	con = dbr.establish_connection(paramfile=paramfile)  # TODO error handling for paramfile
	print(f'Connection established to database {con.info.dbname}')
	cur = con.cursor()
	db_df = pd.DataFrame(dbr.query('SELECT datname FROM pg_database',[],[],con,cur))
	db_idx,desired_db = pick_one(db_df,0,item='database')

	if db_idx == None:	# if we're going to need a brand new db

		desired_db = input('Enter name for new database (alphanumeric only):\n')
		dbr.create_database(con,cur,desired_db)

	if desired_db != con.info.dbname:
		cur.close()
		con.close()
		con = dbr.establish_connection(paramfile,db_name=desired_db)
		cur = con.cursor()

	if db_idx == None: 	# if our db is brand new
		eng,meta = dbr.sql_alchemy_connect(paramfile=db_paramfile,db_name=desired_db)
		Session = sessionmaker(bind=eng)
		pick_db_session = Session()

		db_cdf.create_common_data_format_tables(pick_db_session,None,
												dirpath=os.path.join(
													project_root,'election_anomaly/CDF_schema_def_info/'),
												delete_existing=False)
		db_cdf.fill_cdf_enum_tables(pick_db_session,None,dirpath=os.path.join(project_root,'election_anomaly/CDF_schema_def_info/'))

	# clean up
	if cur:
		cur.close()
	if con:
		con.close()
	return desired_db


def pick_state(con,schema,path_to_states='local_data/',state_name=None):
	"""Returns a State object.
	If <state_name> is given, this just initializes based on info
	in the folder with that name; """
	if state_name is None:
		choice_list = [x for x in os.listdir(path_to_states) if os.path.isdir(os.path.join(path_to_states,x))]
		state_df = pd.DataFrame(choice_list,columns=['State'])
		state_idx,state_name = pick_one(state_df,'State', item='state')

		if state_idx is None:
			# user chooses state short_name
			state_name = input('Enter a short name (alphanumeric only, no spaces) for your state '
							   '(e.g., \'NC\')\n')
		state_path = os.path.join(path_to_states,state_name)

		# create state directory
		try:
			os.mkdir(state_path)
		except FileExistsError:
			print(f'Directory {state_path} already exists, will be preserved')
		else:
			print(f'Directory {state_path} created')

		# create subdirectories
		subdir_list = ['context','data','output']
		for sd in subdir_list:
			sd_path = os.path.join(state_path,sd)
			try:
				os.mkdir(sd_path)
			except FileExistsError:
				print(f'Directory {sd_path} already exists, will be preserved')
			else:
				print(f'Directory {sd_path} created')

		# ensure context directory has what it needs
		context_file_list = ['Office.txt','Party.txt','ReportingUnit.txt','remark.txt']
		if not all([os.path.isfile(os.path.join(state_path,'context',x)) for x in context_file_list]):
			# pull necessary enumeration from db: ReportingUnitType
			ru_type = pd.read_sql_table('ReportingUnitType',con,schema=schema,index_col='Id')
			standard_ru_types = set(ru_type[ru_type.Txt != 'other']['Txt'])
			ru = fill_context_file(os.path.join(state_path,'context'),
							  os.path.join(path_to_states,'context_templates'),
								'ReportingUnit',standard_ru_types,'ReportingUnitType')
			ru_list = ru['Name'].to_list()
			fill_context_file(os.path.join(state_path,'context'),
							  os.path.join(path_to_states,'context_templates'),
								'Office',ru_list,'ElectionDistrict',reportingunittype_list=standard_ru_types)
			# Party.txt
			fill_context_file(os.path.join(state_path,'context'),
							  os.path.join(path_to_states,'context_templates'),
								'Party',None,None)
			# TODO remark
			remark_path = os.path.join(state_path,'context','remark.txt')
			open(remark_path,'a').close()	# creates file if it doesn't exist already
			with open(remark_path,'r') as f:
				remark = f.read()
			print(f'Current contents of remark.txt is:\n{remark}\n')
			input(f'Please add or correct anything that user should know about the state {state_name}.'
						f'Then hit return to continue.')

	# initialize the state
	ss = sf.State(state_name,path_to_states)
	return ss


def create_file_from_template(template_file,new_file,sep='\t'):
	"""For tab-separated files (or others, using <sep>); does not replace existing file
	but creates <new_file> with the proper header row
	taking the headers from the <template_file>"""
	template = pd.read_csv(template_file,sep=sep,header=0,dtype=str)
	if not os.path.isfile(new_file):
		# create file with just header row
		template.iloc[0:0].to_csv(new_file,index=None,sep=sep)
	return


def fill_context_file(context_path,template_dir_path,element,test_list,test_field,reportingunittype_list=None,sep='\t'):
	if element == 'Office':
		assert reportingunittype_list, 'When processing Offices, need to pass non-empty reportingunittype_list'
	template_file = os.path.join(template_dir_path,f'{element}.txt')
	template = pd.read_csv(template_file,sep='\t')
	create_file_from_template(template_file,context_path,sep=sep)
	in_progress = 'y'
	while in_progress == 'y':
		# TODO check for dupes
		# check format of file
		context_df = pd.read_csv(context_path,sep=sep,header=0,dtype=str)
		if not context_df.columns.to_list() == template.columns.to_list():
			print(f'WARNING: {element}.txt is not in the correct format.')		# TODO refine error msg?
			input('Please correct the file and hit return to continue.\n')
		else:
			# report contents of file
			print(f'\nCurrent contents of {element}.txt:\n{context_df}')

			# check test conditions
			if test_list is not None:
				if element == 'Office':	# need to reload from ReportingUnit.txt
					test_list = pd.read_csv(context_path,
										sep=sep,header=0,dtype=str)['Name'].to_list()
				bad_set = {x for x in context_df[test_field] if x not in test_list}
				if len(bad_set) == 0:
					print(f'Congratulations! All {element}s look good!')
					in_progress = 'n'
				else:  # if test condition fails
					if element == 'Office':		# Office.ElectionDistrict must be in ReportingUnit.Name
						print(f'The ElectionDistrict for each Office must be listed in ReportingUnit.txt.\n')
						show_sample(bad_set,f'{test_field}s','fail this condition')
						print(f'To solve the problem, you must either alter the Name column in ReportingUnit.txt '
							  f'to add/correct the missing items,'
							  f'or remove/correct the {test_field} column in the offending row of Office.txt ')
						edit_test_element = input(f'Would you like to edit ReportingUnit.txt (y/n)?\n')
						if edit_test_element:
							fill_context_file(context_path,template_dir_path,'ReportingUnit',reportingunittype_list,'ReportingUnitType')
					else:
						print(f'\tStandard {test_field}s are not required, but you probably want to use them when you can.'
							  f'\n\tYour file has non-standard {test_field}s:')
						for rut in bad_set: print(f'\t\t{rut}')
						print(f'\tStandard {test_field}s are:')
						print(f'\t\t{",".join(test_list)}')

					# invite input
					in_progress = input(f'Would you like to alter {element}.txt (y/n)?\n')
					if in_progress == 'y':
						input('Make alterations, then hit return to continue')
	return context_df


def pick_munger(sess,munger_dir='mungers/',column_list=None,template_dir='zzz_munger_templates'):
	"""pick (or create) a munger """
	choice_list = os.listdir(munger_dir)
	for choice in os.listdir(munger_dir):
		p = os.path.join(munger_dir,choice)
		if not os.path.isdir(p):	# remove non-directories from list
			choice_list.remove(choice)
		elif not os.path.isfile(os.path.join(p,'raw_columns.txt')):
			pass  # list any munger that doesn't have raw_columns.txt file yet
		else:
			# remove from list if columns don't match
			raw_columns = pd.read_csv(os.path.join(p,'raw_columns.txt'),header=0,dtype=str,sep='\t')
			if raw_columns.name.to_list() != column_list:
				choice_list.remove(choice)

	munger_df = pd.DataFrame(choice_list,columns=['Munger'])
	munger_idx,munger_name = pick_one(munger_df,'Munger', item='munger')
	if munger_idx is None:
		# user chooses state munger
		munger_name = input('Enter a short name (alphanumeric only, no spaces) for your munger'
						   '(e.g., \'nc_primary18\')\n')
	munger_path = os.path.join(munger_dir,munger_name)
	# create munger directory
	try:
		os.mkdir(munger_path)
	except FileExistsError:
		print(f'Directory {munger_path} already exists, will be preserved')
	else:
		print(f'Directory {munger_path} created')

	file_list = ['raw_columns.txt','count_columns.txt','cdf_tables.txt','raw_identifiers.txt']
	if not all([os.path.isfile(os.path.join(munger_path,x)) for x in file_list]):
		for ff in file_list:
			create_file_from_template(os.path.join(template_dir,ff),
												   os.path.join(munger_path,ff))
		# write column_list to raw_columns.txt
		if column_list:
			# np.savetxt(os.path.join(munger_path,ff),np.asarray([[x] for x in column_list]),header='name')
			pd.DataFrame(np.asarray([[x] for x in column_list]),columns=['name']).to_csv(
				os.path.join(munger_path,'raw_columns.txt'),sep='\t',index=False)
		else:
			input(f"""The file raw_columns.txt should have one row for each column 
				in the raw datafile to be processed with the munger {munger_name}. 
				The columns must be listed in the order in which they appear in the raw datafile'
				Check the file and correct as necessary. Then hit return to continue.\n""")

		# create ballot_measure_style.txt
		bmso_df = pd.read_csv(os.path.join(munger_dir,'ballot_measure_style_options.txt'),sep='\t')
		try:
			with open(os.path.join(munger_path,'ballot_measure_style.txt'),'r') as f:
				bms=f.read()
			assert bms in bmso_df['short_name'].to_list()
			change = input(f'Ballot measure style is {bms}. Do you need to change it (y/n)?\n')
		except AssertionError:
			print('Ballot measure style not recognized. Please pick a new one.')
			change = 'y'
		except FileNotFoundError:
			change = 'y'
		if change == 'y':
			bms_idx,bms = pick_one(bmso_df,'short_name',item='ballot measure style',required=True)
			with open(os.path.join(munger_path,'ballot_measure_style.txt'),'w') as f:
				f.write(bms)

		# create/correct count_columns.txt
			print(f"""The file count_columns.txt should have one row for each vote-count column  
				in the raw datafile to be processed with the munger {munger_name}. 
				Each row should have the RawName of the column and the CountItemType. 
				Standard CountItemTypes are not required, but are recommended:""")
			cit = pd.read_sql_table('CountItemType',sess.bind)
			print(cit['Txt'].to_list())
			input('Check the file and correct as necessary.  Then hit return to continue.\n')
			# TODO check file against standard CountItemTypes?

		# create atomic_reporting_unit_type.txt
		rut_df = pd.read_sql_table('ReportingUnitType',sess.bind,index_col='Id')
		try:
			with open(os.path.join(munger_path,'atomic_reporting_unit_type.txt'),'r') as f:
				arut=f.read()
			change = input(f'Atomic ReportingUnit type is {arut}. Do you need to change it (y/n)?\n')
		except FileNotFoundError:
			change = 'y'
		if change == 'y':
			arut_idx,arut = pick_one(rut_df,'Txt',item='\'atomic\' reporting unit type for results file',required=True)
			with open(os.path.join(munger_path,'atomic_reporting_unit.txt'),'w') as f:
				f.write(arut)

		# prepare cdf_tables.txt
		prepare_cdf_tables_file(munger_path,bms)

		# prepare raw_identifiers.txt
		prepare_raw_identifiers_file(munger_path,bms)

	munger = sf.Munger(munger_path,cdf_schema_def_dir=os.path.join(project_root,'election_anomaly/CDF_schema_def_info'))
	return munger


def prepare_raw_identifiers_file(dir_path,ballot_measure_style):
	if ballot_measure_style == 'yes_and_no_are_candidates':
		print('\nMake sure to list all raw ballot measure selections, with cdf_internal_name \'Yes\' or \'No\'')
	input('Prepare raw_identifiers.txt and hit return to continue.')
	# TODO add guidance
	return


def prepare_cdf_tables_file(dir_path,ballot_measure_style):
	guided = input(f'Would you like guidance in preparing the cdf_tables.txt file (y/n)?\n')
	if guided != 'y':
		input('Prepare cdf_tables.txt and hit return to continue.')
	else:
		elt_list = ['Office','ReportingUnit','Party','Candidate','CandidateContest',
						'BallotMeasureContest']
		out_lines = []
		if ballot_measure_style == 'yes_and_no_are_candidates':
			elt_list.append('BallotMeasureSelection')
		for element in ['Office','ReportingUnit','Party','Candidate','CandidateContest',
						'BallotMeasureContest','BallotMeasureSelection']:
			print(f'''Enter your formulas for reading the common-data-format elements from each row
					of the results file. Put raw column names in brackets (<>).
					For example if the raw file has columns \'County\' and \'Precinct\',
					the formula for ReportingUnit might be \'<County>;<Precinct>\'.''')
			formula = input(f'Formula for {element}:\n')
			# TODO error check formula against raw_columns.txt and count_columns.txt in <dir_path>
			out_lines.append(f'{element}\t{formula}')
		with open(os.path.join(dir_path,'cdf_tables.txt'),'a') as f:
			f.write('\n'.join(out_lines))
	return


def create_munger(column_list=None):
	# TODO walk user through munger creation
	#
	munger = None # TODO temp
	return munger


def new_datafile(raw_file,raw_file_sep,db_paramfile,project_root='.',state_name=None):
	"""Guide user through process of uploading data in <raw_file>
	into common data format.
	Assumes cdf db exists already"""
	# connect to postgres to create schema if necessary

	db_name = pick_database(db_paramfile,state_name=state_name)

	eng, meta = dbr.sql_alchemy_connect(paramfile=db_paramfile,db_name=db_name)
	Session = sessionmaker(bind=eng)
	new_df_session = Session()

	state = pick_state(new_df_session.bind,None,
					   path_to_states=os.path.join(project_root,'local_data'),state_name=state_name)

	# update db from state context file

	print('Specify the election:')
	election_idx, election = pick_one(pd.read_sql_table('Election',new_df_session.bind,index_col='Id'),'Name','election')
	if election_idx is None:
		# create record in Election table
		election_name = input('Enter a unique short name for the election for your datafile\n') # TODO error check
		electiontype_idx,electiontype = \
			pick_one(pd.read_sql_table('ElectionType',new_df_session.bind,index_col='Id'),'Txt','election type')
		if electiontype == 'other':
			otherelectiontype = input('Enter the election type:\n')	# TODO assert type is not in standard list, not ''
		else:
			otherelectiontype = ''
		elections_df = dbr.dframe_to_sql(pd.DataFrame({'Name':election_name,'EndDate':
			input('Enter the end date of the election, a.k.a. \'Election Day\' (YYYY-MM-DD)\n'),'StartDate':
														   input('Enter the start date of the election (YYYY-MM-DD)\n'),'ElectionType_Id':
														   electiontype_idx,'OtherElectionType':otherelectiontype},index= [-1]),new_df_session,None,'Election')

	raw = pd.read_csv(raw_file,sep=raw_file_sep)
	column_list = raw.columns.to_list()
	print('Specify the munger:')
	munger = pick_munger(new_df_session,column_list=column_list,munger_dir=os.path.join(project_root,'mungers'),
						 template_dir=os.path.join(project_root,'mungers/zzz_munger_templates'))
	print(f'Munger {munger.name} has been chosen and prepared.\n')

	# TODO present munger.ballot_measure_selections and give user chance to correct it.

	print('What types of contests would you like to analyze from the datafile?')
	bmc_results,cc_results = mr.contest_type_split(raw,munger)
	contest_type_df = pd.DataFrame([
		['Candidate'], ['Ballot Measure'], ['Both Candidate and Ballot Measure']
	], columns=['Contest Type'])
	contest_type_idx, contest_type = pick_one(contest_type_df,'Contest Type', item='contest type',required=True)

	if contest_type in ['Candidate','Both Candidate and Ballot Measure']:
		munger.check_new_results_dataset(cc_results,state,new_df_session,'Candidate',project_root=project_root)
	if contest_type in ['Ballot Measure','Both Candidate and Ballot Measure']:
		munger.check_new_results_dataset(cc_results,state,new_df_session,'BallotMeasure',project_root=project_root)

	# TODO process new results dataset(s)

	return

if __name__ == '__main__':
	project_root = os.getcwd().split('election_anomaly')[0]

	#state_name = 'NC_test2'
	state_name = None
	raw_file = os.path.join(project_root,'local_data/NC/data/2018g/nc_general/results_pct_20181106.txt')
	raw_file_sep = '\t'
	db_paramfile = os.path.join(project_root,'local_data/database.ini')

	new_datafile(raw_file, raw_file_sep, db_paramfile,project_root,state_name=state_name)
	print('Done! (user_interface)')