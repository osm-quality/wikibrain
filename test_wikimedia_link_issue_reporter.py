import unittest
import wikibrain.wikipedia_knowledge
import wikibrain.wikidata_knowledge
import wikibrain.wikimedia_link_issue_reporter
import wikibrain
import wikimedia_connection.wikimedia_connection as wikimedia_connection
import wikimedia_connection.wikidata_processing as wikidata_processing
import osm_handling_config.global_config as osm_handling_config


class Tests(unittest.TestCase):
    def detector(self):
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        return wikibrain.wikimedia_link_issue_reporter.WikimediaLinkIssueDetector()

    def test_old_style_be_tarask_link(self):
        # https://www.openstreetmap.org/node/243018588/history
        # https://be.wikipedia.org/wiki/be:Цярэшкі%20(Шаркаўшчынскі%20раён)
        # https://be-tarask.wikipedia.org/wiki/Цярэшкі%20(Шаркоўшчынскі%20раён)
        # https://www.wikidata.org/wiki/Q6545847
        tags = {"wikipedia": "be:Цярэшкі (Шаркаўшчынскі раён)", "wikipedia:be-tarask": "Цярэшкі (Шаркоўшчынскі раён)"}
        location = None
        object_type = 'node'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertEqual("Q6545847", wikimedia_connection.get_wikidata_object_id_from_link("be:Цярэшкі (Шаркаўшчынскі раён)"))
        self.assertEqual("Q6545847", wikimedia_connection.get_wikidata_object_id_from_link("be-tarask:Цярэшкі (Шаркоўшчынскі раён)"))
        self.assertNotEqual(None, problem)
        self.assertNotEqual('wikipedia tag in outdated form and there is mismatch between links', problem.data()['error_id'])
        self.assertEqual("wikipedia tag in an outdated form for removal", problem.data()['error_id'])

    def test_nonexisting_wikidata_link(self):
        # not malformed but does not exist
        tags = {"wikidata": "Q999999999999999999999999999999999999"}
        location = None
        object_type = 'node'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertNotEqual(None, problem)
        self.assertEqual("wikidata tag links to 404", problem.data()['error_id'])

    def test_https_link_as_invalid_in_wikipedia_tag(self):
        # not malformed but does not exist
        tags = {"wikipedia": "https://wikipedia.org/wiki/Article"}
        location = None
        object_type = 'node'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertNotEqual(None, problem)
        self.assertEqual("malformed wikipedia tag", problem.data()['error_id'])

    def test_https_link_as_invalid_in_secondary_wikipedia_tag(self):
        # not malformed but does not exist
        tags = {"name:etymology:wikipedia": "https://de.wikipedia.org/wiki/Konrad_Wirnhier"}
        location = None
        object_type = 'node'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertNotEqual(None, problem)
        self.assertEqual("malformed wikipedia tag", problem.data()['error_id'])

    def test_malformed_wikidata_link(self):
        # not malformed but does not exist
        tags = {"wikidata": "Saturn"}
        location = None
        object_type = 'node'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertNotEqual(None, problem)
        self.assertEqual("malformed wikidata tag", problem.data()['error_id'])

    def test_nonexisting_secondary_wikidata_link(self):
        # not malformed but does not exist
        tags = {"nonsense:wikidata": "Q999999999999999999999999999999999999"}
        location = None
        object_type = 'node'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertNotEqual(None, problem)
        self.assertEqual("secondary wikidata tag links to 404", problem.data()['error_id'])

    def test_empty_wikidata_is_malformed(self):
        self.assertNotEqual(None, self.detector().critical_structural_issue_report('node', {'wikidata': '', 'wikipedia': 'en:Oslo'}))

    def test_malformed_secondary_wikidata_is_malformed(self):
        self.assertNotEqual(None, self.detector().critical_structural_issue_report('node', {'operator:wikidata': '#'}))

    def test_getting_redirected_wikidata_on_one_without_redirect(self):
        self.assertEqual("Q42", self.detector().get_wikidata_id_after_redirect("Q42"))

    def test_getting_redirecting_wikidata_on_one_with_redirect(self):
        self.assertEqual("Q30168242", self.detector().get_wikidata_id_after_redirect("Q86673356"))

    def test_allow_trailing_semicolon_with_multiple_elements(self):
        # https://t.me/osmhr/17923
        # https://www.openstreetmap.org/way/365519518
        problem = self.detector().critical_structural_issue_report('node', {'buried:wikidata': 'Q12636988;Q988613;Q125654;Q3446366;Q1280010;Q1254204;Q6154837;Q1253890;Q1254973;Q1564945;Q1564896;Q1564308;Q1275600;Q11043751;Q12629841;Q12633385;Q3446999;Q3446505;Q3436888;Q12644887;Q640602;Q1565289;Q1564970;Q13566201;Q551371;'})
        if problem != None:
            print(problem.data()['error_message'])
        self.assertEqual(None, problem)

    def test_allow_trailing_semicolon_with_multiple_elements_minimal_case(self):
        # https://t.me/osmhr/17923
        # https://www.openstreetmap.org/way/365519518
        problem = self.detector().critical_structural_issue_report('node', {'buried:wikidata': 'Q1565289;Q1564970;Q13566201;Q551371;'})
        if problem != None:
            print(problem.data()['error_message'])
        self.assertEqual(None, problem)

    def test_allow_trailing_semicolon_with_multiple_elements_direct_function_test(self):
        self.assertEqual(False, self.detector().is_wikidata_tag_clearly_broken('Q12636988;Q988613;Q125654;Q3446366;Q1280010;Q1254204;Q6154837;Q1253890;Q1254973;Q1564945;Q1564896;Q1564308;Q1275600;Q11043751;Q12629841;Q12633385;Q3446999;Q3446505;Q3436888;Q12644887;Q640602;Q1565289;Q1564970;Q13566201;Q551371;'))

    def test_block_semicolon_with_space_with_multiple_elements(self):
        # https://t.me/osmhr/17923
        # https://www.openstreetmap.org/way/365519518
        problem = self.detector().critical_structural_issue_report('node', {'buried:wikidata': 'Q12636988; Q988613'})
        self.assertNotEqual(None, problem)

    def test_block_trailing_semicolon_with_single_element(self):
        # https://t.me/osmhr/17923
        # https://www.openstreetmap.org/way/365519518
        problem = self.detector().critical_structural_issue_report('node', {'buried:wikidata': 'Q12636988;'})
        self.assertNotEqual(None, problem)

    def test_nonexisting_wikidata_is_not_malformed(self):
        self.assertEqual(None, self.detector().critical_structural_issue_report('node', {'wikipedia': 'en:Oslo'}))

    def test_multiple_wikidata_are_not_automatically_malformed(self):
        self.assertEqual(False, self.detector().is_wikidata_tag_clearly_broken('Q8128437837382347234823472;Q38272487927'))

    def test_nonexisting_wikidata_is_not_allowed_in_wikidata_multiple_value_list(self):
        tags = {
            "whatever:wikidata": "Q8128437837382347234823472;Q38272487927",
        }
        location = None
        object_type = 'node'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertNotEqual(None, problem)

    def test_existing_wikidata_is_allowed_in_wikidata_multiple_value_list(self):
        tags = {
            "whatever:wikidata": "Q1;Q2",
        }
        location = None
        object_type = 'node'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertEqual(None, problem)

    def test_well_formed_nonexisting_wikidata(self):
        self.assertNotEqual(None, self.detector().critical_structural_issue_report('node', {'wikidata': 'Q812843783738234723482347238272487927', 'wikipedia': 'en:Oslo'}))

    def test_malformed_wikidata_crash(self):
        self.assertNotEqual(None, self.detector().critical_structural_issue_report('node', {'wikidata': 'Q81927)', 'wikipedia': 'en:Oslo'}))

    def test_description_of_distance_return_string(self):
        example_city_wikidata_id = 'Q31487'
        self.assertEqual(type(""), type(self.detector().get_distance_description_between_location_and_wikidata_id((50, 20), example_city_wikidata_id)))

    def test_description_of_distance_return_string_for_missing_location(self):
        example_city_wikidata_id = 'Q31487'
        self.assertEqual(type(""), type(self.detector().get_distance_description_between_location_and_wikidata_id((None, None), example_city_wikidata_id)))

    def test_description_of_distance_return_string_for_missing_location_and_missing_location_in_wikidata(self):
        example_artist_id = 'Q561127'
        self.assertEqual(type(""), type(self.detector().get_distance_description_between_location_and_wikidata_id((None, None), example_artist_id)))

    def test_description_of_distance_return_string_for_missing_location_in_wikidata(self):
        example_artist_id = 'Q561127'
        self.assertEqual(type(""), type(self.detector().get_distance_description_between_location_and_wikidata_id((50, 20), example_artist_id)))

    def test_wikidata_ids_of_countries_with_language(self):
        self.assertEqual(['Q36'], self.detector().wikidata_ids_of_countries_with_language("pl"))
        self.assertEqual(('Q408' in self.detector().wikidata_ids_of_countries_with_language("en")), True)

    def test_that_completely_broken_wikipedia_tags_are_detected(self):
        self.assertEqual(True, self.detector().is_wikipedia_tag_clearly_broken("pl"))
        self.assertEqual(True, self.detector().is_wikipedia_tag_clearly_broken("polski:Smok"))

    def test_that_completely_broken_wikipedia_tag_detector_has_no_false_positives(self):
        self.assertEqual(False, self.detector().is_wikipedia_tag_clearly_broken("pl:smok"))

    def test_be_tarask_unusual_lang_code_is_accepted_in_wikipedia_tag(self):
        # https://www.openstreetmap.org/node/243011151 0 version 15
        self.assertEqual(False, self.detector().is_wikipedia_tag_clearly_broken("be-tarask:Машніца (Менская вобласьць)"))

    def test_be_tarask_unusual_lang_code_is_accepted(self):
        self.assertEqual(False, self.detector().is_language_code_clearly_broken("be-tarask"))

    def test_be_tarask_unusual_lang_code_is_accepted_full_pass_test(self):
        tags = {
            "wikipedia": "be-tarask:Калілы",
            "wikidata": "Q6496859",
            "place": "hamlet",
            "name": "Калілы",
        }
        location = None
        object_type = 'node'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertEqual(None, problem)

    def test_be_x_old_unusual_lang_code_is_not_considered_as_utterly_broken_in_wikipedia_tag(self):
        # https://www.openstreetmap.org/node/243011151 0 version 15
        self.assertEqual(False, self.detector().is_wikipedia_tag_clearly_broken("be-x-old:Пятроўшчына (прадмесьце)"))

    def test_be_tarask_unusual_lang_code_is_not_considered_as_utterly_broken(self):
        self.assertEqual(False, self.detector().is_language_code_clearly_broken("be-x-old"))

    def test_detector_of_old_style_wikipedia_links_accepts_valid(self):
        key = 'wikipedia:pl'
        self.assertEqual(True, self.detector().check_is_it_valid_key_for_old_style_wikipedia_tag(key))
        tags = {key: 'Kościół Najświętszego Serca Pana Jezusa'}
        self.assertEqual(None, self.detector().check_is_invalid_old_style_wikipedia_tag_present(tags, tags))

    def test_detector_of_old_style_wikipedia_links_refuses_invalid(self):
        key = 'wikipedia:fixme'
        self.assertEqual(False, self.detector().check_is_it_valid_key_for_old_style_wikipedia_tag(key))
        tags = {key: 'Kościół Najświętszego Serca Pana Jezusa'}
        self.assertNotEqual(None, self.detector().check_is_invalid_old_style_wikipedia_tag_present(tags, tags))

    def test_presence_of_fields_in_blacklist_of_unlinkable_entries(self):
        blacklist = wikibrain.wikidata_knowledge.blacklist_of_unlinkable_entries()
        for key in blacklist:
            self.assertEqual("Q", key[0])
            #print(key)
            try:
                blacklist[key]["prefix"]
                blacklist[key]["expected_tags"]
            except KeyError:
                print(key, "test_presence_of_fields_in_blacklist_of_unlinkable_entries")
                print(blacklist[key], "test_presence_of_fields_in_blacklist_of_unlinkable_entries")
                assert False

    def test_that_relinkable_as_animals_target_species(self):
        self.ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary('Q42569')
        blacklist = wikibrain.wikidata_knowledge.blacklist_of_unlinkable_entries()
        count = 0
        for wikidata_id in blacklist:
            if blacklist[wikidata_id]['prefix'] != "species:":
                continue
            count += 1
            is_animal = False
            for type_id in self.detector().wikidata_entries_classifying_entry(wikidata_id):
                potential_failure = self.detector().get_reason_why_type_makes_object_invalid_primary_link(type_id)
                if potential_failure == None:
                    continue
                expected_error = 'an animal or plant (and not an individual one)'
                if potential_failure['what'] != expected_error:
                    self.detector().output_debug_about_wikidata_item(wikidata_id)
                    self.assertEqual(potential_failure['what'], expected_error)
                is_animal = True
                break
            if is_animal != True:
                print()
                print("18888888888888888888888")
                print(wikidata_id, " not recognized as an animal!")
                print("fix wikimedia_link_issue_reporter or fix wikidata and flush cache (wikimedia-connection-cache/wikidata_by_id/<wikidata_id>.wikidata_entity.txt)")
                print("58888888888888888888888")
                for type_id in self.detector().wikidata_entries_classifying_entry(wikidata_id):
                    potential_failure = self.detector().get_reason_why_type_makes_object_invalid_primary_link(type_id)
                    print(type_id, potential_failure)
                assert False
        self.assertNotEqual(count, 0)

    def ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary(self, wikidata_id):
        passed_tags = {'wikipedia': 'dummy_filler'}
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        primary_linkability_status = self.detector().get_error_report_if_secondary_wikipedia_tag_should_be_used(wikidata_id, passed_tags)
        if primary_linkability_status == None:
            self.detector().output_debug_about_wikidata_item(wikidata_id)
        self.assertNotEqual(None, primary_linkability_status)

    def test_that_sheep_is_reported_as_an_animal(self):
        self.ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary('Q7368')

    def test_that_goat_is_reported_as_an_animal(self):
        self.ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary('Q2934')

    def test_that_horse_is_reported_as_an_animal(self):
        self.ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary('Q726')

    def test_that_llama_is_reported_as_an_animal(self):
        self.ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary('Q42569')

    def test_that_generic_and_general_lighthouse_article_is_not_linkable_on_specific_objects(self):
        self.ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary('Q39715')

    def test_that_linking_to_human_is_reported_before_missing_wikipedia_tag(self):
        tags = {"wikipedia": "en:Stanislav Petrov"}
        location = None
        object_type = 'way'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertNotEqual(None, problem)
        self.assertNotEqual('wikidata from wikipedia tag', problem.data()['error_id'])
        self.assertEqual("should use a secondary wikipedia tag - linking from wikipedia tag to a human", problem.data()['error_id'])

    def test_that_shooting_is_reported_more_specifically_than_generic_intentional_human_activity(self):
        # https://www.wikidata.org/wiki/Q112898269
        tags = {"wikipedia": "en:Highland Park parade shooting", 'wikidata': 'Q112898269'}
        location = None
        object_type = 'way'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertEqual(False, "tag to an intentional human activity" in problem.data()['error_id'])

    def test_that_agriculture_is_reported_more_specifically_than_generic_intentional_human_activity(self):
        # https://www.wikidata.org/wiki/Q11451
        tags = {"wikipedia": "en:Agriculture", 'wikidata': 'Q11451'}
        location = None
        object_type = 'way'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertEqual(False, "tag to an intentional human activity" in problem.data()['error_id'])

    # TODO: investigate after
    # https://github.com/matkoniecz/OSM-wikipedia-tag-validator/issues/17
    # is resolved and this error is reenabled
    #def test_that_redirect_link_to_taxon_is_detected_as_problematic(self):
    #    tags = {"wikipedia": "de:Walnussbaum", 'natural': 'tree'}
    #    location = None
    #    object_type = 'node'
    #    object_description = "fake test object"
    #    problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
    #    self.assertNotEqual (None, problem)

    def test_that_direct_link_to_taxon_is_detected_as_problematic(self):
        tags = {"wikipedia": "de:Walnüsse", 'natural': 'tree'}
        location = None
        object_type = 'node'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertNotEqual(None, problem)

    def test_that_linking_to_human_is_reported_from_reordeable_issues(self):
        tags = {"wikipedia": "en:Stanislav Petrov"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual(None, problem)
        self.assertEqual("should use a secondary wikipedia tag - linking from wikipedia tag to a human", problem.data()['error_id'])

    def test_that_linking_to_human_is_reported_from_reordeable_issues_specified_as_wikidata(self):
        tags = {"wikidata": "Q52412"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual(None, problem)
        self.assertEqual("should use a secondary wikipedia tag - linking from wikidata tag to a human", problem.data()['error_id'])

    def test_that_linking_to_human_is_reported_based_on_wikidata(self):
        wikidata_id = "Q52412"
        location = None
        object_description = "fake test object"
        tags = {'wikipedia': 'dummy'}
        problem = self.detector().get_problem_based_on_wikidata_and_osm_element(object_description, location, wikidata_id, tags)
        self.assertNotEqual(None, problem)
        self.assertEqual("should use a secondary wikipedia tag - linking from wikipedia tag to a human", problem.data()['error_id'])

    def test_that_linking_to_event_is_reported_based_on_wikidata(self):
        wikidata_id = "Q635051"
        location = None
        object_description = "fake test object"
        tags = {'wikipedia': 'dummy'}
        problem = self.detector().get_problem_based_on_wikidata_and_osm_element(object_description, location, wikidata_id, tags)
        self.assertNotEqual(None, problem)
        self.assertEqual("should use a secondary wikipedia tag - linking from wikipedia tag to an event", problem.data()['error_id'])

    def test_that_linking_to_art_genre_is_preferred_to_be_reported_to_reporting_linking_to_an_event(self):
        # https://www.wikidata.org/wiki/Q2078515 should link to something less specific than an event
        wikidata_id = "Q2078515"
        location = None
        object_description = "fake test object"
        tags = {'wikipedia': 'dummy'}
        problem = self.detector().get_error_report_if_type_unlinkable_as_primary(wikidata_id, tags)
        self.assertNotEqual(None, problem)
        self.assertNotEqual("should use a secondary wikipedia tag - linking from wikipedia tag to an event", problem.data()['error_id'])
        self.assertEqual("should use a secondary wikipedia tag - linking from wikipedia tag to an oration", problem.data()['error_id'])

    def test_that_linking_to_tax_is_preferred_to_be_reported_to_reporting_linking_to_unspecific_activity(self):
        # https://www.wikidata.org/wiki/Q2078515 should link to something less specific than an event
        wikidata_id = "Q1270515"
        location = None
        object_description = "fake test object"
        tags = {'wikidata': wikidata_id}
        problem = self.detector().get_error_report_if_type_unlinkable_as_primary(wikidata_id, tags)
        self.assertNotEqual(None, problem)
        self.assertNotEqual("should use a secondary wikipedia tag - linking from wikidata tag to an intentional human activity", problem.data()['error_id'])
        self.assertEqual("should use a secondary wikipedia tag - linking from wikidata tag to a tax", problem.data()['error_id'])

    def test_that_military_operation_complaint_is_more_specific_than_just_an_event(self):
        # https://www.wikidata.org/wiki/Q708235 should link to something less specific than an event
        wikidata_id = "Q708235"
        location = None
        object_description = "fake test object"
        tags = {'wikipedia': 'dummy'}
        problem = self.detector().get_error_report_if_type_unlinkable_as_primary(wikidata_id, tags)
        self.assertNotEqual(None, problem)
        self.assertNotEqual("should use a secondary wikipedia tag - linking from wikipedia tag to an event", problem.data()['error_id'])

    def test_that_linking_aircraft_family_is_detected(self):
        self.ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary('Q2101666')

    def test_effective_wikipedia(self):
        tags = {"wikidata": "Q52412"}
        wikipedia = self.detector().get_effective_wikipedia_tag(tags)
        self.assertEqual("en:Stanislav Petrov", wikipedia)

    def test_effective_wikidata(self):
        tags = {"wikipedia": "en:Stanislav Petrov"}
        wikidata = self.detector().get_effective_wikidata_tag(tags)
        self.assertEqual("Q52412", wikidata)

    def test_valid_redirect_links(self):
        # "wikipedia wikidata mismatch" not reported where redirect is assigned own wikidata
        # https://it.wikipedia.org/w/index.php?title=Savazza&redirect=no Q18438710
        # https://github.com/matkoniecz/OSM-wikipedia-tag-validator/issues/8
        tags = {"wikipedia": "it:Savazza", "wikidata": "Q18438710"}
        location = None
        object_type = 'node'
        object_description = "fake test object"
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertEqual(None, problem)

    # TODO: implement this at certain point
    #def test_576_in_future(self):
    #    wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
    #    self.assertEqual(self.detector().check_is_object_is_existing('Q650270'), None)

    def test_that_indian_teritory_is_considered_as_linkable_by_passing_tags(self):
        wikidata_id = 'Q1516298'
        passed_tags = {'wikidata': wikidata_id}
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        primary_linkability_status = self.detector().get_error_report_if_secondary_wikipedia_tag_should_be_used(wikidata_id, passed_tags)
        # somehow changed on its own? well, I will not protest...
        # stopped being merged with another entity, see for example
        # https://www.wikidata.org/w/index.php?title=Q1516298&diff=1357250965&oldid=1357245965
        #if primary_linkability_status == None:
        #    self.detector().output_debug_about_wikidata_item(wikidata_id)
        #self.assertNotEqual (None, primary_linkability_status)

        wikidata_id = 'Q1516298'
        passed_tags = {'boundary': 'aboriginal_lands', 'wikidata': wikidata_id}
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        primary_linkability_status = self.detector().get_error_report_if_secondary_wikipedia_tag_should_be_used(wikidata_id, passed_tags)
        if primary_linkability_status != None:
            self.detector().output_debug_about_wikidata_item(wikidata_id)
        self.assertEqual(None, primary_linkability_status)

    def test_simplest_passing_case_for_why_object_is_allowed_to_have_foreign_language_label(self):
        self.assertNotEqual(None, self.detector().why_object_is_allowed_to_have_foreign_language_label("dummy description", 'Q205547'))

    def test_that_object_with_part_of_indicating_border_is_allowed_to_have_foreign_language_label(self):
        # https://www.wikidata.org/w/index.php?title=Q2124428&diff=prev&oldid=1015357102
        object_description = "part of"
        self.assertNotEqual(None, self.detector().why_object_is_allowed_to_have_foreign_language_label(object_description, 'Q2124428'))
        tags = {"wikidata": "Q2124428", 'wikipedia': "en:Mont d'Ambin"}
        location = None
        problem = self.detector().get_wikipedia_language_issues(object_description, tags, "en:Mont d'Ambin", "Q2124428")
        self.assertEqual(None, problem)

    def test_that_wikipedia_wikidata_conflict_is_detected_for_secondary_tags(self):
        # https://www.wikidata.org/wiki/Q2743499 - that bank
        matching_tags = {"brand:wikidata": "Q2743499", "brand:wikipedia": "en:Punjab National Bank"}
        # https://www.wikidata.org/wiki/Q274349 - some astronomer
        not_matching_tags = {"brand:wikidata": "Q274349", "brand:wikipedia": "en:Punjab National Bank"}
        location = None
        object_description = "fake test object"
        should_be_fine = self.detector().get_the_most_important_problem_generic(matching_tags, location, "node", object_description)
        should_be_failing = self.detector().get_the_most_important_problem_generic(not_matching_tags, location, "node", object_description)
        self.assertEqual(None, should_be_fine)
        self.assertNotEqual(None, should_be_failing)

    def test_that_wikidata_works_with_multiple_brands(self):
        # https://www.wikidata.org/wiki/Q53268
        matching_tags = {"brand:wikidata": "Q53268;Q6746;Q27597;Q40966;Q30113"}
        location = None
        object_description = "fake test object"
        should_be_fine = self.detector().get_the_most_important_problem_generic(matching_tags, location, "node", object_description)
        self.assertEqual(None, should_be_fine)

    def test_that_wikidata_works_with_multiple_brands_one_invalid(self):
        # https://www.wikidata.org/wiki/Q53268
        matching_tags = {"brand:wikidata": "Q7501155;Q6746"}
        location = None
        object_description = "fake test object"
        should_be_fine = self.detector().get_the_most_important_problem_generic(matching_tags, location, "node", object_description)
        self.assertIsNone(should_be_fine)

    def test_get_dissolved_brands(self):
        # Basic test against Q4746
        self.assertEqual(
            [],
            self.detector().get_dissolved_brands(['Q6746']),
            'Q6746 is marked as dissolved but expected to be valid'
        )
        self.assertEqual(
            [],
            self.detector().get_dissolved_brands(['Q53268','Q6746']),
            'Q53268 and Q6746 is marked as dissolved but expected to be valid'
        )

        self.assertEqual(
            ['Q7501155'],
            self.detector().get_dissolved_brands(['Q7501155']),
            'Q7501155 is marked as valid but expected to be dissolved'
        )
        self.assertEqual(
            ['Q7501155'],
            self.detector().get_dissolved_brands(['Q7501155','Q6746']),
            'Q7501155 is marked as valid but expected to be dissolved'
        )
        self.assertEqual(
            ['Q7501155'],
            self.detector().get_dissolved_brands(['Q6746','Q7501155']),
            'Q7501155 is marked as valid but expected to be dissolved'
        )

    def test_get_dissolved_brands_p576(self):
        # Basic test against Q4746
        self.assertEqual(
            [],
            self.detector().get_dissolved_brands(['Q465952']),
            'Q6746 is marked as dissolved but expected to be valid'
        )
    def test_that_not_prefixes_are_respected(self):
        # https://www.openstreetmap.org/way/165659335
        tags = {"not:brand:wikidata": "Q177054", "brand:wikidata": "Q177054"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual(None, problem)
        self.assertEqual("wikipedia/wikidata type tag that is incorrect according to not:* tag", problem.data()['error_id'])

    def test_that_specific_error_is_reported(self):
        # https://www.wikidata.org/w/index.php?title=Q502053
        tags = {"wikidata": "Q502053"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual(None, problem)
        self.assertNotEqual("should use a secondary wikipedia tag - linking from wikidata tag to an event", problem.data()['error_id'])

    def test_that_specific_error_is_reported_b(self):
        tags = {"wikidata": "Q1595342"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual(None, problem)
        self.assertNotEqual("should use a secondary wikipedia tag - linking from wikidata tag to an event", problem.data()['error_id'])

    def test_that_special_manual_exclusion_list_is_respected(self):
        # in wikidata_knowledge.skipped_cases
        # https://www.wikidata.org/wiki/Q106617236
        tags = {"wikidata": "Q106617236"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertEqual(None, problem)

    def test_that_species_links_species(self):
        tags = {"species:wikidata": "Q169"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual(None, problem)

        tags = {"species:wikipedia": "en:Mango"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual(None, problem)

    def test_that_species_links_species_not_genus(self):
        # https://www.wikidata.org/wiki/Q42292
        tags = {"species:wikidata": "Q42292"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual(None, problem)

    def test_that_species_linking_species_is_fine(self):
        # https://www.wikidata.org/wiki/Q156895
        tags = {"species:wikidata": "Q156895"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertEqual(None, problem)

    def test_that_mecca_cases_not_raising_annoying_warnings(self):
        tags = {"wikidata": "Q175047"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        if problem != None:
            print(problem.data())
        self.assertEqual(None, problem)

        tags = {"wikidata": "Q1415790"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        if problem != None:
            print(problem.data())
        self.assertEqual(None, problem)

    def test_that_taxon_linking_species_is_fine(self):
        # https://www.wikidata.org/wiki/Q42292
        tags = {"taxon:wikidata": "Q156895"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        if problem != None:
            print(problem.data()['error_id'])
        self.assertEqual(None, problem)

    def test_that_semicolon_separation_in_taxon_tags_is_not_causing_crashes(self):
        # https://www.wikidata.org/wiki/Q42292
        tags = {"taxon:wikidata": "Q156895;Q156895"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)

    def test_that_false_positive_bit_is_gone(self):
        tags = {"wikidata": "Q4462601", "wikipedia": "ru:3-я Новоостанкинская улица"}
        location = None
        object_description = "fake test object"
        object_type = 'way'
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        if problem != None:
            print(problem.data()['error_id'])
        self.assertEqual(None, problem)

    def test_that_metawikidatatags_are_not_reported_for_note_prefix(self):
        tags = {"note:wikidata": "gibberish"}
        location = None
        object_description = "fake test object"
        object_type = 'way'
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        if problem != None:
            print(problem.data()['error_id'])
        self.assertEqual(None, problem)

    def test_that_metawikidatatags_are_not_reported_for_source_prefix(self):
        tags = {"source:wikidata": "gibberish"}
        location = None
        object_description = "fake test object"
        object_type = 'way'
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        if problem != None:
            print(problem.data()['error_id'])
        self.assertEqual(None, problem)

    def test_that_metawikidatatags_are_not_reported_for_markers_of_missing_wikidatas(self):
        # see 
        # https://www.wikidata.org/wiki/User:Mateusz_Konieczny/failing_testcases#apparently_missing_wikidata_entries
        tags = {"name:etymology:wikidata:missing": "gibberish"}
        location = None
        object_description = "fake test object"
        object_type = 'way'
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        if problem != None:
            print(problem.data()['error_id'])
        self.assertEqual(None, problem)

    def test_handle_per_lane_wikidata_tags_somehow(self):
        tags = {"destination:ref:wikidata:lanes": "Q2119632|||"}
        location = None
        object_description = "fake test object"
        object_type = 'way'
        problem = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        if problem != None:
            print(problem.data()['error_id'])
        self.assertEqual(None, problem)

    def test_that_cebwiki_complaints_work_well(self):
        object_description = "test"
        tags = {"wikipedia": "ceb:Bot generated article"}
        wikipedia = "ceb:Bot generated article"
        effective_wikidata_id = None
        problem = self.detector().get_wikipedia_language_issues(object_description, tags, wikipedia, effective_wikidata_id)
        self.assertEqual(None, 1)


if __name__ == '__main__':
    unittest.main()
