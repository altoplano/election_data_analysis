import election_data_analysis as e


def test_data_exists(dbname):
    assert e.data_exists("2016 General", "Minnesota", dbname=dbname)


def test_mn_presidential_16(dbname):
    assert (
        e.contest_total(
            "2016 General",
            "Minnesota",
            "US President (MN)",
            dbname=dbname,
        )
        == 2944813
    )


def test_mn_senate_totals_16(dbname):
    assert (
        e.contest_total(
            "2016 General",
            "Minnesota",
            "MN Senate District 49",
            dbname=dbname,
        )
        == 51903
    )


def test_mn_house_totals_16(dbname):
    assert (
        e.contest_total(
            "2016 General",
            "Minnesota",
            "MN House District 4B",
            dbname=dbname,
        )
        == 20526
    )
