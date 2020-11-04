import election_data_analysis as e

#WV20g test
# Instructions:
#   Delete any tests for contest types your state doesn't have in 2020 (e.g., Florida has no US Senate contest)
#   (Optional) Change district numbers
#   Replace each '-1' with the correct number calculated from the results file.
#   Move this testing file to the correct jurisdiction folder in `election_data_analysis/tests`

def data_exists(dbname):
    assert e.data_exists("2020 General","West Virginia",dbname=dbname)

def test_presidential(dbname):
    assert(e.contest_total(
        "2020 General",
        "West Virginia",
        "US President (WV)",
        dbname=dbname,
        )
        == -1
    )

def test_senate_totals(dbname):
    assert (e.contest_total(
        "2020 General",
        "West Virginia",
        "US Senate WV",
        dbname=dbname,
        )
        == -1
    )

def test_congressional_totals(dbname):
    assert (e.contest_total(
        "2020 General",
        "West Virginia",
        "US House WV District 1",
        dbname=dbname,
        )
        == -1
    )

def test_state_senate_totals(dbname):
    assert (e.contest_total(
        "2020 General",
        "West Virginia",
        "WV Senate District 1",
        dbname=dbname,
        )
        == -1
    )

def test_state_house_totals(dbname):
    assert ( e.contest_total(
        "2020 General",
        "West Virginia",
        "WV House District 1",
        dbname=dbname,
        )
        == -1
    )
