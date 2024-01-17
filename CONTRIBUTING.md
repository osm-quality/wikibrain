# Nonsense reports

Purpose of this tool is to find broken OpenStreetMap data.

But sometimes it detects broken Wikidata data.

Sometimes you get reports that make no sense whatosever. In many cases it happens because `wikidata` links are verified using Wikidata, which sometimes has bogus claims. At some point it claimed that [secondary education (Q14623204) is a process that takes place without human involvement](https://www.wikidata.org/wiki/User:Mateusz_Konieczny/failing_testcases/Archive_1#secondary_education_(Q14623204)_is_process_that_takes_place_without_human_involvement).

This specific one was fixed already but new ones can easily appear.

If you run tests in [test_wikidata_structure.py](test_wikidata_structure.py) with fresh cache you may get some reports about failures - that typically happens when broken ontology was reintroduced at Wikidata. In such case you can skip to step 3 (as test already exist)

## Step 1: recognize a problem

Errors claiming that castle is an event or that plantation is an object that exists outside physical reality are caused by broken Wikidata ontology.

At [one point](https://github.com/osm-quality/wikibrain/issues/10) a [forest plantation]()https://www.openstreetmap.org/relation/10031487) was listed as "an object that exists outside physical reality".
This is case where Wikidata had some silly ontology.

## Step 2: create a test

To prevent reoccurence of problem in generated reports it is useful to create test guarding against reoccurence - which will also ensure that code will not be broken without spotting it.

See [https://github.com/osm-quality/wikibrain/commit/d1ea32aa53c62350970b33c932072aa7f1815063](https://github.com/osm-quality/wikibrain/commit/d1ea32aa53c62350970b33c932072aa7f1815063) for an example.

When you run test suite something like

```
== {{Q|Q23734811}} is an object that exists outside physical reality, according to Wikidata ontology ==

en: plantation (artificially established forest, farm or estate, where crops are grown for sale) [https://www.wikidata.org/wiki/Q188913]
:en: forestry (science and craft of creating, managing, using, conserving and repairing forests, woodlands, and associated resources for human and environmental benefits) [https://www.wikidata.org/wiki/Q38112]
::en: engineering (applied science) [https://www.wikidata.org/wiki/Q11023]
:::en: applied science (discipline that applies existing scientific knowledge to develop more practical applications) [https://www.wikidata.org/wiki/Q28797]
::::en: science (systematic enterprise that builds and organizes knowledge, and the set of knowledge produced by this enterprise) [https://www.wikidata.org/wiki/Q336]
:::::en: knowledge system (systems of knowledge produced over time through interactions with other human beings) [https://www.wikidata.org/wiki/Q105948247]
::::::en: conceptual system (system composed of non-physical objects, i.e. ideas or concepts) [https://www.wikidata.org/wiki/Q3622126]
:::::::en: abstract entity (entity that exists outside physical reality, including abstract objects and properties) [https://www.wikidata.org/wiki/Q7048977] this was unexpected here as it indicates an object that exists outside physical reality !!!!!!!!!!!!!!!!!!!!!!!!!!
```

and

```
== {{Q|Q23734811}} classified as an object that exists outside physical reality ==
{{Q|Q188913}}
:{{Q|Q38112}}
::{{Q|Q11023}}
:::{{Q|Q28797}}
::::{{Q|Q336}}
:::::{{Q|Q105948247}}
::::::{{Q|Q3622126}}
:::::::{{Q|Q7048977}}
```

should appear in output.

## Step 3: report it to Wikidata community

This step is entirely optional and can be skipped.

I created [a page in my userspace](https://www.wikidata.org/wiki/User:Mateusz_Konieczny/failing_testcases) where I report some issues and as of 2024 some Wikidata editors process problems reported there.

Such broken ontology can be also reported at [Wikidata talk:WikiProject Ontology](https://www.wikidata.org/wiki/Wikidata_talk:WikiProject_Ontology) and [general discussion page](https://www.wikidata.org/wiki/Wikidata:Pump) but in general I usually post it on more specialized page.

This weird formatting of log above can be directly copy pasted onto wiki page. See [example report](https://www.wikidata.org/w/index.php?title=User:Mateusz_Konieczny/failing_testcases&diff=prev&oldid=2056198648). Feel free to use that user page to report such issues, as long as reports make sense.

## Step 4: insulate this tool from broken ontology

In example above Q188913 (plantation) was mistakenly classified as being subclass of forestry 
(Q38112).

As Q188913 has invalid classification it should be ignored.


This can be done by adding it to `workarounds_for_wikidata_bugs_breakage_and_mistakes` function which wuill cause it to be skipped.

This can be verified by running tests, newly added test should start passing.

Note that sometimes Wikidata entry is broken in several ways at once and multiple entries need to be added.

See [https://github.com/osm-quality/wikibrain/commit/94e9a12ece8c77b7b1ee16efc312d10bb8e29ec8]()https://github.com/osm-quality/wikibrain/commit/94e9a12ece8c77b7b1ee16efc312d10bb8e29ec8) for an example.
