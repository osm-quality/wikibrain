import csv


def main():
    rows_grouped_by_language = {}

    # official_languages_from_wikidata.csv obtained from Wikidata
    # https://www.wikidata.org/w/index.php?title=Wikidata:Request_a_query&oldid=1776349815#Listing_countries_where_languages_have_status_of_an_official_language

    with open('official_languages_from_wikidata.csv') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader, None)
        for row in reader:
            language_name = row[1]
            wikidata_id = row[5].replace("http://www.wikidata.org/entity/", "")
            if wikidata_id == "Q504081":  # Greek military junta of 1967–1974 (yes, Wikidata as source was a mistake)
                continue
            if "Sign Language" in language_name:
                continue
            language_code = get_language_code_from_row(row)
            if language_code not in rows_grouped_by_language:
                rows_grouped_by_language[language_code] = []
            rows_grouped_by_language[language_code].append(row)

    for language_code in rows_grouped_by_language.keys():
        tab = "    "
        prefix = tab + tab
        rows = rows_grouped_by_language[language_code]
        language_name = rows[0][1]
        returned = ""
        returned += prefix + "if language_code == \"" + language_code + "\": # " + language_name + "\n"
        if len(rows) > 1:
            returned += prefix + tab + "return [\n"
            for row in rows:
                country_wikidata_where_language_is_official = row[5].replace("http://www.wikidata.org/entity/", "")
                country_name_where_language_is_official = row[6]
                returned += prefix + tab + tab + "\"" + country_wikidata_where_language_is_official + "\", # " + country_name_where_language_is_official + "\n"
            returned += prefix + tab + "]\n"
        else:
            country_wikidata_where_language_is_official = rows[0][5].replace("http://www.wikidata.org/entity/", "")
            returned += prefix + tab + "return [\"" + country_wikidata_where_language_is_official + "\"] # " + rows[0][6] + "\n"
        print(returned)


def get_language_code_from_row(row):
    language_codes = []
    if row[2] != "":
        language_codes.append(row[2])
    if row[3] != "":
        language_codes.append(row[3])
    if row[4] != "":
        language_codes.append(row[4])
    return language_codes[0]


main()
