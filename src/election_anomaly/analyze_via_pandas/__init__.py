#!usr/bin/python3

import pandas as pd
import user_interface as ui
import db_routines as dbr
import munge_routines as mr
import warnings
import analyze as an
import datetime


def contest_type_and_name_by_id(eng):
	"""create and return id-to-contest-type dict"""

	df = {}
	for element in [
		"CandidateContest","BallotMeasureContest",
		"BallotMeasureSelection","CandidateSelection","Candidate",
		"ReportingUnitType","ComposingReportingUnitJoin"]:
		df[element] = pd.read_sql_table(element,eng,index_col='Id')
	candidate_name_by_selection_id = df['CandidateSelection'].merge(
		df['Candidate'],left_on='Candidate_Id',right_index=True)

	contest_type = {}
	contest_name = {}
	selection_name = {}

	for i,r in df['CandidateContest'].iterrows():
		contest_type[i] = 'Candidate'
		contest_name[i] = r['Name']
	for i,r in df['BallotMeasureContest'].iterrows():
		contest_type[i] = 'BallotMeasure'
		contest_name[i] = r['Name']
	for i,r in df['BallotMeasureSelection'].iterrows():
		selection_name[i] = r['Selection']
	for i,r in candidate_name_by_selection_id.iterrows():
		selection_name[i] = r['BallotName']
	return contest_type,contest_name,selection_name


def child_rus_by_id(session,parents,ru_type=None):
	"""Given a list <parents> of parent ids, return
	list of those parents along with all children of those parents.
	If (ReportingUnitType_Id,OtherReportingUnit) pair <rutype> is given,
	restrict children to that ReportingUnitType"""
	assert len(ru_type) == 2,f'argument {ru_type} does not have exactly 2 elements'
	cruj = pd.read_sql_table('ComposingReportingUnitJoin',session.bind)
	children = list(cruj[cruj.ParentReportingUnit_Id.isin(parents)].ChildReportingUnit_Id.unique()) + parents
	if ru_type:
		ru = pd.read_sql_table('ReportingUnit',session.bind,index_col='Id')
		right_type_ru = ru[(ru.ReportingUnitType_Id == ru_type[0]) & (ru.OtherReportingUnitType == ru_type[1])]
		children = [x for x in children if x in right_type_ru.index]
	# TODO test
	return children


def get_id_check_unique(df,conditions={}):
	"""Finds the index of the unique row of <df> satisfying the <conditions>.
	Raises exception if there is no unique row"""
	found = df.loc[(df[list(conditions)] == pd.Series(conditions)).all(axis=1)]
	if found.shape[0] == 0:
		raise Exception(f'None found')
	elif found.shape[0] > 1:
		raise Exception(f'More than one found')
	else:
		return found.first_valid_index()


def rollup(session,top_ru,sub_ru_type,atomic_ru_type,election,target_dir,exclude_total=True):
	"""<top_ru> is the internal cdf name of the ReportingUnit whose results will be reported
	(e.g., Florida or Pennsylvania;Philadelphia).
	<sub_ru_type> is the ReportingUnitType of the ReportingUnits used in each line of the results file
	for <election> created by the routine. (E.g., county or ward)
	<atomic_ru_type> is the ReportingUnitType in the database from which the results
	at the <sub_ru_type> level are calculated. (E.g., county or precinct)
	<session> and <db> provide access to the db containing results.
	If <exclude_total> is True, don't include 'total' CountItemType
	(unless 'total' the only CountItemType)"""

	# Get name of db for error messages
	db = session.bind.url.database

	# pull relevant tables
	df = {}
	for element in [
		"SelectionElectionContestVoteCountJoin","VoteCount",
		"ComposingReportingUnitJoin","Election","ReportingUnit",
		"ComposingReportingUnitJoin"]:
		df[element] = pd.read_sql_table(element,session.bind,index_col='Id')
	for enum in ["ReportingUnitType","CountItemType"]:
		df[enum] = pd.read_sql_table(
			enum,session.bind)  # keep 'Id' as col, not index
	count_item_type = {r.Id:r.Txt for i,r in df['CountItemType'].iterrows()}

	# Get id for top reporting unit, election
	top_ru_id = get_id_check_unique(df['ReportingUnit'],conditions={'Name':top_ru})
	election_id = get_id_check_unique(df['Election'],conditions={'Name':election})

	atomic_ru_type_id, atomic_other_ru_type = mr.get_id_othertext_from_enum_value(
		df['ReportingUnitType'],atomic_ru_type)
	sub_ru_type_id, sub_other_ru_type = mr.get_id_othertext_from_enum_value(
		df['ReportingUnitType'],sub_ru_type)

	# limit to atomic and sub RUs nested inside the top RU
	atomic_ru_list = child_rus_by_id(session,[top_ru_id],ru_type=[atomic_ru_type_id, atomic_other_ru_type])
	if not atomic_ru_list:
		raise Exception(f'Database {db} shows no ReportingUnits of type {atomic_ru_type} nested inside {top_ru}')
	atomic_ru = df['ReportingUnit'].loc[atomic_ru_list]

	sub_ru_list = child_rus_by_id(session,[top_ru_id],ru_type=[sub_ru_type_id, sub_other_ru_type])
	if not sub_ru_list:
		raise Exception(f'Database {db} shows no ReportingUnits of type {sub_ru_type} nested inside {top_ru}')
	sub_ru = df['ReportingUnit'].loc[sub_ru_list]

	atomic_in_sub_list = child_rus_by_id(session,sub_ru_list,ru_type=[atomic_ru_type_id, atomic_other_ru_type])
	missing_atomic = [x for x in atomic_ru_list if x not in atomic_in_sub_list]
	if missing_atomic:
		missing_names = set(df['ReportingUnit'].loc[missing_atomic,'Name'])
		ui.show_sample(missing_names,'atomic ReportingUnits',f'are not in any {sub_ru_type}')

	# TODO calculate specified dataframe with columns [ReportingUnit,Contest,Selection,VoteCount,CountItemType]
	ru_c = df['ReportingUnit'].loc[atomic_ru_list]
	ru_p = df['ReportingUnit'].loc[sub_ru_list]
	secvcj = df['SelectionElectionContestVoteCountJoin'][
		df['SelectionElectionContestVoteCountJoin'].Election_Id == election_id
	]

	unsummed = secvcj.merge(
		df['VoteCount'],left_on='VoteCount_Id',right_index=True).merge(
		df['ComposingReportingUnitJoin'],left_on='ReportingUnit_Id',right_on='ChildReportingUnit_Id').merge(
		ru_c,left_on='ChildReportingUnit_Id',right_index=True).merge(
		ru_p,left_on='ParentReportingUnit_Id',right_index=True,suffixes=['','_Parent'])
	# TODO check this merge -- does it need how='inner'?

	# TODO add columns with names
	contest_type,contest_name,selection_name = contest_type_and_name_by_id(session.bind)
	unsummed['contest_type'] = unsummed['Contest_Id'].map(contest_type)
	unsummed['Contest'] = unsummed['Contest_Id'].map(contest_name)
	unsummed['Selection'] = unsummed['Selection_Id'].map(selection_name)
	unsummed['CountItemType'] = unsummed['CountItemType_Id'].map(count_item_type)

	unsummed.rename(columns={'Name_Parent':'ReportingUnit'},inplace=True)

	cis = 'unknown'
	cit_list = unsummed['CountItemType'].unique()
	if len(cit_list) > 1:
		cit = 'mixed'
		if exclude_total:
			unsummed = unsummed[unsummed.CountItemType != 'total']
	elif len(cit_list) == 1:
		cit = cit_list[0]
	else:
		raise Exception(
			f'Results dataframe has no CountItemTypes; maybe dataframe is empty?')
	count_item = f'TYPE{cit}_STATUS{cis}'

	# sum by groups
	summed_by_name = unsummed[[
		'contest_type','Contest','Selection','ReportingUnit','CountItemType','Count']].groupby(
		['contest_type','Contest','Selection','ReportingUnit','CountItemType']).sum()

	inventory_columns = [
		'Election','ReportingUnitType','CountItemType','CountItemStatus',
		'source_db_url','timestamp']
	inventory_values = [
		election,sub_ru_type,cit,'TODO',
		str(session.bind.url),datetime.date.today()]
	an.export_to_inventory_file_tree(
		target_dir,f'{session.bind.url.database}/by_{sub_ru_type}',f'{count_item}.txt',
		inventory_columns,inventory_values,summed_by_name)
	return summed_by_name
