import unittest
import wikibrain.wikipedia_knowledge
import wikibrain.wikidata_knowledge
import wikibrain.wikimedia_link_issue_reporter
import wikibrain
import wikimedia_connection.wikimedia_connection as wikimedia_connection
import wikimedia_connection.wikidata_processing as wikidata_processing
import osm_handling_config.global_config as osm_handling_config

class Tests(unittest.TestCase):
    def issue_reporter(self):
        return wikibrain.wikimedia_link_issue_reporter.WikimediaLinkIssueDetector()

    def test_empty_wikidata_is_malformed(self):
        self.assertNotEqual (None, self.issue_reporter().critical_structural_issue_report('node', {'wikidata': '', 'wikipedia': 'en:Oslo'}))

    def test_nonexisting_wikidata_is_not_malformed(self):
        self.assertEqual (None, self.issue_reporter().critical_structural_issue_report('node', {'wikipedia': 'en:Oslo'}))

    def test_well_formed_nonexisting_wikidata(self):
        self.assertNotEqual (None, self.issue_reporter().critical_structural_issue_report('node', {'wikidata': 'Q812843783738234723482347238272487927', 'wikipedia': 'en:Oslo'}))

    def test_malformed_wikidata_crash(self):
        self.assertNotEqual (None, self.issue_reporter().critical_structural_issue_report('node', {'wikidata': 'Q81927)', 'wikipedia': 'en:Oslo'}))

    def test_complain_function(self):
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        self.issue_reporter().complain_in_stdout_if_wikidata_entry_not_of_known_safe_type('Q824359', "explanation")

    def test_description_of_distance_return_string(self):
        example_city_wikidata_id = 'Q31487'
        self.assertEqual(type(""), type(self.issue_reporter().get_distance_description_between_location_and_wikidata_id((50, 20), example_city_wikidata_id)))

    def test_description_of_distance_return_string_for_missing_location(self):
        example_city_wikidata_id = 'Q31487'
        self.assertEqual(type(""), type(self.issue_reporter().get_distance_description_between_location_and_wikidata_id((None, None), example_city_wikidata_id)))

    def test_description_of_distance_return_string_for_missing_location_and_missing_location_in_wikidata(self):
        example_artist_id = 'Q561127'
        self.assertEqual(type(""), type(self.issue_reporter().get_distance_description_between_location_and_wikidata_id((None, None), example_artist_id)))

    def test_description_of_distance_return_string_for_missing_location_in_wikidata(self):
        example_artist_id = 'Q561127'
        self.assertEqual(type(""), type(self.issue_reporter().get_distance_description_between_location_and_wikidata_id((50, 20), example_artist_id)))

    def test_wikidata_ids_of_countries_with_language(self):
        self.assertEqual (['Q36'], self.issue_reporter().wikidata_ids_of_countries_with_language("pl"))
        self.assertEqual (('Q408' in self.issue_reporter().wikidata_ids_of_countries_with_language("en")), True)

    def test_that_completely_broken_wikipedia_tags_are_detected(self):
        self.assertEqual (True, self.issue_reporter().is_wikipedia_tag_clearly_broken("pl"))
        self.assertEqual (True, self.issue_reporter().is_wikipedia_tag_clearly_broken("polski:Smok"))

    def test_that_completely_broken_wikipedia_tag_detector_has_no_false_positives(self):
        self.assertEqual (False, self.issue_reporter().is_wikipedia_tag_clearly_broken("pl:smok"))

    def test_detector_of_old_style_wikipedia_links_accepts_valid(self):
        key = 'wikipedia:pl'
        self.assertEqual (True, self.issue_reporter().check_is_it_valid_key_for_old_style_wikipedia_tag(key))
        tags = {key: 'Kościół Najświętszego Serca Pana Jezusa'}
        self.assertEqual (None, self.issue_reporter().check_is_invalid_old_style_wikipedia_tag_present(tags, tags))

    def test_detector_of_old_style_wikipedia_links_refuses_invalid(self):
        key = 'wikipedia:fixme'
        self.assertEqual (False, self.issue_reporter().check_is_it_valid_key_for_old_style_wikipedia_tag(key))
        tags = {key: 'Kościół Najświętszego Serca Pana Jezusa'}
        self.assertNotEqual (None, self.issue_reporter().check_is_invalid_old_style_wikipedia_tag_present(tags, tags))

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
            count+=1
            is_animal = False
            for type_id in wikidata_processing.get_all_types_describing_wikidata_object(wikidata_id, self.issue_reporter().ignored_entried_in_wikidata_ontology()):
                potential_failure = self.issue_reporter().get_reason_why_type_makes_object_invalid_primary_link(type_id)
                if potential_failure == None:
                    continue
                if potential_failure['what'] != 'an animal or plant':
                    self.issue_reporter().output_debug_about_wikidata_item(wikidata_id)
                    self.assertEqual(potential_failure['what'], 'an animal or plant')
                is_animal = True
                break
            if is_animal != True:
                print(wikidata_id, " not recognized as an animal!")
                print("fix wikimedia_link_issue_reporter or fix wikidata and flush cache (wikimedia-connection-cache/wikidata_by_id/<wikidata_id>.wikidata_entity.txt)")
                self.issue_reporter().output_debug_about_wikidata_item(wikidata_id)
                assert False
        self.assertNotEqual(count, 0)

    def ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary(self, wikidata_id):
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        primary_linkability_status = self.issue_reporter().get_error_report_if_secondary_wikipedia_tag_should_be_used(wikidata_id)
        if primary_linkability_status == None:
            self.issue_reporter().output_debug_about_wikidata_item(wikidata_id)
        self.assertNotEqual (None, primary_linkability_status)

    def test_that_sheep_is_reported_as_an_animal(self):
        self.ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary('Q7368')

    def test_that_goat_is_reported_as_an_animal(self):
        self.ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary('Q2934')

    def test_that_horse_is_reported_as_an_animal(self):
        self.ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary('Q726')

    def test_that_llama_is_reported_as_an_animal(self):
        self.ensure_that_wikidata_id_is_recognized_as_not_linkable_as_primary('Q42569')

    def test_that_linking_to_human_is_reported_before_missing_wikipedia_tag(self):
        tags = {"wikipedia": "en:Stanislav Petrov"}
        location = None
        object_type = 'way'
        object_description = "fake test object"
        problem = self.issue_reporter().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        self.assertNotEqual (None, problem)
        self.assertNotEqual ('wikidata from wikipedia tag', problem.data()['error_id'])
        self.assertEqual ("should use a secondary wikipedia tag - linking to a human", problem.data()['error_id'])

    def test_that_linking_to_human_is_reported_from_reordeable_issues(self):
        tags = {"wikipedia": "en:Stanislav Petrov"}
        location = None
        object_description = "fake test object"
        problem = self.issue_reporter().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual (None, problem)
        self.assertEqual ("should use a secondary wikipedia tag - linking to a human", problem.data()['error_id'])

    def test_that_linking_to_human_is_reported_from_reordeable_issues_specified_as_wikidata(self):
        tags = {"wikidata": "Q52412"}
        location = None
        object_description = "fake test object"
        problem = self.issue_reporter().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual (None, problem)
        self.assertEqual ("should use a secondary wikipedia tag - linking to a human", problem.data()['error_id'])

    def test_that_linking_to_human_is_reported_based_on_wikidata(self):
        wikidata_id = "Q52412"
        location = None
        object_description = "fake test object"
        problem = self.issue_reporter().get_problem_based_on_wikidata_and_osm_element(object_description, location, wikidata_id)
        self.assertNotEqual (None, problem)
        self.assertEqual ("should use a secondary wikipedia tag - linking to a human", problem.data()['error_id'])

    def test_effective_wikipedia(self):
        tags = {"wikidata": "Q52412"}
        wikipedia = self.issue_reporter().get_effective_wikipedia_tag(tags)
        self.assertEqual("en:Stanislav Petrov", wikipedia)

    def test_effective_wikidata(self):
        tags = {"wikipedia": "en:Stanislav Petrov"}
        wikidata = self.issue_reporter().get_effective_wikidata_tag(tags)
        self.assertEqual("Q52412", wikidata)

    def test_576_in_future(self):
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        self.assertEqual(self.issue_reporter().check_is_object_is_existing('Q650270'), None)
        

if __name__ == '__main__':
    unittest.main()
