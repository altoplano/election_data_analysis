import election_data_analysis as e
#WA16 tests

def data_exists(dbname):
    assert e.data_exists("2016 General", "Washington", dbname=dbname)

def test_wa_presidential_16(dbname):
    assert (e.contest_total(
            "2016 General",
            "Washington",
            "US President (WA)",
            dbname=dbname,
        )
            == 3209214
    )


def test_wa_statewide_totals_16(dbname):
    assert (e.contest_total(
            "2016 General",
            "Washington",
            "WA Attorney General",
            dbname=dbname,
        )
            == 2979909
    )


def test_wa_senate_totals_16(dbname):
    assert (e.contest_total(
            "2016 General",
            "Washington",
            "WA Senate District 22",
            dbname=dbname,
        )
            == 68868
    )


def test_wa_house_totals_16(dbname):
    assert (e.contest_total(
            "2016 General",
            "Washington",
            "WA House District 37",
            dbname=dbname,
        )
            == 62801
    )


