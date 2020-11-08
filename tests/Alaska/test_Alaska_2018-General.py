import election_data_analysis as e


def test_data_exists(dbname):
    assert e.data_exists("2018 General", "Colorado", dbname=dbname)


def test_ak_statewide_totals_18(dbname):
    assert (
        e.contest_total(
            "2018 General",
            "Colorado",
            "CO Attorney General",
            dbname=dbname,
        )
        == 2491954
    )


def test_ak_senate_totals_18(dbname):
    assert (
        e.contest_total(
            "2018 General",
            "Colorado",
            "CO Senate District 15",
            dbname=dbname,
        )
        == 83690
    )


def test_ak_rep_18(dbname):
    assert (
        e.contest_total(
            "2018 General",
            "Colorado",
            "CO House District 60",
            dbname=dbname,
        )
        == 39237
    )
