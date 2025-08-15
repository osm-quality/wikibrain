import wikimedia_connection
from wikimedia_connection import wikimedia_connection
from wikimedia_connection import wikidata_processing
import geopy.distance
import re
import yaml
from wikibrain import wikipedia_knowledge
from wikibrain import wikidata_knowledge


class ErrorReport:
    def __init__(self, error_message=None, error_general_intructions=None, debug_log=None, error_id=None, prerequisite=None, extra_data=None, proposed_tagging_changes=None):
        # to include something in serialization - modify data function
        self.error_id = error_id
        self.error_message = error_message
        self.error_general_intructions = error_general_intructions
        self.debug_log = debug_log
        self.prerequisite = prerequisite
        self.extra_data = extra_data  # TODO - replace by more specific
        self.proposed_tagging_changes = proposed_tagging_changes
        self.osm_object_url = None
        self.location = None
        self.tags = None

    def bind_to_element(self, element):
        self.tags = element.get_tag_dictionary()
        self.osm_object_url = element.get_link()
        if element.get_coords() == None:
            self.location = (None, None)
        else:
            self.location = (element.get_coords().lat, element.get_coords().lon)

    def data(self):
        return {
            "error_id": self.error_id,
            "error_message": self.error_message,
            "error_general_intructions": self.error_general_intructions,
            "debug_log": self.debug_log,
            "osm_object_url": self.osm_object_url,
            "proposed_tagging_changes": self.proposed_tagging_changes,
            "extra_data": self.extra_data,
            "prerequisite": self.prerequisite,
            "location": self.location,
            "tags": self.tags,
        }

    def yaml_output(self, filepath):
        with open(filepath, 'a') as outfile:
            yaml.dump([self.data()], outfile, default_flow_style=False)


class WikimediaLinkIssueDetector:
    def __init__(self, forced_refresh=False, expected_language_code=None, languages_ordered_by_preference=None, additional_debug=False, allow_requesting_edits_outside_osm=False, allow_false_positives=False):
        if languages_ordered_by_preference == None:
            languages_ordered_by_preference = []
        self.forced_refresh = forced_refresh
        self.expected_language_code = expected_language_code
        self.languages_ordered_by_preference = languages_ordered_by_preference
        self.additional_debug = additional_debug
        self.allow_requesting_edits_outside_osm = allow_requesting_edits_outside_osm
        self.allow_false_positives = allow_false_positives

    @staticmethod
    def workarounds_for_wikidata_bugs_breakage_and_mistakes():
        wikidata_bugs = []
        wikidata_bugs += WikimediaLinkIssueDetector.workarounds_for_long_term_wikidata_bugs_breakage_and_mistakes()
        #return wikidata_bugs # count 14 extra errors, I guess (remember to reduce by count of open nonwikidata problems)

        # reported at https://www.wikidata.org/wiki/User:Mateusz_Konieczny/failing_testcases
        wikidata_bugs.append("Q117859862")
        wikidata_bugs.append("Q17362920")
        wikidata_bugs.append("Q1434274")
        wikidata_bugs.append("Q30022")
        wikidata_bugs.append("Q20437094")
        wikidata_bugs.append("Q16675884")
        wikidata_bugs.append("Q2973801")
        wikidata_bugs.append("Q2352616")
        wikidata_bugs.append("Q148571")
        wikidata_bugs.append("Q5307737")
        wikidata_bugs.append("Q60533375")
        wikidata_bugs.append("Q245188")
        wikidata_bugs.append("Q123585930")
        wikidata_bugs.append("Q350783")
        wikidata_bugs.append("Q97145897")
        wikidata_bugs.append("Q217102")
        wikidata_bugs.append("Q3456301")
        wikidata_bugs.append("Q1077064")
        wikidata_bugs.append('Q1067164')
        wikidata_bugs.append('Q1370468')
        wikidata_bugs.append('Q7590')
        wikidata_bugs.append('Q133346')
        wikidata_bugs.append('Q1292279')
        wikidata_bugs.append('Q676211')
        wikidata_bugs.append('Q30014735')
        wikidata_bugs.append('Q1441983')
        wikidata_bugs.append('Q854550')
        wikidata_bugs.append('Q2750030')
        wikidata_bugs.append('Q9311671')
        wikidata_bugs.append('Q1517374')
        wikidata_bugs.append('Q392371')
        wikidata_bugs.append('Q4736398')
        wikidata_bugs.append('Q3783831')
        wikidata_bugs.append('Q1962728')
        wikidata_bugs.append('Q745221')
        wikidata_bugs.append('Q3153117')
        wikidata_bugs.append('Q44946')
        wikidata_bugs.append('Q464980')
        wikidata_bugs.append('Q1233637')
        wikidata_bugs.append('Q3536096')
        wikidata_bugs.append('Q1193753')
        wikidata_bugs.append('Q8513')
        wikidata_bugs.append('Q23392')
        wikidata_bugs.append('Q1307347')
        wikidata_bugs.append('Q921099')
        wikidata_bugs.append('Q386147')
        wikidata_bugs.append('Q1232589')
        wikidata_bugs.append('Q8564039')
        wikidata_bugs.append('Q17493662')
        wikidata_bugs.append('Q8187769')
        wikidata_bugs.append('Q1341387')
        wikidata_bugs.append('Q15617994')
        wikidata_bugs.append('Q255848')
        wikidata_bugs.append('Q2494008')
        wikidata_bugs.append('Q47848')
        wikidata_bugs.append('Q2142845')
        wikidata_bugs.append('Q848330')
        wikidata_bugs.append('Q2918418')
        wikidata_bugs.append('Q25608610')        


        # see https://www.wikidata.org/wiki/User:Mateusz_Konieczny/failing_testcases#Kappa_Kappa_Kappa_(Q6367049)_is_an_object_that_exists_outside_physical_reality,_according_to_Wikidata_ontology
        # escalate? add to pernament ones?
        wikidata_bugs.append("Q18811583")  # sorority
        wikidata_bugs.append("Q18811582")  # faternity
        wikidata_bugs.append("Q992253")  # confraternity
        wikidata_bugs.append('Q69502391') # bus transit route

        return wikidata_bugs

    @staticmethod
    def workarounds_for_long_term_wikidata_bugs_breakage_and_mistakes():
        wikidata_bugs = []
        # Potentially fixable, but it is widespread problem affecting wikidata, not OSM
        # so extremely low priority

        # theatre as art form vs theatre as a building
        # that would be basically detecting only wikidata issues
        # not worth it
        # https://www.wikidata.org/wiki/Q11635
        # https://www.wikidata.org/wiki/Q24354
        wikidata_bugs.append("Q11635")

        # systematic confusion of newsagent as profession and newsagent as shop
        # not interested in spending time on fixing wikidata bugs
        # maybe if everything else will become fixed
        wikidata_bugs.append('Q1528905')

        # Considered as unfixable:

        # conflating two distinct things
        # but for tidal races there is no good solution
        # https://www.wikidata.org/w/index.php?title=User:Mateusz_Konieczny/failing_testcases&oldid=1921440592#The_Bitches_(Q878769)_(set_of_rocks)_is_a_physical_process,_according_to_Wikidata_ontology

        wikidata_bugs.append('Q495844')

        # walk of fame mess
        # https://www.wikidata.org/w/index.php?title=User:Mateusz_Konieczny/failing_testcases&oldid=1927584762#Walk_of_Fame_of_Cabaret_(Q2345775)_is_an_award,_according_to_Wikidata_ontology
        wikidata_bugs.append('Q47502370')

        # merging items
        # https://www.wikidata.org/w/index.php?title=User:Mateusz_Konieczny/failing_testcases&oldid=1937087915#Project_Riese_(Q320076)_classified_as_an_intentional_human_activity
        wikidata_bugs.append('Q170584')
        # https://www.wikidata.org/w/index.php?title=User:Mateusz_Konieczny/failing_testcases&oldid=2025970960#KATRIN_(Q316053)_is_a_human_activity,_according_to_Wikidata_ontology
        wikidata_bugs.append('Q101965')

        # Jesus mess
        # https://www.wikidata.org/w/index.php?title=User:Mateusz_Konieczny/failing_testcases&oldid=1940322493#Jesus_(Q302)_is_a_fictional_entity,_according_to_Wikidata_ontology
        wikidata_bugs.append('Q51625')
        wikidata_bugs.append('Q302')

        # Andorra is not for a sale
        wikidata_bugs.append('Q208500')

        # https://www.wikidata.org/wiki/Q15104297 - often applies to "open pit mine"
        # created https://www.wikidata.org/wiki/Q1323960
        wikidata_bugs.append('Q208500')

        # merging entries about general prosecutor office and general prosecutor as person and as profession
        # see https://www.wikidata.org/wiki/User:Mateusz_Konieczny/failing_testcases#Profession_or_office?
        wikidata_bugs.append('Q3368517')
        wikidata_bugs.append('Q169180')
        wikidata_bugs.append('Q83307')  # see https://www.wikidata.org/wiki/Q107919654 - minister vs ministry
        wikidata_bugs.append('Q10726370')  # other legal official position

        # hall of fame (list of outstanding individuals in a particular group,
        # which may or may not be embodied in a literal physical structure)
        # "may or may not be" blocks it from being useful
        wikidata_bugs.append('Q1046088')

        # wikidata mixes describing reality and internal project issues
        wikidata_bugs.append('Q1263068')

        return wikidata_bugs

    @staticmethod
    def reality_is_to_complicated_so_lets_ignore_that_parts_of_wikidata_ontology():
        skipped = []
        # proposed road https://www.wikidata.org/wiki/Q30106829
        # skipping this as sadly some proposed roads are actually mapped in OSM :(
        # and in this case there is no agreement to delete them :(
        skipped.append('Q30106829')
        # proposed rail infrastructure - applied to in-construction one
        # see https://www.wikidata.org/wiki/Q7985674
        skipped.append('Q28043022')
        # proposed building or structure
        skipped.append('Q811683')
        # proposed features in general
        skipped.append('Q64728694')

        # trademark is ignored as even hamlet can be trademarked
        # so it provides no extra info and detangling architecture here is too tricky
        # see https://www.wikidata.org/wiki/Q1392479
        skipped.append("Q167270")

        # physical object can be cultural symbols
        # https://www.wikidata.org/wiki/Q180376
        skipped.append("Q3139104")

        # or part of heritage
        # https://www.wikidata.org/wiki/Q10356475
        skipped.append("Q210272")

        # again, anything may be symbol of anything
        skipped.append("Q80071")

        # allow meridian linking due to meridian markers
        skipped.append("Q32099")

        # landslides are fine (despite being subclass of disaster that is subclass of an event)
        # there was weird associated behaviour but I am not going to
        # debug Wikidata structure and discover why landlide is classified
        # as a social issue
        # https://www.wikidata.org/wiki/Q167903
        skipped.append("Q167903")

        # https://www.wikidata.org/wiki/Q860863
        # merges event that created it and sculpture garden
        # likely unfixable
        # and if fixable then it should be fixed on my side by accepting
        # cases with both "sculpture garden" (physical) and "sculpture gathering" (event)
        skipped.append("Q860879")

        # messy, not worth dealing with, may be correct
        # https://www.openstreetmap.org/node/9724249774
        # https://www.openstreetmap.org/way/584197021
        skipped.append("Q175047")
        skipped.append("Q1415790")  # also in skipped_cases() to ensure full removal

        # awards are often closely linked to physical manifestations
        skipped.append("Q618779")

        # are ferry routes instances of intentional human activity?
        # see https://www.wikidata.org/w/index.php?title=User:Mateusz_Konieczny/failing_testcases&oldid=2046224482#Woolwich_Ferry_(Q2593299)_is_intentional_human_activity,_according_to_Wikidata_ontology
        skipped.append("Q18984099")
        skipped.append("Q20180855")
        # what about train routes?
        skipped.append("Q67454740")
        skipped.append("Q91908084")
        skipped.append("Q15141321")

        skipped.append("Q1567542")  # https://www.wikidata.org/wiki/Q27849294 landslide is reasonable to map in OSM and can be treated as event - so lets ignore this specific subclass of events (events are still not mappable)

        # we are not mapping services in OSM
        # except train/bus/etc routes
        return skipped

    @staticmethod
    def ignored_entries_in_wikidata_ontology_without_skipping_known_bugs():
        too_abstract_or_wikidata_bugs = wikidata_processing.wikidata_entries_for_abstract_or_very_broad_concepts()
        too_abstract_or_wikidata_bugs += WikimediaLinkIssueDetector.reality_is_to_complicated_so_lets_ignore_that_parts_of_wikidata_ontology()
        too_abstract_or_wikidata_bugs.append("Q13930359")  # many Volkfest are mapped in OSM - opened some probing notes for now, not sure whether they will be deleted
        too_abstract_or_wikidata_bugs.append("Q15275719")  # many recurring events are mapped in OSM - opened some probing notes for now, not sure whether they will be deleted
        too_abstract_or_wikidata_bugs.append("Q673514")  # many recurring events are mapped in OSM - opened some probing notes for now, not sure whether they will be deleted
        too_abstract_or_wikidata_bugs.append("Q132241")  # festivals in general are exempt for now
        too_abstract_or_wikidata_bugs.append("Q11706236")  # also church festivals
        return too_abstract_or_wikidata_bugs

    @staticmethod
    def ignored_entries_in_wikidata_ontology():
        too_abstract_or_wikidata_bugs = WikimediaLinkIssueDetector.ignored_entries_in_wikidata_ontology_without_skipping_known_bugs()
        too_abstract_or_wikidata_bugs += WikimediaLinkIssueDetector.workarounds_for_wikidata_bugs_breakage_and_mistakes()
        return too_abstract_or_wikidata_bugs

    def get_problem_for_given_element(self, element):
        tags = element.get_tag_dictionary()
        object_type = element.get_element().tag
        location = (element.get_coords().lat, element.get_coords().lon)
        object_description = self.describe_osm_object(element)
        return self.get_the_most_important_problem_generic(tags, location, object_type, object_description)

    def get_problem_for_given_tags(self, tags, object_type, object_description):
        location = None
        return self.get_the_most_important_problem_generic(tags, location, object_type, object_description)

    def get_the_most_important_problem_generic(self, tags, location, object_type, object_description):
        if self.object_should_be_deleted_not_repaired(object_type, tags):
            return None

        something_reportable = self.use_special_properties_allowing_to_ignore_wikipedia_tags(tags)
        if something_reportable != None:
            return something_reportable

        something_reportable = self.critical_structural_issue_report(object_type, tags)
        if something_reportable != None:
            if something_reportable.error_id == "wikipedia wikidata mismatch":
                if "#" in tags.get("wikipedia"):
                    something_reportable.error_id = "wikipedia wikidata mismatch, wikipedia links to section - high risk of false positive"
            return something_reportable

        something_reportable = self.freely_reorderable_issue_reports(object_description, location, tags)
        if something_reportable != None:
            return something_reportable

        something_reportable = self.add_wikipedia_and_wikidata_based_on_each_other(tags)
        if something_reportable != None:
            return something_reportable

        return None

    def use_special_properties_allowing_to_ignore_wikipedia_tags(self, tags):
        if tags.get("wikidata") != None:
            if tags.get("teryt:simc") != None:
                wikidata_simc_object = wikimedia_connection.get_property_from_wikidata(tags.get("wikidata"), 'P4046')
                if wikidata_simc_object == None:
                    return None
                wikidata_simc = wikidata_simc_object[0]['mainsnak']['datavalue']['value']
                if wikidata_simc != tags.get("teryt:simc"):
                    message = "mismatching teryt:simc codes in wikidata (" + tags.get("wikidata") + ") where " + str(wikidata_simc)
                    message += " is declared and in osm element, where teryt:simc="
                    message += tags.get("teryt:simc")
                    message += " is declared. TERYT database may be searched at http://eteryt.stat.gov.pl/eTeryt/rejestr_teryt/udostepnianie_danych/baza_teryt/uzytkownicy_indywidualni/wyszukiwanie/wyszukiwanie.aspx?contrast=default (switch to SIMC tab) "
                    return ErrorReport(
                        error_id="mismatching teryt:simc codes in wikidata and in osm element",
                        error_message=message,
                        prerequisite={'wikidata': tags.get("wikidata"), "teryt:simc": tags.get("teryt:simc")},
                    )
                wikipedia_expected = self.get_best_interwiki_link_by_id(tags.get("wikidata"))
                all_languages = wikipedia_knowledge.WikipediaKnowledge.all_wikipedia_language_codes_order_by_importance()
                if tags.get("wikipedia") != wikipedia_expected:
                    if wikipedia_expected != None:
                        message = "new wikipedia tag " + wikipedia_expected + " proposed based on matching teryt:simc codes in wikidata (" + tags.get("wikidata") + ") and in osm element, where teryt:simc=" + tags.get("teryt:simc") + " is declared"
                        return ErrorReport(
                            error_id="wikipedia needs to be updated based on wikidata code and teryt:simc identifier",
                            error_message=message,
                            prerequisite={'wikidata': tags.get("wikidata"), "teryt:simc": tags.get("teryt:simc"), 'wikipedia': tags.get("wikipedia"), },
                        )
                    else:
                        message = " it seems that wikipedia tag should be removed given matching teryt:simc codes in wikidata (" + tags.get("wikidata") + ") and in osm element, where teryt:simc=" + tags.get("teryt:simc") + " is declared"
                        return ErrorReport(
                            error_id="wikipedia tag needs to be removed based on wikidata code and teryt:simc identifier",
                            error_message=message,
                            prerequisite={'wikidata': tags.get("wikidata"), "teryt:simc": tags.get("teryt:simc"), 'wikipedia': tags.get("wikipedia"), },
                        )
        return None

    def critical_structural_issue_report(self, object_type, tags):
        #TODO - is it OK?
        #if tags.get("wikipedia").find("#") != -1:
        #    return "link to section (\"only provide links to articles which are 'about the feature'\" - http://wiki.openstreetmap.org/wiki/Key:wikipedia):"

        something_reportable = self.remove_old_style_wikipedia_tags(tags)
        if something_reportable != None:
            return something_reportable

        for key in tags.keys():
            if "wikidata" in key:
                something_reportable = self.check_is_wikidata_link_clearly_malformed(key, tags.get(key))
                if something_reportable != None:
                    return something_reportable

                something_reportable = self.check_is_wikidata_page_existing(key, tags.get(key))
                if something_reportable != None:
                    return something_reportable

            if "wikipedia" in key:
                if tags.get(key) == None:
                    print(tags)
                    raise Exception("impossible")
                something_reportable = self.check_is_wikipedia_link_clearly_malformed(key, tags.get(key))
                if something_reportable != None:
                    return something_reportable

                language_code = wikimedia_connection.get_language_code_from_link(tags.get(key))
                article_name = wikimedia_connection.get_article_name_from_link(tags.get(key))

                if key == "wikipedia":
                    something_reportable = self.check_is_wikipedia_page_existing(language_code, article_name)
                    if something_reportable != None:
                        return something_reportable
                else:
                    pass  # TODO, make check_is_wikipedia_page_existing support also secondary wikipedia tags

        if tags.get("wikipedia") != None:
            language_code = wikimedia_connection.get_language_code_from_link(tags.get("wikipedia"))
            article_name = wikimedia_connection.get_article_name_from_link(tags.get("wikipedia"))

            # early to ensure that passing later wikidata_id of article is not going to be confusing
            if tags.get("wikidata") != None: # in case of completely missing wikidata tag it is not a critical issue and will be solved
                                             # by add_wikipedia_and_wikidata_based_on_each_other
                something_reportable = self.check_for_wikipedia_wikidata_collision(tags, "wikidata", "wikipedia")
                if something_reportable != None:
                    return something_reportable
        for wikidata_key in tags.keys():
            if wikidata_key.find("wikidata") != -1:
                wikipedia_key = wikidata_key.replace("wikidata", "wikipedia")
                if wikipedia_key in tags:
                    something_reportable = self.check_for_wikipedia_wikidata_collision(tags, wikidata_key, wikipedia_key)
                    if something_reportable != None:
                        return something_reportable
        return None

    def add_wikipedia_and_wikidata_based_on_each_other(self, tags):
        wikidata_id = None
        if tags.get("wikipedia") != None:
            wikidata_id = wikimedia_connection.get_wikidata_object_id_from_link(tags.get("wikipedia"))
        something_reportable = self.check_is_wikidata_tag_is_misssing(tags.get('wikipedia'), tags.get('wikidata'), wikidata_id)
        if something_reportable != None:
            return something_reportable

        old_style_wikipedia_tags = self.get_old_style_wikipedia_keys(tags)

        if tags.get("wikipedia") != None:
            return None

        if tags.get('wikidata') != None and old_style_wikipedia_tags == []:
            return self.get_wikipedia_from_wikidata_assume_no_old_style_wikipedia_tags(tags.get('wikidata'), tags)

        return None

    def get_effective_wikipedia_tag(self, tags):
        wikipedia = tags.get('wikipedia')
        if wikipedia != None:
            return wikipedia
        return self.get_best_interwiki_link_by_id(tags.get('wikidata'))

    def get_effective_wikidata_tag(self, tags):
        wikidata_id = tags.get('wikidata')
        if wikidata_id != None:
            return wikidata_id
        wikipedia = tags.get('wikipedia')
        if wikipedia != None:
            return wikimedia_connection.get_wikidata_object_id_from_link(tags.get("wikipedia"))
        return None

    def replace_prerequisites_to_match_actual_tags(self, something_reportable, tags):
        """
        hack necessary in some cases :(

        object may have no wikidata tag at all, but it may be calculated from wikipedia tag
        in such case report may be made about wikidata_id indicating a clear issue, such as link to a disambig page

        in such case using reprequisite with wikidata=QXXXXX is wrong as object has no such tag,
        it is necessary to replace it by an actual source

        in this case function blindly assumes that wikipedia is a good replacement

        TODO: replace this monstrous hack
        """
        if 'wikidata' in something_reportable.prerequisite:
            if 'wikidata' not in tags and 'wikipedia' in tags:
                something_reportable.prerequisite.pop('wikidata')
                something_reportable.prerequisite['wikipedia'] = tags['wikipedia']
        return something_reportable

    def freely_reorderable_issue_reports(self, object_description, location, tags):
        if "fixme:wikipedia" in tags:
            return ErrorReport(
                error_id="something is wrong with wikipedia tag - fixme:wikipedia is present",
                error_message="see fixme:wikipedia tag for hints",
                prerequisite={'fixme:wikipedia': tags.get("wikipedia")},
            )

        effective_wikipedia = self.get_effective_wikipedia_tag(tags)
        effective_wikidata_id = self.get_effective_wikidata_tag(tags)
        # Note that wikipedia may be None - maybe there is just a Wikidata entry!
        # Note that effective_wikidata_id may be None - maybe it was not created yet!

        # IDEA links from buildings to parish are wrong - but from religious admin are OK https://www.wikidata.org/wiki/Q11808149

        if effective_wikidata_id in wikidata_knowledge.skipped_cases():
            return None  # manually excluded

        something_reportable = self.get_problem_based_on_wikidata_blacklist(effective_wikidata_id, tags.get('wikidata'), effective_wikipedia)
        if something_reportable != None:
            return self.replace_prerequisites_to_match_actual_tags(something_reportable, tags)

        if tags.get("information") == "board":
            if tags.get("wikipedia") != None:
                return ErrorReport(
                    error_id="information board with wikipedia tag, not subject:wikipedia",
                    error_message="information board topic must be tagged with subject:wikipedia tag - not with wikipedia tag",
                    prerequisite={'wikipedia': tags.get("wikipedia"), "information": tags.get("information")},
                )
            if tags.get("wikidata") != None:
                return ErrorReport(
                    error_id="information board with wikidata tag, not subject:wikidata",
                    error_message="information board topic must be tagged with subject:wikidata tag - not with wikipedia tag",
                    prerequisite={'wikidata': tags.get("wikidata"), "information": tags.get("information")},
                )

        for key in tags.keys():
            if key.find("not:") == 0:
                being_checked_key = key[4:]
                if being_checked_key in tags:
                    if tags[being_checked_key] == tags[key]:
                        if "wikipedia" in key or "wikidata" in key:
                            return ErrorReport(
                                error_id="wikipedia/wikidata type tag that is incorrect according to not:* tag",
                                error_message=being_checked_key + "=" + tags.get(being_checked_key) + " is present despite that " + key + "=" + tags[key] + " is also present - at least one of them is wrong",
                                prerequisite={being_checked_key: tags.get(being_checked_key), key: tags.get(key)},
                            )
                        else:
                            print("not: key (not concerning wikipedia/wikidata) is being ignored in", object_description)

        something_reportable = self.get_problem_based_on_wikidata_and_osm_element(object_description, location, effective_wikidata_id, tags)
        if something_reportable != None:
            if something_reportable.error_id == "link to a list" and tags.get("wikipedia") != None and "#" in tags.get("wikipedia"):
                pass
                # not actually a real error, I think
            else:
                return self.replace_prerequisites_to_match_actual_tags(something_reportable, tags)

        something_reportable = self.get_wikipedia_language_issues(object_description, tags, tags.get("wikipedia"), effective_wikidata_id)
        if something_reportable != None:
            return something_reportable

        something_reportable = self.check_is_object_is_existing(effective_wikidata_id)
        if something_reportable != None:
            return something_reportable

        if "brand:wikidata" in tags:
            something_reportable = self.check_is_object_brand_is_existing(tags)
            if something_reportable != None:
                return something_reportable

        if "bridge:wikipedia" in tags and "bridge:wikidata" in tags:
            return ErrorReport(
                error_id="bridge:wikipedia and bridge:wikidata - move to bridge outline",
                error_message="bridge:wikipedia and bridge:wikidata links should be tagged on man_made=bridge outline - without prefixes as wikipedia=* and wikidata=*, not on way across bridge. man_made=bridge object may be missing and it may be necessary to draw it, it may be useful to move also some other bridge tags",
                prerequisite={'bridge:wikipedia': tags.get("bridge:wikipedia"), 'bridge:wikidata': tags.get("bridge:wikipedia")},
            )

        if "bridge:wikipedia" in tags:
            return ErrorReport(
                error_id="bridge:wikipedia - move to bridge outline",
                error_message="bridge:wikipedia link should be tagged on man_made=bridge outline - without prefix, as just wikipedia=*, not on way across bridge. man_made=bridge object may be missing and it may be necessary to draw it, it may be useful to move also some other bridge tags",
                prerequisite={'bridge:wikipedia': tags.get("bridge:wikipedia"), 'bridge:wikidata': tags.get("bridge:wikipedia")},
            )

        if "bridge:wikidata" in tags:
            return ErrorReport(
                error_id="bridge:wikipedia and bridge:wikidata - move to bridge outline",
                error_message="bridge:wikidata link should be tagged on man_made=bridge outline - without prefix, as just wikidata=*, not on way across bridge. man_made=bridge object may be missing and it may be necessary to draw it, it may be useful to move also some other bridge tags",
                prerequisite={'bridge:wikipedia': tags.get("bridge:wikipedia"), 'bridge:wikidata': tags.get("bridge:wikipedia")},
            )

        return None

    def get_problem_based_on_wikidata_blacklist(self, wikidata_id, present_wikidata_id, link):
        if wikidata_id == None:
            wikidata_id = present_wikidata_id

        try:
            prefix = wikidata_knowledge.blacklist_of_unlinkable_entries()[wikidata_id]['prefix']
        except KeyError:
            return None

        message = ("it is a typical wrong link and it has an obvious replacement, " +
                   prefix + "wikipedia/" + prefix + "wikidata should be used instead")

        return ErrorReport(
            error_id="blacklisted connection with known replacement",
            error_message=message,
            prerequisite={'wikipedia': link, 'wikidata': present_wikidata_id},
            extra_data=prefix
        )

    def check_is_wikidata_page_existing(self, key, present_wikidata_id):
        if not self.is_an_actual_wikidata_or_wikipedia_key(key):
            # not an actual wikidata link, see https://www.openstreetmap.org/way/139505589
            return None
        if present_wikidata_id == None:
            raise Exception("check_is_wikidata_page_existing null pointer exception on " + key)
        wikidata = wikimedia_connection.get_data_from_wikidata_by_id(present_wikidata_id)
        if wikidata != None:
            return None
        error_id_description = "wikidata tag links to 404"
        if key != "wikidata":
            error_id_description = "secondary wikidata tag links to 404"
            if ";" in present_wikidata_id:
                for part in present_wikidata_id.split(";"):
                    returned = self.check_is_wikidata_page_existing(key, part)
                    if returned != None:
                        return returned
                return None
        link = wikimedia_connection.wikidata_url(present_wikidata_id)
        return ErrorReport(
            error_id=error_id_description,
            error_message=key + " tag present on element points to not existing element (" + link + ")",
            prerequisite={key: present_wikidata_id},
        )

    def check_is_wikipedia_link_clearly_malformed(self, key, link):
        if link == None:
            raise Exception("Null pointer exception, unexpected None in link")
        if self.is_wikipedia_tag_clearly_broken(link):
            return self.malformed_secondary_link_error("wikipedia", key, link)
        else:
            language_code = wikimedia_connection.get_language_code_from_link(link)
            if language_code in wikipedia_knowledge.WikipediaKnowledge.wikipedia_language_code_redirects():
                return ErrorReport(
                    error_id="wikipedia tag using redirecting language code",
                    error_message="language code (" + language_code + ") in wikipedia tag (" + link + ") points to redirecting language code, see https://en.wikipedia.org/wiki/List_of_Wikipedias#Redirects",
                    prerequisite={'wikipedia': link},
                )
            if language_code not in wikimedia_connection.interwiki_language_codes():
                return ErrorReport(
                    error_id="malformed wikipedia tag - nonexisting language code",
                    error_message="language code (" + language_code + ") in wikipedia tag (" + link + ") points to nonexisting Wikipedia",
                    prerequisite={'wikipedia': link},
                )
            return None

    def check_is_wikidata_link_clearly_malformed(self, key, link):
        if key == "name:etymology:wikidata:missing":
            if link == "yes":
                return ErrorReport(
                    error_id="name:etymology:wikidata:missing",
                    error_message="name:etymology:wikidata:missing with value '" + link + "' - a really dubious tagging scheme, just create missing wikidata entries if you really need them. See also https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&oldid=1800873697#Is_someone_who_is_a_patron_of_a_street_always_notable_enough_for_Wikidata_identifier?",
                    prerequisite={key: link},
                )

        if self.is_wikidata_tag_clearly_broken(link):
            return self.malformed_secondary_link_error("wikidata", key, link)
        else:
            return None

    def malformed_secondary_link_error(self, wikidata_or_wikipedia, key, link):
        if key == wikidata_or_wikipedia:
            return ErrorReport(
                error_id="malformed " + wikidata_or_wikipedia + " tag",
                error_message="malformed value in " + key + " tag (" + link + ")",
                prerequisite={key: link},
            )
        if not self.is_an_actual_wikidata_or_wikipedia_key(key):
            return None
        if key.endswith(":" + wikidata_or_wikipedia):
            prefix = key[:-len(":" + wikidata_or_wikipedia)]
            return ErrorReport(
                error_id="malformed secondary " + wikidata_or_wikipedia + " tag - for " + prefix + " prefixed tags",
                error_message="malformed value in " + key + " tag (" + link + ")",
                prerequisite={key: link},
            )
        else:
            return ErrorReport(
                error_id="malformed secondary " + wikidata_or_wikipedia + " tag for " + key + " tag",
                error_message="malformed value in " + key + " tag (" + link + ")",
                prerequisite={key: link},
            )

    def is_an_actual_wikidata_or_wikipedia_key(self, key):
        for entry in [
            'fixme:wikidata',  # note "something is wrong with wikipedia tag - fixme:wikipedia is present" report

            # have freeform format
            "note:wikidata", "wikidata:note", "source:wikidata", "source:species:wikidata",
            "name:etymology:wikidata:fixme",
            'name:etymology:wikidata:note',

            # not worth a special support
            "image:license:wikidata",

            # per lane
            'destination:ref:to:wikidata:lanes',
            'destination:ref:wikidata:lanes',
            'destination:ref:wikidata:lanes:forward',
            'destination:ref:wikidata:lanes:backward',
            'destination:ref:to:wikidata:lanes:backward',
            'destination:ref:to:wikidata:lanes',
        ]:
            if key == entry:
                return False
            if key == entry.replace("wikidata", "wikipedia"):
                return False
        for warn_part in ["lanes", "note", "fixme"]:
            if ":" + warn_part in key:
                return False
            if warn_part + ":" in key:
                return False
        return True

    def check_is_wikidata_tag_is_misssing(self, wikipedia, present_wikidata_id, wikidata_id):
        if present_wikidata_id == None and wikidata_id != None:
            return ErrorReport(
                error_id="wikidata from wikipedia tag",
                error_message=wikidata_id + " may be added as wikidata tag based on wikipedia tag",
                prerequisite={'wikipedia': wikipedia, 'wikidata': None}
            )
        else:
            return None

    def check_is_wikipedia_page_existing(self, language_code, article_name):
        page_according_to_wikidata = wikimedia_connection.get_interwiki_article_name(language_code, article_name, language_code, self.forced_refresh)
        if page_according_to_wikidata != None:
            # assume that wikidata is correct to save downloading page
            return None
        page = wikimedia_connection.get_wikipedia_page(language_code, article_name, self.forced_refresh)
        if page == None:
            wikidata_id = wikimedia_connection.get_wikidata_object_id_from_article(language_code, article_name)
            return self.report_failed_wikipedia_page_link(language_code, article_name, wikidata_id)

    def get_best_interwiki_link_by_id(self, wikidata_id):
        all_languages = wikipedia_knowledge.WikipediaKnowledge.all_wikipedia_language_codes_order_by_importance()
        for potential_language_code in (self.languages_ordered_by_preference + all_languages):
            if potential_language_code != None:
                potential_article_name = wikimedia_connection.get_interwiki_article_name_by_id(wikidata_id, potential_language_code, self.forced_refresh)
                if potential_article_name != None:
                    return potential_language_code + ':' + potential_article_name
        return None

    def report_failed_wikipedia_page_link(self, language_code, article_name, wikidata_id):
        error_general_intructions = ""
        error_general_intructions += "Wikipedia article linked from OSM object using wikipedia tag is missing.\n"
        error_general_intructions += "Often article was moved without leaving redirect and wikipedia tag should be edited to point to the new one.\n"
        error_general_intructions += "Article may be deleted and no longer existing, or link was never valid. In such cases wikipedia tag should be deleted."
        proposed_new_target = self.get_best_interwiki_link_by_id(wikidata_id)
        message = ""
        if proposed_new_target != None:
            message += " wikidata tag present on element points to an existing article"
        return ErrorReport(
            error_id="wikipedia tag links to 404",
            error_general_intructions=error_general_intructions,
            error_message=message,
            prerequisite={'wikipedia': language_code+":"+article_name},
            proposed_tagging_changes=[{"from": {"wikipedia": language_code+":"+article_name}, "to": {"wikipedia": proposed_new_target}}],
        )

    def wikidata_data_quality_warning(self):
        return "REMEMBER TO VERIFY! WIKIDATA QUALITY MAY BE POOR! WIKIDATA MUST NOT BE USED AS SOURCE! ALWAYS VERIFY!"

    def check_is_object_is_existing(self, present_wikidata_id):
        if present_wikidata_id == None:
            return None
        no_longer_existing = wikimedia_connection.get_property_from_wikidata(present_wikidata_id, 'P576')
        if no_longer_existing != None:
            error_general_intructions = "Wikidata claims that this object no longer exists. Historical, no longer existing object should not be mapped in OSM (except temporary marking to avoid remapping them from aerial imagery or similar sources) - so it means that either Wikidata is mistaken or has only partial data - for example it is fine to link ruins of a church to its wikipedia entry ( see https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&oldid=1361617968#Tagging_ruins/remains_left_after_object ) or wikipedia/wikidata tag is wrong or OSM has an outdated object that should be removed." + " " + self.wikidata_data_quality_warning()
            message = ""
            return ErrorReport(
                error_id="no longer existing object (according to Wikidata)",
                error_general_intructions=error_general_intructions,
                error_message=message,
                prerequisite={'wikidata': present_wikidata_id}
            )

    @staticmethod
    def get_dissolved_brands(present_wikidata_ids: list):
        dissolved_brands = []
        for present_wikidata_id in present_wikidata_ids:
            no_longer_existing = wikimedia_connection.get_property_from_wikidata(present_wikidata_id, 'P576')
            if no_longer_existing is None:
                continue

            for existence_blockade in no_longer_existing:
                try:
                    excluding = existence_blockade['qualifiers']['P1011']
                    continue
                except KeyError:
                    # P1011 is missing, therefore it is not marked as a statement partially excluded
                    dissolved_brands.append(present_wikidata_id)
        return dissolved_brands

    def check_is_object_brand_is_existing(self, tags):
        marked_as_defunct = False
        marked_as_active = False
        for main_tag in ["office", "shop", "leisure", "amenity"]:
            for disused_prefix in ["disused:", "abandoned:"]:
                if tags.get(disused_prefix + main_tag) != None:
                    marked_as_defunct = True
                if main_tag == "shop" and tags.get(main_tag) == "vacant":
                    marked_as_defunct = True
                if tags.get(main_tag) not in [None, "no", "vacant"]:
                    marked_as_active = True
        present_wikidata_id = tags.get("brand:wikidata")
        if present_wikidata_id == None:
            return None

        dissolved_brands = self.get_dissolved_brands(present_wikidata_id.split(';'))
        if dissolved_brands:
            error_general_intructions = "Wikidata claims that assigned brand object no longer exists. That means that either this shop is gone or it is rebranded. Or brand:wikidata tag is wrong. Historical, no longer existing object should not be mapped in OSM." + " " + self.wikidata_data_quality_warning()
            message = "wikidata " + ", ".join(dissolved_brands) + " is marked as dissolved"
            state = "no longer existing brand (according to Wikidata)"
            if marked_as_defunct and not marked_as_active:
                # see say https://www.openstreetmap.org/way/80889053
                #
                # disused:shop = department_store
                # brand:wikidata = <pointing at defunct brand>
                #
                # should not raise alarms
                return None
            if marked_as_defunct == False and marked_as_active == True:
                state += " - and marked as active shop in OSM"
            elif marked_as_defunct == True and marked_as_active == True:
                state += " - and marked as active shop in OSM, with tagging referring to defunct one"
            elif marked_as_defunct == False and marked_as_active == False:
                state += " - and tag processing has not worked well"
            else:
                raise Exception("supposed to be impossible")
            return ErrorReport(
                error_id=state,
                error_general_intructions=error_general_intructions,
                error_message=message,
                prerequisite={'wikidata': present_wikidata_id}
            )

    def tag_from_wikidata(self, present_wikidata_id, wikidata_property):
        from_wikidata = wikimedia_connection.get_property_from_wikidata(present_wikidata_id, wikidata_property)
        if from_wikidata == None:
            return None
        returned = wikidata_processing.decapsulate_wikidata_value(from_wikidata)
        if not isinstance(returned, str):
            print(present_wikidata_id + " unexpectedly failed within decapsulate_wikidata_value for property " + wikidata_property)
            return None
        return returned

    def generate_error_report_for_tag_from_wikidata(self, from_wikidata, present_wikidata_id, osm_key, element, id_suffix="", message_suffix=""):
        if element.get_tag_value(osm_key) == None:
            return ErrorReport(
                error_id="tag may be added based on wikidata" + id_suffix,
                error_message=str(from_wikidata) + " may be added as " + osm_key + " tag based on wikidata entry" + message_suffix + " " + self.wikidata_data_quality_warning(),
                prerequisite={'wikidata': present_wikidata_id, osm_key: None}
            )
        elif element.get_tag_value(osm_key) != from_wikidata:
            if not self.allow_requesting_edits_outside_osm:
                # typically Wikidata is wrong, not OSM
                return None
            message = str(from_wikidata) + " conflicts with " + element.get_tag_value(osm_key) + " for " + osm_key + " tag based on wikidata entry - note that OSM value may be OK and Wikidata entry is wrong, in that case one may either ignore this error or fix Wikidata entry" + message_suffix + " " + self.wikidata_data_quality_warning()
            return ErrorReport(
                error_id="tag conflict with wikidata value" + id_suffix,
                error_message=message,
                prerequisite={'wikidata': present_wikidata_id, osm_key: element.get_tag_value(osm_key)}
            )

    def get_old_style_wikipedia_keys(self, tags):
        old_style_wikipedia_tags = []
        for key in tags.keys():
            if key.find("wikipedia:") != -1:
                old_style_wikipedia_tags.append(key)
        return old_style_wikipedia_tags

    def remove_old_style_wikipedia_tags(self, tags):
        old_style_wikipedia_tags = self.get_old_style_wikipedia_keys(tags)

        reportable = self.check_is_invalid_old_style_wikipedia_tag_present(old_style_wikipedia_tags, tags)
        if reportable:
            return reportable

        if old_style_wikipedia_tags != []:
            return self.convert_old_style_wikipedia_tags(old_style_wikipedia_tags, tags)
        return None

    def check_is_invalid_old_style_wikipedia_tag_present(self, old_style_wikipedia_tags, tags):
        for key in old_style_wikipedia_tags:
            if not self.check_is_it_valid_key_for_old_style_wikipedia_tag(key):
                return ErrorReport(
                    error_id="invalid old-style wikipedia tag",
                    error_message="wikipedia tag in outdated form (" + key + "), is not using any known language code",
                    prerequisite={key: tags[key]},
                )
        return None

    def check_is_it_valid_key_for_old_style_wikipedia_tag(self, key):
        for lang in wikipedia_knowledge.WikipediaKnowledge.all_wikipedia_language_codes_order_by_importance():
            if "wikipedia:" + lang == key:
                return True
        return False

    def normalized_id_with_conflicts_list(self, links, wikidata_id):
        normalized_link_form = wikidata_id  # may be None
        conflict_list = []
        for link in links:
            if link == None:
                conflict_list.append("one of links has value None")
            else:
                id_from_link = wikimedia_connection.get_wikidata_object_id_from_link(link, self.forced_refresh)

                if normalized_link_form == None and id_from_link != None:
                    normalized_link_form = id_from_link
                    continue
                if normalized_link_form == id_from_link and id_from_link != None:
                    continue

                language_code = wikimedia_connection.get_language_code_from_link(link)
                article_name = wikimedia_connection.get_article_name_from_link(link)
                if article_name == None or language_code == None:
                    conflict_list.append("one of links (" + link + ") has unexpected invalid format")
                    continue
                try:
                    title_after_possible_redirects = self.get_article_name_after_redirect(language_code, article_name)
                    is_article_redirected = (article_name != title_after_possible_redirects and article_name.find("#") == -1)
                    if is_article_redirected:
                        id_from_link = wikimedia_connection.get_wikidata_object_id_from_article(language_code, title_after_possible_redirects, self.forced_refresh)
                except wikimedia_connection.TitleViolatesKnownLimits:
                    pass # redirected link is invalied and not reported as noexsiting - typically due to "feature" of special handling invalid ling with lang: prefixes
                         # for example asking about en:name article on Polish-language will return info whethere "name" article exists on enwiki!
                         # as result special check and throwing this exception is done on invalid ones
                         # and in case of link leading nowhere nothing special needs to be done and it can be silently swallowed

                if normalized_link_form == None and id_from_link != None:
                    normalized_link_form = id_from_link
                    continue
                if normalized_link_form == id_from_link and id_from_link != None:
                    continue

                text_link_description = None
                if id_from_link == None:
                    text_link_description = "no link"
                else:
                    text_link_description = "link " + id_from_link
                conflict_list.append(link + " gives " + text_link_description + " conflicting with another link " + str(normalized_link_form))
        return normalized_link_form, conflict_list

    def convert_old_style_wikipedia_tags(self, wikipedia_type_keys, tags):
        links = self.wikipedia_candidates_based_on_old_style_wikipedia_keys(tags, wikipedia_type_keys)

        if tags.get('wikipedia') != None:
            links.append(tags.get('wikipedia'))

        prerequisite = {}
        prerequisite['wikidata'] = tags.get('wikidata')
        prerequisite['wikipedia'] = tags.get('wikipedia')
        for key in wikipedia_type_keys:
            prerequisite[key] = tags.get(key)

        normalized, conflicts = self.normalized_id_with_conflicts_list(links, tags.get('wikidata'))
        if conflicts != []:
            return ErrorReport(
                error_id="wikipedia tag in outdated form and there is mismatch between links",
                error_message="wikipedia tag in outdated form (" + str(wikipedia_type_keys) + ", with following conflicts: " + str(conflicts) + "). Mismatch between different links happened and requires human judgment to solve.",
                prerequisite=prerequisite,
            )
        elif tags.get('wikipedia') == None:
            new_wikipedia = self.get_best_interwiki_link_by_id(normalized)
            return ErrorReport(
                error_id="wikipedia tag from wikipedia tag in an outdated form",
                error_message="wikipedia tag in outdated form (" + str(wikipedia_type_keys) + "), wikipedia tag may be added",
                prerequisite=prerequisite,
                proposed_tagging_changes=[{"from": {"wikipedia": None}, "to": {"wikipedia": new_wikipedia}}],
            )
        else:
            from_tags = {}
            for key in wikipedia_type_keys:
                from_tags[key] = tags.get(key)
            return ErrorReport(
                error_id="wikipedia tag in an outdated form for removal",
                error_message="wikipedia tag in outdated form (" + str(wikipedia_type_keys) + "), with wikipedia and wikidata tag present and may be safely removed",
                prerequisite=prerequisite,
                proposed_tagging_changes=[{"from": from_tags, "to": {}}],
            )

    def get_wikipedia_from_wikidata_assume_no_old_style_wikipedia_tags(self, present_wikidata_id, tags):
        # present_wikidata_id is string with, well, wikidata id (such as "Q42")
        # tags is dictionary represeting OSM tags of the object
        location = (None, None)
        description = "object with wikidata=" + present_wikidata_id
        problem_indicated_by_wikidata = self.get_problem_based_on_wikidata(present_wikidata_id, tags, description, location)
        if problem_indicated_by_wikidata:
            return problem_indicated_by_wikidata

        link = self.get_best_interwiki_link_by_id(present_wikidata_id)
        if link == None:
            return None
        language_code = wikimedia_connection.get_language_code_from_link(link)
        if language_code in ["ceb"]:
            return None  # not a real Wikipedia
        elif language_code == self.expected_language_code:
            return ErrorReport(
                error_id="wikipedia from wikidata tag",
                error_message="without wikipedia tag, without wikipedia:language tags, with wikidata tag present that provides article, article language is not surprising",
                prerequisite={'wikipedia': None, 'wikidata': present_wikidata_id},
                proposed_tagging_changes=[{"from": {"wikipedia": None}, "to": {"wikipedia": link}}],
            )
        else:
            return ErrorReport(
                error_id="wikipedia from wikidata tag, unexpected language",
                error_message="without wikipedia tag, without wikipedia:language tags, with wikidata tag present that provides article",
                prerequisite={'wikipedia': None, 'wikidata': present_wikidata_id},
                proposed_tagging_changes=[{"from": {"wikipedia": None}, "to": {"wikipedia": link}}],
            )

    def wikipedia_candidates_based_on_old_style_wikipedia_keys(self, tags, wikipedia_type_keys):
        links = []
        for key in wikipedia_type_keys:
            language_code = wikimedia_connection.get_text_after_first_colon(key)  # wikipedia:pl -> pl
            article_name = tags.get(key)
            article_link_from_old_style_tag = language_code + ":" + article_name
            if ":" in article_name:
                potential_already_present_prefix_length = len(language_code) + 1
                if language_code + ":" == article_name[:potential_already_present_prefix_length]:
                    # cases like https://www.openstreetmap.org/node/1735170302
                    # wikipedia:de = de:Troszyn (Mieszkowice)
                    # note double de
                    article_link_from_old_style_tag = article_name
                    language_code = wikimedia_connection.get_text_before_first_colon(article_name)
                    article_name = wikimedia_connection.get_text_after_first_colon(article_name)

            wikidata_id = wikimedia_connection.get_wikidata_object_id_from_article(language_code, article_name)
            if wikidata_id == None:
                links.append(article_link_from_old_style_tag)
                continue

            link = self.get_best_interwiki_link_by_id(wikidata_id)
            if link == None:
                links.append(article_link_from_old_style_tag)
                continue

            links.append(link)
        return list(set(links))

    def get_wikidata_id_after_redirect(self, wikidata_id, forced_refresh=False):
        wikidata_data = wikimedia_connection.get_data_from_wikidata_by_id(wikidata_id, forced_refresh)
        try:
            return wikidata_data['entities'][wikidata_id]['id']
        except (TypeError, KeyError) as e:
            print(e)
            print("requested <" + str(wikidata_id) + ">)")
            print(wikidata_data)
            return None

    def get_article_name_after_redirect(self, language_code, article_name):
        try:
            return wikimedia_connection.get_from_wikipedia_api(language_code, "", article_name)['title']
        except KeyError as e:
            print(e)
            print("requested <" + str(language_code) + ", <" + str(article_name) + ">)")
            raise e

    def check_for_wikipedia_wikidata_collision(self, tags, wikidata_key, wikipedia_key):
        language_code = wikimedia_connection.get_language_code_from_link(tags.get(wikipedia_key))
        article_name = wikimedia_connection.get_article_name_from_link(tags.get(wikipedia_key))
        present_wikidata_id = tags.get(wikidata_key)
        if self.is_wikidata_tag_clearly_broken_or_with_multiple_values(present_wikidata_id):
            # TODO: support somehow
            # worth doing only after I start running out of errors to report to people
            return None
        prefix = wikidata_key.replace(":wikidata", "")
        error_id_suffix = ""
        if wikidata_key != "wikidata":
            error_id_suffix = " - for " + prefix + " prefixed tags"

        if prefix == "not":
            return None  # not really worth validating, various assumprions are not applying
                         # technically even not:wikidata=ogórek is valid tag
                         # not:wikidata and not:wikipedia may mismatch
                         # and so on

        if present_wikidata_id == None:
            return None

        if article_name == None:
            return None
        article_name_with_section_stripped = article_name
        if article_name.find("#") != -1:
            article_name_with_section_stripped = re.match('([^#]*)#(.*)', article_name).group(1)

        wikidata_id_from_article = wikimedia_connection.get_wikidata_object_id_from_article(language_code, article_name_with_section_stripped, self.forced_refresh)
        if present_wikidata_id == wikidata_id_from_article:
            return None

        base_message = wikidata_key + " and " + wikipedia_key + " tags link to a different objects"
        common_message = base_message + ", because " + wikidata_key + " tag points to a redirect that should be followed"
        message = self.compare_wikidata_ids(present_wikidata_id, wikidata_id_from_article)
        maybe_redirected_wikidata_id = self.get_wikidata_id_after_redirect(present_wikidata_id)
        if maybe_redirected_wikidata_id != present_wikidata_id:
            if maybe_redirected_wikidata_id == wikidata_id_from_article:
                return ErrorReport(
                    error_id="wikipedia wikidata mismatch - follow wikidata redirect" + error_id_suffix,
                    error_general_intructions=common_message,
                    error_message=message,
                    prerequisite={wikidata_key: present_wikidata_id, wikipedia_key: language_code+":"+article_name},
                )

        title_after_possible_redirects = article_name
        try:
            title_after_possible_redirects = self.get_article_name_after_redirect(language_code, article_name)
        except wikimedia_connection.TitleViolatesKnownLimits:
            return ErrorReport(
                error_id="malformed wikipedia tag" + error_id_suffix,
                error_message="malformed " + wikipedia_key + " tag (" + language_code + ":" + article_name + ")",
                prerequisite={wikipedia_key: language_code + ":" + article_name},
            )

        is_article_redirected = (article_name != title_after_possible_redirects and article_name.find("#") == -1)
        if is_article_redirected:
            wikidata_id_from_redirect = wikimedia_connection.get_wikidata_object_id_from_article(language_code, title_after_possible_redirects, self.forced_refresh)
            if present_wikidata_id == wikidata_id_from_redirect:
                common_message = base_message + ", because " + wikipedia_key + " tag points to a redirect that should be followed"
                message = self.compare_wikidata_ids(present_wikidata_id, wikidata_id_from_article)
                message += " article redirects from " + language_code + ":" + article_name + " to " + language_code + ":" + title_after_possible_redirects
                new_wikipedia_link = language_code+":"+title_after_possible_redirects
                return ErrorReport(
                    error_id="wikipedia wikidata mismatch - follow wikipedia redirect" + error_id_suffix,
                    error_general_intructions=common_message,
                    error_message=message,
                    prerequisite={wikidata_key: present_wikidata_id, wikipedia_key: language_code+":"+article_name},
                    proposed_tagging_changes=[{"from": {wikipedia_key: language_code+":"+article_name}, "to": {wikipedia_key: new_wikipedia_link}}],
                )

        if self.is_first_wikidata_disambig_while_second_points_to_something_not_disambig(wikidata_id_from_article, present_wikidata_id):
            new_wikipedia = self.get_best_interwiki_link_by_id(present_wikidata_id)
            message = "article claims to point to disambig, " + wikidata_key + " does not. " + wikidata_key + " tag is likely to be correct, " + wikipedia_key + " tag almost certainly is not"
            return ErrorReport(
                error_id="wikipedia wikidata mismatch - wikipedia points to disambiguation page and wikidata does not" + error_id_suffix,
                error_general_intructions=common_message,
                error_message=message,
                prerequisite={wikidata_key: present_wikidata_id, wikipedia_key: language_code+":"+article_name},
                proposed_tagging_changes=[{"from": {wikipedia_key: language_code+":"+article_name}, "to": {wikipedia_key: new_wikipedia}}],
            )
        redirected = self.get_article_name_after_redirect(language_code, article_name)
        if redirected != None:
            link = language_code + ":" + article_name
            language_code_redirected = wikimedia_connection.get_language_code_from_link(link)
            article_name_redirected = wikimedia_connection.get_article_name_from_link(link)
            wikidata_of_redirected = wikimedia_connection.get_wikidata_object_id_from_article(language_code_redirected, article_name_redirected, self.forced_refresh)
            if self.is_first_wikidata_disambig_while_second_points_to_something_not_disambig(wikidata_of_redirected, present_wikidata_id):
                new_wikipedia = self.get_best_interwiki_link_by_id(present_wikidata_id)
                message = "article claims to redirect to disambig, " + wikidata_key + " does not. " + wikidata_key + " tag is likely to be correct, " + wikipedia_key + " tag almost certainly is not"
                return ErrorReport(
                    error_id="wikipedia wikidata mismatch - wikipedia points to disambiguation page and wikidata does not" + error_id_suffix,
                    error_general_intructions=common_message,
                    error_message=message,
                    prerequisite={wikidata_key: present_wikidata_id, wikipedia_key: language_code+":"+article_name},
                    proposed_tagging_changes=[{"from": {wikipedia_key: language_code+":"+article_name}, "to": {wikipedia_key: new_wikipedia}}],
                )

        message = (base_message + " (" +
                   self.compare_wikidata_ids(present_wikidata_id, wikidata_id_from_article) +
                   " wikidata id assigned to linked Wikipedia article)")
        if maybe_redirected_wikidata_id != present_wikidata_id:
            message += " Note that this OSM object has " + wikidata_key + " tag links a redirect ("
            message += present_wikidata_id + " to " + maybe_redirected_wikidata_id + ")."
        if is_article_redirected:
            message += " Note that this OSM object has " + wikipedia_key + " tag that links redirect ('"
            message += article_name + "' to '" + title_after_possible_redirects + "')."
        return ErrorReport(
            error_id="wikipedia wikidata mismatch" + error_id_suffix,
            error_message=message,
            prerequisite={wikidata_key: present_wikidata_id, wikipedia_key: language_code + ":" + article_name},
        )

    def is_first_wikidata_disambig_while_second_points_to_something_not_disambig(self, first, second):
        if first == None:
            return False
        if first == None:
            return False
        for type_id in wikidata_processing.get_all_types_describing_wikidata_object(second, self.ignored_entries_in_wikidata_ontology()):
            if type_id == self.disambig_type_id():
                return False
        for type_id in wikidata_processing.get_all_types_describing_wikidata_object(first, self.ignored_entries_in_wikidata_ontology()):
            if type_id == self.disambig_type_id():
                return True

    def compare_wikidata_ids(self, id1, id2):
        if id1 == None:
            id1 = "(missing)"
        if id2 == None:
            id2 = "(missing)"
        return id1 + " vs " + id2

    def is_wikipedia_tag_clearly_broken(self, link):
        if link == None:
            raise Exception("Null pointer exception, unexpected None in link")
        language_code = wikimedia_connection.get_language_code_from_link(link)
        if self.is_language_code_clearly_broken(language_code):
            return True
        article_name = wikimedia_connection.get_article_name_from_link(link)
        if self.is_article_name_clearly_broken(article_name):
            return True
        return False

    def is_wikidata_tag_clearly_broken(self, link):
        if link == "":
            return True
        if link[-1] == ";" and link.count(";") > 1:
            return self.is_wikidata_tag_clearly_broken(link[:-1])
        if ";" in link:
            for part in link.split(";"):
                if self.is_wikidata_tag_clearly_broken_or_with_multiple_values(part):
                    return True
            return False
        return self.is_wikidata_tag_clearly_broken_or_with_multiple_values(link)

    def is_wikidata_tag_clearly_broken_or_with_multiple_values(self, link):
        if link == None:
            return True
        if len(link) < 2:
            return True
        if link[0] != "Q":
            return True
        if re.search(r"^\d+\Z", link[1:]) == None:
            return True
        return False

    def is_article_name_clearly_broken(self, link):
        # TODO - implement other indicators from https://en.wikipedia.org/wiki/Wikipedia:Naming_conventions_(technical_restrictions)
        language_code = wikimedia_connection.get_language_code_from_link(link)

        # https://en.wikipedia.org/wiki/Wikipedia:Naming_conventions_(technical_restrictions)#Colons
        if language_code != None:
            if language_code in wikipedia_knowledge.WikipediaKnowledge.all_wikipedia_language_codes_order_by_importance():
                return True
        if "?" in link:
            return True
        return False

    def is_language_code_clearly_broken(self, language_code):
        # detects missing language code
        #         unusually long language code
        #         broken language code "pl|"
        if language_code is None:
            return True
        if language_code in wikipedia_knowledge.WikipediaKnowledge.all_wikipedia_language_codes_order_by_importance():
            return False
        if language_code in wikipedia_knowledge.WikipediaKnowledge.wikipedia_language_code_redirects():
            return False
        if len(language_code) > 3:
            return True
        if re.search("^[a-z]+$", language_code) == None:
            return True
        return False

    def get_wikipedia_language_issues(self, object_description, tags, wikipedia, effective_wikidata_id):
        botpedia_message = None
        prerequisite = {'wikipedia': wikipedia, 'wikidata': tags.get("wikidata")}

        # complains when Wikipedia page is not in the preferred language,
        # in cases when it is possible
        if wikipedia == None:
            return  # there may be just a Wikidata entry, without a Wikipedia article

        current_language_code = wikimedia_connection.get_language_code_from_link(wikipedia)
        botpedia_message = "wikipedia page in unexpected language - " + current_language_code + " is a low quality, bot generated wikipedia - it should not be linked"

        bot_wikipedias = ["ceb"]
        if self.expected_language_code == None:
            if current_language_code in bot_wikipedias:
                return ErrorReport(
                    error_id="wikipedia tag links bot wikipedia",
                    error_message=botpedia_message,
                    prerequisite=prerequisite,
                )
            # further checks are useless
            return

        recommended_article_name = wikimedia_connection.get_interwiki_article_name_by_id(effective_wikidata_id, self.expected_language_code, self.forced_refresh)
        if recommended_article_name == None:
            if current_language_code in bot_wikipedias:
                return ErrorReport(
                    error_id="wikipedia tag links bot wikipedia",
                    error_message=botpedia_message,
                    prerequisite=prerequisite,
                )
            return
        recommended_language_code = self.expected_language_code
        good_link = recommended_language_code + ":" + recommended_article_name
        if self.expected_language_code == current_language_code:
            # everything is fine
            return None

        if recommended_language_code in bot_wikipedias:
            if recommended_language_code == self.expected_language_code:
                pass
            else:
                raise Exception("why botpedia got recommended?")

        reason = self.why_object_is_allowed_to_have_foreign_language_label(object_description, effective_wikidata_id)
        if reason != None:
            if self.additional_debug:
                print(object_description + " is allowed to have foreign wikipedia link, because " + reason)
            if current_language_code in bot_wikipedias:
                # not a real Wikipedia
                if current_language_code != recommended_language_code:
                    return ErrorReport(
                        error_id="wikipedia tag links bot wikipedia in border region, can be changed to alternative",
                        error_message=botpedia_message,
                        prerequisite=prerequisite,
                    )
                else:
                    return ErrorReport(
                        error_id="wikipedia tag links bot wikipedia in border region",
                        error_message=botpedia_message,
                        prerequisite=prerequisite,
                    )
            return None

        if recommended_article_name != None:
            error_message = "wikipedia page in unexpected language - " + self.expected_language_code + " was expected:"
            if current_language_code in bot_wikipedias:
                # not a real Wikipedia
                return ErrorReport(
                    error_id="wikipedia tag links bot wikipedia",
                    error_message=botpedia_message + " fortunately, in this case, a potential replacement exists",
                    proposed_tagging_changes=[{"from": {"wikipedia": wikipedia}, "to": {"wikipedia": good_link}}],
                    prerequisite=prerequisite,
                )
            return ErrorReport(
                error_id="wikipedia tag unexpected language",
                error_message=error_message,
                proposed_tagging_changes=[{"from": {"wikipedia": wikipedia}, "to": {"wikipedia": good_link}}],
                prerequisite=prerequisite,
            )
        else:
            if not self.allow_requesting_edits_outside_osm:
                return None
            if not self.allow_false_positives:
                return None
            error_message = "wikipedia page in unexpected language - " + self.expected_language_code + " was expected, no page in that language was found:"
            if current_language_code in bot_wikipedias:
                return ErrorReport(
                    error_id="wikipedia tag links bot wikipedia",
                    error_message=botpedia_message,
                    prerequisite=prerequisite,
                )
            return ErrorReport(
                error_id="wikipedia tag unexpected language, article missing",
                error_message=error_message,
                prerequisite=prerequisite,
            )
        assert False

    def should_use_subject_message(self, topic, special_prefix, wikidata_id):
        link = self.get_best_interwiki_link_by_id(wikidata_id)
        linked_object = "wikidata entry (" + wikidata_id + ")"
        about_article = ""
        if link != None:
            article_name = wikimedia_connection.get_article_name_from_link(link)
            about_article = "(" + article_name + " article)"

        special_prefix_text = ""
        if special_prefix != None:
            special_prefix_text = "or " + special_prefix + "wikipedia"
        about = "linked " + linked_object + about_article + " is about """ + topic
        message = about + ", so it is very unlikely to be correct \n\
        subject:wikipedia=* " + special_prefix_text + " tag would be probably better \
        (see https://wiki.openstreetmap.org/wiki/Key:wikipedia#Secondary_Wikipedia_links for full list of what else may be applicable) \n\
        in case of change remember to add such prefix (or remove) wikidata tag if it is present \n\
        object categorised by Wikidata - wrong classification may be caused by wrong data on Wikidata"
        return message

    def get_should_use_subject_error_tag_summary(self, tags):
        if "wikidata" in tags and "wikipedia" in tags:
            return "wikipedia and wikidata"
        if "wikidata" in tags and "wikipedia" not in tags:
            return "wikidata"
        if "wikidata" not in tags and "wikipedia" in tags:
            return "wikipedia"
        raise Exception("what is going on")

    def get_should_use_subject_error(self, topic, special_prefix, wikidata_id, summary_of_tags_in_use):
        return ErrorReport(
            error_id="should use a secondary wikipedia tag - linking from " + summary_of_tags_in_use + " tag to " + topic,
            error_message=self.should_use_subject_message(topic, special_prefix, wikidata_id),
            prerequisite={'wikidata': wikidata_id},
        )

    def get_list_of_links_from_disambig(self, wikidata_id):
        link = self.get_best_interwiki_link_by_id(wikidata_id)
        if link == None:
            print("ops, no language code matched for " + wikidata_id)
            return []
        return self.get_list_of_links_from_specific_page(link)

    def get_list_of_links_from_specific_page(self, link):
        article_name = wikimedia_connection.get_article_name_from_link(link)
        language_code = wikimedia_connection.get_language_code_from_link(link)
        links_from_disambig_page = wikimedia_connection.get_from_wikipedia_api(language_code, "&prop=links", article_name)['links']
        returned = []
        for link_on_disambig_page in links_from_disambig_page:
            if link_on_disambig_page['ns'] == 0:
                returned.append({'title': link_on_disambig_page['title'], 'language_code': language_code})
        return returned

    def distance_in_km_to_string(self, distance_in_km):
        if distance_in_km > 3:
            return str(int(distance_in_km)) + " km"
        else:
            return str(int(distance_in_km*1000)) + " m"

    def distance_in_km_of_wikidata_object_from_location(self, coords_given, wikidata_id):
        # coords_given are (latititude, longitude) tuple
        if wikidata_id == None:
            return None
        location_from_wikidata = wikimedia_connection.get_location_from_wikidata(wikidata_id)
        # recommended by https://stackoverflow.com/a/43211266/4130619
        # documentation on https://github.com/geopy/geopy#measuring-distance
        # geopy.distance.distance((latititude, longitude), (latititude, longitude))
        return geopy.distance.distance(coords_given, location_from_wikidata).km

    def get_distance_description_between_location_and_wikidata_id(self, location, wikidata_id):
        # location is (latititude, longitude) tuple
        if location == (None, None):
            return " <no location data>"
        distance = self.distance_in_km_of_wikidata_object_from_location(location, wikidata_id)
        if distance == None:
            return " <no location data on wikidata>"
        return ' is ' + self.distance_in_km_to_string(distance) + " away"

    def get_list_of_disambig_fixes(self, target_location, element_wikidata_id):
        # target_location is (latititude, longitude) tuple
        # TODO open all pages, merge duplicates using wikidata and list them as currently
        links = self.get_list_of_links_from_disambig(element_wikidata_id)
        if element_wikidata_id == None:
            return "page without wikidata element, unable to load link data. Please, create wikidata element (TODO: explain how it can be done)"
        if links == None:
            return "TODO improve language handling on foreign disambigs"
        return self.string_with_list_of_distances_to_locations(target_location, links)

    def string_with_list_of_distances_to_locations(self, target_location, links):
        # target_location is (latititude, longitude) tuple
        """
        links: list of dictionary entries, each with language_code and title
        for example: [{'title': 'Candedo (Murça)', 'language_code': 'pt'}]
        """
        returned = ""
        for link in links:
            link_wikidata_id = wikimedia_connection.get_wikidata_object_id_from_article(link['language_code'], link['title'])
            distance_description = self.get_distance_description_between_location_and_wikidata_id(target_location, link_wikidata_id)
            returned += link['title'] + distance_description + "\n"
        return returned

    def get_error_report_if_secondary_wikipedia_tag_should_be_used(self, effective_wikidata_id, tags):
        # contains ideas based partially on constraints in https://www.wikidata.org/wiki/Property:P625
        class_error = self.get_error_report_if_type_unlinkable_as_primary(effective_wikidata_id, tags)
        if class_error != None:
            return class_error

        tag_summary = self.get_should_use_subject_error_tag_summary(tags)
        property_error = self.get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary(effective_wikidata_id, tag_summary)
        if property_error != None:
            return property_error

    def get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary(self, wikidata_id, tag_summary, show_debug=False):
        if wikimedia_connection.get_property_from_wikidata(wikidata_id, 'P247') != None:
            return self.get_should_use_subject_error('a spacecraft', 'name:', wikidata_id, tag_summary)
        # https://www.wikidata.org/wiki/Property:P279 - subclass of
        subclass_of = wikimedia_connection.get_property_from_wikidata(wikidata_id, 'P279')
        if subclass_of != None:
            if show_debug:
                for entry in subclass_of:
                    subclass_of_wikidata = entry['mainsnak']['datavalue']['value']['id']
                    print(wikidata_id, "subclass_of", subclass_of_wikidata)
            return self.get_should_use_subject_error('an uncoordinable generic object', 'name:', wikidata_id, tag_summary)

    def wikidata_entries_classifying_entry(self, effective_wikidata_id):
        returned = []

        # instances of subclasses - also of indirect subclasses
        parent_categories = wikidata_processing.get_recursive_all_subclass_of(effective_wikidata_id, self.ignored_entries_in_wikidata_ontology(), False, callback=None)
        for base_type_id in (parent_categories):
            returned.append(base_type_id)
            # TODO is this used: get_all_types_describing_wikidata_object

        # subclasses, of "is instance of"
        root_instance_ids = wikidata_processing.get_wikidata_type_ids_of_entry(effective_wikidata_id)
        if root_instance_ids == None:
            root_instance_ids = []
        for root in root_instance_ids:
            if root in self.ignored_entries_in_wikidata_ontology():
                continue
            parent_categories = wikidata_processing.get_recursive_all_subclass_of(root, self.ignored_entries_in_wikidata_ontology(), False, callback=None)
            for base_type_id in (parent_categories):
                returned.append(base_type_id)

        return returned

    def wikidata_entries_classifying_entry_with_depth_data(self, effective_wikidata_id):
        returned = []

        parent_categories_entries = wikidata_processing.get_recursive_all_subclass_of_with_depth_data(effective_wikidata_id, self.ignored_entries_in_wikidata_ontology(), False, callback=None)
        for base_type_id_entry in parent_categories_entries:
            returned.append(base_type_id_entry)
            base_type_id = base_type_id_entry["id"]
            base_type_id_depth = base_type_id_entry["depth"]
            instance_ids = wikidata_processing.get_wikidata_type_ids_of_entry(base_type_id)
            if instance_ids != None:
                for instance_id in instance_ids:
                    if instance_id not in self.ignored_entries_in_wikidata_ontology():
                        returned.append({"id": instance_id, "depth": base_type_id_depth + 1})

        root_instance_ids = wikidata_processing.get_wikidata_type_ids_of_entry(effective_wikidata_id)
        if root_instance_ids == None:
            root_instance_ids = []
        for root in root_instance_ids:
            if root in self.ignored_entries_in_wikidata_ontology():
                continue
            parent_categories_entries = wikidata_processing.get_recursive_all_subclass_of_with_depth_data(root, self.ignored_entries_in_wikidata_ontology(), False, callback=None)
            for base_type_id_entry in (parent_categories_entries + [{"id": root, "depth": 0}]):
                returned.append(base_type_id_entry)
        return returned

    def get_error_report_if_type_unlinkable_as_primary(self, effective_wikidata_id, tags, debug=False):
        # https://en.wikipedia.org/wiki/Edith_Macefield
        # this pretends to be about human while it is about building
        # see https://osmus.slack.com/archives/C1FKE1NCA/p1668339647063239
        # see https://www.openstreetmap.org/way/217502987
        # for search: [biography][person]
        if effective_wikidata_id == 'Q5338613':
            if debug:
                print("skipped Q5338613")
            return None
        # event entry about hoax/delusion that is actually strongly about location
        if effective_wikidata_id == 'Q5371519':
            if debug:
                print("skipped Q5371519")
            return None
        if effective_wikidata_id in self.ignored_entries_in_wikidata_ontology():
            if debug:
                print(effective_wikidata_id, "is in self.ignored_entries_in_wikidata_ontology()")
            return None
        remembered_potential_failure = None
        for type_id in self.wikidata_entries_classifying_entry(effective_wikidata_id):
            if debug:
                print(type_id)
            if type_id in [
                "Q122754124", # ambiguous Wikidata item - so known to be broken
            ]:
                return None # maybe can be reported as worth handling on Wikidata?
            potential_failure = self.get_reason_why_type_makes_object_invalid_primary_link(type_id)
            if debug:
                print(potential_failure, "potential failure")
                print()
            if potential_failure != None:
                if potential_failure['what'] == "a human" and tags.get('boundary') == 'aboriginal_lands':
                    continue # cases like https://www.openstreetmap.org/way/758139284 where Wikipedia article bundles ethicity group and reservation land in one article
                    # TODO
                    # ideally can be fixed, see https://www.wikidata.org/w/index.php?title=User:Mateusz_Konieczny/failing_testcases/Archive_1&oldid=1808808796#Tulalip_Tribes_of_Washington_(Q1516298)_is_human,_according_to_Wikidata_ontology
                    # bother with it after USA report page is empty and Wikidata Ontology has run out of things to fix
                    # AKA never

                if potential_failure['what'] == "a bicycle sharing system" and tags.get('type') == 'network':
                    continue # for relations like https://www.openstreetmap.org/relation/6409389 it seems fine
                             # though not sure is relation itself is fine
                             # but lets skip and focus on blatantly bad things

                # prefer to not report general one (there could be a more specific one reason in a different branch)
                if 'extremely_broad_and_unspecific' in potential_failure:
                    if potential_failure['extremely_broad_and_unspecific'] == True:
                        if remembered_potential_failure != None:
                            continue
                remembered_potential_failure = potential_failure
        if remembered_potential_failure != None:
            tag_summary = self.get_should_use_subject_error_tag_summary(tags)
            return self.get_should_use_subject_error(remembered_potential_failure['what'], remembered_potential_failure['replacement'], effective_wikidata_id, tag_summary)
        return None

    def get_reason_why_type_makes_object_invalid_primary_link(self, type_id):
        # TODO - also generate_webpage file must be updated
        return self.invalid_types().get(type_id, None)

    def invalid_types(self):
        taxon = {'what': 'an animal or plant (and not an individual one)', 'replacement': None}
        weapon = {'what': 'a weapon model or class', 'replacement': 'model:'}
        vehicle = {'what': 'a vehicle model or class', 'replacement': 'model:'}
        generic_event = {'what': 'an event', 'replacement': None, 'extremely_broad_and_unspecific': True}
        return {
            # metapages
            "Q17379835": {'what': 'a wikimedia page', 'replacement': None},  # 'instance of this class should only describe a Wikimedia page, not the outside world concept described in the page'

            # may be silenced to stop reports that are almost entirely about fixing Wikidata
            "Q756944": {'what': 'a surface mining', 'replacement': None},  # often mistakenly applied to open pit mines on Wikidata
            "Q5138347": {'what': 'a coastal defence and fortification', 'replacement': None},  # often mistakenly added to forts, see https://www.wikidata.org/w/index.php?title=Q5472172&action=history
            'Q1211272': {'what': 'a signage', 'replacement': None},  # very often it should be https://www.wikidata.org/wiki/Q105449313 (a physical sign)

            'Q11483816':  {'what': 'an annual event', 'replacement': None},  # maybe not an actual problem?


            'Q190637':  {'what': 'a web design', 'replacement': None},
            'Q930752':  {'what': 'a medical specialty', 'replacement': None},
            'Q12128':  {'what': 'a dentistry', 'replacement': None},
            'Q31629':  {'what': 'a type of sport', 'replacement': None},
            'Q349':  {'what': 'a sport', 'replacement': None},
            'Q4':  {'what': 'a death', 'replacement': None},
            'Q17550579':  {'what': 'a feeding', 'replacement': None},
            'Q2860334':  {'what': 'a church architecture', 'replacement': None},
            'Q385378':  {'what': 'a construction (as economic activity)', 'replacement': None},
            'Q132821':  {'what': 'a murder', 'replacement': None},
            'Q1800545':  {'what': 'a migration', 'replacement': None},
            'Q1379672':  {'what': 'an evaluation', 'replacement': None},
            'Q1309431':  {'what': 'a structural failure', 'replacement': None},

            'Q3958441': {'what': 'an economic sector', 'replacement': None},
            'Q5': {'what': 'a human', 'replacement': 'name:'},
            'Q178885': {'what': 'a deity', 'replacement': 'subject:'},
            'Q193291': {'what': 'a spirit', 'replacement': 'subject:'},
            'Q14897293': {'what': 'a fictional entity', 'replacement': 'name:etymology:'},
            'Q16858238': {'what': 'a train category', 'replacement': None},
            'Q28747937': {'what': 'a history of a city', 'replacement': None},
            'Q63313685': {'what': 'a history of a geographic region', 'replacement': None},
            'Q690109': {'what': 'a branch of military service', 'replacement': None},
            'Q98924064': {'what': 'an electronic device model series', 'replacement': None},
            "Q111972893": {'what': 'a type of structure', 'replacement': None},
            "Q1358919": {'what': 'a bicycle sharing system', 'replacement': 'brand:'},
            "Q1529128": {'what': 'a postal service', 'replacement': 'brand:'},
            "Q350945": {'what': 'a heraldic animal', 'replacement': None},
            "Q1796040": {'what': 'a geodetic control network', 'replacement': None},
            "Q18325841": {'what': 'a public transport network', 'replacement': 'operator:'},
            "Q1326624": {'what': 'an electric utility', 'replacement': 'operator:'},
            "Q7860962": {'what': 'a road type', 'replacement': None},
            "Q2135540": {'what': 'a legal action', 'replacement': None},
            "Q781413": {'what': 'a mental process', 'replacement': None},
            "Q131569": {'what': 'a treaty', 'replacement': None},
            "Q9788": {'what': 'a letter', 'replacement': None},
            "Q2304706": {'what': 'a spheroidal weathering', 'replacement': None},
            "Q3320743": {'what': 'a title of honor', 'replacement': None},
            'Q18786396': taxon,
            'Q16521': taxon,
            'Q55983715': taxon,
            'Q12045585': taxon,
            'Q5113': taxon,
            'Q38829': taxon,
            'Q34740': taxon,
            'Q7432': taxon,
            'Q726': {'what': 'a horse', 'replacement': None},
            'Q60680430': {'what': 'a branch of psychology', 'replacement': None},
            'Q336': {'what': 'a science', 'replacement': None, 'extremely_broad_and_unspecific': True},
            'Q115372263': {'what': 'a word or phrase', 'replacement': None},
            'Q44497': {'what': 'a mining (activity - likely mine/quarry etc should be set instead)', 'replacement': None},
            'Q26883973': {'what': 'a lost sculpture', 'replacement': 'subject:'},
            'Q4140840': {'what': 'a lost artwork', 'replacement': 'subject:'},
            'Q21752591': {'what': 'a lost work', 'replacement': 'subject:'},
            'Q7625093': {'what': 'a structure fire', 'replacement': 'subject:'},
            'Q61509': {'what': 'a travel', 'replacement': 'subject:'},
            'Q133182': {'what': 'a superstitution', 'replacement': 'subject:'},
            'Q42240': {'what': 'a research', 'replacement': None},
            'Q268592': {'what': 'a general industry', 'replacement': None},
            'Q1344': {'what': 'an opera', 'replacement': None},
            'Q35127': {'what': 'a website', 'replacement': None},
            'Q5398426': {'what': 'a television series', 'replacement': None},
            'Q3026787': {'what': 'a saying', 'replacement': None},
            'Q18534542': {'what': 'a restaurant chain', 'replacement': 'brand:'},
            'Q161726': {'what': 'a multinational corporation', 'replacement': 'brand:'},
            'Q507619': {'what': 'a chain store', 'replacement': 'brand:'},
            'Q202444': {'what': 'a given name', 'replacement': 'name:'},
            'Q34394': {'what': 'a belief', 'replacement': 'brand:', 'extremely_broad_and_unspecific': True},
            'Q879146': {'what': 'a Christian denomination', 'replacement': 'brand:', 'extremely_broad_and_unspecific': True},
            'Q60075825': {'what': 'a Christian holy day', 'replacement': None},
            'Q2915444': {'what': 'a fireworks event', 'replacement': None},
            'Q650711': {'what': 'a military operation', 'replacement': None},
            'Q1707496': {'what': 'a police operation', 'replacement': None},
            'Q180684': {'what': 'a conflict', 'replacement': None},
            'Q1072326': {'what': 'a summit (political conference)', 'replacement': None},
            'Q2761147': {'what': 'a meeting', 'replacement': None},
            'Q331055': {'what': 'a burial', 'replacement': None},
            'Q1437361': {'what': 'a form of art', 'replacement': None},
            # an academic discipline is often unclear and false positive, vast majority comes from dentistry spam covered by above
            'Q11862829': {'what': 'an academic discipline', 'replacement': None, 'extremely_broad_and_unspecific': True},
            'Q1298668': {'what': 'a research project', 'replacement': None},
            'Q7397': {'what': 'a software', 'replacement': None},
            'Q1270515': {'what': 'a tax', 'replacement': None},
            'Q201676': {'what': 'a funeral', 'replacement': None},
            'Q14350': {'what': 'a radio station', 'replacement': 'brand:'},
            'Q1616075': {'what': 'a television station', 'replacement': 'brand:'},
            'Q15265344': {'what': 'a broadcaster', 'replacement': 'brand:'},
            'Q13406554': {'what': 'a sports competition', 'replacement': None},
            'Q18608583': {'what': 'a recurring sports event', 'replacement': None},
            'Q13414953': {'what': 'a religious denomination', 'replacement': None},
            'Q5608878': {'what': 'a dry stone walling (construction technique)', 'replacement': None},  # very often it should be https://www.wikidata.org/wiki/Q544504
            'Q16675884': {'what': 'a religious sculpture (genre)', 'replacement': None},  # very often it should be https://www.wikidata.org/wiki/Q544504
            'Q29584743': {'what': 'a postal and courier activity', 'replacement':  None},
            'Q451967': {'what': 'an intentional human activity', 'replacement':  None, 'extremely_broad_and_unspecific': True},
            'Q61788060': {'what': 'a human activity', 'replacement':  None, 'extremely_broad_and_unspecific': True},
            'Q3769299': {'what': 'a human behavior', 'replacement':  None, 'extremely_broad_and_unspecific': True},
            'Q9332': {'what': 'a behavior', 'replacement':  None, 'extremely_broad_and_unspecific': True},
            # for example Holocaust is instance of a physical process - and very, very technically it is true
            'Q79782': {'what': 'a motion', 'replacement': None, 'extremely_broad_and_unspecific': True},
            'Q17320256': {'what': 'a physical process', 'replacement': None, 'extremely_broad_and_unspecific': True},

            'Q179057': {'what': 'an explosion', 'replacement':  None},
            'Q28640': {'what': 'a profession', 'replacement':  None},
            'Q1914636': {'what': 'an activity', 'replacement':  None},
            'Q20162172': {'what': 'a human language', 'replacement':  None},
            'Q2000908': weapon,
            'Q15142894': weapon,
            'Q15142889': weapon,
            'Q29048322': vehicle,
            'Q22999537': vehicle,
            'Q16335899': vehicle,
            'Q1875621': vehicle,
            'Q37761255': vehicle,
            'Q2095': {'what': 'a food', 'replacement':  None},
            'Q43183': {'what': 'an insurance', 'replacement':  None},  # vs insurance company - to catch and ignore wikidata issues
            'Q1778821': {'what': 'a cuisine', 'replacement':  None},
            # for example religious denominations
            'Q82821': {'what': 'a tradition', 'replacement':  None, 'extremely_broad_and_unspecific': True},
            'Q474191': {'what': 'a diet', 'replacement':  None},
            'Q814610': {'what': 'an emergency service', 'replacement':  'brand:'},
            'Q3241045': {'what': 'a disease outbreak', 'replacement': 'subject:'},
            'Q22222786': {'what': 'a government program', 'replacement': None},
            'Q24634210': {'what': 'a podcast', 'replacement': None},
            'Q273120': {'what': 'a protest', 'replacement': None},
            'Q24716636': {'what': 'a volunteer', 'replacement': None},
            'Q7406919': {'what': 'a service', 'replacement': None},
            'Q908620': {'what': 'a certification mark', 'replacement': None},
            'Q622772': {'what': 'an incineration', 'replacement': None},  # used instead 'incinerator', see https://www.wikidata.org/wiki/Q13416228
            'Q49773': {'what': 'a social movement', 'replacement': None},
            'Q110401282': {'what': 'a type of world view', 'replacement': None},
            'Q1456832': {'what': 'a violation of law', 'replacement': None},
            'Q217327': {'what': 'a suicide attack', 'replacement': None},
            'Q21502408': {'what': 'a wikidata mandatory constraint', 'replacement': None},
            'Q14659': {'what': 'a coat of arms', 'replacement': None},
            'Q101352': {'what': 'a family name', 'replacement': None},
            'Q7048977': {'what': 'an object that exists outside physical reality', 'replacement': None, 'extremely_broad_and_unspecific': True},
            'Q11038979': {'what': 'a cult', 'replacement': None},
            'Q8434': {'what': 'an education (transmission of knowledge and skills)', 'replacement': None},
            'Q7187': {'what': 'a gene', 'replacement': None},
            'Q17127659': {'what': 'a terrorist organisation', 'replacement': None},
            'Q11822042': {'what': 'a transport accident', 'replacement': None},
            'Q178561': {'what': 'a battle', 'replacement': None},
            'Q53706': {'what': 'a robbery', 'replacement': None},
            'Q83267': {'what': 'a crime', 'replacement': None},
            'Q1920219': {'what': 'a social issue', 'replacement': None},
            'Q885167': {'what': 'a television program', 'replacement': None},
            'Q60797': {'what': 'a sermon', 'replacement': None},
            'Q861911': {'what': 'an oration', 'replacement': None},
            'Q11424': {'what': 'a film', 'replacement': None},
            'Q11417': {'what': 'a martial art', 'replacement': None},
            'Q1792379': {'what': 'an art genre', 'replacement': None},
            'Q735': {'what': 'art (field of work, not the resulting work)', 'replacement': None},
            'Q483394': {'what': 'a genre', 'replacement': None},
            'Q2634583': {'what': 'a stampede', 'replacement': None},
            'Q3839081': {'what': 'a disaster', 'replacement': None},
            'Q37929123': {'what': 'an electric vehicle charging network', 'replacement': 'brand:'},
            'Q431289': {'what': 'a brand', 'replacement': 'brand:'},
            'Q7676551': {'what': 'a festival', 'replacement': 'brand:'},
            'Q868557': {'what': 'a music festival', 'replacement': 'brand:'},
            'Q220505': {'what': 'a film festival', 'replacement': 'brand:'},
            'Q1759320': {'what': 'a costume party', 'replacement': 'brand:'},
            'Q20136634': {'what': 'an overview article', 'replacement': None},
            'Q74817647': {'what': 'an aspect in a geographic region', 'replacement': None},
            'Q13418847': {'what': 'a historical event', 'replacement': None},
            'Q2627975': {'what': 'a ceremony', 'replacement': None},
            'Q2252077': {'what': 'a shooting', 'replacement': None},
            'Q2223653': {'what': 'a terrorist attack', 'replacement': None},
            'Q645883': {'what': 'a military operation', 'replacement': None},
            'Q29023906': {'what': 'a temporary exhibition', 'replacement':  None},
            'Q1656682': generic_event,
            'Q4026292': generic_event,
            'Q3249551': generic_event,
            'Q1190554': generic_event,
            # , 'extremely_broad_and_unspecific': True here is kind of hacky not sure is it even working, TODO
            'Q98374631': {'what': 'a transport by country or region', 'replacement': None, 'extremely_broad_and_unspecific': True},
        }

    def disambig_type_id(self):
        return 'Q4167410'

    def get_error_report_if_wikipedia_target_is_of_unusable_type(self, location, wikidata_id):
        # target_location is (latititude, longitude) tuple
        # wikidata id is string with, well, wikidata id (such as "Q42")
        for type_id in wikidata_processing.get_all_types_describing_wikidata_object(wikidata_id, self.ignored_entries_in_wikidata_ontology()):
            if type_id == self.disambig_type_id():
                # TODO note that pageprops may be a better source that should be used
                # it does not require wikidata entry
                # wikidata entry may be wrong
                # https://pl.wikipedia.org/w/api.php?action=query&format=json&prop=pageprops&redirects=&titles=Java%20(ujednoznacznienie)
                disambig_list = self.get_list_of_disambig_fixes(location, wikidata_id)
                error_message = "link leads to a disambig page - not a proper wikipedia link (according to Wikidata - if target is not a disambig check Wikidata entry whether it is correct)\n\n" + disambig_list
                return ErrorReport(
                    error_id="link to a disambiguation page",
                    error_message=error_message,
                    prerequisite={'wikidata': wikidata_id},
                )
            if type_id == 'Q13406463':
                error_message = "article linked in wikipedia tag is a list, so it is very unlikely to be correct"
                return ErrorReport(
                    error_id="link to a list",
                    error_message=error_message,
                    prerequisite={'wikidata': wikidata_id},
                )

    def get_problem_based_on_wikidata_and_osm_element(self, object_description, location, effective_wikidata_id, tags):
        # object_description is
        # location is (latititude, longitude) tuple
        # effective_wikidata_id is string with, well, wikidata id (such as "Q42")
        # tags is dictionary represeting OSM tags of the object
        if effective_wikidata_id != None:
            error = self.get_problem_based_on_wikidata(effective_wikidata_id, tags, object_description, location)
            if error != None:
                return error

        # https://www.wikidata.org/wiki/Q7432
        error = self.get_problem_based_on_taxon_tagging_with_p105_property(tags, object_description, location, "species:", "Q7432")
        if error != None:
            return error

        error = self.get_problem_based_on_taxon_tagging_with_regular_ontology(tags, object_description, location, "taxon:", "Q16521")
        if error != None:
            return error

        error = self.get_problem_based_on_taxon_tagging_with_p105_property(tags, object_description, location, "genus:", "Q34740")
        if error != None:
            return error

    def get_problem_based_on_taxon_tagging_with_p105_property(self, tags, object_description, location, prefix, expected_wikidata):
        wikidata = None
        if prefix + "wikidata" in tags:
            wikidata = tags[prefix + "wikidata"]
        if prefix + "wikipedia" in tags and wikidata == None:
            wikidata = wikimedia_connection.get_wikidata_object_id_from_link(tags.get(prefix + "wikipedia"))
        if wikidata == None:
            return None
        if ";" in wikidata:
            # TODO maybe something can/should be done here?
            return None
        data = wikimedia_connection.get_property_from_wikidata(wikidata, 'P105')
        if data == None:
            return ErrorReport(
                error_id=prefix.replace(":", "") + " secondary tag links something that is not " + prefix.replace(":", "") + " according to wikidata (checking P105)",
                error_message="no P105",
                prerequisite={prefix + 'wikidata': tags.get(prefix + "wikidata"), prefix + "wikipedia": tags.get(prefix + "wikipedia")},
            )
        for entry in data:
            if expected_wikidata == entry['mainsnak']['datavalue']['value']['id']:
                return None
        return ErrorReport(
            error_id=prefix.replace(":", "") + " secondary tag links something that is not " + prefix.replace(":", "") + " according to wikidata (checking P105)",
            error_message="no matching P105",
            prerequisite={prefix + 'wikidata': tags.get(prefix + "wikidata"), prefix + "wikipedia": tags.get(prefix + "wikipedia")},
        )

    def get_problem_based_on_taxon_tagging_with_regular_ontology(self, tags, object_description, location, prefix, expected_wikidata):
        wikidata = None
        if prefix + "wikidata" in tags:
            wikidata = tags[prefix + "wikidata"]
        if prefix + "wikipedia" in tags and wikidata == None:
            wikidata = wikimedia_connection.get_wikidata_object_id_from_link(tags.get(prefix + "wikipedia"))
        if wikidata == None:
            return None
        if ";" in wikidata:
            # TODO maybe something can/should be done here?
            return None
        for type_id in self.wikidata_entries_classifying_entry(wikidata):
            if type_id == expected_wikidata:
                return None
        message = prefix.replace(":", "") + " secondary tag links something that is not " + prefix.replace(":", "") + " according to wikidata (checking regular ontology)"
        return ErrorReport(
            error_id=message,
            error_message=message,
            prerequisite={prefix + 'wikidata': tags.get(prefix + "wikidata"), prefix + "wikipedia": tags.get(prefix + "wikipedia")},
        )

    def get_problem_based_on_wikidata(self, effective_wikidata_id, tags, description, location):
        # effective_wikidata_id is string with, well, wikidata id (such as "Q42")
        # tags is dictionary represeting OSM tags of the object
        # description is
        # location is (latititude, longitude) tuple
        return self.get_problem_based_on_base_types(effective_wikidata_id, tags, description, location)

    def get_problem_based_on_base_types(self, effective_wikidata_id, tags, description, location):
        # effective_wikidata_id is string with, well, wikidata id (such as "Q42")
        # tags is dictionary represeting OSM tags of the object
        # description is
        # location is (latititude, longitude) tuple
        base_type_problem = self.get_problem_based_on_wikidata_base_types(location, effective_wikidata_id, tags)
        if base_type_problem != None:
            return base_type_problem

    def get_problem_based_on_wikidata_base_types(self, location, effective_wikidata_id, tags):
        # location is (latititude, longitude) tuple
        # effective_wikidata_id is string with, well, wikidata id (such as "Q42")
        # tags is dictionary represeting OSM tags of the object
        unusable_wikipedia_article = self.get_error_report_if_wikipedia_target_is_of_unusable_type(location, effective_wikidata_id)
        if unusable_wikipedia_article != None:
            return unusable_wikipedia_article

        secondary_tag_error = self.get_error_report_if_secondary_wikipedia_tag_should_be_used(effective_wikidata_id, tags)
        if secondary_tag_error != None:
            return secondary_tag_error

        if location != None:
            tag_summary = self.get_should_use_subject_error_tag_summary(tags)
            secondary_tag_error = self.headquaters_location_indicate_invalid_connection(location, effective_wikidata_id, tag_summary)
            if secondary_tag_error != None:
                return secondary_tag_error

    def get_location_of_this_headquaters(self, headquarters):
        try:
            position = headquarters['qualifiers']['P625'][0]['datavalue']['value']
            position = (position['latitude'], position['longitude'])
            return position
        except KeyError:
            pass
        try:
            id_of_location = headquarters['mainsnak']['datavalue']['value']['id']
            return wikimedia_connection.get_location_from_wikidata(id_of_location)
        except KeyError:
            pass
        return (None, None)

    def headquaters_location_indicate_invalid_connection(self, location, wikidata_id, tag_summary):
        if location == (None, None):
            return None
        headquarters_location_data = wikimedia_connection.get_property_from_wikidata(wikidata_id, 'P159')
        area_of_object = wikimedia_connection.get_property_from_wikidata(wikidata_id, 'P2046')
        if area_of_object != None:
            return None  # for example administrative boundaries such as https://www.wikidata.org/wiki/Q1364786
        if headquarters_location_data == None:
            return None
        for option in headquarters_location_data:
            location_from_wikidata = self.get_location_of_this_headquaters(option)
            if location_from_wikidata != (None, None):
                if geopy.distance.geodesic(location, location_from_wikidata).km > 20:
                    return self.get_should_use_subject_error('a company that has multiple locations', 'brand:', wikidata_id, tag_summary)

        return None

    def output_debug_about_wikidata_item(self, wikidata_id):
        print("**********************")
        print("starting output_debug_about_wikidata_item")
        print(wikidata_processing.get_wikidata_type_ids_of_entry(wikidata_id))
        print(wikidata_processing.get_all_types_describing_wikidata_object(wikidata_id, self.ignored_entries_in_wikidata_ontology()))
        self.show_in_stdout_and_in_log_file_unexpected_wikidata_structure(wikidata_id, show_only_banned=False)

    def callback_reporting_banned_categories(self, category_id):
        ban_reason = self.get_reason_why_type_makes_object_invalid_primary_link(category_id)
        if ban_reason != None:
            return " this was unexpected here as it indicates " + ban_reason['what'] + " !!!!!!!!!!!!!!!!!!!!!!!!!!"
        return ""

    def show_in_stdout_and_in_log_file_unexpected_wikidata_structure(self, type_id, show_only_banned):
        structure = self.get_list_describing_unexpected_wikidata_structure(type_id, show_only_banned)
        to_show_in_log_file = ""
        for entry in structure:
            to_show_in_log_file += ":"*entry["depth"] + "{{Q|" + entry["category_id"] + "}}" + "\n"
            if entry.get("ban_reason") != None:
                header = "== {{Q|" + type_id + "}} classified as " + entry["ban_reason"]['what'] + " ==\n"
                with open("wikidata_report.txt", "a") as myfile:
                    myfile.write(header + to_show_in_log_file + "\n\n")
            print(":"*entry["depth"] + wikidata_processing.wikidata_description(entry["category_id"]) + entry["note"])

    def get_list_describing_unexpected_wikidata_structure(self, type_id, show_only_banned):
        callback = self.callback_reporting_banned_categories

        # is get_recursive_all_subclass_of_with_depth_data needed anywhere?
        found = self.wikidata_entries_classifying_entry_with_depth_data(type_id)

        entries_to_show = []
        if show_only_banned:
            for index, entry in enumerate(found):
                category_id = entry["id"]
                depth = entry["depth"]
                if self.new_banned_entry_in_this_branch(found, index):
                    note = self.callback_reporting_banned_categories(category_id)
                    ban_reason = self.get_reason_why_type_makes_object_invalid_primary_link(category_id)
                    entries_to_show.append({"depth": depth, "category_id": category_id, "note": note, "ban_reason": ban_reason})
        else:
            for index, entry in enumerate(found):
                category_id = entry["id"]
                depth = entry["depth"]
                note = self.callback_reporting_banned_categories(category_id)
                entries_to_show.append({"depth": depth, "category_id": category_id, "note": note})
            # print entire inheritance set
            show_debug = True
            parent_categories = wikidata_processing.get_recursive_all_subclass_of(type_id, self.ignored_entries_in_wikidata_ontology(), show_debug, callback)
            #for parent_category in parent_categories:
            #    print("if type_id == '" + parent_category + "':")
            #    print(wikidata_processing.wikidata_description(parent_category))
        return entries_to_show

    def new_banned_entry_in_this_branch(self, data, checked_position):
        index = checked_position - 1
        relevant_level = data[checked_position]["depth"] - 1
        # higher depth is not relevant as it is some other branch with a sgared parent
        # it can be only lower than 1 - as depth increases by one
        while index > 0:
            if data[index]["depth"] == relevant_level:
                relevant_level -= 1  # next level will be lower, again we skip branches with shared parent
                ban_reason = self.get_reason_why_type_makes_object_invalid_primary_link(data[index]["id"])
                if ban_reason != None:
                    # one of direct parents/grandparents is already banned so not a new banned entry
                    return False
            index -= 1

        for index, _id in enumerate(data, start=checked_position):
            ban_reason = self.get_reason_why_type_makes_object_invalid_primary_link(data[index]["id"])
            if ban_reason != None:
                #print("returning True")
                #print("00000000000000000000000000")
                return True
            if (index + 1) >= len(data):
                #print("00000000000000000000000000")
                return False
            if data[index + 1]["depth"] <= data[checked_position]["depth"]:
                #print(index, "+ 1", data[index + 1], "returning false")
                #print("00000000000000000000000000")
                return False

    def wikidata_ids_of_countries_with_language(self, language_code):
        # data from Wikidata generated using generate_official_language_list.py in top level of repository
        if language_code == "jiv":  # Shuar
            return ["Q736"]  # Ecuador

        if language_code == "gcl":  # Grenadian Creole English
            return ["Q769"]  # Grenada

        if language_code == "es":  # Spanish
            return [
                "Q298",  # Chile
                "Q414",  # Argentina
                "Q419",  # Peru
                "Q717",  # Venezuela
                "Q733",  # Paraguay
                "Q736",  # Ecuador
                "Q739",  # Colombia
                "Q750",  # Bolivia
                "Q774",  # Guatemala
                "Q783",  # Honduras
                "Q786",  # Dominican Republic
                "Q792",  # El Salvador
                "Q983",  # Equatorial Guinea
                "Q29",  # Spain
                "Q77",  # Uruguay
                "Q96",  # Mexico
                "Q241",  # Cuba
                "Q800",  # Costa Rica
                "Q804",  # Panama
                "Q811",  # Nicaragua
            ]

        if language_code == "hi":  # Hindi
            return ["Q668"]  # India

        if language_code == "en":  # English
            return [
                "Q258",  # South Africa
                "Q334",  # Singapore
                "Q408",  # Australia
                "Q664",  # New Zealand
                "Q668",  # India
                "Q672",  # Tuvalu
                "Q678",  # Tonga
                "Q683",  # Samoa
                "Q685",  # Solomon Islands
                "Q686",  # Vanuatu
                "Q691",  # Papua New Guinea
                "Q695",  # Palau
                "Q697",  # Nauru
                "Q702",  # Federated States of Micronesia
                "Q709",  # Marshall Islands
                "Q710",  # Kiribati
                "Q712",  # Fiji
                "Q734",  # Guyana
                "Q754",  # Trinidad and Tobago
                "Q757",  # Saint Vincent and the Grenadines
                "Q760",  # Saint Lucia
                "Q763",  # Saint Kitts and Nevis
                "Q766",  # Jamaica
                "Q769",  # Grenada
                "Q778",  # The Bahamas
                "Q781",  # Antigua and Barbuda
                "Q784",  # Dominica
                "Q986",  # Eritrea
                "Q1005",  # The Gambia
                "Q1009",  # Cameroon
                "Q1013",  # Lesotho
                "Q1014",  # Liberia
                "Q1020",  # Malawi
                "Q1027",  # Mauritius
                "Q1030",  # Namibia
                "Q1033",  # Nigeria
                "Q1036",  # Uganda
                "Q1037",  # Rwanda
                "Q1042",  # Seychelles
                "Q1044",  # Sierra Leone
                "Q1049",  # Sudan
                "Q1050",  # Eswatini
                "Q16",  # Canada
                "Q27",  # Republic of Ireland
                "Q30",  # United States of America
                "Q114",  # Kenya
                "Q117",  # Ghana
                "Q145",  # United Kingdom
                "Q233",  # Malta
                "Q242",  # Belize
                "Q244",  # Barbados
                "Q967",  # Burundi
                "Q921",  # Brunei
                "Q924",  # Tanzania
                "Q928",  # Philippines
                "Q953",  # Zambia
                "Q954",  # Zimbabwe
                "Q958",  # South Sudan
                "Q963",  # Botswana
            ]

        if language_code == "ay":  # Aymara
            return [
                "Q419",  # Peru
                "Q750",  # Bolivia
            ]

        if language_code == "pt":  # Portuguese
            return [
                "Q574",  # East Timor
                "Q983",  # Equatorial Guinea
                "Q1007",  # Guinea-Bissau
                "Q1011",  # Cape Verde
                "Q1029",  # Mozambique
                "Q1039",  # São Tomé and Príncipe
                "Q45",  # Portugal
                "Q155",  # Brazil
                "Q916",  # Angola
                "Q824489",  # Estado Novo
            ]

        if language_code == "qu":  # Quechua
            return [
                "Q419",  # Peru
                "Q750",  # Bolivia
            ]

        if language_code == "ja":  # Japanese
            return [
                "Q695",  # Palau
                "Q17",  # Japan
            ]

        if language_code == "ta":  # Tamil
            return [
                "Q334",  # Singapore
                "Q854",  # Sri Lanka
            ]

        if language_code == "nl":  # Dutch
            return [
                "Q730",  # Suriname
                "Q29999",  # Kingdom of the Netherlands
                "Q31",  # Belgium
            ]

        if language_code == "hy":  # Armenian
            return ["Q399"]  # Armenia

        if language_code == "fa":  # Persian
            return ["Q794"]  # Iran

        if language_code == "ko":  # Korean
            return [
                "Q423",  # North Korea
                "Q884",  # South Korea
            ]

        if language_code == "km":  # Khmer
            return ["Q424"]  # Cambodia

        if language_code == "ms":  # Malay
            return [
                "Q334",  # Singapore
                "Q833",  # Malaysia
                "Q921",  # Brunei
            ]

        if language_code == "mn":  # Mongolian
            return ["Q711"]  # Mongolia

        if language_code == "uz":  # Uzbek
            return [
                "Q265",  # Uzbekistan
                "Q889",  # Afghanistan
            ]

        if language_code == "sr":  # Serbian
            return [
                "Q403",  # Serbia
                "Q225",  # Bosnia and Herzegovina
            ]

        if language_code == "zu":  # Zulu
            return ["Q258"]  # South Africa

        if language_code == "xh":  # Xhosa
            return [
                "Q258",  # South Africa
                "Q954",  # Zimbabwe
            ]

        if language_code == "na":  # Nauruan
            return ["Q697"]  # Nauru

        if language_code == "ar":  # Arabic
            return [
                "Q262",  # Algeria
                "Q398",  # Bahrain
                "Q657",  # Chad
                "Q977",  # Djibouti
                "Q986",  # Eritrea
                "Q1016",  # Libya
                "Q1025",  # Mauritania
                "Q1028",  # Morocco
                "Q1045",  # Somalia
                "Q1049",  # Sudan
                "Q79",  # Egypt
                "Q970",  # Comoros
                "Q796",  # Iraq
                "Q805",  # Yemen
                "Q810",  # Jordan
                "Q817",  # Kuwait
                "Q822",  # Lebanon
                "Q842",  # Oman
                "Q846",  # Qatar
                "Q851",  # Saudi Arabia
                "Q858",  # Syria
                "Q878",  # United Arab Emirates
                "Q889",  # Afghanistan
                "Q948",  # Tunisia
                "Q958",  # South Sudan
            ]

        if language_code == "af":  # Afrikaans
            return ["Q258"]  # South Africa

        if language_code == "gil":  # Gilbertese
            return ["Q710"]  # Kiribati

        if language_code == "ve":  # Venda
            return [
                "Q258",  # South Africa
                "Q954",  # Zimbabwe
            ]

        if language_code == "fr":  # French
            return [
                "Q657",  # Chad
                "Q686",  # Vanuatu
                "Q790",  # Haiti
                "Q971",  # Republic of the Congo
                "Q974",  # Democratic Republic of the Congo
                "Q977",  # Djibouti
                "Q983",  # Equatorial Guinea
                "Q1000",  # Gabon
                "Q1006",  # Guinea
                "Q1008",  # Ivory Coast
                "Q1009",  # Cameroon
                "Q1019",  # Madagascar
                "Q1027",  # Mauritius
                "Q1032",  # Niger
                "Q1037",  # Rwanda
                "Q1041",  # Senegal
                "Q1042",  # Seychelles
                "Q16",  # Canada
                "Q31",  # Belgium
                "Q32",  # Luxembourg
                "Q39",  # Switzerland
                "Q142",  # France
                "Q235",  # Monaco
                "Q965",  # Burkina Faso
                "Q967",  # Burundi
                "Q970",  # Comoros
                "Q912",  # Mali
                "Q929",  # Central African Republic
                "Q945",  # Togo
                "Q962",  # Benin
            ]

        if language_code == "de":  # German
            return [
                "Q347",  # Liechtenstein
                "Q31",  # Belgium
                "Q32",  # Luxembourg
                "Q39",  # Switzerland
                "Q40",  # Austria
                "Q183",  # Germany
            ]

        if language_code == "fj":  # Fijian
            return ["Q712"]  # Fiji

        if language_code == "ht":  # Haitian Creole
            return ["Q790"]  # Haiti

        if language_code == "ho":  # Hiri Motu
            return ["Q691"]  # Papua New Guinea

        if language_code == "pau":  # Palauan
            return ["Q695"]  # Palau

        if language_code == "nso":  # Northern Sotho
            return ["Q258"]  # South Africa

        if language_code == "sm":  # Samoan
            return ["Q683"]  # Samoa

        if language_code == "ss":  # Swazi
            return [
                "Q258",  # South Africa
                "Q1050",  # Eswatini
            ]

        if language_code == "tvl":  # Tuvaluan
            return ["Q672"]  # Tuvalu

        if language_code == "to":  # Tongan
            return ["Q678"]  # Tonga

        if language_code == "tet":  # Tetum
            return ["Q574"]  # East Timor

        if language_code == "tn":  # Tswana
            return [
                "Q258",  # South Africa
                "Q954",  # Zimbabwe
            ]

        if language_code == "tpi":  # Tok Pisin
            return ["Q691"]  # Papua New Guinea

        if language_code == "ts":  # Tsonga
            return [
                "Q258",  # South Africa
                "Q954",  # Zimbabwe
            ]

        if language_code == "st":  # Sesotho
            return [
                "Q258",  # South Africa
                "Q1013",  # Lesotho
                "Q954",  # Zimbabwe
            ]

        if language_code == "bi":  # Bislama
            return ["Q686"]  # Vanuatu

        if language_code == "gn":  # Guarani
            return [
                "Q733",  # Paraguay
                "Q750",  # Bolivia
            ]

        if language_code == "mh":  # Marshallese
            return ["Q709"]  # Marshall Islands

        if language_code == "mi":  # Māori
            return ["Q664"]  # New Zealand

        if language_code == "nr":  # Southern Ndebele
            return ["Q258"]  # South Africa

        if language_code == "hif":  # Fiji Hindi
            return ["Q712"]  # Fiji

        if language_code == "zgh":  # Standard Moroccan Berber
            return ["Q1028"]  # Morocco

        if language_code == "sw":  # Swahili
            return [
                "Q1036",  # Uganda
                "Q1037",  # Rwanda
                "Q114",  # Kenya
                "Q924",  # Tanzania
            ]

        if language_code == "mg":  # Malagasy
            return ["Q1019"]  # Madagascar

        if language_code == "so":  # Somali
            return ["Q1045"]  # Somalia

        if language_code == "ny":  # Chewa
            return [
                "Q1020",  # Malawi
                "Q954",  # Zimbabwe
            ]

        if language_code == "rw":  # Kinyarwanda
            return ["Q1037"]  # Rwanda

        if language_code == "crs":  # Seychellois Creole
            return ["Q1042"]  # Seychelles

        if language_code == "ti":  # Tigrinya
            return ["Q986"]  # Eritrea

        if language_code == "wo":  # Wolof
            return ["Q1041"]  # Senegal

        if language_code == "pbp":  # Badyara
            return ["Q1041"]  # Senegal

        if language_code == "kri":  # Krio
            return ["Q1044"]  # Sierra Leone

        if language_code == "kea":  # Cape Verdean Creole
            return ["Q1011"]  # Cape Verde

        if language_code == "bjs":  # Bajan Creole
            return ["Q244"]  # Barbados

        if language_code == "tr":  # Turkish
            return [
                "Q43",  # Turkey
                "Q229",  # Cyprus
            ]

        if language_code == "is":  # Icelandic
            return ["Q189"]  # Iceland

        if language_code == "it":  # Italian
            return [
                "Q38",  # Italy
                "Q39",  # Switzerland
                "Q238",  # San Marino
            ]

        if language_code == "pl":  # Polish
            return ["Q36"]  # Poland

        if language_code == "fi":  # Finnish
            return ["Q33"]  # Finland

        if language_code == "ab":  # Abkhaz
            return ["Q230"]  # Georgia

        if language_code == "hr":  # Croatian
            return [
                "Q224",  # Croatia
                "Q225",  # Bosnia and Herzegovina
            ]

        if language_code == "ca":  # Catalan
            return ["Q228"]  # Andorra

        if language_code == "ru":  # Russian
            return [
                "Q159",  # Russia
                "Q184",  # Belarus
                "Q232",  # Kazakhstan
                "Q813",  # Kyrgyzstan
                "Q863",  # Tajikistan
            ]

        if language_code == "zh":  # Chinese
            return [
                "Q148",  # People's Republic of China
                "Q865",  # Taiwan
            ]

        if language_code == "ro":  # Romanian
            return [
                "Q217",  # Moldova
                "Q218",  # Romania
            ]

        if language_code == "bg":  # Bulgarian
            return ["Q219"]  # Bulgaria

        if language_code == "ka":  # Georgian
            return ["Q230"]  # Georgia

        if language_code == "sq":  # Albanian
            return [
                "Q221",  # North Macedonia
                "Q222",  # Albania
            ]

        if language_code == "uk":  # Ukrainian
            return ["Q212"]  # Ukraine

        if language_code == "cnr":  # Montenegrin
            return ["Q236"]  # Montenegro

        if language_code == "sv":  # Swedish
            return [
                "Q33",  # Finland
                "Q34",  # Sweden
            ]

        if language_code == "da":  # Danish
            return [
                "Q35",  # Denmark
                "Q756617",  # Kingdom of Denmark
            ]

        if language_code == "no":  # Norwegian
            return ["Q20"]  # Norway

        if language_code == "lb":  # Luxembourgish
            return ["Q32"]  # Luxembourg

        if language_code == "sk":  # Slovak
            return ["Q214"]  # Slovakia

        if language_code == "cs":  # Czech
            return ["Q213"]  # Czech Republic

        if language_code == "sl":  # Slovene
            return ["Q215"]  # Slovenia

        if language_code == "hu":  # Hungarian
            return ["Q28"]  # Hungary

        if language_code == "et":  # Estonian
            return ["Q191"]  # Estonia

        if language_code == "lv":  # Latvian
            return ["Q211"]  # Latvia

        if language_code == "lt":  # Lithuanian
            return ["Q37"]  # Lithuania

        if language_code == "be":  # Belarusian
            return ["Q184"]  # Belarus

        if language_code == "el":  # Greek
            return [
                "Q41",  # Greece
                "Q229",  # Cyprus
                "Q229",  # Cyprus
            ]

        if language_code == "ga":  # Irish
            return ["Q27"]  # Republic of Ireland

        if language_code == "mt":  # Maltese
            return ["Q233"]  # Malta

        if language_code == "id":  # Indonesian
            return ["Q252"]  # Indonesia

        if language_code == "kk":  # Kazakh
            return ["Q232"]  # Kazakhstan

        if language_code == "az":  # Azerbaijani
            return ["Q227"]  # Azerbaijan

        if language_code == "mk":  # Macedonian
            return ["Q221"]  # North Macedonia

        if language_code == "bs":  # Bosnian
            return ["Q225"]  # Bosnia and Herzegovina

        if language_code == "rm":  # Romansh
            return ["Q39"]  # Switzerland

        if language_code == "nah":  # Nahuatl
            return ["Q96"]  # Mexico

        if language_code == "mwl":  # Mirandese
            return ["Q45"]  # Portugal

        if language_code == "yua":  # Yucatec Maya
            return ["Q96"]  # Mexico

        if language_code == "nb":  # Bokmål
            return ["Q20"]  # Norway

        if language_code == "nn":  # Nynorsk
            return ["Q20"]  # Norway

        if language_code == "am":  # Amharic
            return ["Q115"]  # Ethiopia

        if language_code == "jv":  # Javanese
            return ["Q252"]  # Indonesia

        if language_code == "rn":  # Kirundi
            return ["Q967"]  # Burundi

        if language_code == "smi":  # Sámi
            return ["Q20"]  # Norway

        if language_code == "prs":  # Dari
            return ["Q889"]  # Afghanistan

        if language_code == "pwn":  # Paiwan
            return ["Q865"]  # Taiwan

        if language_code == "nmq":  # Nambya
            return ["Q954"]  # Zimbabwe

        if language_code == "bwg":  # Barwe
            return ["Q954"]  # Zimbabwe

        if language_code == "ur":  # Urdu
            return ["Q843"]  # Pakistan

        if language_code == "vi":  # Vietnamese
            return ["Q881"]  # Vietnam

        if language_code == "lo":  # Lao
            return ["Q819"]  # Laos

        if language_code == "th":  # Thai
            return ["Q869"]  # Thailand

        if language_code == "my":  # Burmese
            return ["Q836"]  # Myanmar

        if language_code == "ky":  # Kyrgyz
            return ["Q813"]  # Kyrgyzstan

        if language_code == "tg":  # Tajik
            return ["Q863"]  # Tajikistan

        if language_code == "tk":  # Turkmen
            return [
                "Q874",  # Turkmenistan
                "Q889",  # Afghanistan
            ]

        if language_code == "he":  # Hebrew
            return ["Q801"]  # Israel

        if language_code == "bn":  # Bengali
            return ["Q902"]  # Bangladesh

        if language_code == "si":  # Sinhala
            return ["Q854"]  # Sri Lanka

        if language_code == "ndc":  # Ndau
            return ["Q954"]  # Zimbabwe

        if language_code == "fo":  # Faroese
            return ["Q756617"]  # Kingdom of Denmark

        if language_code == "kl":  # Greenlandic
            return ["Q756617"]  # Kingdom of Denmark

        if language_code == "dv":  # Maldivian
            return ["Q826"]  # Maldives

        if language_code == "bal":  # Balochi
            return ["Q889"]  # Afghanistan

        if language_code == "dz":  # Dzongkha
            return ["Q917"]  # Bhutan

        if language_code == "fil":  # Filipino
            return ["Q928"]  # Philippines

        if language_code == "khi":  # Khoisan
            return ["Q954"]  # Zimbabwe

        if language_code == "kck":  # Kalanga
            return ["Q954"]  # Zimbabwe

        if language_code == "ne":  # Nepali
            return ["Q837"]  # Nepal

        if language_code == "sg":  # Sango
            return ["Q929"]  # Central African Republic

        if language_code == "sn":  # Shona
            return ["Q954"]  # Zimbabwe

        if language_code == "toi":  # Tonga
            return ["Q954"]  # Zimbabwe

        if language_code == "ami":  # Amis language
            return ["Q865"]  # Taiwan

        if language_code == "nd":  # Northern Ndebele
            return ["Q954"]  # Zimbabwe

        if language_code == "ku":  # Kurdish
            return ["Q796"]  # Iraq

        if language_code == "map":  # Austronesian
            return ["Q865"]  # Taiwan

        if language_code == "ps":  # Pashto
            return ["Q889"]  # Afghanistan

        assert False, "language code <" + language_code + "> without hardcoded list of matching countries"

    # unknown data, known to be completely inside -> not allowed, returns None
    # known to be outside or on border -> allowed, returns reason
    def why_object_is_allowed_to_have_foreign_language_label(self, object_description, wikidata_id):
        if wikidata_id == None:
            return "no wikidata entry exists"

        if self.expected_language_code == None:
            return "no expected language is defined"

        country_ids_where_expected_language_will_be_enforced = self.wikidata_ids_of_countries_with_language(self.expected_language_code)

        countries = self.get_country_location_from_wikidata_id(wikidata_id)
        if countries == None:
            # TODO locate based on coordinates...
            return None
        for country_id in countries:
            if country_id in country_ids_where_expected_language_will_be_enforced:
                continue
            country_name = wikidata_processing.get_wikidata_label(country_id, 'en')
            if country_name == None:
                return "it is at least partially in country without known name on Wikidata (country_id=" + country_id + ")"
            if country_id == 'Q7318':  # Nazi Germany. Wikidata is being silly again
                # not reporting or mentioning as this is not a Wikidata validator
                # and there is enormous amount of ontology issues if anyone would care about them
                # print(object_description + " is tagged on wikidata as location in no longer existing " + country_name)
                return None
            return "it is at least partially in " + country_name
        return None

    def get_country_location_from_wikidata_id(self, object_wikidata_id):
        countries = wikimedia_connection.get_property_from_wikidata(object_wikidata_id, 'P17')
        if countries == None:
            return None
        returned = []
        for country in countries:
            country_id = country['mainsnak']['datavalue']['value']['id']
            # we need to check whether locations still belongs to a given country
            # it is necessary to avoid gems like
            # "Płock is allowed to have foreign wikipedia link, because it is at least partially in Nazi Germany"
            # P582 indicates the time an item ceases to exist or a statement stops being valid
            # so statements qualified by P582 refer to the past
            try:
                country['qualifiers']['P582']
            except KeyError:
                # P582 is missing, therefore it is not marked as a statement applying only to the past
                returned.append(country_id)
        return returned

    def element_can_be_reduced_to_position_at_single_location(self, element):
        if element.get_element().tag == "relation":
            relation_type = element.get_tag_value("type")
            if relation_type in ('person', 'route'):
                return False
        if element.get_tag_value("waterway") == "river":
            return False
        return True

    def object_should_be_deleted_not_repaired(self, object_type, tags):
        if object_type == "relation":
            if tags.get("type") == "person":
                return True
        if tags.get("historic") == "battlefield":
            return True
        if tags.get("boundary") == "timezone":
            return True
        if tags.get("xmas:feature") != None:
            return True  # events mapped as features, seem quite dubious to me but can be sort of treated as places
        return False

    def describe_osm_object(self, element):
        name = element.get_tag_value("name")
        if name == None:
            name = ""
        return name + " " + element.get_link()

    def is_wikipedia_page_geotagged(self, page):
        # <span class="latitude">50°04'02”N</span>&#160;<span class="longitude">19°55'03”E</span>
        index = page.find("<span class=\"latitude\">")
        inline = page.find("coordinates inline plainlinks")
        if index > inline != -1:
            index = -1  # inline coordinates are not real ones
        if index == -1:
            kml_data_str = "><span id=\"coordinates\"><b>Route map</b>: <a rel=\"nofollow\" class=\"external text\""
            if page.find(kml_data_str) == -1:  # enwiki article links to area, not point (see 'Central Park')
                return False
        return True
