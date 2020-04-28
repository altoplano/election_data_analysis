import db_routines as dbr
import user_interface as ui
from sqlalchemy.orm import sessionmaker
import os
import munge_routines as mr
import pandas as pd
import csv
import tkinter as tk


if __name__ == '__main__':
	print("""Ready to load some election result data?
			"This program will walk you through the process of creating or checking
			"an automatic munger that will load your data into a database in the 
			"NIST common data format.""")

	project_root = '/Users/Steph-Airbook/Documents/CampaignScientific/NSF2019/State_Data/results_analysis/src/'

	# initialize root widget for tkinter

	# pick db to use
	db_paramfile = '/Users/Steph-Airbook/Documents/CampaignScientific/NSF2019/database.ini'

	db_name = 'NC_5'

	# connect to db
	eng, meta = dbr.sql_alchemy_connect(paramfile=db_paramfile,db_name=db_name)
	Session = sessionmaker(bind=eng)
	sess = Session()

	ui.pick_or_create_record(sess,project_root,'Election',known_info_d={})

	eng.dispose()
	print('Done!')

	exit()
